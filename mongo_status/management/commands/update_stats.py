from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from mongo_status.mongo_access import MongoAccess

class Command(BaseCommand):
    help = 'Takes a StatusCount data sample for persistant storage'
    option_list = BaseCommand.option_list + (
        make_option('-o', '--host', action='store', dest='host',
                    default=settings.MONGO_HOST, help='The mongo host to query.'),
        )

    def handle(self, *args, **options):
        """
        Take a snapshot of the basic stats from the specified host.

        Make sure not to use cache when calling get_status_counts or it'll
        might not actually read from mongo.

        The host option has been set up so it's always safe to just toss that
        parameter in.
        """
        mongo_access = MongoAccess(options['host'])
        mongo_access.get_status_counts(use_cache=False)
