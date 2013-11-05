#! /usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import Queue
from optparse import make_option

import dateutil.parser
import splunklib.client as client
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mongo_status.models import SentAssetSummary
from mongo_status.splunk_access import ThreadedSplunkSearch
from mongo_status.mysql_access import AbstractFile

class Command(BaseCommand):
    args = '<day>'
    help =  """Creates a summary for the files that were transferred in a day.

    The Day should be YYYY-MM-DD format.
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

        previously_existing_summaries = SentAssetSummary.objects.filter(day=day, connection=options['host'])
        if (not options['force_overwrite']) and previously_existing_summaries:
            # If we didn't use -f and there's already something there, fail and inform
            self.stderr.write('There is already a sent asset summary for %s on %s. Use -f to force overwrite.' % (day.strftime('%Y-%m-%d'), options['host']))
            return

        # Create a Splunk Service instance and log in
        service = client.connect(host=options['host'], port=options['port'],
                                 username=options['username'], password=options['password'])

        # This threading process is now probably overkill. We're only doing
        # one search on splunk.
        job_queue = Queue.Queue()
        summariser = ThreadedSplunkSearch(job_queue, service)
        summariser.setDaemon(True)
        # Start it spinning right away.
        summariser.start()

        latest_time = day + datetime.timedelta(1)
        # Populate the queue with data
        job_queue.put({
                'search_string' : 'search "Change to Bluesky File" "Sent Asset"',
                'latest_time'   : latest_time,
                'earliest_time' : day
                })

        # wait on the queue until everything has been processed
        job_queue.join()

        search_query = str(summariser)
        unique_ids = list(summariser.get_unique_ids())

        for id in unique_ids:
            abstract_file = AbstractFile.objects.get(id=id)
            create_tuple = SentAssetSummary.objects.get_or_create(
                day=day, connection=options['host'],
                abstract_type_id=abstract_file.abstract_type_id,
                is_exclusive = abstract_file.is_exclusive(),
                taxonomy_id = abstract_file.collection_number()
            )
            # false means it already existed. increment the count
            if create_tuple[1] == False:
                create_tuple[0].count += 1
            else:
                create_tuple[0].count = 1
            create_tuple[0].save()
        return
