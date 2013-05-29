from django.conf.urls import patterns, url

from mongo_status import views
urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^get_status/', views.get_status, name='get_status'),
    url(r'^status_details/(?P<status>\w+)/$', views.complete_details, name='complete_details')
    )
