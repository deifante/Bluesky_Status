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
    assets_collection = get_assets_collection()
    total = assets_collection.count();

    counts = {'complete'  : assets_collection.find({'partnerData.getty.status':'complete'}).count(),
              'error'     : assets_collection.find({'partnerData.getty.status':'error'}).count(),
              'pending'   : assets_collection.find({'partnerData.getty.status':'pending'}).count(),
              'processing': assets_collection.find({'partnerData.getty.status':'processing'}).count()}
    counts['undetermined'] = total - counts['complete'] - counts['error'] - counts['pending'] - counts['processing']
    counts['total'] = total
    return counts
