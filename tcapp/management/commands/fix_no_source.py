# Copyright (c) 2017, TeaCapp LLC
# All rights reserved.

"""
Find all income with no Source.
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Income, Source


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Fix all income with no source'

    requires_model_validation = False

    def handle(self, *args, **options):
        nb_empty_sources = 0
        self.stdout.write(
            "The following income entries have an empty source:\n")
        with transaction.atomic():
            for income in Income.objects.all():
                if income.source is None or not income.source.name:
                    self.stdout.write("pk %d on question %s for resident %s" % (
                        income.pk, income.question.slug,
                        income.resident.printable_name))
                    if income.source:
                        income.source.name = "N/A"
                        income.source.position = None
                        income.source.save()
                    else:
                        source, _ = Source.objects.get_or_create(
                            resident=income.resident, name="N/A", position=None,
                            defaults={'country': "US", 'region': "CA"})
                        income.source = source
                        income.save()
                    nb_empty_sources += 1
        self.stdout.write("fixed %d income records\n" % nb_empty_sources)
