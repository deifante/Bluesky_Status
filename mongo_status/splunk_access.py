import json
import re

import dateutil.parser

import splunklib.client as client
import splunklib.results as results

from django.conf import settings

class SplunkAccess:
    """
    Small class for retrieving logged information.

    The information stored in splunk is process flow logging. When a file is added to the bluesky queue or when data is sent and so on.

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
        extraction_string = r'^Change to Bluesky File. Action: (?P<action>.+)Asset ID: (?P<assetId>\d+) Partner: (?P<partner>\w+)'
        self.extraction_pattern = re.compile(extraction_string)

    def make_history_snippet_slug(self, source_string):
        return "mongo_status/history_snippets/%s.html" % source_string.strip().lower().replace('.','').replace(' ', '_')

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
        m = self.extraction_pattern.search(original_string)
        log_time = dateutil.parser.parse(oneshot_json[0]['_time'])
        return {
            'action'          :m.group('action').strip(),
            'assetId'         :m.group('assetId'),
            'partner'         :m.group('partner'),
            'log_time'        :log_time,
            'history_snippet' :self.make_history_snippet_slug(m.group('action'))
            }

    def get_all_actions(self, assetId):
        kwargs_oneshot = {'output_mode':'json'}
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
            m = self.extraction_pattern.search(original_string)
            log_time = dateutil.parser.parse(result['_time'])
            all_actions.append({
                    'action'          :m.group('action').strip(),
                    'assetId'         :m.group('assetId'),
                    'partner'         :m.group('partner'),
                    'log_time'        :log_time,
                    'history_snippet' :self.make_history_snippet_slug(m.group('action'))
                    })

        return all_actions
