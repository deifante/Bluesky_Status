import datetime

from django.conf.urls import patterns, url
from django.conf import settings
from django.views.generic.base import TemplateView

from mongo_status import views
from mongo_status.views import DaySummariesView, CompleteGraphsView, ContributorView, DaySummariesYearView, DaySummariesMonthView, SentAssetSummariesView, SentAssetSummariesYearView, SentAssetSummariesMonthView

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^get_status/', views.get_status, name='get_status'),
    url(r'^status_details/(?P<status>\w+)/$', views.complete_details, name='complete_details'),

    # Day Summary Views
    url(r'^day_summaries/$', DaySummariesView.as_view(), name='day_summaries'), # View all Day Summaries/Year view
    url(r'^day_summaries/(?P<year>\d{4})/$', DaySummariesYearView.as_view(), name='day_summaries_year'), # See all valid months in a year
    url(r'^day_summaries/(?P<year>\d{4})/(?P<month>\d{1,2})/$', DaySummariesMonthView.as_view(), name='day_summaries_month'), # See all summaries in a month
    url(r'^day_summary/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', views.day_summary, name='day_summary'),  # See a specific day summary
    url(r'^day_summary/yesterday/$', views.yesterdays_day_summary, name='yesterdays_day_summary'), # Short cut to "yesterday's" day summary

    # Sent Asset Views
    url(r'^sent_asset_summaries/$', SentAssetSummariesView.as_view(), name='sent_asset_summaries'), # View all Sent Asset Summaries/Year view
    url(r'^sent_asset_summaries/(?P<year>\d{4})/$', SentAssetSummariesYearView.as_view(), name='sent_asset_summaries_year'), # See all valid months in a year
    url(r'^sent_asset_summaries/(?P<year>\d{4})/(?P<month>\d{1,2})/$', SentAssetSummariesMonthView.as_view(), name='sent_asset_summaries_month'), # See all sent asset summaries in a month
    url(r'^sent_asset_summary/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$', views.sent_asset_summary, name='sent_asset_summary'), # See a specific sent asset summary
    url(r'^sent_asset_summary/yesterday/$', views.yesterdays_sent_asset_summary, name='yesterdays_sent_asset_summary'), # Short cut to "yesterday's" sent asset summary

    url(r'^complete_queue_status/$', views.complete_queue_status, name='complete_queue_status'),
    url(r'^complete_graphs/$', CompleteGraphsView.as_view(), name='complete_graphs'),
    url(r'^documentation/$', TemplateView.as_view(template_name = 'mongo_status/documentation.html'), name='documentation'),
    url(r'^contributor/(?P<contributor_id>\d+)/$', ContributorView.as_view(), name='contributor'),
    url(r'^contributor/(?P<contributor_id>\d+)/csv/$', views.contributor_csv_export, name='contributor_csv_export'),
    url(r'^exclusion_list/$', views.exclusion_list, name='exclusion_list'),
)
