from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib.sites.models import Site

admin.autodiscover()
admin.site.unregister(Site)

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mycron.views.home', name='home'),
    # url(r'^mycron/', include('mycron.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^task/index', 'mycron.task.views.index'),
    url(r'^task/show', 'mycron.task.views.show'),
    url(r'^task/create', 'mycron.task.views.create'),
    url(r'^task/destroy', 'mycron.task.views.destroy'),
    url(r'^task/update', 'mycron.task.views.update'),
    url(r'^task/toggleStatus', 'mycron.task.views.toggleStatus'),
    url(r'^task/run', 'mycron.task.views.run'),
    url(r'^task/search', 'mycron.task.views.search'),
    url(r'^', 'mycron.task.views.index'),
)
