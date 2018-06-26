# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

from __future__ import unicode_literals

import csv, logging
from io import BytesIO

from django.http import HttpResponse
from django.views.generic import View
from deployutils.helpers import datetime_or_now

from .verification import DATETIME_FORMAT
from ..models import Application
from ..humanize import as_money
from .. import mixins


LOGGER = logging.getLogger(__name__)


class CSVDownloadView(View):

    basename = 'download'
    headings = []

    def get(self, *args, **kwargs): #pylint: disable=unused-argument
        content = BytesIO()
        csv_writer = csv.writer(content)
        csv_writer.writerow([head.encode('utf-8')
            for head in self.get_headings()])
        for record in self.get_queryset():
            csv_writer.writerow(self.queryrow_to_columns(record))
        content.seek(0)
        resp = HttpResponse(content, content_type='text/csv')
        resp['Content-Disposition'] = \
            'attachment; filename="{}"'.format(
                self.get_filename())
        return resp

    def get_headings(self):
        return self.headings

    def get_queryset(self):
        # Note: this should take the same arguments as for
        # Searchable and SortableListMixin in "extra_views"
        raise NotImplementedError

    def get_filename(self):
        return datetime_or_now().strftime(self.basename + '-%Y%m%d.csv')

    def queryrow_to_columns(self, record):
        raise NotImplementedError


class IncomeReportCSVView(mixins.PropertyMixin, CSVDownloadView):

    basename = 'income-report'
    headings = ['Created at', 'Full name', 'Family size', 'Annual income',
        'Income limit 60% AMI', 'Income limit 50% AMI', 'status', 'Unit']

    def get_queryset(self):
        return Application.objects.filter(
            lihtc_property__slug=self.project).order_by('-created_at')

    def queryrow_to_columns(self, record):
        application = record
        limit = application.lihtc_property.county.income_limits.filter(
            family_size=application.family_size,
            created_at__lt=application.effective_date).order_by(
                '-created_at').first()
        if limit is not None:
            limit_60 = as_money(limit.sixty_percent, whole_dollars=True)
            limit_50 = as_money(limit.fifty_percent, whole_dollars=True)
        else:
            limit_60 = "N/A"
            limit_50 = "N/A"
        return (
            application.created_at.strftime(DATETIME_FORMAT),
            application.printable_name,
            application.family_size,
            as_money(application.total_annual_income,
                     whole_dollars=True),
            limit_60, limit_50,
            dict(Application.HUMANIZED_STATUS)[application.status],
            application.unit_number)
