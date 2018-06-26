# Copyright (c) 2016, TeaCapp LLC
# All rights reserved.

"""
Reports applications at a property.
"""

import logging

from django.core.management.base import BaseCommand

from ...humanize import as_money
from ...models import Application
from ...views.verification import DATETIME_FORMAT


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Reports applications at a property."

    requires_model_validation = False

    def add_arguments(self, parser):
        parser.add_argument('properties', metavar='properties', nargs='+',
            help="properties to run reports against.")

    def handle(self, *args, **options):
        for lihtc_property in options['properties']:
            self.stdout.write("Created at\tFull name\tFamily size"\
                "\tAnnual income\tIncome limit 60% AMI\tIncome limit 50% AMI\t"\
                "status\n")
            for application in Application.objects.filter(
                    lihtc_property__slug=lihtc_property):
                limit = application.lihtc_property.county.income_limits.filter(
                    family_size=application.family_size,
                    created_at__lt=application.effective_date).order_by(
                        '-created_at').first()
                self.stdout.write(
                    "%s\t%s\t%d\t%s\t%s\t%s\t%s\n" % (
                    application.created_at.strftime(DATETIME_FORMAT),
                    application.printable_name,
                    application.family_size,
                    as_money(application.total_annual_income,
                        whole_dollars=True),
                    as_money(limit.sixty_percent, whole_dollars=True),
                    as_money(limit.fifty_percent, whole_dollars=True),
                    dict(Application.HUMANIZED_STATUS)[application.status]))
