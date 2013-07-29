import re
import json
import time
import Queue
import threading
import datetime

import dateutil.parser # cute util for dealing with splunk dates
import splunklib.client as client
import splunklib.results as results
from django.conf import settings

class SplunkAccess:
    """
    Small class for retrieving logged information.

    The information stored in splunk is process flow logging. When a file is
    added to the bluesky queue or when data is sent and so on.

   | Thing that happend       | logging message                   |
   |--------------------------+-----------------------------------|
   | file set to pending      | Queued.                           |
   | setAssetStatus (error)   | Received Error.                   |
   | setAssetStatus (success) | Received Success.                 |
   | getAssetData             | 'Sent Metadata.' for each file ID |
   | getAssetDataById         | Sent Metadata by Id.              |
   | generateNewAssetUri      | Sent Uri.                         |
   | File retrieved           | Sent Asset.                       |

   Each log entry has the same format

       Change to Bluesky File. Action: Sent Asset. Asset ID: 11604984 Partner: getty
    """

    # This is more maintenance than I desire. A more automatic solution would be
    # to find the snippet directory via the settings directory then load the
    # valid snippets that way. This way is less processing power per request
    # so it's got that in it's favour.
    VALID_HISTORY_SNIPPETS = ['queued', 'received_error', 'received_success',
                              'sent_asset', 'sent_metadata_by_id', 'sent_metadata',
                              'sent_uri']

    extraction_pattern = re.compile(r'^Change to Bluesky File. Action: (?P<action>.+)Asset ID: (?P<assetId>\d+) Partner: (?P<partner>\w+)')
    def __init__(self, host=None, port=None, username=None, password=None):
        """
        Connect to a splunk instance
        """
        if host == None:
            host = settings.SPLUNK_HOST

        if port == None:
            port = settings.SPLUNK_PORT

        if username == None:
            username = settings.SPLUNK_USERNAME

        if password == None:
            password = settings.SPLUNK_PASSWORD

        self.service = client.connect(host=host, port=port, username=username, password = password)

    def make_history_snippet_slug(self, source_string):
        """
        I originally wanted to have the template just load what ever action was
        there, but unfortunately log data isn't always perfect so some filtering
        is required.
        """
        history_template = source_string.strip().lower().replace('.','').replace(' ', '_')
        if history_template in SplunkAccess.VALID_HISTORY_SNIPPETS:
            return "mongo_status/history_snippets/%s.html" % history_template
        return None

    def get_most_recent_action(self, assetId):
        """
        Returns a dict indicating the last recored thing that happened with this file
        """
        kwargs_oneshot = {'output_mode':'json'}
        # I only want one log entry. The most recent one.
        search_query_oneshot = 'search "Change to Bluesky File" "Asset ID: %d" | head 1' % assetId
        oneshot_results = self.service.jobs.oneshot(search_query_oneshot, **kwargs_oneshot)
        temp = str(oneshot_results)

        try:
            oneshot_json = json.loads(temp.strip())
        except ValueError: # Error decoding
            return None

        sub_index = oneshot_json[0]['_raw'].find('Change to Bluesky File')
        original_string  = oneshot_json[0]['_raw'][sub_index:].strip()
        m = SplunkAccess.extraction_pattern.search(original_string)
        log_time = dateutil.parser.parse(oneshot_json[0]['_time'])
        return {
            'action'          :m.group('action').strip(),
            'assetId'         :m.group('assetId'),
            'partner'         :m.group('partner'),
            'log_time'        :log_time,
            'history_snippet' :self.make_history_snippet_slug(m.group('action'))
            }

    def get_actions(self, assetId, earliest_time = None):
        """
        Originally meant to retrieve all events found in splunk for a specific asset ID
        this started taking too long so it now has a non-default time window and
        a default max_time of 7 seconds. The 7 second time out is just pulled out of the
        air and might be tuned later.
        """
        kwargs_oneshot = {'output_mode':'json', 'max_time':7}

        if earliest_time:
            kwargs_oneshot['earliest_time'] = earliest_time.isoformat()

        search_query_oneshot = 'search "Change to Bluesky File" "Asset ID: %d"' % assetId
        oneshot_results = self.service.jobs.oneshot(search_query_oneshot, **kwargs_oneshot)
        temp = str(oneshot_results)

        try:
            oneshot_json = json.loads(temp.strip())
        except ValueError: # Error decoding
            return None

        all_actions = []
        for result in oneshot_json:
            sub_index = result['_raw'].find('Change to Bluesky File')
            original_string = result['_raw'][sub_index:].strip()
            m = SplunkAccess.extraction_pattern.search(original_string)
            log_time = dateutil.parser.parse(result['_time'])
            all_actions.append({
                    'action'          :m.group('action').strip(),
                    'assetId'         :m.group('assetId'),
                    'partner'         :m.group('partner'),
                    'log_time'        :log_time,
                    'history_snippet' :self.make_history_snippet_slug(m.group('action'))
                    })

        return all_actions

class ThreadedSplunkSearch(threading.Thread):
    """Threaded Splunk Results Retrieval"""

    extraction_pattern = SplunkAccess.extraction_pattern

    def __init__(self, queue, splunk_service):
        """Just get some storage variables and init the threading"""
        threading.Thread.__init__(self)
        self.queue = queue
        self.splunk_service = splunk_service

    def run(self):
        """
        This function is called by the threading library code after start() is
        called on this object. I probably wouldn't need the while loop if I
        loaded the queue before starting the workers.
        """
        while True:
            job_specs = self.queue.get()
            self.search_string = job_specs['search_string']
            # Besides the search_string key, I expect the job to be
            # search parameters for a ResultsSpitter::start_search.
            del job_specs['search_string']
            # This line starts the actual async searching jobs
            self.start_search(**job_specs)
            # Spin while the search job isn't done
            while not self.job.is_done():
                # I'm not super fond of this but total execution
                # times are in minutes right now.
                time.sleep(1)
            self.store_results()
            self.queue.task_done()

    def start_search(self, latest_time = None, earliest_time = None):
        """
        Get splunk started on a search.
        Both dates can be a standard python datetime.datetime or a string in ISO 8601 format

        latest_time: the time closest to now. The higher number.
        earliest_time: the time closest to the start of time. The lower number.
        """
        # Cutting the ttl super low cause I'd been running out of search space
        # on the splunk server and it's not seeming to affect the #'s so far.
        search_kwargs = {'exec_mode':'normal', 'ttl':30}
        if latest_time:
            if type(latest_time) == datetime.datetime:
                search_kwargs['latest_time'] = latest_time.isoformat()
            else:
                search_kwargs['latest_time'] = latest_time

        if earliest_time:
            if type(earliest_time) == datetime.datetime:
                search_kwargs['earliest_time'] = earliest_time.isoformat()
            else:
                search_kwargs['earliest_time'] = earliest_time

        self.job = self.splunk_service.jobs.create(self.search_string, **search_kwargs)

    def store_results(self):
        """
        Fetch the results from splunk

        Fetchs the results from splunk (inlcuding results on multiple pages),
        processes json data into something useful and get a few metrics on the data.
        """
        self.search_results = []
        search_results = []
        # I originally wanted this to be max of the server, but then I found that I would get an empty
        # json response on the 10th consecutive call. I'm still not sure of the reason.
        result_fetch_count = 49123
        result_fetch_offest = 0

        # eventCount should be the total number of matches found on splunk.
        self.total_events = int(self.job['eventCount'])
        # I'm not sure why I got better results using a dictionary to pass the keyword args
        kwargs_paginate = {'output_mode':'json', 'ttl':30}

        try:
            # Start retrieving json results from splunk
            while result_fetch_offest < self.total_events:
                kwargs_paginate['count'] = result_fetch_count
                kwargs_paginate['offset'] = result_fetch_offest
                # Not sure why I had to explicitly convert the results to string when
                # the return type was meant to be json. The results are returned as
                # a list of elements so they add together nicely
                search_results += json.loads(str(self.job.results(**kwargs_paginate)))
                result_fetch_offest += result_fetch_count

        except ValueError as e:
            # good chance there's no results
            # probably a 'no JSON object could be decoded' error
            # This was also occuring on the 10th request when paging
            # results with a step of 50 000
            if len(search_results) == 0:
                return
            # If we have results, just continue on with what we have.

        # Now that we have the actual results we have to parse out the event data.
        for search_result in search_results:
            # the _raw element has the actual logged line. Everything
            # after "Change to Bluesky File" has the actual information.
            sub_index = search_result['_raw'].find('Change to Bluesky File')

            # use some regex fun to pull out the data from the surrounding
            # info to make it human readable.
            original_string = search_result['_raw'][sub_index:].strip()
            m = ThreadedSplunkSearch.extraction_pattern.search(original_string)

            # _time holds the time when the log message was made
            log_time = dateutil.parser.parse(search_result['_time'])
            self.search_results.append({
                'action':m.group('action').strip(),
                'assetId':int(m.group('assetId')),
                'partner':m.group('partner'),
                'log_time':log_time
                })

    def get_unique_ids(self):
        """
        Get the unique file Id's found in this search.
        """
        # Use the fact that there are no duplicates allowed in sets
        # to make a set comprehension with only unique file ids
        return {int(x['assetId']) for x in self.search_results}

    def __str__(self):
        """Provide the search query"""
        return self.search_string

    def __len__(self):
        """The total number of matched events"""
        return int(self.total_events)
