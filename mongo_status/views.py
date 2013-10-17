import pprint
import datetime
import csv

import django.utils.timezone
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic.dates import ArchiveIndexView
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView

from mysql_access import AbstractFile, User, AgencyContributorXUser
from mongo_access import MongoAccess
from splunk_access import SplunkAccess
from oracle_access import get_teams_reporting_data

from mongo_status.models import StatusCount, DetailedStatus, BasicStatus, DaySummary, SentAssetSummary

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
    # Used to display all history here. Now it's become too much so we're just
    # keeping it to one week now
    one_week_ago = django.utils.timezone.now() - datetime.timedelta(7)
    historical_status = StatusCount.objects.filter(connection=settings.MONGO_HOST).\
                        filter(generation_time__gt=one_week_ago).order_by('-generation_time')
    basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).latest()
    historical_basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).\
                              filter(generation_time__gt=one_week_ago).order_by('-generation_time')

    return render(request, 'mongo_status/index.html',
                  {'status_counts':status_counts,
                   'historical_basic_status': historical_basic_status,
                   'basic_status':basic_status,
                   'historical_status':historical_status})

def complete_queue_status(request):
    """
    Since the front page now only displays a week of history, this view
    will provide all the history we've got @ the cost of a hefty page weight.
    """
    basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).latest()
    historical_basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).\
                              order_by('-generation_time')
    return render(request, 'mongo_status/complete_queue_status.html',
                  {'basic_status':basic_status,
                   'viewing_complete_history': True,
                   'historical_basic_status':historical_basic_status})

def get_status(request):
    """
    Get detailed information on a specific file ID.
    """
    asset = None
    mongo_access = MongoAccess()
    one_week_ago = django.utils.timezone.now() - datetime.timedelta(7)
    historical_status = StatusCount.objects.filter(connection=settings.MONGO_HOST).\
                        filter(generation_time__gt=one_week_ago).order_by('-generation_time')
    basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).latest()
    historical_basic_status = BasicStatus.objects.filter(connection=settings.MONGO_HOST).\
                              filter(generation_time__gt=one_week_ago).order_by('-generation_time')

    try:
        # if we happen to be in this view without the assumed get param
        assetId = int(request.GET['assetId'])
    except KeyError: # no get param
        assetId = 0
    except ValueError: # not an int
        assetId = 0

    splunk_access = SplunkAccess()
    # cause splunk kinda takes a long time if I search for everything
    # I'm just gonna do the previous 30 days and make a separate page
    # for retrieving *all* the actions from splunk for those
    # that are willing to wait.
    thirty_days_ago = datetime.datetime.now() + datetime.timedelta(-30)
    all_splunk_actions = splunk_access.get_actions(assetId, thirty_days_ago)

    try:
        # This can happen on an empty datastore
        status_counts = StatusCount.objects.filter(connection=settings.MONGO_HOST).latest()
    except StatusCount.DoesNotExist:
        status_counts = None

    try:
        # This can happen on an empty datastore
        istock_asset = AbstractFile.objects.get(id=assetId)
    except AbstractFile.DoesNotExist:
        istock_asset = None

    response_dict = {'query_value'            : assetId,
                     'istock_asset'           : istock_asset,
                     'contributor'            : istock_asset.contributor(),
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

    return render(request, 'mongo_status/full_asset.html', response_dict)

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

def yesterdays_day_summary(request):
    """
    Several attempts at making this work via the view only have not worked out
    the way I desire.
    """
    yesterday = django.utils.timezone.now() - datetime.timedelta(1)
    return day_summary(request, yesterday.year, yesterday.month, yesterday.day)

def exclusion_list(request):
    """
    The exclusion list is a list of contributors that will not have any of their files
    go through Bluesky.

    Unfortunately it is split between 2 datastores. The entries in MySql serve
    other application purposes and the ones stored in Mongo are only for the
    Bluesky exclusion list.
    """
    mongo_access = MongoAccess()
    agency_ids = [x.user_id for x in AgencyContributorXUser.objects.all()] + \
                 [x['userId'] for x in mongo_access.get_exclusion_list()]
    agency_users = User.objects.filter(user_id__in=agency_ids).order_by('username')
    response_dict = {'agency_users':agency_users}
    return render(request, 'mongo_status/exclusion_list.html', response_dict)

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

def sent_asset_summary(request, year, month, day):
    """
    Display a breakdown of what was transferred on a particular day.
    """
    day_to_summarise = datetime.datetime(int(year), int(month), int(day))
    sent_asset_summary = None
    next_day = None
    prev_day = None

    try:
        sent_asset_summary = SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST,
                                                     day=day_to_summarise)
    except SentAssetSummary.DoesNotExist:
        pass

    try:
        next_day = SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST,
                                                   day=(day_to_summarise + datetime.timedelta(1)))
    except SentAssetSummary.DoesNotExist:
        pass

    try:
        prev_day = SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST,
                                                   day=(day_to_summarise - datetime.timedelta(1)))
    except SentAssetSummary.DoesNotExist:
        pass

    tree = {
        'ex_photo_main'           : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=1, taxonomy_id=1),
        'ex_photo_vetta'          : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=1, taxonomy_id=2),
        'ex_photo_dollar'         : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=1, taxonomy_id=3),
        'ex_photo_signature'      : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=1, taxonomy_id=4),
        'ex_photo_signature_plus' : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=1, taxonomy_id=5),

        'non_ex_photo_main'           : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=1, taxonomy_id=1),
        'non_ex_photo_vetta'          : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=1, taxonomy_id=2),
        'non_ex_photo_dollar'         : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=1, taxonomy_id=3),
        'non_ex_photo_signature'      : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=1, taxonomy_id=4),
        'non_ex_photo_signature_plus' : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=1, taxonomy_id=5),

        'ex_vector_main'           : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=7, taxonomy_id=1),
        'ex_vector_vetta'          : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=7, taxonomy_id=2),
        'ex_vector_dollar'         : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=7, taxonomy_id=3),
        'ex_vector_signature'      : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=7, taxonomy_id=4),
        'ex_vector_signature_plus' : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=7, taxonomy_id=5),

        'non_ex_vector_main'           : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=7, taxonomy_id=1),
        'non_ex_vector_vetta'          : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=7, taxonomy_id=2),
        'non_ex_vector_dollar'         : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=7, taxonomy_id=3),
        'non_ex_vector_signature'      : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=7, taxonomy_id=4),
        'non_ex_vector_signature_plus' : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=7, taxonomy_id=5),

        'ex_video_main'           : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=8, taxonomy_id=1),
        'ex_video_vetta'          : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=8, taxonomy_id=2),
        'ex_video_dollar'         : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=8, taxonomy_id=3),
        'ex_video_signature'      : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=8, taxonomy_id=4),
        'ex_video_signature_plus' : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=True, abstract_type_id=8, taxonomy_id=5),

        'non_ex_video_main'           : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=8, taxonomy_id=1),
        'non_ex_video_vetta'          : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=8, taxonomy_id=2),
        'non_ex_video_dollar'         : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=8, taxonomy_id=3),
        'non_ex_video_signature'      : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=8, taxonomy_id=4),
        'non_ex_video_signature_plus' : SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST, day=day_to_summarise, is_exclusive=False, abstract_type_id=8, taxonomy_id=5),
    }

    for leaf in tree:
        if len(tree[leaf]) == 0:
            tree[leaf] = 0
        else:
            tree[leaf] = tree[leaf][0].count

    response_dict = {
        'day_logged'         :day_to_summarise,
        'sent_asset_summary' :sent_asset_summary,
        'next_day'           :next_day,
        'prev_day'           :prev_day,
        'tree'               :tree,
    }
    return render(request, 'mongo_status/sent_asset_summary.html', response_dict)

def contributor_csv_export(request, contributor_id):
    """
    Export some useful contributor data

    This used to be *super* naive about getting data from mongo and istock-mysql.
    Using models and such it would make 2 connections per csv row.
    Now there are 2 connections per request. taking a 14 second request down to 0.7 seconds in dev.
    """
    contributor = get_object_or_404(User, user_id=int(contributor_id))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contributor-%d.csv"' % contributor.user_id
    writer = csv.writer(response)

    mongo_access = MongoAccess()
    mongo_assets = mongo_access.get_assets([a.id for a in contributor.assets()])

    # mongo constraints ensure there'll be an assetId
    accumulator = {}
    for mongo_asset in mongo_assets:
        accumulator[mongo_asset['assetId']] = mongo_asset

    getty_id = None
    bluesky_status = None
    writer.writerow(['File ID', 'Getty ID', 'Bluesky Status', 'iStock Status'])
    for asset in contributor.assets():

        try:
            # mongo data is nebulous
            getty_id = int(accumulator[asset.id]['partnerData']['getty']['partnerId'])
        except:
            getty_id = None

        try:
            bluesky_status = accumulator[asset.id]['partnerData']['getty']['status']
        except:
            bluesky_status = None
        writer.writerow([asset.id, getty_id, bluesky_status, asset.status])
    return response

class DaySummariesView(ArchiveIndexView):
    """
    Generic views are classes since django 1.4.
    """
    template_name ='mongo_status/day_summaries.html'
    date_field = 'day'
    queryset = DaySummary.objects.filter(connection=settings.SPLUNK_HOST)
    context_object_name = 'day_summaries'

class CompleteGraphsView(TemplateView):
    """
    The graphs on the front page have too many data points to graph on every
    page load. This view will provide a list of graphs that people can view for
    the entire history if they want to endure the page load time.
    """
    template_name = 'mongo_status/complete_graphs.html'

class ContributorView(DetailView):
    pk_url_kwarg = 'contributor_id'
    model = User
    context_object_name = 'contributor'
    template_name = 'mongo_status/contributor.html'
