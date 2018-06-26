# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import logging

from django.core.urlresolvers import reverse
from django.db import transaction
from extra_views.contrib.mixins import SearchableListMixin, SortableListMixin
from rest_framework.generics import (CreateAPIView, ListAPIView,
    RetrieveUpdateAPIView)

from .. import signals
from ..mixins import ApplicationMixin, PropertyMixin
from ..models import Application
from ..serializers import (ApplicationDetailSerializer,
    ApplicationSummarySerializer)


LOGGER = logging.getLogger(__name__)


class ApplicationFilterMixin(SearchableListMixin):
    """
    ``Application`` list result of a search query, filtered by dates.
    """

    search_fields = ['applicants__last_name',
                     'applicants__first_name']


class SmartApplicationListMixin(SortableListMixin, ApplicationFilterMixin):
    """
    ``Application`` list which is also searchable and sortable.
    """

    sort_fields_aliases = [('created_at', 'created_at'),
                           ('printable_name', 'printable_name'),
                           ('status', 'status'),
                           ('unit_number', 'unit_number')]


class ApplicationQuerysetMixin(PropertyMixin):

    def get_queryset(self):
        return Application.objects.filter(lihtc_property=self.project)


class ApplicationAPIView(SmartApplicationListMixin,
                         ApplicationQuerysetMixin, ListAPIView):
    """
    GET queries all ``Application`` for a LIHTC project.

    The queryset can be further filtered to a range of dates between
    ``start_at`` and ``ends_at``.

    The queryset can be further filtered by passing a ``q`` parameter.
    The value in ``q`` will be matched against:

      - Application.printable_name

    The result queryset can be ordered by:

      - Application.created_at
      - Application.printable_name
      - Application.status

    **Example request**:

    .. sourcecode:: http

        GET /api/projects/:project/applications?start_at=2017-01-01T00:00:00\
    .000Z&o=created_at&ot=desc

    **Example response**:

    .. sourcecode:: http

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [
                {
                    "created_at": "2017-01-01T00:00:00Z",
                    "printable_name": "Donny Test"
                    "slug": "ABC123",
                    "status": "new-application"
                }
            ]
        }
    """
    serializer_class = ApplicationSummarySerializer


class ApplicationCreateAPIView(PropertyMixin, CreateAPIView):
    """
    Create a new application

    **Example request**:

    .. sourcecode:: http

        POST /api/:project/application/

        {
            "applicants": [{
                "full_name": "Bill",
                "date_of_birth": "2016-01-01",
                "relation_to_head": "HEAD",
                "marital_status": "married",
                "ssn": "",
                "race": "",
                "ethnicity": "",
                "disabled": "",
                "email": "bill@example.com",
                "phone": "415-555-5555",
                "children": [],
                "self_employed": [{
                  "name": "",
                  "position": "",
                  "incomes": {
                    category: "",
                    amount: 0,
                    period: "hourly",
                    avg: "weekly",
                    period_per_avg: 40,
                    avg_per_year: 0
                }}],
                "employee": [{
                  "name": "",
                  "position": "",
                  "incomes": {
                    category: "",
                    amount: 0,
                    period: "hourly",
                    avg: "weekly",
                    period_per_avg: 40,
                    avg_per_year: 0
                }}],
                "disability": [{"incomes":{
                    amount: 0,
                    period: "monthly",
                    avg_per_year: 12
                }}],
                "publicassistance: [{"incomes":{
                    amount: 0,
                    period: "monthly",
                    avg_per_year: 12
                }}],
                "socialsecurity": [{"incomes":{
                    amount: 0,
                    period: "monthly",
                    avg_per_year: 12
                }}],
                "supplemental": [{"incomes":{
                    amount: 0,
                    period: "monthly",
                    avg_per_year: 12
                }}],
                "unemployment": [{"incomes":{
                    amount: 0,
                    period: "monthly",
                    avg_per_year: 12
                }}],
                "veteran": [{"incomes":{
                    amount: 0,
                    period: "monthly",
                    avg_per_year: 12
                }}],
                "support_payments": []
                "assets": [],
                "student_status": {}
            }]
        }
    """

    serializer_class = ApplicationDetailSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            application = serializer.save()
            signals.application_created.send(
                sender=self, application=application,
                url=self.request.build_absolute_uri(reverse('calculation',
                    args=(application.lihtc_property, application,))))


class ApplicationDetailAPIView(ApplicationMixin, RetrieveUpdateAPIView):
    """
    GET Retrieve a single ``Application``
    PUT Update information on an ``Application``

    **Example request**:

    .. sourcecode:: http

        PUT /api/application/ea709e622c8e40a6869b492c078b2b5f/

        {
            "applicants": [{
                "slug": "9bf9150cdf7149bc8e006df20765064f",
                "employee": [{
                  "name": "",
                  "position": "",
                  "accounts": {
                    category: "",
                    amount: 0,
                    period: "hourly",
                    avg: "weekly",
                    period_per_avg: 40,
                    avg_per_year: 0
                }}],
            }]
        }
    """

    serializer_class = ApplicationDetailSerializer

    def get_object(self):
        return self.application
