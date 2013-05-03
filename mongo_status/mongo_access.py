import datetime

from django.core.cache import cache

from pymongo import Connection, ASCENDING, DESCENDING

def get_assets_collection():
    # connection = Connection('10.2.241.213')
    connection = Connection('cf-mongo3.istockphoto.com')
    bluesky_database = connection.bluesky
    return bluesky_database.assets

def get_asset(assetId):
    assets_collection = get_assets_collection()
    return assets_collection.find_one({'assetId':assetId})

def get_status_counts():
    cached_status_counts = cache.get('mongo_get_status_counts')
    if cached_status_counts:
        return cached_status_counts

    assets_collection = get_assets_collection()
    total = assets_collection.count();

    counts = \
        {'generation_time': datetime.datetime.now().strftime('%A %B %d %Y %H:%M:%S'),
         'complete'  : assets_collection.find({'partnerData.getty.status':'complete'}, slave_okay=True, await_data=False).count(),
         'error'     : assets_collection.find({'partnerData.getty.status':'error'}, slave_okay=True, await_data=False).count(),
         'pending'   : assets_collection.find({'partnerData.getty.status':'pending'}, slave_okay=True, await_data=False).count(),
         'processing': assets_collection.find({'partnerData.getty.status':'processing'}, slave_okay=True, await_data=False).count()}
    counts['undetermined'] = total - counts['complete'] - counts['error'] - counts['pending'] - counts['processing']
    counts['total'] = total
    cache.set('mongo_get_status_counts', counts, 60 * 14)
    return counts

def get_status_details(status):
    assets_collection = get_assets_collection()
    status_details = \
        {'generation_time'  : datetime.datetime.now().strftime('%A %B %d %Y %H:%M:%S'),
         'total'            : assets_collection.find({'partnerData.getty.status':status}, slave_okay=True, await_data=False).count(),
         'updates'          : assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 0,  '$lte': 4}}, slave_okay=True, await_data=False).count(),
         'new'              : assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 10, '$lte': 14}}, slave_okay=True, await_data=False).count(),
         'special'          : assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 40, '$lte': 44}}, slave_okay=True, await_data=False).count(),
         'delete'           : assets_collection.find({'partnerData.getty.status':status, 'priority':{'$gte': 50, '$lte': 54}}, slave_okay=True, await_data=False).count(),
         'legacy_migration' : assets_collection.find({'partnerData.getty.status':status, 'partnerData.getty.legacyMigration':{'$exists':True}}, slave_okay=True, await_data=False).count(),
         'migrated'         : assets_collection.find({'partnerData.getty.status':status, 'partnerData.getty.migrated':{'$exists':True}}, slave_okay=True, await_data=False).count(),
         'hand_selected'    : assets_collection.find({'partnerData.getty.status':status, 'partnerData.getty.handSelected':{'$exists':True}}, slave_okay=True, await_data=False).count(),
         }

    try:
        status_details['oldest'] = assets_collection.find({'partnerData.getty.status':status, 'version':{'$exists':True}},
                                                          fields={'_id':False, 'assetId':True, 'version':True},
                                                          sort=[('version', ASCENDING)], limit=1, slave_okay=True, await_data=False)[0]
    except IndexError:
        status_details['oldest'] = {'assetId': None, 'date': None, 'version':None}
    if status_details['oldest']['version']:
        status_details['oldest']['date'] = datetime.datetime.fromtimestamp(int(status_details['oldest']['version'])).strftime('%A %B %d %Y %H:%M:%S')

    try:
        status_details['newest'] = assets_collection.find({'partnerData.getty.status':status, 'version':{'$exists':True}},
                                                          fields={'_id':False, 'assetId':True, 'version':True},
                                                          sort=[('version', DESCENDING)], limit=1, slave_okay=True, await_data=False)[0]
    except IndexError:
        status_details['newest'] = {'assetId': None, 'date': None, 'version':None}
    if status_details['newest']['version']:
        status_details['newest']['date'] = datetime.datetime.fromtimestamp(int(status_details['newest']['version'])).strftime('%A %B %d %Y %H:%M:%S')
    return status_details
