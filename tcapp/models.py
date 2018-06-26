#pylint: disable=too-many-lines
# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.
from __future__ import unicode_literals

import calendar, datetime, hashlib, logging, uuid
from functools import cmp_to_key

from dateutil.relativedelta import relativedelta
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.template.defaultfilters import slugify
from django_countries.fields import CountryField

from .utils import datetime_or_now

LOGGER = logging.getLogger(__name__)


@python_2_unicode_compatible
class County(models.Model):
    """
    County as described by HUD.
    """
    fips_2000 = models.CharField(max_length=10, null=True)
    fips_2010 = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    metro_area_name = models.CharField(max_length=100)
    cbsa_sub = models.CharField(max_length=50)
    region = models.CharField(max_length=2)
    is_metro = models.BooleanField()

    def __str__(self):
        return self.name

    @property
    def current_effective_date(self):
        queryset = self.income_limits.all().order_by(
            '-created_at').values('created_at').first()
        return queryset.get('created_at')

    @property
    def current_income_limits(self):
        limits = []
        effective_date = None
        for limit in self.income_limits.all().order_by(
                '-created_at', 'family_size'):
            if effective_date is None:
                effective_date = limit.created_at
                limits += [limit]
            elif effective_date != limit.created_at:
                break
            else:
                limits += [limit]
        return limits

    @property
    def current_rent_limits(self):
        limits = []
        effective_date = None
        for limit in self.rent_limits.all().order_by(
                '-created_at', 'nb_bedrooms'):
            if effective_date is None:
                effective_date = limit.created_at
                limits += [limit]
            elif effective_date != limit.created_at:
                break
            else:
                limits += [limit]
        return limits


@python_2_unicode_compatible
class RentLimit(models.Model):
    """
    Maximum Federal LIHTC Rent Limit
    """
    created_at = models.DateTimeField()
    county = models.ForeignKey(County, related_name="rent_limits")
    nb_bedrooms = models.IntegerField()
    full_amount = models.IntegerField(help_text='100%')

    class Meta:
        unique_together = ('created_at', 'county', 'nb_bedrooms')

    def __str__(self):
        return "%s_%s_%d" % (
            self.created_at.strftime("%Y-%m-%d"),
            slugify(self.county.name),
            self.nb_bedrooms
        )

    def as_percent(self, percent):
        percent_amount = (self.full_amount * percent) / 100
        rem = percent_amount % 100
        if rem > 25:
            percent_amount += 100 - rem
            if percent == 60:
                for county_name, nb_bedrooms in [
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
                        ('Tuolumne County', 3)]:
                    if (self.county.name == county_name
                        and self.nb_bedrooms == nb_bedrooms):
                        percent_amount -= 100
                        break
        else:
            percent_amount -= rem
            if percent == 60:
                for county_name, nb_bedrooms in [
                        ('Amador County', 3),
                        ('Lassen County', 5),
                        ('Los Angeles County', 3),
                        ('Mariposa County', 3),
                        ('Mendocino County', 3),
                        ('Nevada County', 5),
                        ('San Benito County', 3),
                        ('San Diego County', 3),
                        ('Solano County', 5)]:
                    if (self.county.name == county_name
                        and self.nb_bedrooms == nb_bedrooms):
                        percent_amount += 100
                        break
        return percent_amount

    @property
    def fifty_percent(self):
        return self.as_percent(50)

    @property
    def sixty_percent(self):
        return self.as_percent(60)


@python_2_unicode_compatible
class IncomeLimit(models.Model):
    """
    Maximum Federal LIHTC Income Limit
    """
    created_at = models.DateTimeField()
    county = models.ForeignKey(County, related_name="income_limits")
    family_size = models.IntegerField()
    full_amount = models.IntegerField(help_text='100% of median income')

    class Meta:
        unique_together = ('created_at', 'county', 'family_size')

    def __str__(self):
        return "%s_%s_%d" % (
            datetime.datetime.strftime("%Y-%m-%d", self.created_at),
            self.county.name.lower(),
            self.family_size
        )

    def as_percent(self, percent):
        return (self.full_amount * percent) // 100

    @property
    def fifty_percent(self):
        return self.as_percent(50)

    @property
    def sixty_percent(self):
        return self.as_percent(60)


@python_2_unicode_compatible
class Property(models.Model):
    """
    Property for which an Application is registered
    """
    APPLICATION_STAGE = (
        (0, "Unknown"),
        (1, "Extended"),
        (2, "Placed in Service"),
        (3, "Preliminary Reservation"),
    )

    CONSTRUCTION_TYPE = (
        (0, "Unknown"),
        (1, "Acquisition/Rehabilitation"),
        (2, "NC/AR"),
        (3, "New Construction"),
        (4, "New Construction/ Acq. Rehab."),
        (5, "Rehabilitation"),
    )

    HOUSING_TYPE = (
        (0, "Unknown"),
        (1, "At-Risk"),
        (2, "Large Family"),
        (3, "Non Targeted"),
        (4, "Special Needs"),
        (5, "Special Needs/Large Family"),
        (6, "SRO"),
        (7, "SRO/At-Risk"),
    )

    # Tenant Income Certification - Part I Development Data
    slug = models.SlugField(unique=True)
    account = models.SlugField() # organization
    name = models.CharField(max_length=100)
    county = models.ForeignKey(County)
    tcac_number = models.CharField(max_length=50)
    bin_number = models.CharField(max_length=50)
    cdlac_number = models.CharField(max_length=50, null=True)
    # XXX Keep information consistent with organization
    street_address = models.CharField(max_length=150)
    locality = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=50)
    phone = models.CharField(max_length=50)
    # --
    tax_credit_funding = models.IntegerField(default=0)
    assembly_district = models.IntegerField(default=0)
    senate_district = models.IntegerField(default=0)
    federal_congressional_district = models.IntegerField(default=0)
    census_tract = models.DecimalField(
        max_digits=12, decimal_places=2, default=0)
    assessor_parcel_number = models.CharField(max_length=200)
    application_stage = models.PositiveSmallIntegerField(
        choices=APPLICATION_STAGE, default=0)
    placed_in_service = models.DateTimeField(null=True)
    last_building = models.DateTimeField(null=True)
    construction_type = models.PositiveSmallIntegerField(
        choices=CONSTRUCTION_TYPE, default=0)
    housing_type = models.PositiveSmallIntegerField(
        choices=HOUSING_TYPE, default=0)
    total_units = models.IntegerField(default=0)
    low_income_units = models.IntegerField(default=0)

    def __str__(self):
        return self.slug

    @property
    def region(self):
        return self.county.region

    @property
    def printable_name(self):
        return self.name


@python_2_unicode_compatible
class PropertyAMIUnits(models.Model):
    """
    Average Median income under the program for a ``Property``.
    """
    lihtc_property = models.ForeignKey(Property)
    ami_percentage = models.IntegerField(default=0)
    units = models.IntegerField(default=0)

    def __str__(self):
        return '%s<%s>' % (self.__class__, self.lihtc_property)


@python_2_unicode_compatible
class UtilityAllowance(models.Model):
    """
    Utility allowance schedule for a ``Property``.
    """
    created_at = models.DateTimeField()
    lihtc_property = models.ForeignKey(Property,
        related_name='utility_allowances')
    nb_bedrooms = models.IntegerField(null=True)
    full_amount = models.IntegerField(default=0)
    non_optional_amount = models.IntegerField(default=0)
    units = models.IntegerField(default=0)
    name = models.CharField(max_length=100)

    def __str__(self):
        return '%s<%s, %s, %d>' % (self.__class__,
            self.lihtc_property, self.created_at, self.nb_bedrooms)


@python_2_unicode_compatible
class Application(models.Model):
    """
    Application for rental of a unit under LIHTC
    """
    STATUS_NEW_APPLICATION = 0
    STATUS_VERIFICATION = 1
    STATUS_HOUSEHOLD_INCOME = 2
    STATUS_CERTIFICATION = 3
    STATUS_LEASE = 4
    STATUS_MOVE_IN = 5
    STATUS_RE_CERTIFICATION = 6
    STATUS_ARCHIVED = 7

    STATUS = (
        (STATUS_NEW_APPLICATION, "new-application"),
        (STATUS_VERIFICATION, "verification"),
        (STATUS_HOUSEHOLD_INCOME, "household-income"),
        (STATUS_CERTIFICATION, "certification"),
        (STATUS_LEASE, "lease"),
        (STATUS_MOVE_IN, "move-in"),
        (STATUS_RE_CERTIFICATION, "re-certification"),
        (STATUS_ARCHIVED, "archived"), # i.e. over income
    )

    HUMANIZED_STATUS = (
        (STATUS_NEW_APPLICATION, "New application"),
        (STATUS_VERIFICATION, "Verification"),
        (STATUS_HOUSEHOLD_INCOME, "Household Income"),
        (STATUS_CERTIFICATION, "Certification"),
        (STATUS_LEASE, "Lease"),
        (STATUS_MOVE_IN, "Move-in"),
        (STATUS_RE_CERTIFICATION, "Re-certification"),
        (STATUS_ARCHIVED, "Archived"), # i.e. over income
    )

    FEDERAL_RENT_ASSISTANCE_SOURCE = (
        (1, "1. ** HUD Multi-Family Project Based Rental Assistance (PBRA)"),
        (2, "2. Section 8 Moderate Rehabilitation"),
        (3, "3. Public Housing Operating Subsidy"),
        (4, "4. HOME Rental Assistance"),
        (5, "5. HUD Housing Choice Voucher (HCV), tenant-based"),
        (6, "6. HUD Project-based Voucher (PBV)"),
        (7, "7. USDA Section 521 Rental Assistance Program"),
        (8, "8. Other Federal Rental Assistance"),
        (0, "0. Missing"))

    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    status = models.PositiveSmallIntegerField(choices=STATUS, default=0)
    owner = models.SlugField() # user
    certification_type = models.CharField( # Initial, Recertification, Other.
        max_length=16, null=True, default='initial')
    effective_date = models.DateTimeField(auto_now_add=True)
    move_in_date = models.DateTimeField(auto_now_add=True)

    # Part I Development Data
    lihtc_property = models.ForeignKey(Property)
    unit_number = models.CharField(max_length=50, null=True)
    nb_bedrooms = models.IntegerField(null=True, default=1)
    square_footage = models.IntegerField(null=True)
    household_vacant = models.BooleanField(default=False, help_text=
        "Check if unit was vacant on December 31 of the Effective Date Year")

    # Part II, III, IV, and V Determination of Income Eligibility
    federal_income_restriction = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)], default=0)
    # Part VI Rent
    monthly_rent = models.IntegerField(default=0)
    monthly_utility_allowance = models.IntegerField(default=0)
    monthly_other_charges = models.IntegerField(default=0)
    federal_rent_restriction = models.PositiveSmallIntegerField(default=0,
        validators=[MinValueValidator(1), MaxValueValidator(100)])
    bond_rent_restriction = models.PositiveSmallIntegerField(default=0,
        validators=[MinValueValidator(1), MaxValueValidator(100)])
    federal_rent_assistance = models.IntegerField(default=0)
    non_federal_rent_assistance = models.IntegerField(default=0)
    rent_assistance_source = models.PositiveSmallIntegerField(
        choices=FEDERAL_RENT_ASSISTANCE_SOURCE, null=True)

    # Part VIII Program Type
    program_tax_credit = models.BooleanField(default=False)
    program_home = models.BooleanField(default=False)
    program_tax_exempt = models.BooleanField(default=False)
    program_ahdp = models.BooleanField(default=False)
    program_other = models.CharField(max_length=50, null=True,
        help_text='Name of program')
    program_home_rate = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)], null=True, default=0)
    program_tax_exempt_rate = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)], null=True, default=0)
    program_ahdp_rate = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)], null=True, default=0)
    program_other_rate = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(100)], null=True, default=0)

    applicants = models.ManyToManyField('tcapp.Resident',
        related_name='applications', through='tcapp.ApplicationResident')

    def __str__(self):
        return self.slug

    def children_residents(self):
        eighteen_years_ago = datetime_or_now() - relativedelta(years=18)
        return self.applicants.filter(date_of_birth__gte=eighteen_years_ago)

    @property
    def residents(self):
        if not hasattr(self, '_residents'):
            self._residents = ApplicationResident.objects.filter(
                application=self).order_by(
                'relation_to_head', 'id').select_related('resident')
        return self._residents

    @property
    def printable_name(self):
        head_of_household = self.head
        if head_of_household:
            return head_of_household.printable_name
        return self.slug

    @property
    def is_other_certification(self):
        return self.certification_type not in ['initial', 'recertification']

    @property
    def gross_monthly_rent_for_unit(self):
        return (self.monthly_rent + self.monthly_utility_allowance
            + self.monthly_other_charges)

    @property
    def earned_income(self):
        result = 0
        for applicant in self.applicants.all():
            result += applicant.earned_income
        return result

    @property
    def social_security_and_pensions(self):
        result = 0
        for applicant in self.applicants.all():
            result += applicant.social_security_and_pensions
        return result

    @property
    def public_assistance(self):
        result = 0
        for applicant in self.applicants.all():
            result += applicant.public_assistance
        return result

    @property
    def other_income(self):
        result = 0
        for applicant in self.applicants.all():
            result += applicant.other_income
        return result

    @property
    def total_income(self):
        return (self.earned_income
                + self.social_security_and_pensions
                + self.public_assistance
                + self.other_income)

    @property
    def cash_value_of_assets(self):
        result = 0
        for applicant in self.applicants.all():
            result += applicant.cash_value_of_assets
        return result

    @property
    def has_no_assets(self):
        return not Asset.objects.filter(resident__applications=self).exists()

    @property
    def annual_income_from_assets(self):
        result = 0
        for applicant in self.applicants.all():
            result += applicant.annual_income_from_assets
        return result

    @property
    def imputed_income_from_assets(self):
        total = self.cash_value_of_assets
        if total < 500000:
            result = 0
        else:
            result = (total * 6) / 10000
        return result

    @property
    def total_income_from_assets(self):
        return max(self.annual_income_from_assets,
            self.imputed_income_from_assets)

    @property
    def total_annual_income(self):
        return self.total_income + self.total_income_from_assets

    @property
    def family_size(self):
        return self.applicants.count()

    @property
    def income_limit_100(self):
        # Latest income limit that was published
        # before the application effective date.
        limit = self.lihtc_property.county.income_limits.filter(
            family_size=self.family_size,
            created_at__lt=self.effective_date).order_by('-created_at').first()
        if limit:
            full_amount = limit.full_amount
        else:
            full_amount = 0
        return full_amount

    @property
    def income_limit_140(self):
        return self.income_limit * 140 / 100

    def get_income_limit(self, restriction=None):
        """
        Current Federal LIHTC Income Limit per Family Size pro-rated
        by the Federal Income Restriction for the unit, either 60%,
        50% (very low income) or sometimes lower for deeper targetting.
        """
        full_amount = self.income_limit_100
        if restriction is None:
            try:
                restriction = int(self.federal_income_restriction)
            except TypeError:
                restriction = 0
        return (full_amount * restriction) / 100

    @property
    def income_limit(self):
        return self.get_income_limit()

    @property
    def rent_limit(self):
        limit = RentLimit.objects.filter(
            county=self.lihtc_property.county,
            nb_bedrooms=self.nb_bedrooms,
            created_at__lt=self.effective_date).order_by('-created_at').first()
        if limit:
            full_amount = limit.full_amount
        else:
            full_amount = 0
        try:
            federal_rent_restriction = int(self.federal_rent_restriction)
        except TypeError:
            federal_rent_restriction = 0
        return (full_amount * federal_rent_restriction) / 100

    @property
    def total_rent_assistance(self):
        return self.federal_rent_assistance + self.non_federal_rent_assistance

    @property
    def is_eligible_140(self):
        return self.total_annual_income <= self.income_limit_140

    @property
    def head(self):
        head_of_household = ApplicationResident.objects.filter(application=self,
            relation_to_head=ApplicationResident.HEAD_OF_HOUSEHOLD).first()
        if head_of_household:
            return head_of_household.resident
        return None

    @property
    def full_time_student(self):
        #pylint:disable=no-member
        return self.head.full_time_student

    @property
    def current_full_time_student(self):
        #pylint:disable=no-member
        result = False
        for student_answer in Answer.objects.filter(
                resident__in=self.applicants.all(),
                question__in=Question.CURRENT_FULL_TIME_STUDENT):
            result |= student_answer.present
        return result

    @property
    def past_full_time_student(self):
        #pylint:disable=no-member
        result = False
        for student_answer in Answer.objects.filter(
                resident__in=self.applicants.all(),
                question__in=Question.PAST_FULL_TIME_STUDENT):
            result |= student_answer.present
        return result

    @property
    def future_full_time_student(self):
        #pylint:disable=no-member
        result = False
        for student_answer in Answer.objects.filter(
                resident__in=self.applicants.all(),
                question__in=Question.FUTURE_FULL_TIME_STUDENT):
            result |= student_answer.present
        return result

    @property
    def student_explanation(self):
        #pylint:disable=no-member
        result = []
        for student_answer in Answer.objects.filter(resident=self.head,
            present=True, question__in=Question.STUDENT_EXPLANATION).order_by(
                'question__rank').values('question__rank'):
            result += [student_answer['question__rank']
                - Question.STUDENT_EXPLANATION[0] + 1]
        return result

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.slug:
            self.slug = slugify(uuid.uuid4().hex)
        return super(Application, self).save(force_insert=force_insert,
            force_update=force_update, using=using, update_fields=update_fields)

    @property
    def tenants(self):
        if not hasattr(self, '_tenants'):
            eighteen_years_ago = datetime_or_now(
                self.effective_date) - relativedelta(years=18)
            self._tenants = ApplicationResident.objects.filter(application=self,
                resident__date_of_birth__lt=eighteen_years_ago).order_by(
                    'relation_to_head', 'id').select_related('resident')
        return self._tenants


@python_2_unicode_compatible
class Resident(models.Model):
    """
    Resident on an Application (Part II Household Composition)
    """
    #pylint:disable=too-many-instance-attributes

    MARRIED_FILE_JOINTLY = 1
    SEPARATED = 2
    LEGALY_SEPARATED = 3

    MARITAL_STATUS = {
        (0, "Other"),
        (MARRIED_FILE_JOINTLY,
         "Married and filing (or are entitled to file) a joint tax return"),
        (SEPARATED, "Separated"),
        (LEGALY_SEPARATED, "Legaly Separated"),
    }

    # XXX Can choose multiple
    # bit position or power of 2
    RACE = [
        (1, 'White'),
        (2, 'Black / African American'),
        (4, 'American Indian / Alaska Native'),
        (8, 'Asian'),
        (16, 'Native Hawaiian / Other Pacific Islander'),
        (32, 'Other'),
        (64, 'Did not respond')
    ]

    ETHNICITY = [
        (1, 'Hispanic'),
        (2, 'Not Hispanic'),
        (3, 'Did not respond')
    ]

    DISABILITY = [
        (1, 'Yes'),
        (2, 'No'),
        (3, 'Did not respond')
    ]

    slug = models.SlugField(unique=True)
    # Part II Household Composition
    # The ``full_name`` is as entered by the resident. ``first_name``,
    # ``last_name`` and ``middle_initial`` are derived from the ``full_name``
    # through ``full_name_natural_split`` whenever possible or entered directly
    # if they cannot be accurately infered.
    full_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    middle_initial = models.CharField(max_length=5, null=True, blank=True)
    date_of_birth = models.DateTimeField()
    marital_status = models.PositiveSmallIntegerField(
        choices=MARITAL_STATUS, null=True)

    # Part IX supplemental information form
    race = models.PositiveSmallIntegerField(choices=RACE, null=True)
    ethnicity = models.PositiveSmallIntegerField(choices=ETHNICITY, null=True)
    disabled = models.PositiveSmallIntegerField(choices=DISABILITY, null=True)
    ssn = models.CharField(max_length=50, null=True)

    # Contact information
    email = models.EmailField(null=True)
    phone = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.slug

    @property
    def ssn_last4(self):
        if self.ssn is None:
            return "N/A"
        if len(self.ssn) < 4:
            return str(self.ssn)
        return str(self.ssn)[-4:]

    @property
    def has_no_income(self):
        return not Income.objects.filter(resident=self).exists()

    @property
    def race_code(self):
        result = ""
        if self.race is None:
            self.race = 0
        for idx in range(0, 7):
            code = self.race & (1 << idx)
            if code:
                result += str(idx + 1)
        return result

    @property
    def is_unborn(self):
        app_resident = ApplicationResident.objects.filter(resident=self).first()
        return (app_resident and
            app_resident.relation_to_head == ApplicationResident.UNBORN_CHILD)

    @property
    def is_adult(self):
        age = relativedelta(datetime_or_now(), self.date_of_birth)
        return age.years >= 21

    @property
    def is_marital_separation(self):
        return self.marital_status in [
            Resident.SEPARATED, Resident.LEGALY_SEPARATED]

    @property
    def cash_wages(self):
        return self.income.filter(cash_wages=True).exists()

    @property
    def full_time_student(self):
        #pylint:disable=no-member
        result = False
        for student_answer in Answer.objects.filter(
                resident=self, question__in=Question.FULL_TIME_STUDENT):
            result |= student_answer.present
        return result

    @property
    def printable_name(self):
        if self.full_name:
            return self.full_name
        result = self.first_name
        if self.middle_initial:
            result += " %s" % self.middle_initial
        result += " %s" % self.last_name
        return result

    @property
    def current_address(self):
        if not hasattr(self, '_current_address'):
            self._current_address = self.past_addresses.order_by(
                'starts_at').first()
        return self._current_address

    def assets_by_source(self):
        """
        Returns a dictionnary by source, by verification type of ``Asset``.
        """
        group_by = {}
        for asset in Asset.objects.filter(resident=self).order_by(
                'question', 'source', 'category', 'verified'):
            # If not source, make one up.
            source = asset.source if asset.source else 'no-source'
            if source not in group_by:
                group_by[source] = {}
            if asset.category not in group_by[source]:
                group_by[source][asset.category] = []
            group_by[source][asset.category] += [asset]
        return group_by

    def income_by_source(self):
        """
        Returns a dictionnary by questions, by source, by verification type
        of ``Income``.
        """
        group_by = {}
        income_iter = Income.objects.filter(resident=self).order_by(
            'question', 'source', 'verified').iterator()
        questions = Question.objects.filter(category=Question.INCOME).order_by(
            'id')
        for question in questions:
            group_by[question] = {}
        try:
            income = next(income_iter)
            for question in group_by:
                while income.question_id <= question.id:
                    # If not source, make one up.
                    source = income.source if income.source else 'no-source'
                    if source not in group_by[question]:
                        group_by[question][source] = {}
                    if income.verified not in group_by[question][source]:
                        group_by[question][source][income.verified] = []
                    group_by[question][source][income.verified] += [income]
                    income = next(income_iter)
        except StopIteration:
            pass
        return group_by

    # Part III Gross Annual Income
    @property
    def total_income(self):
        try:
            return (self.earned_income + self.social_security_and_pensions
                    + self.public_assistance + self.other_income)
        except ValueError:
            # XXX until we figure out how to report divide by zero
            return six.MAXSIZE

    @property
    def earned_income(self):
        try:
            return self.self_employed_income + self.employee_income
        except ValueError as err:
            # XXX until we figure out how to report divide by zero
            LOGGER.exception("error: computing earned income - %s", err)
            return six.MAXSIZE

    @property
    def self_employed_income(self):
        if not hasattr(self, '_self_employed_income'):
            self._self_employed_income = self.get_income_by_questions(
                Question.INCOME_SELF_EMPLOYED)
        return self._self_employed_income

    @property
    def employee_income(self):
        """
        Returns the annualized income for W2 employees.
        """
        if not hasattr(self, '_employee_income'):
            self._employee_income = self.get_income_by_questions(
                Question.INCOME_EMPLOYEE)
        return self._employee_income

    @property
    def social_security_and_pensions(self):
        if not hasattr(self, '_social_security_and_pensions'):
            self._social_security_and_pensions = self.get_income_by_questions(
                Question.B_SOCIAL_SECURITY_AND_PENSIONS)
        return self._social_security_and_pensions

    @property
    def public_assistance(self):
        if not hasattr(self, '_public_assistance'):
            self._public_assistance = self.get_income_by_questions(
                Question.C_PUBLIC_ASSISTANCE)
        return self._public_assistance

    @property
    def other_income(self):
        if not hasattr(self, '_other_income'):
            self._other_income = self.get_income_by_questions(
                Question.D_OTHER_INCOME)
        return self._other_income

    def get_income_by_questions(self, questions):
        #pylint:disable=too-many-nested-blocks
        results = {}
        group_by = self.income_by_source()
        for question_id in questions:
            for question, group in six.iteritems(group_by):
                if question.pk == question_id:
                    # We have to loop through the sources because of the same
                    # source can be used accross multiple questions (ex: N/A).
                    for source, verifications in six.iteritems(group):
                        if source in results:
                            for verified, incomes in six.iteritems(
                                    verifications):
                                if verified in results[source]:
                                    results[source][verified] += incomes
                                else:
                                    results[source].update({verified: incomes})
                        else:
                            results.update({source: verifications})
        return sum_greater_of_annualize_income(results)

    # Part IV Income From Assets
    def get_declared_assets(self):
        return Asset.objects.filter(
            resident=self, verified=Asset.VERIFIED_TENANT).order_by(
                'question', 'source', 'category')

    def get_greater_of_assets(self):
        results = []
        for verifications in six.itervalues(self.assets_by_source()):
            for assets in six.itervalues(verifications):
                results.append(greater_of_assets(assets))
        return results

    @property
    def cash_value_of_assets(self):
        if not hasattr(self, '_cash_value_of_assets'):
            self._cash_value_of_assets = 0
            for verifications in six.itervalues(self.assets_by_source()):
                for assets in six.itervalues(verifications):
                    greater_of = greater_of_assets(assets)
                    if greater_of:
                        self._cash_value_of_assets += greater_of.amount
        return self._cash_value_of_assets

    @property
    def annual_income_from_assets(self):
        if not hasattr(self, '_annual_income_from_assets'):
            self._annual_income_from_assets = 0
            for asset in self.get_greater_of_assets():
                self._annual_income_from_assets += asset.annual_income
        return self._annual_income_from_assets

    def student_financial_aid(self):
        """
        Returns the annualized amount of financial aid received by the tenant.
        TIC Questionnaire #15.
        """
        result = 0
        for income in self.income.filter(
            question__in=Question.INCOME_STUDENT_FINANCIAL_AID):
            result += income.annual_income
        return result

    def is_disabled(self):
        """
        Returns ``True`` if the resident has answered "Yes"
        on the TIC Questionnaire #9
        """
        return Answer.objects.filter(resident=self,
            question__in=Question.INCOME_DISABILITY,
            present=True).exists()

    def is_single_parent(self):
        """
        Returns ``True`` if the resident has answered "Yes"
        on the TIC Questionnaire #32
        """
        return Answer.objects.filter(resident=self,
            question__in=Question.SINGLE_PARENT,
            present=True).exists()

    def is_foster_care(self):
        """
        Returns ``True`` if the resident has answered "Yes"
        on the TIC Questionnaire #33.
        """
        return Answer.objects.filter(resident=self,
            question__in=Question.FOSTER_CARE,
            present=True).exists()

    def employee_sources(self):
        """
        Returns a ``QuesrySet`` of unique ``Source``s from which the resident
        derives employment income.
        """
        return Source.objects.filter(
            income__resident=self,
            income__question__in=Question.INCOME_EMPLOYEE).distinct()

    def support_awards_sources(self):
        return Source.objects.filter(
            income__resident=self,
            income__question__in=Question.CHILD_SPOUSAL_SUPPORT,
            income__court_award__in=Income.SUPPORT_AWARD_COURT).distinct()

    def child_spousal_support_sources(self):
        return Source.objects.filter(
            income__resident=self,
            income__question__in=Question.CHILD_SPOUSAL_SUPPORT).distinct()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.slug:
            self.slug = slugify(uuid.uuid4().hex)
        return super(Resident, self).save(force_insert=force_insert,
            force_update=force_update, using=using, update_fields=update_fields)


@python_2_unicode_compatible
class ApplicationResident(models.Model):

    HEAD_OF_HOUSEHOLD = 1
    UNBORN_CHILD = 10

    # RELATION_TO_HEAD are ordered by block (tenant followed by under age
    # children) such that sorting by relation will lead to consistent
    # rank in the TIC.
    RELATION_TO_HEAD = {
        (HEAD_OF_HOUSEHOLD, "HEAD"),
        (2, "Adult Co-Tenant"),
        (3, "Live-in Caretaker"),
        (4, "Spouse"),
        (5, "Foster adult"),
        (6, "Other Family Member"),
        (7, "None of the above"),
        # Under age to sign tenant agreement
        (8, "Child"),
        (9, "Foster child"),
        (UNBORN_CHILD, "Unborn child"),
        (11, "Anticipated adoption or foster"),
        (12, "None of the above"),
    }

    RELATION_TO_HEAD_TIC_CODE = {
        HEAD_OF_HOUSEHOLD: "H",
        2: "A",
        3: "L",
        4: "S",
        5: "F",
        6: "O",
        7: "N",
        # Under age to sign tenant agreement
        8: "C",
        9: "F",
        UNBORN_CHILD: "U",
        11: "U",
        12: "N"
    }

    DEPENDENTS = (8, 9, 10, 11)

    application = models.ForeignKey(Application)
    resident = models.ForeignKey(Resident, related_name="relation")
    relation_to_head = models.PositiveSmallIntegerField(default=1,
        choices=RELATION_TO_HEAD)

    class Meta:
        unique_together = ('application', 'resident')

    def __str__(self):
        return '%s-%s' % (self.application, self.resident)

    @property
    def printable_name(self):
        return self.resident.printable_name

    @property
    def relation_to_head_tic_code(self):
        return self.RELATION_TO_HEAD_TIC_CODE[self.relation_to_head]

    @property
    def income_verification_url(self):
        return reverse('income_verification',
            args=(self.application.lihtc_property, self.resident))

    @property
    def ticq_download_url(self):
        return reverse('tenant_verification_ticq',
            args=(self.application.lihtc_property, self.application,
                  self.resident))


@python_2_unicode_compatible
class HousingHistory(models.Model):
    """
    Tenant housing history for the past 2 years.
    """

    resident = models.ForeignKey(Resident, related_name="past_addresses")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    street_address = models.CharField(max_length=150)
    locality = models.CharField(max_length=50)
    region = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=50)
    country = CountryField()
    monthly_rent = models.IntegerField(default=0)

    def __str__(self):
        return "%s, %s, %s" % (self.street_address, self.locality, self.region)


@python_2_unicode_compatible
class Question(models.Model):

    INCOME = 1
    ASSETS = 2
    STUDENT = 3

    CATEGORY = (
        (INCOME, "Income"),
        (ASSETS, "Assets"),
        (STUDENT, "Student"),
    )

    # Income questions
    INCOME_SELF_EMPLOYED = [1]
    INCOME_EMPLOYEE = [2]
    INCOME_GIFTS = [3]
    INCOME_UNEMPLOYMENT_BENEFITS = [4]
    INCOME_VETERAN_BENEFITS = [5]
    INCOME_SOCIAL_BENEFITS = [6]
    INCOME_UNEARNED_INCOME = [7]
    INCOME_SUPPLEMENTAL_BENEFITS = [8]
    INCOME_DISABILITY = [9]
    INCOME_PUBLIC_ASSISTANCE = [10]
    INCOME_CHILD_SUPPORT_ENTITLED = [11]
    INCOME_CHILD_SUPPORT_RECEIVE = [11]
    INCOME_CHILD_SUPPORT_COLLECT = [11]
    INCOME_ALIMONY_SUPPORT = [12]
    INCOME_TRUSTS = [13]
    INCOME_PROPERTY = [14]
    INCOME_STUDENT_FINANCIAL_AID = [15]

    INCOME_BENEFITS = INCOME_UNEMPLOYMENT_BENEFITS + INCOME_VETERAN_BENEFITS \
        + INCOME_SOCIAL_BENEFITS + INCOME_SUPPLEMENTAL_BENEFITS \
        + INCOME_DISABILITY + INCOME_PUBLIC_ASSISTANCE
    INCOME_OTHERS = INCOME_GIFTS + INCOME_UNEARNED_INCOME \
        + INCOME_TRUSTS + INCOME_PROPERTY
    CHILD_SPOUSAL_SUPPORT = INCOME_CHILD_SUPPORT_ENTITLED \
        + INCOME_ALIMONY_SUPPORT
    CURRENT_FULL_TIME_STUDENT = [26]
    PAST_FULL_TIME_STUDENT = [27]
    FUTURE_FULL_TIME_STUDENT = [28]
    FULL_TIME_STUDENT = CURRENT_FULL_TIME_STUDENT + PAST_FULL_TIME_STUDENT + \
        FUTURE_FULL_TIME_STUDENT
    SINGLE_PARENT = [32]
    FOSTER_CARE = [33]
    STUDENT_STATUS_TITLE_IV = [29]
    STUDENT_STATUS_JOB_TRAINING = [30]
    STUDENT_EXPLANATION = STUDENT_STATUS_TITLE_IV + STUDENT_STATUS_JOB_TRAINING\
        + [31] + SINGLE_PARENT + FOSTER_CARE

    A_EMPLOYMENT_OR_WAGES = INCOME_SELF_EMPLOYED + INCOME_EMPLOYEE
    B_SOCIAL_SECURITY_AND_PENSIONS = [5, 6, 8, 13]
    C_PUBLIC_ASSISTANCE = INCOME_DISABILITY + [10]
    D_OTHER_INCOME = [3, 4, 7, 14] \
        + CHILD_SPOUSAL_SUPPORT + INCOME_STUDENT_FINANCIAL_AID

    ASSET_IMPUTED = 25

    # Assets questions
    CHECKING = [16]
    SAVINGS = [17]
    REVOCABLE_TRUST = [18]
    REAL_ESTATE = [19]
    STOCKS = [20]
    MONEY_MARKET = [21]
    RETIREMENT = [22]
    DISPOSED_ASSETS = [25]
    OWN_OR_DISPOSED_REAL_ESTATE = [19] + DISPOSED_ASSETS
    FINANCIAL_ACCOUNTS = [16, 17, 18, 20, 21, 22]
    LIFE_INSURANCE = [23]
    CASH_ON_HAND = [24]

    slug = models.SlugField()
    title = models.TextField(
        help_text="Short title for the question (ex: Wages, Social Security)")
    text = models.TextField(
        help_text="Full text of the question (answer by yes or no)")
    rank = models.IntegerField()
    category = models.PositiveSmallIntegerField(choices=CATEGORY, null=True)
    multiple_sources = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pk)


class AnswerManager(models.Manager):

    def populate(self, resident):
        """
        Return a list of ``Answer`` for all questions
        in thequestionnaire.
        associated to a *response* even when there are no such record
        in the db.
        """
        answers = list(self.filter(resident=resident))
        questions = Question.objects.exclude(
            pk__in=[answer.question_id for answer in answers])
        for question in questions:
            answers += [Answer(question=question)]
        answers.sort(key=cmp_to_key(
            lambda x, y: (y.question.rank < x.question.rank)
            - (y.question.rank > x.question.rank)))
        return answers


@python_2_unicode_compatible
class Answer(models.Model):

    objects = AnswerManager()

    question = models.ForeignKey(Question)
    resident = models.ForeignKey(Resident, related_name="questionnaire")
    present = models.BooleanField()

    class Meta:
        unique_together = ('resident', 'question')

    def __str__(self):
        resident = self.resident if self.resident_id else None
        return "%s/%d" % (resident, self.question.rank)

    @property
    def is_valid(self):
        return self.present is not None

    @property
    def rank(self):
        return not self.question.rank


class SourceManager(models.Manager):

    @staticmethod
    def candidate(resident, question):
        candidate = None
        queryset = Income.objects.filter(
            resident=resident, question=question)
        previous = queryset.first()
        if previous:
            candidate = previous.source
        if candidate is None:
            address = resident.past_addresses.all().order_by('ends_at').first()
            if address:
                country = address.country
                region = address.region
            else:
                country = 'US'
                region = 'CA'
            candidate = Source(country=country, region=region)
        return candidate


@python_2_unicode_compatible
class Source(models.Model):
    """
    Source of the income (employer address, etc.) or asset (bank, etc.)
    """
    objects = SourceManager()

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=50, null=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    street_address = models.CharField(max_length=150, null=True, blank=True)
    locality = models.CharField(max_length=50, null=True, blank=True)
    region = models.CharField(max_length=50, null=True)
    postal_code = models.CharField(max_length=50, null=True, blank=True)
    country = CountryField(null=True)
    resident = models.ForeignKey(Resident, related_name="sources")

    # related to employment
    position = models.CharField(max_length=50, null=True, blank=True)
    mananger = models.CharField(max_length=50, null=True)

    # related to support payments
    dependents = models.ManyToManyField(Resident, related_name="dependents")

    def __str__(self):
        return self.slug

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.slug:
            self.slug = slugify(uuid.uuid4().hex)
        return super(Source, self).save(force_insert=force_insert,
            force_update=force_update, using=using, update_fields=update_fields)

    @property
    def printable_name(self):
        if self.position:
            return "%s at %s" % (self.position, self.name)
        if self.name and self.name != "N/A":
            return self.name
        return ""


@python_2_unicode_compatible
class Asset(models.Model):
    """
    Details of the asset declared by the tenant.
    """
    OWNER = 0
    NORMAL_SALE = 1
    FORECLOSURE = 2
    SHORT_SALE = 3
    BANK_CHECKING = 4
    BANK_SAVINGS = 5
    BANK_CD = 6
    BANK_MONEY_MARKET = 7
    BANK_REVOKABLE_TRUST = 8
    BANK_IRA = 9
    BANK_LUMP_SUM_PENSION = 10
    BANK_KEOGH_ACCOUNT = 11
    BANK_401K = 12
    BANK_BROKERAGE = 13
    LIFE_INSURANCE = 14
    CASH_ASSET = 15

    CATEGORY = {
        (OWNER, "own"),
        (NORMAL_SALE, "normal sale"),
        (FORECLOSURE, "foreclosure"),
        (SHORT_SALE, "short sale"),
        (BANK_CHECKING, "checking"),
        (BANK_SAVINGS, "savings"),
        (BANK_CD, "certificate of deposit"),
        (BANK_MONEY_MARKET, "money market"),
        (BANK_REVOKABLE_TRUST, "revokable trust"),
        (BANK_IRA, "IRA"),
        (BANK_LUMP_SUM_PENSION, "lump sump pension"),
        (BANK_KEOGH_ACCOUNT, "Keogh account"),
        (BANK_401K, "401K"),
        (BANK_BROKERAGE, "brokerage"),
        (LIFE_INSURANCE, "life insurance"),
        (CASH_ASSET, "cash on hand")
    }

    VERIFIED_THIRD_PARTY = 1
    VERIFIED_TENANT = 5

    VERIFIED_SLUG = {
        VERIFIED_TENANT: 'tenant',
        VERIFIED_THIRD_PARTY: 'employer'
    }

    VERIFIED = {
        (VERIFIED_TENANT, 'Tenant - Direct calculation'),
        (VERIFIED_THIRD_PARTY, '3rd party - Direct calculation')
    }

    slug = models.SlugField(unique=True)
    question = models.ForeignKey(Question)
    resident = models.ForeignKey(Resident, related_name="assets")
    source = models.ForeignKey(Source, null=True)
    category = models.PositiveSmallIntegerField(
        choices=CATEGORY, default=OWNER)
    verified = models.PositiveSmallIntegerField(choices=VERIFIED, default=0)
    amount = models.IntegerField(default=0)
    interest_rate = models.IntegerField(default=0)

    # for audits
    descr = models.TextField(default="", blank=True)
#XXX    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    def __str__(self):
        return self.slug

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.slug:
            # XXX not enough entropy for hash.
            self.slug = hashlib.sha1(','.join(
                [str(attr) for attr in ['question', 'resident', 'source',
                    'category', 'descr', 'amount', 'interest_rate',
                ]])).hexdigest()
            self.slug = slugify(uuid.uuid4().hex)
        return super(Asset, self).save(force_insert=force_insert,
            force_update=force_update, using=using, update_fields=update_fields)

    @property
    def is_current(self):
        return self.question.pk != Question.ASSET_IMPUTED

    @property
    def annual_income(self):
        return (self.amount * self.interest_rate) / 10000


@python_2_unicode_compatible
class Income(models.Model):
    """
    Details of income calculation from a source.

    They are the basis for yearly income computation.
    """
    OTHER = 0
    HOURLY = 1
    DAILY = 2
    WEEKLY = 3
    BI_WEEKLY = 4
    SEMI_MONTHLY = 5
    MONTHLY = 6
    YEARLY = 7

    PERIOD = {
        (OTHER, 'other'),
        (HOURLY, 'hourly'),
        (DAILY, 'daily'),
        (WEEKLY, 'weekly'),
        (BI_WEEKLY, 'bi-weekly'),
        (SEMI_MONTHLY, 'semi-monthly'),
        (MONTHLY, 'monthly'),
        (YEARLY, 'yearly'),
    }

    VERIFIED_EMPLOYER = 1
    VERIFIED_YEAR_TO_DATE = 2
    VERIFIED_PERIOD_TO_DATE = 3
    VERIFIED_TAX_RETURN = 4
    VERIFIED_TENANT = 5

    VERIFIED_SLUG = {
        VERIFIED_TENANT: 'tenant',
        VERIFIED_EMPLOYER: 'employer',
        VERIFIED_YEAR_TO_DATE: 'year-to-date',
        VERIFIED_PERIOD_TO_DATE: 'period-to-date',
        VERIFIED_TAX_RETURN: 'tax-return',
    }

    VERIFIED = {
        (VERIFIED_TENANT, 'Tenant - Direct calculation'),
        (VERIFIED_EMPLOYER, '3rd party - Direct calculation'),
        (VERIFIED_YEAR_TO_DATE, 'Year to date calculation'),
        (VERIFIED_PERIOD_TO_DATE, 'Period to date calculation'),
        (VERIFIED_TAX_RETURN, 'Tax return'),
    }

    DIRECT_CALCULATION = [VERIFIED_TENANT, VERIFIED_EMPLOYER]

    REGULAR = 1
    OVERTIME = 2
    SHIFT_DIFFERENTIAL = 3
    TIPS = 4
    COMMISSION = 5
    BONUSES = 6
    CHILD_SUPPORT = 7
    SPOUSAL_SUPPORT = 8
    ANNUITIES = 9
    INHERITANCE = 10
    INSURANCE_POLICIES = 11
    LOTTERY_WINNINGS = 12
    PENSIONS = 13
    RETIREMENT_FUNDS = 14
    TRUSTS = 15
    UNEARNED = 16
    GIFTS = 17

    CATEGORY = {
        # for employee
        (OTHER, 'other'),
        (REGULAR, 'regular'),
        (OVERTIME, 'overtime'),
        (SHIFT_DIFFERENTIAL, 'shift-differential'),
        (TIPS, 'tips'),
        (COMMISSION, 'commission'),
        (BONUSES, 'bonuses'),
        # for support payments
        (CHILD_SUPPORT, 'child support'),
        (SPOUSAL_SUPPORT, 'spousal support'),
        # For other periodic payments
        (ANNUITIES, 'annuities'),
        (GIFTS, 'gifts'),
        (INHERITANCE, 'inheritance'),
        (INSURANCE_POLICIES, 'insurance-policies'),
        (LOTTERY_WINNINGS, 'lottery-winnings'),
        (PENSIONS, 'pensions'),
        (RETIREMENT_FUNDS, 'retirement-funds'),
        (TRUSTS, 'trusts'),
        (UNEARNED, 'unearned'),
    }

    CHILD_SPOUSAL_SUPPORT_CATEGORY = [CHILD_SUPPORT, SPOUSAL_SUPPORT]
    EMPLOYEE_CATEGORY = [REGULAR, OVERTIME, SHIFT_DIFFERENTIAL, TIPS,
        COMMISSION, BONUSES, OTHER]
    TRUSTS_CATEGORY = [ANNUITIES, INHERITANCE, INSURANCE_POLICIES,
        LOTTERY_WINNINGS, PENSIONS, RETIREMENT_FUNDS, TRUSTS]

    SUPPORT_PAYER_DIRECT = 1
    SUPPORT_PAYER_COURT_OF_LAW = 2
    SUPPORT_PAYER_AGENCY = 3

    SUPPORT_PAYER = {
        (SUPPORT_PAYER_DIRECT, 'Direct from responsible party'),
        (SUPPORT_PAYER_COURT_OF_LAW, 'Court of Law'),
        (SUPPORT_PAYER_AGENCY, 'Enforcement agency'),
        (OTHER, 'Other'),
    }

    SUPPORT_AWARD_NO = 1
    SUPPORT_AWARD_PARTIAL = 2
    SUPPORT_AWARD_FULL = 3

    SUPPORT_AWARD = {
        (SUPPORT_AWARD_NO, 'no'),
        (SUPPORT_AWARD_PARTIAL, 'partial'),
        (SUPPORT_AWARD_FULL, 'yes'),
        (OTHER, 'other'),
    }

    SUPPORT_AWARD_COURT = [SUPPORT_AWARD_PARTIAL, SUPPORT_AWARD_FULL]

    group = models.SlugField()
    question = models.ForeignKey(Question)
    resident = models.ForeignKey(Resident, related_name="income")
    source = models.ForeignKey(Source, null=True)
    category = models.PositiveSmallIntegerField(
        choices=CATEGORY, default=REGULAR)
    verified = models.PositiveSmallIntegerField(choices=VERIFIED, default=0)
    period = models.PositiveSmallIntegerField(choices=PERIOD, default=1)
    amount = models.IntegerField(default=0)

    # Related to employment
    avg = models.PositiveSmallIntegerField(default=3, choices=PERIOD)
    period_per_avg = models.IntegerField(default=0,
        validators=[MaxValueValidator(878400)])
    avg_per_year = models.IntegerField(default=0,
        validators=[MaxValueValidator(36600)])
    starts_at = models.DateTimeField(null=True)
    ends_at = models.DateTimeField(null=True)
    cash_wages = models.BooleanField(default=False)

    # Related to child/spousal support
    court_award = models.PositiveSmallIntegerField(
        choices=SUPPORT_AWARD, default=SUPPORT_AWARD_FULL)
    payer = models.PositiveSmallIntegerField(choices=SUPPORT_PAYER, default=0)

    # for audits
    descr = models.TextField(default="", blank=True)
#XXX    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    def __str__(self):
        return self.group

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.group:
            self.group = slugify(uuid.uuid4().hex)
        return super(Income, self).save(force_insert=force_insert,
            force_update=force_update, using=using, update_fields=update_fields)

    def total_natural_periods_per_year(self):
        """
        Total number of days, weeks, months, etc. in a year. (invariant)
        """
        natural_period = self.period
        if self.period in [Income.HOURLY, Income.DAILY, Income.WEEKLY]:
            natural_period = self.avg
        return total_natural_periods_per_year(
            natural_period, time_at=self.ends_at)

    def nb_natural_periods_per_year(self):
        """
        Number of days, weeks, months, etc. this position is worked out
        of a year.
        """
        if self.avg_per_year == 0:
            return self.total_natural_periods_per_year()
        return self.avg_per_year

    @property
    def annual_income(self):
        if self.verified == self.VERIFIED_TAX_RETURN:
            return self.amount
# XXX We are always using the ``OTHER`` path when we have dates. more accurate.
#        if self.verified == self.VERIFIED_YEAR_TO_DATE:
#            return self.ytd_weekly_amount * 52
        result = 0
        if self.period == self.HOURLY:
            avg_per_year = self.nb_natural_periods_per_year() / 100.0
            result = (
                self.amount * self.period_per_avg / 100) * avg_per_year
        elif self.period == self.DAILY:
            avg_per_year = self.nb_natural_periods_per_year() / 100.0
            result = (
                self.amount * self.period_per_avg / 100) * avg_per_year
        elif self.period == self.WEEKLY:
            result = self.amount * self.nb_natural_periods_per_year() / 100.0
        elif self.period == self.BI_WEEKLY:
            result = self.amount * self.nb_natural_periods_per_year() / 100.0
        elif self.period == self.SEMI_MONTHLY:
            result = self.amount * self.nb_natural_periods_per_year() / 100.0
        elif self.period == self.MONTHLY:
            result = self.amount * self.nb_natural_periods_per_year() / 100.0
        elif self.period == self.YEARLY:
            result = self.amount * self.nb_natural_periods_per_year() / 100.0
        elif self.period == self.OTHER:
            if self.nb_days == 0:
                raise ValueError("Unable to compute annual income with a zero "\
                    "days period")
            result = (self.amount
                * self.nb_natural_periods_per_year() / self.nb_days) / 100.0
        else:
            raise ValueError("Unable to compute annual income with period:"\
                " '%s'" % self.period)
        return int(result)

    @property
    def monthly_income_display(self):
        return "%.2f" % (self.annual_income / (12 * 100.0))

    @property
    def nb_days(self):
        try:
            result = (self.ends_at - self.starts_at).days + 1
        except TypeError:
            result = 0
        return result

    @property
    def ytd_nb_weeks(self):
        return float(self.nb_days) / 7

    @property
    def ytd_weekly_amount(self):
        if self.ytd_nb_weeks:
            return self.amount / self.ytd_nb_weeks
        return 0

    @property
    def get_period_per_avg_display(self):
        result = ""
        if self.period in [self.HOURLY, self.DAILY]:
            if self.period == self.HOURLY:
                result = "%.2f hrs" % (self.period_per_avg / 100.0)
            elif self.period == self.DAILY:
                result = "%.2f days" % (self.period_per_avg / 100.0)
            if self.avg == self.WEEKLY:
                result += " weekly"
            elif self.avg == self.BI_WEEKLY:
                result += " bi-weekly"
            elif self.avg == self.SEMI_MONTHLY:
                result += " semi-monthly"
            elif self.avg == self.SEMI_MONTHLY:
                result += " monthly"
            elif self.avg == self.YEARLY:
                result += " yearly"
            else:
                result += " (invalid)"
        return result

    @property
    def get_avg_per_year_display(self):
        natural_period = self.period
        if self.period in [Income.HOURLY, Income.DAILY, Income.WEEKLY]:
            natural_period = self.avg
        if natural_period == self.WEEKLY:
            noum = "weeks"
        elif natural_period == self.BI_WEEKLY:
            noum = "bi-weeklies"
        elif natural_period == self.SEMI_MONTHLY:
            noum = "semi-months"
        elif natural_period == self.MONTHLY:
            noum = "months"
        elif natural_period == self.YEARLY:
            noum = "year"
        elif natural_period == self.OTHER:
            noum = "days"
        else:
            raise ValueError("Unable to compute annual income'\
' with period: '%s'" % natural_period)
        avg_per_year = self.nb_natural_periods_per_year() / 100.0
        return "%.2f %s" % (avg_per_year, noum)


@python_2_unicode_compatible
class UploadedDocument(models.Model):
    """
    Uploaded support documentation or form signed by tenant.
    """

    OTHER = 0
    CONSECUTIVE_PAYSTUBS = 1
    VERIFICATION_OF_EMPLOYMENT = 2
    MARITAL_SEPARATION_AFFIDAVIT = 3
    DISABILITY_AID_VERIFICATION = 4
    STUDENT_AID_VERIFICATION = 5
    STUDENT_STATUS_VERIFICATION = 6
    SINGLE_PARENT_STUDENT_AFFIDAVIT = 7
    FOSTER_CARE_VERIFICATION = 8
    ZERO_INCOME_CERTIFICATION = 9
    DEPENDANT_SUPPORT_AFFIDAVIT = 21
    DEPENDANT_SUPPORT_VERIFICATION = 10
    UNDER_5000_ASSET_CERTIFICATION = 11
    COURT_AWARD = 12
    ENFORCEMENT_AGENCY_PAYMENTS = 13
    FORM_1040_OR_4506_T = 14
    LEGAL_SEPARATION_AGREEMENT = 15
    TENANT_INCOME_CERTIFICATION = 16
    TENANT_TICQ = 17
    INITIAL_APPLICATION = 18
    GOOD_CAUSE_EVICTION_LEASE_RIDER = 19
    LEASE = 20

    CATEGORY = {
        (OTHER, 'other'),
        (CONSECUTIVE_PAYSTUBS, "3 months of consecutive pay-stubs"),
        (VERIFICATION_OF_EMPLOYMENT, "Verification of Employment"),
        (MARITAL_SEPARATION_AFFIDAVIT, "Marital Separation Status Affidavit"),
        (DISABILITY_AID_VERIFICATION, "Live-in Aide Request for Verification"),
        (STUDENT_AID_VERIFICATION, "Student Financial Aid Verification"),
        (STUDENT_STATUS_VERIFICATION, "Student Status Verification"),
        (SINGLE_PARENT_STUDENT_AFFIDAVIT,
         "Single Parent Full-time Student Affidavit"),
        (FOSTER_CARE_VERIFICATION, "Foster Care Verification"),
        (ZERO_INCOME_CERTIFICATION, "Certification of Zero Income"),
        (DEPENDANT_SUPPORT_AFFIDAVIT,
         "Child or Spousal Support Affidavit"),
        (DEPENDANT_SUPPORT_VERIFICATION,
         "Child or Spousal Support Verification"),
        (UNDER_5000_ASSET_CERTIFICATION, "Under $5,000 Asset Certification"),
        # XXX must add to list of required documents
        (COURT_AWARD, "Child or spousal support awarded by court order"),
        (ENFORCEMENT_AGENCY_PAYMENTS,
         "Child or spousal support paid by enforcement agency"),
        (FORM_1040_OR_4506_T,
         "Form 1040 Tax Return, or form 4506-T Did not file taxes"),
        (LEGAL_SEPARATION_AGREEMENT, "Legal Separation Agreement"),
        (TENANT_INCOME_CERTIFICATION, "Tenant Income Certification (TIC)"),
        (TENANT_TICQ, "Tenant Income Certification Questionnaire (TICQ)"),
        (INITIAL_APPLICATION, "Initial Application"),
        (GOOD_CAUSE_EVICTION_LEASE_RIDER, "Good Cause Eviction Lease Rider"),
        (LEASE, "Lease")
    }

    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=253)
    application = models.ForeignKey(Application, related_name="documents")
    resident = models.ForeignKey(Resident, null=True, related_name="documents")
    url = models.URLField()
    category = models.PositiveSmallIntegerField(choices=CATEGORY)
    source = models.ForeignKey(Source, null=True)

    def __str__(self):
        return self.url

    @property
    def printable_name(self):
        if self.title:
            return self.title
        return self.created_at.strftime("%Y-%m-%d")


def annualize_income_employer(incomes):
    annual_income = 0
    for income in incomes:
        annual_income += income.annual_income
    return annual_income


def annualize_income_period_to_date(incomes):
    annual_income = 0
    amounts = {}
    yearly_fractions = {}
    for income in incomes:
        if income.category not in amounts:
            amounts[income.category] = 0
            yearly_fractions[income.category] = 0.0
        amounts[income.category] += income.amount
        yearly_fractions[income.category] += (income.nb_days * 100.0
            / income.total_natural_periods_per_year())
    for category, amount in six.iteritems(amounts):
        if yearly_fractions[category] > 0:
            annual_income += amount / yearly_fractions[category]
        else:
            LOGGER.warning("divide by zero in PTD calculation with incomes %s",
            [income.group for income in incomes])
    return int(annual_income)


def annualize_income_tax_return(incomes):
    annual_income = 0
    for income in incomes:
        annual_income += income.amount
    return annual_income


def annualize_income_year_to_date(incomes):
    annual_income = 0
    lasts = {}
    for income in incomes:
        if income.category not in lasts:
            lasts[income.category] = income
        if lasts[income.category].ends_at is None or income.ends_at is None:
            LOGGER.warning(
                "Using a data point without an ends_at for YTD calculation")
            raise ValueError(
                "Using a data point without an ends_at for YTD calculation")
        if lasts[income.category].ends_at < income.ends_at:
            lasts[income.category] = income
        elif (lasts[income.category].ends_at.date() == income.ends_at.date()
              and lasts[income.category].annual_income < income.annual_income):
            # Because two entries with the same ends_at could have been entered
            # for the same source in case of a bogus entry (XXX alert).
            lasts[income.category] = income
    for _, income in six.iteritems(lasts):
        annual_income += income.annual_income
    return annual_income


def annualize_income(incomes, verified):
    """
    Annualize a list of ``Income`` based on a verification method.
    """
    if verified == Income.VERIFIED_YEAR_TO_DATE:
        return annualize_income_year_to_date(incomes)
    elif verified == Income.VERIFIED_PERIOD_TO_DATE:
        return annualize_income_period_to_date(incomes)
    elif verified == Income.VERIFIED_TAX_RETURN:
        return annualize_income_tax_return(incomes)
    # default for VERIFIED_TENANT or VERIFIED_EMPLOYER
    return annualize_income_employer(incomes)


def greater_of_annualize_income(verifications):
    """
    Greater of annualized income based on various verification method.

    *verifications* is a dict of {verified: [Income, ...]}
    """
    result = 0
    for verified, incomes in six.iteritems(verifications):
        try:
            annual = annualize_income(incomes, verified)
            if annual > result:
                result = annual
        except ValueError:
            # XXX We skip bogus entries
            pass
    return result


def sum_greater_of_annualize_income(verif_by_sources):
    """
    Sum of greater of annualized income based on various verification method
    accross all sources.

    *verif_by_sources* is a dict of {source: {verified: [Income, ...]}}
    """
    result = 0
    for _, verifications in six.iteritems(verif_by_sources):
        result += greater_of_annualize_income(verifications)
    return result


def greater_of_assets(assets):
    """
    Greater of from a list of `Assets`.
    """
    result = None
    for asset in assets:
        if result is None or asset.amount > result.amount:
            result = asset
    return result


def full_name_natural_split(full_name):
    """
    This function splits a full name into a natural first name, last name
    and middle initials.
    """
    parts = full_name.strip().split(' ')
    first_name = ""
    if len(parts) > 0:
        first_name = parts.pop(0)
    if first_name.lower() == "el" and len(parts) > 0:
        first_name += " " + parts.pop(0)
    last_name = ""
    if len(parts) > 0:
        last_name = parts.pop()
    if (last_name.lower() == 'i' or last_name.lower() == 'ii'
        or last_name.lower() == 'iii' and len(parts) > 0):
        last_name = parts.pop() + " " + last_name
    middle_initials = ""
    for middle_name in parts:
        if len(middle_name) > 0:
            middle_initials += middle_name[0]
    return first_name, middle_initials, last_name


def nb_days_in_year(time_at):
    return 366 if calendar.isleap(time_at.year) else 365


def total_natural_periods_per_year(natural_period, time_at=None):
    """
    Total number of days, weeks, months, etc. in a year. (invariant)
    """
    result = 0
    if natural_period == Income.WEEKLY:
        result = 5200
    elif natural_period == Income.BI_WEEKLY:
        result = 2600
    elif natural_period == Income.SEMI_MONTHLY:
        result = 2400
    elif natural_period == Income.MONTHLY:
        result = 1200
    elif natural_period == Income.YEARLY:
        result = 100
    elif natural_period == Income.OTHER:
        result = nb_days_in_year(datetime_or_now(time_at)) * 100
    else:
        raise ValueError("Unable to compute natural periods per year'\
' with period: '%s'" % natural_period)
    return result
