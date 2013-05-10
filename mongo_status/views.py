import pprint

from django.shortcuts import render
from django.views.decorators.cache import cache_page

from mongo_access import MongoAccess
from mysql_access import is_partner_program

def index(request):
    mongo_access = MongoAccess()
    return render(request, 'mongo_status/index.html', {'status_counts': mongo_access.get_status_counts()})

def get_status(request):
    asset = None
    mongo_access = MongoAccess()
    response_dict = {'query_value':request.GET['assetId'],
                     'is_partner_program':is_partner_program(int(request.GET['assetId'])),
                     'status_counts': mongo_access.get_status_counts()}
    try:
        assetId = int(request.GET['assetId'])
        asset = mongo_access.get_asset(assetId)
        response_dict['asset'] = asset

        if asset and asset['partnerData']['getty']['status'] in ['processing', 'pending', 'complete', 'error']:
            response_dict['status_snippet'] = 'mongo_status/asset_snippets/%s.html' % asset['partnerData']['getty']['status'];
    except ValueError:
        pass
    except KeyError:
        # Probably caused by a 'non-standard' record and not checking every dictionary key on the asset.
        # Not a huge deal if we're just missing the status snippet.
        pass

    if asset:
        pretty_asset = pprint.pformat(asset)
        response_dict['pretty_asset'] = pretty_asset

    return render(request, 'mongo_status/index.html', response_dict)

def complete_details(request, status):
    mongo_access = MongoAccess()
    response_dict = {'status': status, 'status_details': mongo_access.get_status_details(status)}
    return render(request, 'mongo_status/status_details.html', response_dict)
