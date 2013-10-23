import json

from django.conf import settings
from django.http import HttpResponse
from django.core import serializers
from django.views.generic.list import ListView, BaseListView
from django.views.generic import TemplateView
from django.db.models.query import QuerySet

from mongo_status.models import BasicStatus

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
            self.convert_object_list_to_json(context),
            **response_kwargs
        )
    def convert_object_list_to_json(self, context):
        return serializers.serialize('json', context['object_list'])

def index(request):
    return HttpResponse(json.dumps("Working"), content_type='application/json')

class BasicStatusListView(JSONResponseMixin, BaseListView):
    queryset = BasicStatus.objects.filter(connection=settings.MONGO_HOST)
