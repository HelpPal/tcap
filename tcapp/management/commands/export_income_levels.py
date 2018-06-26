# Copyright (c) 2017, TeaCapp LLC
# All rights reserved.

"""
Export the income limits currently in the database.

Check that computed values match the 100% income limits from PDF
   at http://www.treasurer.ca.gov/ctcac/rentincome/17/income/\
10-income-limits-post041417.pdf
   (linked from http://www.treasurer.ca.gov/ctcac/compliance.asp)
"""

import datetime, logging, sys

from django.core.management.base import BaseCommand
from django.utils.timezone import utc

from ...models import County
from ...humanize import as_money

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Export CTCAC maximum income limits.'

    def add_arguments(self, parser):
        parser.add_argument('--effective', action='store',
            dest='effective', default=None,
            help='effective date.')

    def handle(self, *args, **options):
        whole_dollars = False
        if options['effective']:
            created_at = datetime.datetime.strptime(
                options['effective'], "%Y-%m-%d")
        else:
            created_at = datetime.datetime.utcnow()
        created_at = created_at.replace(tzinfo=utc)
        LOGGER.debug("effective at: %s", created_at)
        for county in County.objects.order_by('name'):
            sys.stdout.write('%s\n' % county.name)
            sys.stdout.write('100% Income Level')
            for income in county.current_income_limits:
                sys.stdout.write('\t%s' % as_money(
                    income.full_amount, whole_dollars=whole_dollars).rjust(6))
            sys.stdout.write('\n')
            sys.stdout.write('60% Income Level')
            for income in county.current_income_limits:
                sys.stdout.write('\t%s' % as_money(
                    income.sixty_percent, whole_dollars=whole_dollars).rjust(6))
            sys.stdout.write('\n')
            sys.stdout.write('55% Income Level\n')
            sys.stdout.write('50% Income Level')
            for income in county.current_income_limits:
                sys.stdout.write('\t%s' % as_money(
                    income.fifty_percent, whole_dollars=whole_dollars).rjust(6))
            sys.stdout.write('\n')
            sys.stdout.write('45% Income Level\n')
            sys.stdout.write('40% Income Level\n')
            sys.stdout.write('35% Income Level\n')
            sys.stdout.write('30% Income Level\n')
