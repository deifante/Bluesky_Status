import pprint
import datetime

from django.conf import settings
from django.shortcuts import render
from django.views.generic.dates import ArchiveIndexView
from mongo_access import MongoAccess
from mysql_access import is_partner_program
from oracle_access import get_teams_reporting_data
from splunk_access import SplunkAccess

from mongo_status.models import StatusCount, DetailedStatus, BasicStatus, DaySummary

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
    basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).latest()
    historical_basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).order_by('-generation_time')
    return render(request, 'mongo_status/index.html',
                  {'status_counts':status_counts,
                   'historical_basic_status': historical_basic_status,
                   'basic_status':basic_status,
                   'historical_status':historical_status})

def get_status(request):
    """
    Get detailed information on a specific file ID.
    """
    asset = None
    mongo_access = MongoAccess()
    historical_status = StatusCount.objects.filter(connection=settings.MONGO_HOST).order_by('-generation_time')
    basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).latest()
    historical_basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).order_by('-generation_time')

    try:
        # if we happen to be in this view without the assumed get param
        assetId = int(request.GET['assetId'])
    except KeyError: # no get param
        assetId = 0
    except ValueError: # not an int
        assetId = 0

    splunk_access = SplunkAccess()
    # cause splunk kinda takes a long time if I search for everything
    # I'm just gonna do the previous 2 weeks and make a separate page
    # for retrieving *all* the actions from splunk for those
    # that are willing to wait.
    two_weeks_ago = datetime.datetime.now() + datetime.timedelta(-14)
    all_splunk_actions = splunk_access.get_actions(assetId, two_weeks_ago)

    try:
        # This can happen on an empty datastore
        status_counts = StatusCount.objects.filter(connection=settings.MONGO_HOST).latest()
    except StatusCount.DoesNotExist:
        status_counts = None

    response_dict = {'query_value'            : assetId,
                     'is_partner_program'     : is_partner_program(assetId),
                     'teams_reporting_data'   : get_teams_reporting_data(assetId),
                     'status_counts'          : status_counts,
                     'historical_basic_status': historical_basic_status,
                     'basic_status'           : basic_status,
                     'most_recent_action'     : all_splunk_actions[0] if all_splunk_actions else None,
                     'all_splunk_actions'     : all_splunk_actions,
                     'historical_status'      : historical_status}
    try:
        asset = mongo_access.get_asset(assetId)
        response_dict['asset'] = asset

        if asset and asset['partnerData']['getty']['status'] in \
                ['processing', 'pending', 'complete', 'error']:
            response_dict['status_snippet'] = 'mongo_status/asset_snippets/%s.html' % \
                asset['partnerData']['getty']['status'];
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

def day_summary(request, year, month, day):
    """
    Display the summary for this day.
    Looks good for a generic view, but ended up being longer and more
    complicated looking than the straight forward way.
    """
    day_to_summarise = datetime.datetime(int(year), int(month), int(day))
    day_summary = None
    next_day = None
    prev_day = None

    try:
        day_summary = DaySummary.objects.get(connection=settings.SPLUNK_HOST,
                                             day=day_to_summarise)
    except DaySummary.DoesNotExist:
        pass

    try:
        next_day = DaySummary.objects.get(connection=settings.SPLUNK_HOST,
                                          day=(day_to_summarise + datetime.timedelta(1)))
    except DaySummary.DoesNotExist:
        pass

    try:
        prev_day = DaySummary.objects.get(connection=settings.SPLUNK_HOST,
                                          day=(day_to_summarise - datetime.timedelta(1)))
    except DaySummary.DoesNotExist:
        pass

    response_dict = {
        'day_logged'  :day_to_summarise,
        'day_summary' :day_summary,
        'next_day'    :next_day,
        'prev_day'    :prev_day,
        }
    return render(request, 'mongo_status/day_summary.html', response_dict)

class DaySummariesView(ArchiveIndexView):
    """
    Generic views are classes since django 1.4.
    """
    template_name ='mongo_status/day_summaries.html'
    date_field = 'day'
    queryset = DaySummary.objects.filter(connection=settings.SPLUNK_HOST)
    context_object_name = 'day_summaries'
