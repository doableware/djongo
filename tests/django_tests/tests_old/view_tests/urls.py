import os
from functools import partial

from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, re_path
from django.utils.translation import gettext_lazy as _
from django.views import defaults, i18n, static

from . import views

base_dir = os.path.dirname(os.path.abspath(__file__))
media_dir = os.path.join(base_dir, 'media')
locale_dir = os.path.join(base_dir, 'locale')

urlpatterns = [
    url(r'^$', views.index_page),

    # Default views
    url(r'^nonexistent_url/', partial(defaults.page_not_found, exception=None)),
    url(r'^server_error/', defaults.server_error),

    # a view that raises an exception for the debug view
    url(r'raises/$', views.raises),

    url(r'raises400/$', views.raises400),
    url(r'raises403/$', views.raises403),
    url(r'raises404/$', views.raises404),
    url(r'raises500/$', views.raises500),

    url(r'technical404/$', views.technical404, name="my404"),
    url(r'classbased404/$', views.Http404View.as_view()),

    # i18n views
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^jsi18n/$', i18n.JavaScriptCatalog.as_view(packages=['view_tests'])),
    url(r'^jsi18n/app1/$', i18n.JavaScriptCatalog.as_view(packages=['view_tests.app1'])),
    url(r'^jsi18n/app2/$', i18n.JavaScriptCatalog.as_view(packages=['view_tests.app2'])),
    url(r'^jsi18n/app5/$', i18n.JavaScriptCatalog.as_view(packages=['view_tests.app5'])),
    url(r'^jsi18n_english_translation/$', i18n.JavaScriptCatalog.as_view(packages=['view_tests.app0'])),
    url(r'^jsi18n_multi_packages1/$',
        i18n.JavaScriptCatalog.as_view(packages=['view_tests.app1', 'view_tests.app2'])),
    url(r'^jsi18n_multi_packages2/$',
        i18n.JavaScriptCatalog.as_view(packages=['view_tests.app3', 'view_tests.app4'])),
    url(r'^jsi18n_admin/$',
        i18n.JavaScriptCatalog.as_view(packages=['django.contrib.admin', 'view_tests'])),
    url(r'^jsi18n_template/$', views.jsi18n),
    url(r'^jsi18n_multi_catalogs/$', views.jsi18n_multi_catalogs),
    url(r'^jsoni18n/$', i18n.JSONCatalog.as_view(packages=['view_tests'])),

    # Static views
    url(r'^site_media/(?P<path>.*)$', static.serve, {'document_root': media_dir, 'show_indexes': True}),
]

urlpatterns += i18n_patterns(
    url(_(r'^translated/$'), views.index_page, name='i18n_prefixed'),
)

urlpatterns += [
    url(r'template_exception/$', views.template_exception, name='template_exception'),
    url(
        r'^raises_template_does_not_exist/(?P<path>.+)$',
        views.raises_template_does_not_exist,
        name='raises_template_does_not_exist'
    ),
    url(r'^render_no_template/$', views.render_no_template, name='render_no_template'),
    url(r'^test-setlang/(?P<parameter>[^/]+)/$', views.with_parameter, name='with_parameter'),
    # Patterns to test the technical 404.
    re_path(r'^regex-post/(?P<pk>[0-9]+)/$', views.index_page, name='regex-post'),
    path('path-post/<int:pk>/', views.index_page, name='path-post'),
]
