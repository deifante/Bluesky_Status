from django.conf.urls import patterns, url

from mongo_status_api.views import BasicStatusListView, index

urlpatterns = patterns(
    '',
    url(r'^$', index, name='index'),
    url(r'^basic_status/$', BasicStatusListView.as_view(), name='basic_status'),
)
