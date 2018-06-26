# Copyright (c) 2017, TeaCapp LLC
# All rights reserved.

"""
All TCAC projects in California.

To import projects:
1. Download "TCAC Projects in MS EXCEL"
2. Convert the MS EXCEL in CSV format
3. Run:
   python manage.py import_projects --effective 2017-11-27 projects.csv
"""

import csv, datetime, decimal, sys

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError
from django.template.defaultfilters import slugify
from django.utils.timezone import utc

from ...models import County, Property, UtilityAllowance, PropertyAMIUnits


class Command(BaseCommand):

    help = 'Import TCAC projects.'

    requires_model_validation = False

    def add_arguments(self, parser):
        parser.add_argument('--email', action='store',
            dest='default_email', default='support@teacapp.co',
            help='E-mail to initialize a property with.')
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
        self.stderr.write("effective at: %s\n" % created_at.isoformat())
        for dataset_path in options['csvfiles']:
            with open(dataset_path) as dataset_file:
                reader = csv.reader(dataset_file)
                with transaction.atomic():
                    load_projects(reader, created_at,
                        default_email=options['default_email'],
                        output=sys.stdout)


def read_project(row):
    #pylint:disable=too-many-locals,too-many-statements
    tcac_number = row[0]                   # 0 Application Number
    name = row[3]                          # 3 Project Name
    street_address = row[4].split(',')[0]  # 4 Project Address
    locality = row[5]                      # 5 Project City
    postal_code = row[6]                   # 6 Project Zip Code
    phone = row[7]                         # 7 Project Phone Number
    county_name = row[8]
    if tcac_number == 'CA-2017-741':
        locality = 'Los Angeles'
        county_name = 'Los Angeles'
    if tcac_number == 'CA-2017-758':
        locality = 'Gilroy'
        county_name = 'Santa Clara'
    if county_name == 'Contra Cosa':
        # CA-1999-814
        county_name = 'Contra Costa'
    try:
        county = County.objects.get(
            region='CA',
            name__istartswith=county_name
        )
    except County.MultipleObjectsReturned:
        sys.stderr.write(
            "error: %s multiple county starting with '%s'\n" % (
                tcac_number, county_name))
        raise
    application_stage = row[14]            # 14 Application Stage
    if application_stage.lower().startswith('extended'):
        application_stage = 1
    elif application_stage.lower().startswith('placed in service'):
        application_stage = 2
    elif application_stage.lower().startswith('preliminary reservation'):
        application_stage = 3
    else:
        application_stage = 0
    construction_type = row[17]            # 17 Construction Type
    if construction_type.startswith('Acquisition'):
        construction_type = 1
    elif construction_type.startswith('NC/AR'):
        construction_type = 2
    elif construction_type.startswith('New Construction/'):
        construction_type = 4
    elif construction_type.startswith('New Construction'):
        construction_type = 3
    elif construction_type.startswith('Rehabilitation'):
        construction_type = 5
    else:
        construction_type = 0
    housing_type = row[18]                 # 18 Housing Type
    if housing_type.lower().startswith('at-risk'):
        housing_type = 1
    elif housing_type.lower().startswith('large family'):
        housing_type = 2
    elif housing_type.lower().startswith('non targeted'):
        housing_type = 3
    elif housing_type.lower().startswith('special needs/'):
        housing_type = 5
    elif housing_type.lower().startswith('special needs'):
        housing_type = 4
    elif housing_type.lower().startswith('sro/'):
        housing_type = 7
    elif housing_type.lower().startswith('sro'):
        housing_type = 6
    else:
        housing_type = 0
    try:
        tax_credit_funding = float(row[2][:-1]) * 100 # 2 tax credit funding
    except ValueError:
        tax_credit_funding = 0
    try:
        assembly_district = int(row[9])   # 9 California Assembly District
    except ValueError:
        assembly_district = 0
    try:
        senate_district = int(row[10])    # 10 California Senate District
    except ValueError:
        senate_district = 0
    # 11 Federal Congressional District
    try:
        federal_congressional_district = int(row[11])
    except ValueError:
        federal_congressional_district = 0
    try:
        census_tract = decimal.Decimal(row[12]) # 12 Census Tract
    except (ValueError, decimal.InvalidOperation):
        census_tract = decimal.Decimal(0)

    try:
        # 15 Placed in Service (PIS) Date
        placed_in_service = datetime.datetime.strptime(row[15], "%m/%d/%y")
        # 16 Last Building PIS Date
        last_building = datetime.datetime.strptime(row[16], "%m/%d/%y")
        placed_in_service = placed_in_service.replace(tzinfo=utc)
        last_building = last_building.replace(tzinfo=utc)
    except ValueError:
        # CA-1989-019, CA-1993-034
        first_site = Property.objects.filter(
            tcac_number=tcac_number).first()
        if first_site:
            placed_in_service = first_site.placed_in_service
            last_building = first_site.last_building
        else:
            # CA-1993-034
            placed_in_service = None
            last_building = None
    try:
        total_units = int(row[19])      # 19 Total Units
    except ValueError:
        total_units = 0
    try:
        low_income_units = int(row[20]) # 20 Low Income Units
    except ValueError:
        low_income_units = 0
    assessor_parcel_number = row[13]    # 13 Assessor Parcel Number (APN)
    email = ""
    return (county, tcac_number, name, street_address,
            locality, postal_code, phone, email, application_stage,
            construction_type, housing_type, tax_credit_funding,
            assembly_district, senate_district, federal_congressional_district,
            census_tract, placed_in_service, last_building,
            total_units, low_income_units, assessor_parcel_number)



def load_projects(reader, created_at, default_email='support@teacapp.co',
                  output=None):
    #pylint:disable=too-many-locals,too-many-statements
    _ = next(reader)
    if output:
        output.write("INSERT INTO saas_organization (slug, created_at, "\
"is_active, is_bulk_buyer, is_provider, full_name, email, phone, "\
"street_address, locality, region, postal_code, country, funds_balance, "\
"processor_id) VALUES\n")
    sep = ""
    for row in reader:
        (county, tcac_number, name, street_address,
         locality, postal_code, phone, email, application_stage,
         construction_type, housing_type, tax_credit_funding,
         assembly_district, senate_district, federal_congressional_district,
         census_tract, placed_in_service, last_building,
         total_units, low_income_units,
         assessor_parcel_number) = read_project(row)
        if not email:
            email = default_email
        slug_base = slugify(name)
        if len(slug_base) > 50:
            slug_base = slug_base[:50]
        slug = slug_base
        idx = 0
        loop = True
        lihtc_property = None
        while loop:
            account = slug
            bin_number = ''
            if Property.objects.filter(tcac_number=tcac_number).count() > 1:
                sys.stderr.write(
                    "warning: %s multiple sites (skipped)\n" % tcac_number)
                break
            lihtc_property = Property.objects.filter(
                tcac_number=tcac_number).first()
            if lihtc_property and lihtc_property.name != name:
                sys.stderr.write(
                    "warning: dealing with multiple sites? (%s vs %s)\n" % (
                        lihtc_property.name, name))
                lihtc_property = None
            if lihtc_property:
                changes = {}
                # slug, account and tcac_number shouldn't be changed.
                if lihtc_property.tax_credit_funding != tax_credit_funding:
                    changes.update({'tax_credit_funding': {
                        'pre': lihtc_property.tax_credit_funding,
                        'post': tax_credit_funding}})
                    lihtc_property.tax_credit_funding = tax_credit_funding
                if lihtc_property.name != name:
                    changes.update({'name': {
                        'pre': lihtc_property.name, 'post': name}})
                    lihtc_property.name = name
                if lihtc_property.street_address != street_address:
                    changes.update({'street_address': {
                        'pre': lihtc_property.street_address,
                        'post': street_address}})
                    lihtc_property.street_address = street_address
                if lihtc_property.county != county:
                    changes.update({'county': {
                        'pre': lihtc_property.county, 'post': county}})
                    lihtc_property.county = county
                if lihtc_property.bin_number != bin_number:
                    changes.update({'bin_number': {
                        'pre': lihtc_property.bin_number, 'post': bin_number}})
                    lihtc_property.bin_number = bin_number
                if lihtc_property.locality != locality:
                    changes.update({'locality': {
                        'pre': lihtc_property.locality, 'post': locality}})
                    lihtc_property.locality = locality
                if lihtc_property.postal_code != postal_code:
                    changes.update({'postal_code': {
                        'pre': lihtc_property.postal_code,
                        'post': postal_code}})
                    lihtc_property.postal_code = postal_code
                if lihtc_property.phone != phone:
                    changes.update({'phone': {
                        'pre': lihtc_property.phone, 'post': phone}})
                    lihtc_property.phone = phone
                if lihtc_property.assembly_district != assembly_district:
                    changes.update({'assembly_district': {
                        'pre': lihtc_property.assembly_district,
                        'post': assembly_district}})
                    lihtc_property.assembly_district = assembly_district
                if lihtc_property.senate_district != senate_district:
                    changes.update({'senate_district': {
                        'pre': lihtc_property.senate_district,
                        'post': senate_district}})
                    lihtc_property.senate_district = senate_district
                if (lihtc_property.federal_congressional_district
                    != federal_congressional_district):
                    changes.update({'federal_congressional_district': {
                        'pre': lihtc_property.federal_congressional_district,
                        'post': federal_congressional_district}})
                    lihtc_property.federal_congressional_district \
                        = federal_congressional_district
                if lihtc_property.census_tract != census_tract:
                    changes.update({'census_tract': {
                        'pre': lihtc_property.census_tract,
                        'post': census_tract}})
                    lihtc_property.census_tract = census_tract
                if (lihtc_property.assessor_parcel_number
                    != assessor_parcel_number):
                    changes.update({'assessor_parcel_number': {
                        'pre': lihtc_property.assessor_parcel_number,
                        'post': assessor_parcel_number}})
                    lihtc_property.assessor_parcel_number \
                        = assessor_parcel_number
                if lihtc_property.application_stage != application_stage:
                    changes.update({'application_stage': {
                        'pre': lihtc_property.application_stage,
                        'post': application_stage}})
                    lihtc_property.application_stage = application_stage
                if lihtc_property.placed_in_service != placed_in_service:
                    changes.update({'placed_in_service': {
                        'pre': lihtc_property.placed_in_service,
                        'post': placed_in_service}})
                    lihtc_property.placed_in_service = placed_in_service
                if lihtc_property.last_building != last_building:
                    changes.update({'last_building': {
                        'pre': lihtc_property.last_building,
                        'post': last_building}})
                    lihtc_property.last_building = last_building
                if lihtc_property.construction_type != construction_type:
                    changes.update({'construction_type': {
                        'pre': lihtc_property.construction_type,
                        'post': construction_type}})
                    lihtc_property.construction_type = construction_type
                if lihtc_property.housing_type != housing_type:
                    changes.update({'housing_type': {
                        'pre': lihtc_property.housing_type,
                        'post': housing_type}})
                    lihtc_property.housing_type = housing_type
                if lihtc_property.total_units != total_units:
                    changes.update({'total_units': {
                        'pre': lihtc_property.total_units,
                        'post': total_units}})
                    lihtc_property.total_units = total_units
                if lihtc_property.low_income_units != low_income_units:
                    changes.update({'low_income_units': {
                        'pre': lihtc_property.low_income_units,
                        'post': low_income_units}})
                    lihtc_property.low_income_units = low_income_units
                if changes:
                    sys.stderr.write("(Changed %s %s PIS: %s => %s)\n" % (
                        tcac_number, county, placed_in_service, changes))
                    # Because we did a bad import first time around.
                    if 'street_address' in changes:
                        del changes['street_address']
                    prev_import_dt = datetime.datetime(
                        2015, 9, 26, 20, 35, 51, 196871, tzinfo=utc)
                    if ('placed_in_service' in changes and
                        changes['placed_in_service']['pre'] == prev_import_dt):
                        del changes['placed_in_service']
                    if ('last_building' in changes and
                        changes['last_building']['pre'] == prev_import_dt):
                        del changes['last_building']
                    if changes:
                        sys.stderr.write("Cleaned %s %s PIS: %s => %s\n" % (
                            tcac_number, county, placed_in_service, changes))
                    lihtc_property.save()
                else:
                    sys.stderr.write("Skipped %s %s PIS: %s (no change)\n" % (
                        tcac_number, county, placed_in_service))
                loop = False
            else:
                sys.stderr.write("Create  %s %s PIS: %s (new)\n" % (
                    tcac_number, county, placed_in_service))
                try:
                    if len(slug) > 50:
                        sys.stderr.write(
                            'error: %s "slug" is too long (\'%s\')\n' % (
                            tcac_number, slug))
                    if len(tcac_number) > 50:
                        sys.stderr.write(
                            'error: %s "tcac_number" is too long (\'%s\')\n' % (
                            tcac_number, tcac_number))
                    if len(locality) > 50:
                        sys.stderr.write(
                            'error: %s "locality" is too long (\'%s\')\n' % (
                            tcac_number, locality))
                    if len(postal_code) > 50:
                        sys.stderr.write(
                            'error: %s "postal_code" is too long (\'%s\')\n' % (
                            tcac_number, postal_code))
                    if len(account) > 50:
                        sys.stderr.write(
                            'error: %s "account" is too long (\'%s\')\n' % (
                            tcac_number, account))
                    if len(phone) > 50:
                        sys.stderr.write(
                            'error: %s "phone" is too long (\'%s\')\n' % (
                            tcac_number, phone))
                    if len(assessor_parcel_number) > 200:
                        sys.stderr.write(
                'error: %s "assessor_parcel_number" is too long (\'%s\')\n' % (
                            tcac_number, assessor_parcel_number))
                    with transaction.atomic():
                        lihtc_property = Property.objects.create(
                            slug=slug,
                            tcac_number=tcac_number,
                            account=account,
                            tax_credit_funding=tax_credit_funding,
                            name=name,
                            street_address=street_address,
                            county=county,
                            bin_number='',
                            locality=locality,
                            postal_code=postal_code,
                            phone=phone,
                            assembly_district=assembly_district,
                            senate_district=senate_district,
        federal_congressional_district=federal_congressional_district,
                            census_tract=census_tract,
                            assessor_parcel_number=assessor_parcel_number,
                            application_stage=application_stage,
                            placed_in_service=placed_in_service,
                            last_building=last_building,
                            construction_type=construction_type,
                            housing_type=housing_type,
                            total_units=total_units,
                            low_income_units=low_income_units)
                    loop = False
                    if output:
                        output.write(sep + "('%s', '%s', 't', 'f', 'f', "\
    "'%s', '%s', '%s', '%s', '%s', 'CA', '%s', 'US', 0, 1)" % (
        slug, created_at, name.replace("'", "''"), email, phone,
        street_address.replace("'", "''"), locality.replace("'", "''"),
        postal_code))
                    sep = ",\n"
                except IntegrityError:
                    idx = idx + 1
                    suffix = '-%d' % idx
                    slug = slug_base + suffix
                    if len(slug) > 50:
                        slug = slug_base[:(50-len(suffix))] + suffix

        if lihtc_property:
            # 21 Number of SRO/Studio Units
            # 22 Number of 1 Bedroom Units
            # 23 Number of 2 Bedroom Units
            # 24 Number of 3 Bedroom Units
            # 25 Number of 4 Bedroom Units
            # 26 Number of 5 Bedroom Units
            # 27 Number of 6 Bedroom Units
            for nb_bedrooms in range(0, 6):
                try:
                    units = int(row[21 + nb_bedrooms])
                except ValueError:
                    units = 0
                if units > 0:
                    name = "%d Bedrooms" % nb_bedrooms
                    if nb_bedrooms == 0:
                        name = "SRO/Studio"
                    elif nb_bedrooms == 1:
                        name = "1 Bedroom"
                    utility_allowance, created \
                        = UtilityAllowance.objects.get_or_create(
                            lihtc_property=lihtc_property,
                            nb_bedrooms=nb_bedrooms,
                            defaults={'created_at': created_at, 'units': units,
                                'name': name})
                    if not created and utility_allowance.units != units:
                        # XXX Shifted on first import
                        utility_allowance.units = units
                        utility_allowance.save()
    #                    sys.stderr.write(
    #                   'warning: %s nb of units for %d bedrooms differs
    #                   ' (%d!=%d)\n'
    #                        % (lihtc_property.tcac_number, nb_bedrooms,
    #                           utility_allowance.units, units))

            # 28 Units at or below 30% AMI
            # 29 Units at 35% AMI
            # 30 Units at 40% AMI
            # 31 Units at 45% AMI
            # 32 Units at 50% AMI
            # 33 Units at 55% AMI
            # 34 Units at 60% AMI
            for idx, ami_percentage in enumerate([30, 35, 40, 45, 50, 55, 60]):
                try:
                    units = int(row[28 + idx])
                except ValueError:
                    units = 0
                if units > 0:
                    ami_units, created = PropertyAMIUnits.objects.get_or_create(
                        lihtc_property=lihtc_property,
                        ami_percentage=ami_percentage,
                        defaults={'units': units})
                    if not created and ami_units.units != units:
                        sys.stderr.write('warning: %s nb of units for'\
                            ' %d%% AMI differs {pre: %d, post: %d}\n'
                            % (lihtc_property.tcac_number,
                               ami_percentage, ami_units.units, units))
    if output:
        output.write(";\n")
