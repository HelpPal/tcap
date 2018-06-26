# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

from django.conf import settings
from django.conf.urls import url

from ..api.applications import (ApplicationAPIView, ApplicationCreateAPIView,
    ApplicationDetailAPIView)
from ..api.residents import ApplicationResidentAPIView
from ..api.trials import RequestDemoAPIView
from ..api.documents import DocumentUploadView

urlpatterns = [
    url(r'^projects/(?P<project>%s)/request/' % settings.SLUG_RE,
        RequestDemoAPIView.as_view(),
        name='api_request_demo'),
    url(r'^projects/(?P<project>%s)/application/' % settings.SLUG_RE,
        ApplicationCreateAPIView.as_view(), name='api_application_create'),
    url(r'^properties/(?P<project>%s)/applications/(?P<application>%s)/upload/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        DocumentUploadView.as_view(), name='api_document_upload'),
    url(r'^properties/(?P<project>%s)/applications/(?P<application>%s)'\
        '/(?P<resident>%s)/?' % (settings.SLUG_RE, settings.SLUG_RE,
        settings.SLUG_RE), ApplicationResidentAPIView.as_view(),
        name='api_application_resident'),
    url(r'^properties/(?P<project>%s)/applications/(?P<application>%s)/?' %
        (settings.SLUG_RE, settings.SLUG_RE),
        ApplicationDetailAPIView.as_view(), name='api_application'),
    url(r'^properties/(?P<project>%s)/applications/?' % settings.SLUG_RE,
        ApplicationAPIView.as_view(),
        name='api_applications'),
]
