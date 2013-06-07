import pprint

from django.shortcuts import render

from django.conf import settings
from mongo_access import MongoAccess
from mysql_access import is_partner_program
from oracle_access import get_teams_reporting_data

from mongo_status.models import StatusCount, DetailedStatus

def index(request):
    """
    Retrieves the most recent status counts for the configured connection.

    The data used to be queried from Mongo on request until I was annoyed
    @ how long it takes. Now the data collation process is done via cron.
    Now all this has to do is retrieve results via models.
    """
    try:
        status_counts = StatusCount.objects.filter(connection=settings.MONGO_HOST).latest()
    except StatusCount.DoesNotExist:
        status_counts = None
    historical_status = StatusCount.objects.filter(connection=settings.MONGO_HOST).order_by('-generation_time')
    return render(request, 'mongo_status/index.html',
                  {'status_counts': status_counts,
                   'historical_status':historical_status})

def get_status(request):
    """
    Get detailed information on a specific file ID.
    """
    asset = None
    mongo_access = MongoAccess()
    historical_status = StatusCount.objects.filter(connection=settings.MONGO_HOST).order_by('-generation_time')

    try:
        # if we happen to be in this view without the assumed get param
        assetId = int(request.GET['assetId'])
    except KeyError:
        assetId = 0

    try:
        # This can happen on an empty datastore
        status_counts = StatusCount.objects.filter(connection=settings.MONGO_HOST).latest()
    except StatusCount.DoesNotExist:
        status_counts = None

    response_dict = {'query_value'          :assetId,
                     'is_partner_program'   :is_partner_program(assetId),
                     'teams_reporting_data' :get_teams_reporting_data(assetId),
                     'status_counts'        :status_counts,
                     'historical_status'    :historical_status}
    try:
        asset = mongo_access.get_asset(assetId)
        response_dict['asset'] = asset

        if asset and asset['partnerData']['getty']['status'] in ['processing', 'pending', 'complete', 'error']:
            response_dict['status_snippet'] = 'mongo_status/asset_snippets/%s.html' % asset['partnerData']['getty']['status'];
    except ValueError:
        asset = None
    except KeyError:
        # Probably caused by a 'non-standard' record and not checking every dictionary key on the asset.
        # Not a huge deal if we're just missing the status snippet.
        asset = None

    if asset:
        pretty_asset = pprint.pformat(asset)
        response_dict['pretty_asset'] = pretty_asset

    return render(request, 'mongo_status/index.html', response_dict)

def complete_details(request, status):
    """
    Get detailed information on a particular status.
    """
    try:
        status_details = DetailedStatus.objects.filter(connection=settings.MONGO_HOST, status=status).latest()
    except DetailedStatus.DoesNotExist:
        status_details = None
    # I'm not super convinced that I want all of them,
    # but for now there's not that much data
    historical_data = DetailedStatus.objects.filter(connection=settings.MONGO_HOST, status=status).order_by('-generation_time')
    response_dict = {'status': status, 'status_details': status_details, 'historical_data': historical_data}
    return render(request, 'mongo_status/status_details.html', response_dict)
