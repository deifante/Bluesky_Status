import pprint
import datetime
import Queue
from optparse import make_option

import dateutil.parser
import splunklib.client as client
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mongo_status.models import DaySummary
from mongo_status.splunk_access import ThreadedSplunkSearch

class Command(BaseCommand):
    args = '<day>'
    help = """Creates a summary for the actions of a day

    The day should be YYYY-MM-DD format.
    Day can also be 'yesterday'"""

    option_list = BaseCommand.option_list + (
    make_option('-o', '--host', action='store', dest='host',
                default=settings.SPLUNK_HOST, help='The splunk host to query.'),
    make_option('-r', '--port', action='store', dest='port',
                default=settings.SPLUNK_PORT, help='The splunk port to access.'),
    make_option('-u', '--username', action='store', dest='username',
                default=settings.SPLUNK_USERNAME, help='The username to log into splunk with.'),
    make_option('-p', '--password', action='store', dest='password',
                default=settings.SPLUNK_PASSWORD, help='The password to log into splunk with.'),
    make_option('-f', '--force', action='store_true', dest='force_overwrite',
                default=False, help='Force overwriting of previously stored results.'),
    )

    def handle(self, *args, **options):
        try:
            if 'yesterday' == args[0].lower():
                day = datetime.datetime.now() - datetime.timedelta(1)
            else:
                day = dateutil.parser.parse(args[0])
            # Make sure the date is as clean as I expect.
            # I don't want anything more fine grained than the day
            day = datetime.datetime(day.year, day.month, day.day, tzinfo=day.tzinfo)
        except ValueError as e:
            date_string = args[0] if args[0] else None
            self.stderr.write('Error parsing date "%s" (%s)' % (date_string, str(e)) )
            return
        except IndexError:
            # This guy occurs when there are no command line args passed
            self.stderr.write('Please specify a day (YYYY-MM-DD) or use -h for all options')
            return

        day_summary = None
        # The filter method returns a list but there should be only one matching @ most
        previously_existing_summary = DaySummary.objects.filter(day=day, connection=options['host'])
        if (not options['force_overwrite']) and previously_existing_summary:
            # If we didn't use -f and there's already something there, fail and inform
            self.stderr.write('There is already a summary for %s on %s. Use -f to force overwrite.' % (day.strftime('%Y-%m-%d'), options['host']))
            return

        elif options['force_overwrite'] and previously_existing_summary:
            # if -f was used 'properly' then go ahead and overwrite the pre-existing results
            day_summary = previously_existing_summary[0]

        else:
            # otherwise, continue as normal. create a new DaySummary
            day_summary = DaySummary(day=day, connection=options['host'])

        # Create a Service instance and log in
        service = client.connect(host=options['host'],port=options['port'],
                                 username=options['username'], password=options['password'])

        # The list of searches that we are going to perform.
        search_strings = [
            'search "Change to Bluesky File" "Received Error"',
            'search "Change to Bluesky File" Queued',
            'search "Change to Bluesky File" "Received Success"',
            'search "Change to Bluesky File" "Sent Metadata"',
            'search "Change to Bluesky File" "Sent Asset"'
            ]

        summarisers = []
        job_queue = Queue.Queue()

        # Spawn the working threads. One for each search string.
        # Rotating resources would be cool, but not necessary quite yet.
        for i in range(len(search_strings)):
            summariser = ThreadedSplunkSearch(job_queue, service)
            summariser.setDaemon(True)
            # Start them spinning right away.
            summariser.start()
            summarisers.append(summariser)

        latest_time = day + datetime.timedelta(1)
        # Populate the queue with data
        for search_string in search_strings:
            job_queue.put({
                    'search_string' : search_string,
                    'latest_time'   : latest_time,
                    'earliest_time' : day
                    })

        # wait on the queue until everything has been processed
        job_queue.join()

        for summariser in summarisers:
            search_query = str(summariser)
            if search_query.find('Received Error') != -1:
                day_summary.total_errored = len(summariser)
                day_summary.unique_errored = len(summariser.get_unique_ids())

            elif search_query.find('Queued') != -1:
                day_summary.total_queued = len(summariser)
                day_summary.unique_queued = len(summariser.get_unique_ids())

            elif search_query.find('Received Success') != -1:
                day_summary.total_success = len(summariser)
                day_summary.unique_success = len(summariser.get_unique_ids())

            elif search_query.find('Sent Metadata') != -1:
                day_summary.total_sent_metadata = len(summariser)
                day_summary.unique_sent_metadata = len(summariser.get_unique_ids())

            elif search_query.find('Sent Asset') != -1:
                day_summary.total_sent_asset = len(summariser)
                day_summary.unique_sent_asset = len(summariser.get_unique_ids())
        day_summary.save()
        return
