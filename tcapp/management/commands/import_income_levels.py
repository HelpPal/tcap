# Copyright (c) 2016, TeaCapp LLC
# All rights reserved.

"""
Maxium Income Levels can be found at
https://www.huduser.gov/portal/datasets/il.html#2017_data

To import income limits:
1. Download "Data for Section 8 Income Limits in MS EXCEL"
2. Convert the MS EXCEL in CSV format
3. Run:
   python manage.py import_income_levels --effective 2017-04-14 \
       Section8_FY17.csv
"""

# Same fips2000:
#  - Amherst town and Marshall Island UT
#  - Appleton town and Muscle Ridge Island UT
#  - Alna town and Louds Island UT
# No fips2000:
#  - Cumberland County,
#  - Northern Mariana Islands
#  - American Samoa
# Changed fips2010 number:
#  - Burlington-South Burlington, VT MSA (5001300700 to 5001300860)
from __future__ import unicode_literals

import csv, datetime, logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import utc

from ...models import County, IncomeLimit


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import federal maximum income limits.'

    requires_model_validation = False

    def add_arguments(self, parser):
        parser.add_argument('--effective', action='store',
            dest='effective', default=None,
            help='effective date.')
        parser.add_argument('csvfiles', metavar='csvfile', nargs='+',
            help="csv file with data to import")

    def handle(self, *args, **options):
        if options['effective']:
            created_at = datetime.datetime.strptime(
                options['effective'], "%Y-%m-%d")
        else:
            created_at = datetime.datetime.utcnow()
        created_at = created_at.replace(tzinfo=utc)
        LOGGER.debug("effective at: %s", created_at)
        for dataset_path in options['csvfiles']:
            with open(dataset_path) as dataset_file:
                reader = csv.reader(dataset_file)
                with transaction.atomic():
                    self.load_max_income_levels(reader, created_at)


    def load_max_income_levels(self, reader, created_at):
        #pylint:disable=too-many-locals
        headers = next(reader)
        state_alpha_col = headers.index('State_Alpha')
        fips_2010_col = headers.index('fips2010')
        cbsasub_col = headers.index('cbsasub')
        metro_area_name_col = headers.index('Metro_Area_Name')
        county_name_col = headers.index('County_Name')
        is_metro_col = headers.index('metro')
        limit_base = headers.index('l50_1')
        for linenum, row in enumerate(reader):
            LOGGER.debug(
                "import income levels for county %d: %s %s %s %s %s %s",
                linenum + 2, [state_alpha_col], row[fips_2010_col],
                row[cbsasub_col], row[metro_area_name_col],
                row[county_name_col], bool(row[is_metro_col]))
            try:
    #           if row[fips_2010_col] == '5001300860':
                   # Seems like there is/was a mistake in the excel spreadsheet.
    #              county = County.objects.get(
    #                  region=row[state_alpha_col], fips_2000='5001300700')
    #              county.fips_2010 = '5001300860'
    #           else:
                county = County.objects.get(
                    region=row[state_alpha_col],
                    fips_2010=row[fips_2010_col])
                updated = False
                if county.name != row[county_name_col]:
                    self.stdout.write("\t-name: '%s'" % county.name)
                    self.stdout.write("\t+name: '%s'" % row[county_name_col])
                    county.name = row[county_name_col]
                    updated = True
                if county.cbsa_sub != row[cbsasub_col]:
                    self.stdout.write("\t-cbsa_sub: '%s'" % county.cbsa_sub)
                    self.stdout.write("\t+cbsa_sub: '%s'" % row[cbsasub_col])
                    county.cbsa_sub = row[cbsasub_col]
                    updated = True
                if county.metro_area_name != row[metro_area_name_col]:
                    self.stdout.write(
                        "\t-cbsa_sub: '%s'" % county.metro_area_name)
                    self.stdout.write(
                        "\t+cbsa_sub: '%s'" % row[metro_area_name_col])
                    county.metro_area_name = row[metro_area_name_col]
                    updated = True
                if county.is_metro != bool(row[is_metro_col]):
                    self.stdout.write("\t-is_metro: '%s'" % county.is_metro)
                    self.stdout.write("\t+is_metro: '%s'" % row[is_metro_col])
                    county.is_metro = bool(row[is_metro_col])
                    updated = True
                if updated:
                    county.save()
            except County.DoesNotExist:
                county = County.objects.create(
                    region=row[state_alpha_col],        # State_Alpha
                    fips_2010=row[fips_2010_col],       # fips2010
                    # skip column C, D
                    name=row[county_name_col],          # County_Name
                    cbsa_sub=row[cbsasub_col],          # CBSASub
                    metro_area_name=row[metro_area_name_col], # Metro_Area_Name
                    is_metro=bool(row[is_metro_col])
                )
            # skip median2016 column (row[8])
            for family_size in range(1, 8):
                full_amount = int(row[limit_base + family_size - 1]) * 2 * 100
                IncomeLimit.objects.create(
                    created_at=created_at,
                    county=county,
                    family_size=family_size,
                    full_amount=full_amount)
