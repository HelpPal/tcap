# Copyright (c) 2017, TeaCapp LLC
# All rights reserved.

"""
Export the rent limits currently in the database.

Check that computed values match the 100% rent limits from PDF
   at http://www.treasurer.ca.gov/ctcac/rentincome/17/rent/\
11-rent-limits-post-041417.pdf
   (linked from http://www.treasurer.ca.gov/ctcac/compliance.asp)
"""

import datetime, logging, sys

from django.core.management.base import BaseCommand
from django.utils.timezone import utc

from ...models import County, RentLimit
from ...humanize import as_money

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Export CTCAC maximum rent limits.'

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
        for county in County.objects.filter(region='CA').order_by('name'):
            sys.stdout.write('%s\n' % county.name.encode('utf-8'))
            sys.stdout.write('100% Income Level')
            for rent in county.current_rent_limits:
                sys.stdout.write('\t%s' % as_money(
                    rent.full_amount, whole_dollars=whole_dollars).rjust(9))
            sys.stdout.write('\n')
            sys.stdout.write('60% Income Level')
            for rent in county.current_rent_limits:
                sys.stdout.write('\t%s' % as_money(
                    rent.sixty_percent, whole_dollars=whole_dollars).rjust(9))
            sys.stdout.write('\n')
            sys.stdout.write('55% Income Level\n')
            sys.stdout.write('50% Income Level')
            for rent in county.current_rent_limits:
                sys.stdout.write('\t%s' % as_money(
                    rent.fifty_percent, whole_dollars=whole_dollars).rjust(9))
            sys.stdout.write('\n')
            sys.stdout.write('45% Income Level\n')
            sys.stdout.write('40% Income Level\n')
            sys.stdout.write('35% Income Level\n')
            sys.stdout.write('30% Income Level\n')

        for county_name, nb_bedrooms in [
                ('Alameda County', 0),
                # Below
                ('Amador County', 3),
                ('Lassen County', 5),
                ('Los Angeles County', 3),
                ('Mariposa County', 3),
                ('Mendocino County', 3),
                ('Nevada County', 5),
                ('San Benito County', 3),
                ('San Diego County', 3),
#                ('Santa Cruz County', 5),
#                ('Siskiyou County', 5),
                ('Solano County', 5),
                # Above
                ('Calaveras County', 5),
                ('El Dorado County', 5),
                ('Inyo County', 1),
                ('Mono County', 5),
                ('Monterey County', 5),
                ('Napa County', 1),
                ('Placer County', 5),
                ('Sacramento County', 5),
                ('San Benito County', 5),
                ('San Diego County', 1),
                ('San Joaquin County', 1),
                ('San Joaquin County', 5),
                ('San Luis Obispo County', 5),
                ('Santa Cruz County', 3),
                ('Tuolumne County', 3)
        ]:
            limit = RentLimit.objects.get(county__region='CA',
                county__name=county_name, nb_bedrooms=nb_bedrooms)
            sys.stderr.write("%d * 60 / 100 = %d %d brds in %s (=> %d)\n" % (
                limit.full_amount,
                (limit.full_amount * 60) / 100,
                nb_bedrooms,
                county_name, limit.sixty_percent))
