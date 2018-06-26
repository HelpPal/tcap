# Copyright (c) 2017, TeaCapp LLC
# All rights reserved.

"""
Maxium Rent Levels can be found at
https://www.huduser.gov/portal/datasets/mtsp.html#2017_data

To import rent limits:
1. Download "FY 2017 MTSP Income Limits data in MS Excel"
2. Convert the MS EXCEL in CSV format
3. Check that the column names match the expected columns by the script
   (ex: fips_2000 removed between 2016 and 2017).
4. Run:
   python manage.py import_rent_levels --effective 2017-04-14 \
       --compute-limits tcapp/fixtures/rent-limits.csv
5. Check that computed values match the 100% Income Level from PDF
   at http://www.treasurer.ca.gov/ctcac/rentincome/16/rent/post20160328.pdf
   (linked from http://www.treasurer.ca.gov/ctcac/compliance.asp)
"""

import csv, datetime, logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import utc

from ...models import County, RentLimit


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import federal maximum rent limits.'

    requires_model_validation = False

    def add_arguments(self, parser):
        parser.add_argument('--effective', action='store',
            dest='effective', default=None,
            help='effective date.')
        parser.add_argument('--compute-limits', action='store_true',
            dest='compute_limits', default=False,
            help='Compute limits from HUD data or direct import')
        parser.add_argument('csvfiles', metavar='csvfiles', nargs='+',
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
                    load_max_rent_levels(reader, created_at,
                        compute_limits=options['compute_limits'])


def load_max_rent_levels(reader, created_at, compute_limits=False):
    #pylint:disable=too-many-locals
    headers = next(reader)
    region_col = headers.index('stusps')
    if region_col < 0:
        raise KeyError()
    county_name_col = headers.index('county_name')
    fips_2010_col = headers.index('fips2010')
    cbsa_sub_col = headers.index('cbsasub')
    metro_area_name_col = headers.index('areaname')
    is_metro_col = headers.index('metro')
    limit_base = headers.index('lim50_%sp1' % created_at.strftime("%y"))
    for linenum, row in enumerate(reader):
        if row[region_col] == 'CA':
            LOGGER.debug(
                "import rent levels for county %d: %s %s %s %s %s %s",
                linenum + 2, row[region_col],
                row[fips_2010_col], row[county_name_col],
                row[cbsa_sub_col], row[metro_area_name_col],
                bool(row[is_metro_col]))
            try:
                county = County.objects.get(
                    region=row[region_col], fips_2010=row[fips_2010_col])
                county.name = row[county_name_col]
                county.cbsa_sub = row[cbsa_sub_col]
                county.metro_area_name = row[metro_area_name_col]
                county.is_metro = bool(row[is_metro_col])
                county.save()
            except County.DoesNotExist:
                county = County.objects.create(
                    region=row[region_col],                   # State_Alpha
                    # skip column C, D
                    name=row[county_name_col],                # County_Name
                    cbsa_sub=row[cbsa_sub_col],               # CBSASub
                    metro_area_name=row[metro_area_name_col], # Metro_Area_Name
                    fips_2010=row[fips_2010_col],             # fips2010
                    is_metro=bool(row[is_metro_col])
                )
            if compute_limits:
                occupency_limits = [
                    int(row[limit_base]),
                    (int(row[limit_base]) + int(row[limit_base + 1])) / 2.0,
                    int(row[limit_base + 2]),
                    (int(row[limit_base + 3]) + int(row[limit_base + 4])) / 2.0,
                    int(row[limit_base + 5]),
                    (int(row[limit_base + 6]) + int(row[limit_base + 7])) / 2.0,
                    int(row[limit_base + 8])]
            else:
                occupency_limits = [
                    int(row[limit_base]),
                    int(row[limit_base + 1]),
                    int(row[limit_base + 2]),
                    int(row[limit_base + 3]),
                    int(row[limit_base + 4]),
                    int(row[limit_base + 5])]
            #sys.stdout.write("%s" % row[county_name_col].ljust(30))
            for nb_bedrooms in range(0, 6):
                if compute_limits:
                    limit60 = int(occupency_limits[nb_bedrooms]
                        * 1.2 * 0.3 / 12)
                    full_amount = int(limit60 * 100.0 / 60)
                else:
                    limit60 = occupency_limits[nb_bedrooms]
                    full_amount = limit60 * 100 / 60
                #sys.stdout.write("\t$%d(%.2f)" % (full_amount, limit60))
                RentLimit.objects.create(
                    created_at=created_at,
                    county=county,
                    nb_bedrooms=nb_bedrooms,
                    full_amount=full_amount * 100) # in cents
            #sys.stdout.write("\n")
