import datetime

from django.conf.urls import patterns, url
from django.conf import settings

from mongo_status import views
from mongo_status.views import DaySummariesView, CompleteGraphsView, DocumentationView

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^get_status/', views.get_status, name='get_status'),
    url(r'^status_details/(?P<status>\w+)/$', views.complete_details, name='complete_details'),
    url(r'^day_summary/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', views.day_summary, name='day_summary'),
    url(r'^day_summary/yesterday/$', views.yesterdays_day_summary, name='yesterdays_day_summary'),
    url(r'^day_summaries/$', DaySummariesView.as_view(), name='day_summaries'),
    url(r'^complete_queue_status/$', views.complete_queue_status, name='complete_queue_status'),
    url(r'^complete_graphs/$', CompleteGraphsView.as_view(), name='complete_graphs'),
    url(r'^documentation/$', DocumentationView.as_view(), name='documentation'),
)
