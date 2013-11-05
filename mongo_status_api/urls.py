from django.conf.urls import patterns, url

from mongo_status_api import views

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),

    # Basic Status URLs
    url(r'^basic_status/$', views.BasicStatusListView.as_view()),
    url(r'^basic_status/(?P<pk>\d+)/$', views.BasicStatusDetailView.as_view()),

    # Status Count URLs
    url(r'^status_count/$', views.StatusCountListView.as_view()),
    url(r'^status_count/(?P<pk>\d+)/$', views.StatusCountDetailView.as_view()),

    # Detailed Status URLs
    url(r'^detailed_status/$', views.DetailedStatusListView.as_view()),
    url(r'^detailed_status/(?P<pk>\d+)/$', views.DetailedStatusDetailView.as_view()),

    # Day Summary URLs
    url(r'^day_summary/$', views.DaySummaryListView.as_view()),
    url(r'^day_summary/(?P<pk>\d+)/$', views.DaySummaryDetailView.as_view()),

    # Sent Asset Summary URLs
    url(r'^sent_asset_summary/$', views.SentAssetSummaryListView.as_view()),
    url(r'^sent_asset_summary/(?P<pk>\d+)/$', views.SentAssetSummaryDetailView.as_view()),

    # Exclusion List Urls
    url(r'^exclusion_list/$', views.ExclusionListView.as_view()),
    url(r'^exclusion_list/(?P<userId>\d+)/$', views.ExclusionDetailView.as_view()),
)
