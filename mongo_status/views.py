import pprint

from django.shortcuts import render

from Bluesky_Status.settings import MONGO_HOST
from mongo_access import MongoAccess
from mysql_access import is_partner_program

from mongo_status.models import StatusCount, DetailedStatus

def index(request):
    """
    Retrieves the most recent status counts for the configured connection.

    The data used to be queried from Mongo on request until I was annoyed
    @ how long it takes. Now the data collation process is done via cron.
    Now all this has to do is retrieve results via models.
    """
    status_counts = StatusCount.objects.filter(connection=MONGO_HOST).latest()
    return render(request, 'mongo_status/index.html', {'status_counts': status_counts})

def get_status(request):
    """
    Get detailed information on a specific file ID.
    """
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
    """
    Get detailed information on a particular status.
    """
    status_details = DetailedStatus.objects.filter(connection=MONGO_HOST, status=status).latest()
    response_dict = {'status': status, 'status_details': status_details}
    return render(request, 'mongo_status/status_details.html', response_dict)
