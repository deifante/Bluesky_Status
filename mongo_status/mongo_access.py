import datetime

from pymongo import Connection, ASCENDING, DESCENDING

from django.core.cache import cache
from django.conf import settings

from mongo_status.models import StatusCount, DetailedStatus, BasicStatus

class MongoAccess:
    """
    Simple class for getting the information I want out of mongo.
    """

    def __init__(self, connection_ip = None):
        """
        Connect to mongo and get a reference to the assets collection.

        I wanted to default connection_ip to settings.MONGO_HOST but it
        was causing problems during testing.
        """
        # Connection is 'deprecated' on the online pymongo docs, but the
        # replacement class MongoClient, doesn't seem to be available for me
        # so I guess we use the one that we can work with.
        if connection_ip == None:
            connection_ip = settings.MONGO_HOST

        self.connection = Connection(host=connection_ip)
        self.get_assets_collection()

    def get_assets_collection(self):
        """
        Make a local reference to the assets collection and return it just for
        luls.
        """
        self.assets_collection = self.connection.bluesky.assets
        return self.assets_collection

    def get_asset(self, assetId):
        """
        Provide the raw data from mongo from a particular asset.
        """
        return self.assets_collection.find_one({'assetId':assetId})

    def get_status_counts(self, use_cache = True):
        """
        There are 4 statuses that records are meant to be in the assets
        collection, complete, error, pending and processing.

        Any thing else is classified as 'undetermined'. These queries are made
        on a system in flux so all the numbers may not add up very nicely.

        Right now this data is cached for 14 min because it takes a little
        while to get this data and it's probably not a good idea to be stressing
        systems with simple reporting when they have 'real' work to do.

        There is a direct cache control on this method because more than one
        view uses this method. It is also used for generating data points
        separate from web requests.
        """
        cached_status_counts = cache.get('mongo_get_status_counts')
        if cached_status_counts and use_cache:
            return cached_status_counts

        total = self.assets_collection.count();

        counts = \
            {'generation_time': datetime.datetime.now().strftime('%A %B %d %Y %H:%M:%S'),
             'complete'  : self.assets_collection.find({'partnerData.getty.status':'complete'}, slave_okay=True, await_data=False).count(),
             'error'     : self.assets_collection.find({'partnerData.getty.status':'error'}, slave_okay=True, await_data=False).count(),
             'pending'   : self.assets_collection.find({'partnerData.getty.status':'pending'}, slave_okay=True, await_data=False).count(),
             'processing': self.assets_collection.find({'partnerData.getty.status':'processing'}, slave_okay=True, await_data=False).count()}
        counts['undetermined'] = total - counts['complete'] - counts['error'] - counts['pending'] - counts['processing']
        counts['total'] = total

        status_count = StatusCount(connection = self.connection.host,
            complete = counts['complete'], error = counts['error'],
            pending = counts['pending'], processing = counts['processing'],
            undetermined = counts['undetermined'], total = counts['total'])
        status_count.save()
        cache.set('mongo_get_status_counts', counts, 60 * 14)
        return counts

    def get_status_details(self, status):
        """
        Get detailed information about a particular status.

        Querying for this information takes quite a bit of time, so caching is
        quite necessary. Like with get_status_counts, these queries are done
        in serial on a system in flux so the numbers may not add up nicely.
        """
        status_details = \
            {'generation_time'  : datetime.datetime.now().strftime('%A %B %d %Y %H:%M:%S'),
             'total'            : self.assets_collection.find({'partnerData.getty.status':status}, slave_okay=True, await_data=False).count(),
             'updates'          : self.assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 0,  '$lte': 4}}, slave_okay=True, await_data=False).count(),
             'new'              : self.assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 10, '$lte': 14}}, slave_okay=True, await_data=False).count(),
             'special'          : self.assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 40, '$lte': 44}}, slave_okay=True, await_data=False).count(),
             'delete'           : self.assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 50, '$lte': 54}}, slave_okay=True, await_data=False).count(),
             'legacy_migration' : self.assets_collection.find({'partnerData.getty.status':status, 'partnerData.getty.legacyMigration':{'$exists':True}}, slave_okay=True, await_data=False).count(),
             'migrated'         : self.assets_collection.find({'partnerData.getty.status':status, 'partnerData.getty.migrated':{'$exists':True}}, slave_okay=True, await_data=False).count(),
             'hand_selected'    : self.assets_collection.find({'partnerData.getty.status':status, 'partnerData.getty.handSelected':{'$exists':True}}, slave_okay=True, await_data=False).count(),
             }

        try:
            status_details['oldest'] = self.assets_collection.find({'partnerData.getty.status':status, 'version':{'$exists':True}},
                                                                   fields={'_id':False, 'assetId':True, 'version':True},
                                                                   sort=[('version', ASCENDING)], limit=1, slave_okay=True, await_data=False)[0]
        except IndexError:
            status_details['oldest'] = {'assetId': None, 'date': None, 'version':None}
        if status_details['oldest']['version']:
            status_details['oldest']['date'] = datetime.datetime.fromtimestamp(int(status_details['oldest']['version'])).strftime('%A %B %d %Y %H:%M:%S')

        try:
            status_details['newest'] = self.assets_collection.find({'partnerData.getty.status':status, 'version':{'$exists':True}},
                                                                   fields={'_id':False, 'assetId':True, 'version':True},
                                                                   sort=[('version', DESCENDING)], limit=1, slave_okay=True, await_data=False)[0]
        except IndexError:
            status_details['newest'] = {'assetId': None, 'date': None, 'version':None}
        if status_details['newest']['version']:
            status_details['newest']['date'] = datetime.datetime.fromtimestamp(int(status_details['newest']['version'])).strftime('%A %B %d %Y %H:%M:%S')

        detailed_status = DetailedStatus(
            status = status, connection = self.connection.host,
            total = status_details['total'],updates = status_details['updates'],
            new = status_details['new'],special = status_details['special'],
            delete = status_details['delete'],
            legacy_migration = status_details['legacy_migration'],
            migrated = status_details['migrated'],
            hand_selected = status_details['hand_selected'],
            oldest = status_details['oldest']['assetId'] if status_details['oldest']['assetId'] else 0,
            newest = status_details['newest']['assetId'] if status_details['newest']['assetId'] else 0,
            )
        detailed_status.save()
        return status_details

    def get_basic_counts(self):
        """
        Get a simple view of the Bluesky queue.

        This data will provide a quick way to see what is actually queued and
        ready to go out from Bluesky. This is different from adding all the
        records that have a particular status because of special cases here and
        there.

        Getting all this information takes on the order of 100 seconds. It is
        not recommened for a web request. The results will be logged an the
        data used later.
        """
        basic_counts = \
            {
            'update' : self.assets_collection.find({'partnerData.getty.status':'pending', 'partnerData.getty.legacyMigration': {'$exists':False}, 'partnerData.getty.migrated':{'$exists':False}, 'priority':{'$gte':0,  '$lte':14}}, slave_okay=True, await_data=True).count(),
            'new'    : self.assets_collection.find({'partnerData.getty.status':'pending', 'partnerData.getty.legacyMigration': {'$exists':False}, 'partnerData.getty.migrated':{'$exists':False}, 'priority':{'$gte':10, '$lte':14}}, slave_okay=True, await_data=True).count(),
            'delete' : self.assets_collection.find({'partnerData.getty.status':'pending', 'partnerData.getty.legacyMigration': {'$exists':False}, 'partnerData.getty.migrated':{'$exists':False}, 'priority':{'$gte':50, '$lte':54}}, slave_okay=True, await_data=True).count()
            }

        basic_count = BasicStatus.objects.create(
            update = basic_counts['update'], new = basic_counts['new'],
            delete = basic_counts['delete'],connection = self.connection.host
            )
        return basic_count
            
