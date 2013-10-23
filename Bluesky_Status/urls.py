from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    # Examples:
    # url(r'^$', 'Bluesky_Status.views.home', name='home'),
    # url(r'^Bluesky_Status/', include('Bluesky_Status.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^mongo_status_api/', include('mongo_status_api.urls', namespace='mongo_status_api')),
    url(r'^mongo_status/', include('mongo_status.urls', namespace='mongo_status')),
    url(r'^admin/', include(admin.site.urls)),

)
