# Copyright (c) 2016, TeaCapp LLC
#   All rights reserved.

from django.conf import settings
from django.conf.urls import url

if settings.DEBUG:
    # In debug mode we add a path_prefix such that we can test
    # the webapp through the session proxy.
    APP_PREFIX = '%s/' % settings.APP_NAME
else:
    APP_PREFIX = ''

def url_prefixed(regex, view, name=None):
    """
    Returns a urlpattern prefixed with the APP_NAME in debug mode.
    """
    return url(r'^%(app_prefix)s%(regex)s' % {
        'app_prefix': APP_PREFIX, 'regex': regex}, view, name=name)
