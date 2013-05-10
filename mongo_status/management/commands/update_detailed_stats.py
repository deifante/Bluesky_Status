from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from Bluesky_Status.settings import MONGO_HOST
from mongo_status.mongo_access import MongoAccess

class Command(BaseCommand):
    args = '<status>'
    help = 'Takes a DetailedStatus data sample for persistant storage. Status must be one of (pending, processing, complete, error)'
    valid_statuses = ('pending', 'processing', 'complete', 'error')

    option_list = BaseCommand.option_list + (
    make_option('-o', '--host', action='store', dest='host',
                default=MONGO_HOST, help='The mongo host to query.'),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Invalid status try -h for help')

        status = args[0]
        if status not in self.valid_statuses:
            raise CommandError('Invalid status must be one of (pending, processing, complete, error) try -h for help')
        
        mongo_access = MongoAccess(options['host'])
        mongo_access.get_status_details(status)

