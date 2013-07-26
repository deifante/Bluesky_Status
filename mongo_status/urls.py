import datetime

from django.conf.urls import patterns, url
from django.conf import settings

from mongo_status import views, util
from mongo_status.views import DaySummariesView

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^get_status/', views.get_status, name='get_status'),
    url(r'^status_details/(?P<status>\w+)/$', views.complete_details, name='complete_details'),
    url(r'^day_summary/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', views.day_summary, name='day_summary'),
    url(r'^day_summary/yesterday/$', views.day_summary, util.yesterday_dict(), name='yesterdays_day_summary'),
    url(r'^day_summaries/$', DaySummariesView.as_view(), name='day_summaries'),
    )
