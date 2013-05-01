import pprint

from django.shortcuts import render
from django.views.decorators.cache import cache_page

from mongo_access import get_asset, get_status_counts
from mysql_access import is_partner_program


def index(request):
    return render(request, 'mongo_status/index.html', {'status_counts': get_status_counts()})

def get_status(request):
    asset = None
    response_dict = {'query_value':request.GET['assetId'],
                     'is_partner_program':is_partner_program(int(request.GET['assetId'])),
                     'status_counts': get_status_counts()}
    try:
        assetId = int(request.GET['assetId'])
        asset = get_asset(assetId)
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
