import json
import datetime

from django.conf import settings
from django.http import HttpResponse
from django.core import serializers
from django.db import models
from django.views.generic.list import ListView, BaseListView
from django.views.generic import TemplateView, View
from django.views.generic.detail import BaseDetailView
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404

from bson.objectid import ObjectId

from mongo_status.mongo_access import MongoAccess
from mongo_status.models import BasicStatus, StatusCount, DetailedStatus, DaySummary, SentAssetSummary
from mongo_status.mysql_access import AbstractFile, User, AgencyContributorXUser

class DateTimeJSONEncoder(json.JSONEncoder):
    """
    Allows for 8601 formatting of python datetime objects.

    Causes the encoder to silently fail instead of throw
    exceptions.
    """
    def default(self, o):
        """
        Allows for datetime object to be encoded as 8601.
        """
        try:
            if isinstance(o, datetime.datetime):
                return o.isoformat()
            elif isinstance(o, ObjectId):
                return str(o)
            return json.JSONEncoder.default(self, o)
        except TypeError:
            return ''

class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """
    def render_to_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(
            self.convert_context_to_json(context),
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        """
        There's probably a better way to do this, but this works for now.

        Right now we're replacing *every* QuerySet item in context with it's
        equivalent dict. Also tossing most things that aren't handled by
        python's JSON conversion.
        """
        for item in context:
            if isinstance(context[item], QuerySet):
                accumulator = []
                for model_dict in context[item].values():
                    accumulator.append(model_dict)
                # now instead of a query set this is a list of dicts.
                context[item] = accumulator

            elif isinstance(context[item], models.Model):
                # same concept here replace the model with a dict.
                context[item] = model_to_dict(context[item])

        datetime_encoder = DateTimeJSONEncoder(sort_keys=True, indent=2)
        return datetime_encoder.encode(context)

# Using the stuff above, define 2 class based views that can be reused
# for displaying JSON data
class JSONListView(JSONResponseMixin, BaseListView):
    """
    Provide functionality to display a list in JSON
    """
    pass

class JSONDetailView(JSONResponseMixin, BaseDetailView):
    """
    Provide functionality to diplay a single object in JSON
    """
    pass

def index(request):
    return HttpResponse(json.dumps("Working"), content_type='application/json')

class BasicStatusListView(JSONListView):
    queryset = BasicStatus.objects.filter(connection=settings.MONGO_HOST)[:5]

class BasicStatusDetailView(JSONDetailView):
    queryset = BasicStatus.objects.filter(connection=settings.MONGO_HOST)

class StatusCountListView(JSONListView):
    queryset = StatusCount.objects.filter(connection=settings.MONGO_HOST)[:5]

class StatusCountDetailView(JSONDetailView):
    queryset = StatusCount.objects.filter(connection=settings.MONGO_HOST)

class DetailedStatusListView(JSONListView):
    queryset = DetailedStatus.objects.filter(connection=settings.MONGO_HOST)[:5]

class DetailedStatusDetailView(JSONDetailView):
    queryset = DetailedStatus.objects.filter(connection=settings.MONGO_HOST)

class DaySummaryListView(JSONListView):
    queryset = DaySummary.objects.filter(connection=settings.SPLUNK_HOST)[:5]

class DaySummaryDetailView(JSONDetailView):
    queryset = DaySummary.objects.filter(connection=settings.SPLUNK_HOST)

class SentAssetSummaryListView(JSONListView):
    queryset = SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST)[:5]

class SentAssetSummaryDetailView(JSONDetailView):
    queryset = SentAssetSummary.objects.filter(connection=settings.SPLUNK_HOST)

class ExclusionListView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        mongo_access = MongoAccess()
        mongo_exclusion_list = [{'userId':int(x['userId']), '_id':x['_id']} for x in mongo_access.get_exclusion_list()]
        mysql_exclusion_list = [{'userId':x.user_id, 'agency_id':x.agency_id} for x in AgencyContributorXUser.objects.all()]
        context = {
            'exclusion_list':mongo_exclusion_list + mysql_exclusion_list,
            'object_list':mongo_exclusion_list + mysql_exclusion_list
        }
        return self.render_to_response(context)

class ExclusionDetailView(JSONResponseMixin, View):        

    def get(self, request, *args, **kwargs):
        mongo_access = MongoAccess()
        exclusion_user = mongo_access.get_exclusion_list_user(kwargs['userId'])
        context = {}
        if exclusion_user:
            context['exclusion_user'] = exclusion_user
        else:
            context['exclusion_user'] = get_object_or_404(AgencyContributorXUser, user_id=int(kwargs['userId']))
        return self.render_to_response(context)
        
