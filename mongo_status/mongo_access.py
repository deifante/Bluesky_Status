from django.core.cache import cache

from pymongo import Connection

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

    counts = {'complete'  : assets_collection.find({'partnerData.getty.status':'complete'}, slave_okay=True, await_data=False).count(),
              'error'     : assets_collection.find({'partnerData.getty.status':'error'}, slave_okay=True, await_data=False).count(),
              'pending'   : assets_collection.find({'partnerData.getty.status':'pending'}, slave_okay=True, await_data=False).count(),
              'processing': assets_collection.find({'partnerData.getty.status':'processing'}, slave_okay=True, await_data=False).count()}
    counts['undetermined'] = total - counts['complete'] - counts['error'] - counts['pending'] - counts['processing']
    counts['total'] = total
    cache.set('mongo_get_status_counts', counts, 60 * 5)
    return counts
