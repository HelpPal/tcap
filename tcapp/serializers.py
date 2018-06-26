# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import logging, uuid

from dateutil.relativedelta import relativedelta
from django.template.defaultfilters import slugify
from django.utils import six
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from storages.backends.s3boto import S3BotoStorage

from .models import (Application, ApplicationResident, Answer, Asset,
    HousingHistory, Income, Property, Question, Resident, Source,
    UploadedDocument, full_name_natural_split, total_natural_periods_per_year)

#pylint:disable=no-name-in-module,import-error
from django.utils.six.moves.urllib.parse import urlparse


LOGGER = logging.getLogger(__name__)


class EnumField(serializers.Field):
    """
    Treat a ``PositiveSmallIntegerField`` as an enum.
    """
    choices = {}
    inverted_choices = {}

    def __init__(self, choices, *args, **kwargs):
        self.choices = dict(choices)
        self.inverted_choices = {
            val: key for key, val in six.iteritems(self.choices)}
        super(EnumField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        if isinstance(obj, list):
            result = [self.choices.get(item, None) for item in obj]
        else:
            result = self.choices.get(obj, None)
        return result

    def to_internal_value(self, data):
        if isinstance(data, list):
            result = [self.inverted_choices.get(item, None) for item in data]
        else:
            result = self.inverted_choices.get(data, None)
        if result is None:
            if not data:
                raise ValidationError("This field cannot be blank.")
            raise ValidationError(
                "'%s' is not a valid choice. Expected one of %s." % (
                data, [choice for choice in six.itervalues(self.choices)]))
        return result


class AssetSerializer(serializers.ModelSerializer):

    group = serializers.SlugField(source='slug',
        required=False, allow_blank=True)
    question = serializers.SlugRelatedField(slug_field='slug',
        queryset=Question.objects.all(), required=False)
    category = EnumField(choices=Asset.CATEGORY, required=False)
    verified = EnumField(choices=Asset.VERIFIED_SLUG, required=False)

    class Meta: #pylint:disable=old-style-class,no-init
        model = Asset
        fields = ('group', 'question', 'category', 'verified',
                  'amount', 'interest_rate', 'descr')


class ChildResidentSerializer(serializers.ModelSerializer):

    full_name = serializers.CharField(write_only=True)
    relation_to_head = EnumField(choices=ApplicationResident.RELATION_TO_HEAD)

    class Meta: #pylint:disable=old-style-class,no-init
        model = Resident
        fields = ('full_name', 'date_of_birth',
            'relation_to_head', 'full_time_student')


class HousingHistorySerializer(serializers.ModelSerializer):

    street_address = serializers.CharField(allow_blank=True)
    locality = serializers.CharField(allow_blank=True)
    postal_code = serializers.CharField(allow_blank=True)
    monthly_rent = serializers.IntegerField(required=False)

    class Meta: #pylint:disable=old-style-class,no-init
        model = HousingHistory
        fields = ('starts_at', 'ends_at',
            'street_address', 'locality', 'region', 'postal_code', 'country',
            'monthly_rent')


class IncomeSerializer(serializers.ModelSerializer):

    group = serializers.CharField(required=False, allow_blank=True)
    category = EnumField(choices=Income.CATEGORY, required=False)
    period = EnumField(choices=Income.PERIOD)
    avg = EnumField(choices=Income.PERIOD, required=False)
    descr = serializers.CharField(required=False, allow_blank=True)
    verified = EnumField(choices=Income.VERIFIED_SLUG, required=False)
    cash_wages = serializers.BooleanField(required=False)
    payer = EnumField(choices=Income.SUPPORT_PAYER, required=False)
    court_award = EnumField(choices=Income.SUPPORT_AWARD, required=False)

    class Meta: #pylint:disable=old-style-class,no-init
        model = Income
        fields = ('group', 'amount', 'category',
                  'period', 'avg', 'period_per_avg', 'avg_per_year',
                  'starts_at', 'ends_at',
                  'verified', 'descr',
                  # Extra for employee
                  'cash_wages',
                  # Extra for support payments
                  'payer', 'court_award')

    def to_representation(self, obj):
        result = super(IncomeSerializer, self).to_representation(obj)
        if obj is not None:
            result['avg_per_year'] = obj.nb_natural_periods_per_year()
        else:
            result['avg_per_year'] = 0
        return result

    def to_internal_value(self, data):
        result = super(IncomeSerializer, self).to_internal_value(data)
        if result.get('verified', Income.VERIFIED_TENANT) in [
                Income.VERIFIED_PERIOD_TO_DATE,
                Income.VERIFIED_YEAR_TO_DATE]:
            result['period'] = Income.OTHER
            starts_at = result.get('starts_at', None)
            ends_at = result.get('ends_at', None)
            err_msg = "For PTD and YTD calculations,"\
        " the `From` and `To` date must be valid and at least one day apart."
            if not (starts_at and ends_at):
                raise ValidationError(
                    {'starts_at': [err_msg], 'ends_at': [err_msg]})
            if not starts_at < ends_at + relativedelta(days=1):
                raise ValidationError(
                    {'starts_at': [err_msg], 'ends_at': [err_msg]})
        return result


class SourceSerializer(serializers.ModelSerializer):

    dependent = serializers.CharField(required=False, allow_blank=True)
    incomes = IncomeSerializer(many=True, required=False)
    assets = AssetSerializer(many=True, required=False)

    class Meta: #pylint:disable=old-style-class,no-init
        model = Source
        fields = ('slug', 'position', 'name', 'email', 'phone',
            'street_address', 'locality', 'region', 'postal_code', 'country',
            'dependent', 'incomes', 'assets')
        read_only_fields = ('slug',)


class StudentStatusSerializer(serializers.Serializer):

    current = serializers.BooleanField()
    past = serializers.BooleanField()
    future = serializers.BooleanField()
    title_iv = serializers.BooleanField()
    job_training = serializers.BooleanField()
    has_children = serializers.BooleanField()
    foster_care = serializers.BooleanField()

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class ResidentSerializer(serializers.ModelSerializer):

    slug = serializers.CharField(required=False)
    full_name = serializers.CharField(write_only=True, required=False)
    date_of_birth = serializers.DateTimeField(required=False)
    race = serializers.IntegerField(required=False)
    ethnicity = serializers.IntegerField(required=False)
    disabled = serializers.IntegerField(required=False)
    phone = serializers.CharField()
    email = serializers.EmailField()
    ssn = serializers.CharField(required=False, allow_blank=True)
    past_addresses = HousingHistorySerializer(many=True, required=False)

    relation_to_head = EnumField(choices=ApplicationResident.RELATION_TO_HEAD,
        write_only=True)
    student_status = StudentStatusSerializer(write_only=True, required=False)
#XXX    marital_status = EnumField(choices=Resident.MARITAL_STATUS)

    # income
    selfemployed = SourceSerializer(many=True, required=False, write_only=True)
    employee = SourceSerializer(many=True, required=False, write_only=True)
    disability = SourceSerializer(many=True, required=False, write_only=True)
    publicassistance = SourceSerializer(many=True, required=False,
        write_only=True)
    socialsecurity = SourceSerializer(many=True, required=False,
        write_only=True)
    supplemental = SourceSerializer(many=True, required=False, write_only=True)
    unemployment = SourceSerializer(many=True, required=False, write_only=True)
    veteran = SourceSerializer(many=True, required=False, write_only=True)
    others = SourceSerializer(many=True, required=False, write_only=True)
    trusts = SourceSerializer(many=True, required=False, write_only=True)
    unearned = SourceSerializer(many=True, required=False, write_only=True)
    support_payments = SourceSerializer(
        many=True, required=False, write_only=True)
    studentfinancialaid = SourceSerializer(
        many=True, required=False, write_only=True)

    # assets
    fiduciaries = SourceSerializer(many=True, required=False, write_only=True)
    properties = SourceSerializer(many=True, required=False, write_only=True)
    life_insurances = SourceSerializer(
        many=True, required=False, write_only=True)
    cash_on_hand = AssetSerializer(required=False, write_only=True)

    class Meta: #pylint:disable=old-style-class,no-init
        model = Resident
        fields = ('slug', 'full_name', 'phone', 'email', 'ssn',
            'past_addresses', 'date_of_birth', 'relation_to_head',
            'race', 'ethnicity', 'disabled', 'marital_status',
            'student_status',
            'selfemployed', 'employee',
            'disability', 'publicassistance',
            'socialsecurity', 'supplemental',
            'unemployment', 'veteran',
            'others', 'trusts', 'unearned', 'support_payments',
            'studentfinancialaid',
            'fiduciaries', 'properties', 'life_insurances',
            'cash_on_hand')

    @staticmethod
    def get_full_name(instance):
        return instance.printable_name

    @staticmethod
    def validate_relation_to_head(value):
        if not value:
            raise ValidationError("Invalid choice")
        return value

    @staticmethod
    def _create_asset(source, validated_data, question=None):
        verified = validated_data.get('verified', Asset.VERIFIED_TENANT)
        category = validated_data.get('category', Asset.OWNER)
        if not category:
            category = Asset.OWNER
        if question is None:
            if category == Asset.BANK_CHECKING:
                question = Question.CHECKING[0]
            elif category == Asset.BANK_SAVINGS:
                question = Question.SAVINGS[0]
            elif (category == Asset.BANK_CD
                  or category == Asset.BANK_MONEY_MARKET):
                question = Question.MONEY_MARKET[0]
            elif category == Asset.BANK_REVOKABLE_TRUST:
                question = Question.REVOCABLE_TRUST[0]
            elif (category == Asset.BANK_IRA
                  or category == Asset.BANK_LUMP_SUM_PENSION
                  or category == Asset.BANK_KEOGH_ACCOUNT
                  or category == Asset.BANK_401K):
                question = Question.RETIREMENT[0]
            elif category == Asset.BANK_BROKERAGE:
                question = Question.STOCKS[0]
            elif category == Asset.LIFE_INSURANCE:
                question = Question.LIFE_INSURANCE[0]
            elif category == Asset.CASH_ASSET:
                question = Question.CASH_ON_HAND[0]
            question = Question.objects.get(pk=question)
        asset = None
        # "group" translated to "slug" in `validated_data`.
        group = validated_data.get('slug', None)
        if group:
            asset = Asset.objects.get(slug=group, resident=source.resident)
        # A foreclosure will be a $0 imputed asset.
        amount = validated_data.get('amount', 0)
        present = (amount > 0 or question.pk == Question.ASSET_IMPUTED)
        Answer.objects.get_or_create(
            resident=source.resident, question=question,
            defaults={'present': present})
        if present:
            interest_rate = validated_data.get('interest_rate', 0)
            descr = validated_data.get('descr', "")
            if asset:
                asset.category = category
                asset.verified = verified
                asset.source = source
                asset.amount = amount
                asset.interest_rate = interest_rate
                asset.descr = descr
                asset.save()
            else:
                Asset.objects.create(
                    resident=source.resident,
                    question=question,
                    category=category,
                    verified=verified,
                    source=source,
                    amount=amount, interest_rate=interest_rate,
                    descr=descr)
        elif asset:
            asset.delete()

    @staticmethod
    def _create_income(question, source, validated_data, default_group=None):
        #pylint:disable=too-many-locals,too-many-statements
        amount = validated_data.get('amount', 0)
        Answer.objects.get_or_create(
            resident=source.resident, question=question,
            defaults={'present': amount > 0})
        group = validated_data.get('group', None)
        category = validated_data.get('category', Income.OTHER)
        if not category:
            category = Income.OTHER
        income = None
        if group:
            try:
                income = Income.objects.get(group=group,
                    resident=source.resident, question=question,
                    category=category, source=source)
            except Income.DoesNotExist:
                pass # Fall through to create new Income record.
        else:
            group = default_group
        if amount <= 0:
            if income is not None:
                income.delete()
        else:
            verified = validated_data.get('verified', Income.VERIFIED_TENANT)
            period = validated_data.get('period', Income.MONTHLY)
            starts_at = validated_data.get('starts_at', None)
            ends_at = validated_data.get('ends_at', None)
            if verified in [Income.VERIFIED_PERIOD_TO_DATE,
                            Income.VERIFIED_YEAR_TO_DATE]:
                period = Income.OTHER
                if not (starts_at and ends_at):
                    raise ValidationError("For PTD and YTD calculations,"\
        " the `From` and `To` date must be valid and at least one day apart.")
                if not starts_at < ends_at + relativedelta(days=1):
                    raise ValidationError("For PTD and YTD calculations,"\
        " the `From` and `To` date must be valid and at least one day apart.")
            period_per_avg = validated_data.get('period_per_avg', 0)
            # Automatically constraint avg to YEARLY
            # if period is enough to extrapolate annual income.
            avg = validated_data.get('avg', Income.WEEKLY)
            if period not in (Income.HOURLY, Income.DAILY):
                avg = period
            # Automatically constraint avg_per_year when out-of-range.
            periods_per_year = total_natural_periods_per_year(avg)
            avg_per_year = validated_data.get('avg_per_year', periods_per_year)
            if avg_per_year > periods_per_year:
                avg_per_year = periods_per_year
            descr = validated_data.get('descr', "")
            cash_wages = validated_data.get('cash_wages', False)
            court_award = validated_data.get(
                'court_award', Income.SUPPORT_AWARD_NO)
            payer = validated_data.get('payer', Income.SUPPORT_PAYER_DIRECT)
            if income is not None:
                income.verified = verified
                income.period = period
                income.avg = avg
                income.period_per_avg = period_per_avg
                income.avg_per_year = avg_per_year
                income.amount = amount
                income.descr = descr
                income.starts_at = starts_at
                income.ends_at = ends_at
                income.cash_wages = cash_wages
                income.court_award = court_award
                income.payer = payer
                if category in Income.CHILD_SPOUSAL_SUPPORT_CATEGORY:
                    income.category = category
                income.save()
            else:
                Income.objects.create(
                    resident=source.resident,
                    group=group, question=question, category=category,
                    source=source, verified=verified,
                    period=period, avg=avg,
                    period_per_avg=period_per_avg,
                    avg_per_year=avg_per_year,
                    amount=amount, descr=descr, starts_at=starts_at,
                    ends_at=ends_at,
                    cash_wages=cash_wages,
                    payer=payer, court_award=court_award)

    def _create_source(self, resident, validated_data):
        source, _ = Source.objects.get_or_create(
            resident=resident,
            name=validated_data.get('name'),
            position=validated_data.get('position', None),
            defaults={'country': "US", 'region': "CA"})
        dependent = validated_data.get('dependent', None)
        if dependent:
            if dependent == 'myself':
                source.dependents.add(resident)
            else:
                # child-n
                child_idx = int(dependent[6:])
                children_residents = self.context.get(
                    'application').children_residents().order_by('pk')
                if child_idx >= 0 and child_idx < children_residents.count():
                    source.dependents.add(children_residents[child_idx])
                else:
                    extra = {}
                    request = self.context.get('request', None)
                    if request:
                        extra = {'request': request}
                    LOGGER.error("dependent(%s) is outside range for %s"\
                        " in application %s", dependent,
                        list(children_residents),
                        self.context.get('application'), extra=extra)
        return source

    def _create_group(self, source, question, resident):
        no_question = (question is None)
        if question and question.pk in Question.INCOME_BENEFITS:
            # question will be `None` when we are dealing with pensions, etc.
            source.update({'name': "N/A", 'position': None})
        src_obj = self._create_source(resident, source)
        default_group = slugify(uuid.uuid4().hex)
        for income in source.get('incomes', []):
            category = income.get('category', Income.OTHER)
            if no_question:
                if category in(Income.TRUSTS, Income.ANNUITIES,
                        Income.INHERITANCE, Income.RETIREMENT_FUNDS,
                        Income.PENSIONS, Income.INSURANCE_POLICIES,
                        Income.LOTTERY_WINNINGS):
                    question_pk = Question.INCOME_TRUSTS[0]
                elif category == Income.UNEARNED:
                    question_pk = Question.INCOME_UNEARNED_INCOME[0]
                else: # category == Income.GIFTS or Income.OTHER
                    question_pk = Question.INCOME_GIFTS[0]
                question = Question.objects.get(pk=question_pk)
            self._create_income(question, src_obj, income,
                default_group=default_group)

    def create(self, validated_data):
        #pylint:disable=too-many-locals,too-many-statements
        # These are not fields in ``Resident`` though they are used to
        # create additional records in an application.
        _ = validated_data.pop('relation_to_head')
        past_addresses = validated_data.pop('past_addresses', [])
        student_status = validated_data.pop('student_status')

        self_employed = validated_data.pop('selfemployed', [])
        employee = validated_data.pop('employee', [])
        disability_benefits = validated_data.pop('disability', [])
        public_assistance_benefits = validated_data.pop(
            'publicassistance', [])
        social_benefits = validated_data.pop('socialsecurity', [])
        supplemental_benefits = validated_data.pop('supplemental', [])
        unemployment_benefits = validated_data.pop('unemployment', [])
        veteran_benefits = validated_data.pop('veteran', [])
        others = validated_data.pop('others', [])
        support_payments = validated_data.pop('support_payments', [])

        fiduciaries = validated_data.pop('fiduciaries', [])
        properties = validated_data.pop('properties', [])
        life_insurances = validated_data.pop('life_insurances', [])
        cash_on_hand = validated_data.pop('cash_on_hand', None)

        full_name = validated_data.pop('full_name')
        first_name, middle_initial, last_name = full_name_natural_split(
            full_name)
        resident = Resident.objects.create(
            full_name=full_name,
            first_name=first_name, last_name=last_name,
            middle_initial=middle_initial, **validated_data)
        self._create_past_addresses(resident, past_addresses)

        if self_employed:
            question = Question.objects.get(pk=Question.INCOME_SELF_EMPLOYED[0])
            for source in self_employed:
                self._create_group(source, question, resident)

        if employee:
            question = Question.objects.get(pk=Question.INCOME_EMPLOYEE[0])
            for source in employee:
                self._create_group(source, question, resident)

        if disability_benefits:
            question = Question.objects.get(pk=Question.INCOME_DISABILITY[0])
            for source in disability_benefits:
                self._create_group(source, question, resident)

        if public_assistance_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_PUBLIC_ASSISTANCE[0])
            for source in public_assistance_benefits:
                self._create_group(source, question, resident)

        if social_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_SOCIAL_BENEFITS[0])
            for source in social_benefits:
                self._create_group(source, question, resident)

        if supplemental_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_SUPPLEMENTAL_BENEFITS[0])
            for source in supplemental_benefits:
                self._create_group(source, question, resident)

        if unemployment_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_UNEMPLOYMENT_BENEFITS[0])
            for source in unemployment_benefits:
                self._create_group(source, question, resident)

        if veteran_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_VETERAN_BENEFITS[0])
            for source in veteran_benefits:
                self._create_group(source, question, resident)

        if others:
            for source in others:
                self._create_group(source, None, resident)

        if support_payments:
            child_support_question = Question.objects.get(
                    pk=Question.INCOME_CHILD_SUPPORT_ENTITLED[0])
            spousal_support_question = Question.objects.get(
                    pk=Question.INCOME_ALIMONY_SUPPORT[0])
            for source in support_payments:
                category = source.get('category', Income.CHILD_SUPPORT)
                if category == Income.SPOUSAL_SUPPORT:
                    question = spousal_support_question
                else:
                    question = child_support_question
                self._create_group(source, question, resident)

        # Workaround when we have two checking accounts at the same institution.
        sources = {}
        for source in fiduciaries + properties + life_insurances:
            source_name = source.get('name', None)
            if source_name and source_name in sources:
                sources[source_name] += 1
                source['position'] = str(sources[source_name])
            else:
                sources[source_name] = 1
        for source in fiduciaries + properties + life_insurances:
            src_obj = self._create_source(resident, source)
            for asset in source.get('assets', []):
                self._create_asset(src_obj, asset)

        if cash_on_hand:
            question = Question.objects.get(pk=Question.CASH_ON_HAND[0])
            src_obj = self._create_source(resident, {'name': question.slug})
            self._create_asset(src_obj, cash_on_hand, question=question)

        # We want all questions from the TIC Questionnaire to be answered
        # yet for disposed assets we cannot force this with a zero amount
        # (i.e. foreclosure and short sale).
        if not Answer.objects.filter(resident=resident,
                question__pk=Question.ASSET_IMPUTED).exists():
            Answer.objects.get_or_create(
                resident=resident, question_id=Question.ASSET_IMPUTED,
                defaults={'present': False})

        if student_status:
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=26,
                defaults={'present': student_status.get('current', False)})
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=27,
                defaults={'present': student_status.get('past', False)})
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=28,
                defaults={'present': student_status.get('future', False)})
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=29,
                defaults={'present': student_status.get('title_iv', False)})
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=30,
                defaults={'present': student_status.get('job_training', False)})
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=31,
                defaults={'present':
                    resident.marital_status == Resident.MARRIED_FILE_JOINTLY})
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=32,
                defaults={'present': student_status.get('has_children', False)})
            _, _ = Answer.objects.get_or_create(
                resident=resident, question_id=33,
                defaults={'present': student_status.get('foster_care', False)})

        return resident

    @staticmethod
    def _create_past_addresses(resident, past_addresses):
        for address in past_addresses:
            HousingHistory.objects.create(
                resident=resident,
                starts_at=address['starts_at'],
                ends_at=address['ends_at'],
                street_address=address['street_address'],
                locality=address['locality'],
                region=address['region'],
                postal_code=address['postal_code'],
                country=address['country'],
                monthly_rent=address.get('monthly_rent', 0))

    def _update_group(self, source, question, resident):
        no_question = (question is None)
        src_obj = self._create_source(resident, source)
        default_group = None
        for income in source.get('incomes', []):
            group = income.get('group', None)
            if group:
                default_group = group
                break
        if not default_group:
            default_group = slugify(uuid.uuid4().hex)
        for income in source.get('incomes', []):
            category = income.get('category', Income.OTHER)
            if no_question:
                if category in(Income.TRUSTS, Income.ANNUITIES,
                        Income.INHERITANCE, Income.RETIREMENT_FUNDS,
                        Income.PENSIONS, Income.INSURANCE_POLICIES,
                        Income.LOTTERY_WINNINGS):
                    question_pk = Question.INCOME_TRUSTS[0]
                elif category == Income.UNEARNED:
                    question_pk = Question.INCOME_UNEARNED_INCOME[0]
                else: # category == Income.GIFTS or Income.OTHER
                    question_pk = Question.INCOME_GIFTS[0]
                question = Question.objects.get(pk=question_pk)
            self._create_income(question, src_obj, income,
                default_group=default_group)

    def update(self, instance, validated_data):
        #pylint:disable=too-many-locals,too-many-statements
        # -- Income --
        self_employed = validated_data.pop('selfemployed', [])
        if self_employed:
            question = Question.objects.get(pk=Question.INCOME_SELF_EMPLOYED[0])
            for source in self_employed:
                self._update_group(source, question, instance)

        employee = validated_data.pop('employee', [])
        if employee:
            question = Question.objects.get(pk=Question.INCOME_EMPLOYEE[0])
            for source in employee:
                self._update_group(source, question, instance)

        disability_benefits = validated_data.pop('disability', [])
        if disability_benefits:
            question = Question.objects.get(pk=Question.INCOME_DISABILITY[0])
            for source in disability_benefits:
                self._update_group(source, question, instance)

        public_assistance_benefits = validated_data.pop('publicassistance', [])
        if public_assistance_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_PUBLIC_ASSISTANCE[0])
            for source in public_assistance_benefits:
                self._update_group(source, question, instance)

        social_benefits = validated_data.pop('socialsecurity', [])
        if social_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_SOCIAL_BENEFITS[0])
            for source in social_benefits:
                self._update_group(source, question, instance)

        supplemental_benefits = validated_data.pop('supplemental', [])
        if supplemental_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_SUPPLEMENTAL_BENEFITS[0])
            for source in supplemental_benefits:
                self._update_group(source, question, instance)

        unemployment_benefits = validated_data.pop('unemployment', [])
        if unemployment_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_UNEMPLOYMENT_BENEFITS[0])
            for source in unemployment_benefits:
                self._update_group(source, question, instance)

        veteran_benefits = validated_data.pop('veteran', [])
        if veteran_benefits:
            question = Question.objects.get(
                pk=Question.INCOME_VETERAN_BENEFITS[0])
            for source in veteran_benefits:
                self._update_group(source, question, instance)

        others = validated_data.pop('others', [])
        for source in others:
            self._update_group(source, None, instance)
        trusts = validated_data.pop('trusts', [])
        for source in trusts:
            self._update_group(source, None, instance)
        unearned = validated_data.pop('unearned', [])
        for source in unearned:
            self._update_group(source, None, instance)


        support_payments = validated_data.pop('support_payments', [])
        if support_payments:
            # XXX user correct question
            question = Question.objects.get(
                pk=Question.INCOME_ALIMONY_SUPPORT[0])
            for source in support_payments:
                self._update_group(source, question, instance)

# XXX missing
#    INCOME_UNEARNED_INCOME = [7]
#    INCOME_TRUSTS = [13]
#    INCOME_PROPERTY = [14]

        studentfinancialaid = validated_data.pop('studentfinancialaid', [])
        if studentfinancialaid:
            question = Question.objects.get(
                pk=Question.INCOME_STUDENT_FINANCIAL_AID[0])
            for source in studentfinancialaid:
                self._update_group(source, question, instance)

        fiduciaries = validated_data.pop('fiduciaries', [])
        properties = validated_data.pop('properties', [])
        life_insurances = validated_data.pop('life_insurances', [])
        cash_on_hand = validated_data.pop('cash_on_hand', [])
        # Workaround when we have two checking accounts at the same institution.
        sources = {}
        for source in (fiduciaries + properties + life_insurances
                       + cash_on_hand):
            source_name = source.get('name', None)
            if source_name and source_name in sources:
                sources[source_name] += 1
                source['position'] = str(sources[source_name])
            else:
                sources[source_name] = 1
        for source in (fiduciaries + properties + life_insurances
                       + cash_on_hand):
            src_obj = self._create_source(instance, source)
            for asset in source.get('assets', []):
                self._create_asset(src_obj, asset)

        past_addresses = validated_data.pop('past_addresses', None)
        if past_addresses is not None:
            replace = False
            if instance.past_addresses.all().count() != len(past_addresses):
                replace = True
            else:
                try:
                    for address in past_addresses:
                        # Issue converting datetimes when going to browser
                        # and back with no change.
                        # print "XXX address starts_at=%s, ends_at=%s" % (
                        #     address['starts_at'], address['ends_at'])
                        HousingHistory.objects.get(
                            resident=instance,
                            starts_at=address['starts_at'],
                            ends_at=address['ends_at'],
                            street_address=address['street_address'],
                            locality=address['locality'],
                            region=address['region'],
                            postal_code=address['postal_code'],
                            country=address['country'])
                except HousingHistory.DoesNotExist:
                    replace = True
            if replace:
                instance.past_addresses.all().delete()
                self._create_past_addresses(instance, past_addresses)

        return instance


def as_signed_url(location, request):
    parts = urlparse(location)
    bucket_name = parts.netloc.split('.')[0]
    key_name = parts.path
    if bucket_name.startswith('s3-'):
        name_parts = key_name.split('/')
        if name_parts and not name_parts[0]:
            name_parts.pop(0)
        bucket_name = name_parts[0]
        key_name = '/'.join(name_parts[1:])
    if key_name.startswith('/'):
        # we rename leading '/' otherwise S3 copy triggers a 404
        # because it creates an URL with '//'.
        key_name = key_name[1:]
    kwargs = {}
    for key in ['access_key', 'secret_key', 'security_token']:
        if key in request.session:
            kwargs[key] = request.session[key]
    if not kwargs:
        LOGGER.error("called `as_signed_url(bucket_name=%s, key_name=%s)`"\
            " with no credentials.", bucket_name, key_name)
    s3_storage = S3BotoStorage(bucket=bucket_name, **kwargs)
    return s3_storage.url(key_name)


class UploadedDocumentSerializer(serializers.ModelSerializer):

    printable_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta: #pylint:disable=old-style-class,no-init
        model = UploadedDocument
        fields = ('created_at', 'title', 'url', 'printable_name')
        read_only_fields = ('printable_name', 'url')

    @staticmethod
    def get_printable_name(obj):
        return obj.printable_name

    def get_url(self, obj):
        return as_signed_url(obj.url, self.context['request'])


class ApplicationDetailSerializer(serializers.ModelSerializer):

    status = EnumField(choices=Application.STATUS, required=False)
    lihtc_property = serializers.SlugRelatedField(slug_field='slug',
        queryset=Property.objects.all())
    applicants = ResidentSerializer(many=True, required=False)
    children = ChildResidentSerializer(
        many=True, write_only=True, required=False)

    class Meta: #pylint:disable=old-style-class,no-init
        model = Application
        fields = ('created_at', 'slug', 'printable_name', 'status',
            'lihtc_property', 'nb_bedrooms', 'applicants', 'children')
        read_only_fields = ('created_at', 'slug', 'lihtc_property')

    def create(self, validated_data):
        applicants = validated_data.pop('applicants', [])
        children = validated_data.pop('children', [])
        application = Application.objects.create(**validated_data)
        resident_serializer = ResidentSerializer(context={
            'application': application})

        # We create the children first so we can reference them later on
        # in support payments.
        for child in children:
            full_name = child.get('full_name')
            first_name, middle_initial, last_name = full_name_natural_split(
                full_name)
            child_resident = Resident.objects.create(
                full_name=full_name,
                last_name=last_name,
                first_name=first_name,
                middle_initial=middle_initial,
                date_of_birth=child.get('date_of_birth'))
            ApplicationResident.objects.create(
                application=application,
                resident=child_resident,
                relation_to_head=child.get('relation_to_head'))

        for resident_validated_data in applicants:
            relation_to_head = resident_validated_data.get('relation_to_head')
            resident = resident_serializer.create(resident_validated_data)
            ApplicationResident.objects.create(
                application=application,
                resident=resident,
                relation_to_head=relation_to_head)
        return application

    def update(self, instance, validated_data):
        status = validated_data.get('status', None)
        if status is not None:
            instance.status = status
        resident_serializer = ResidentSerializer(
            context={'application': instance})
        for resident_validated_data in validated_data.pop('applicants', []):
            resident = instance.applicants.get(
                slug=resident_validated_data['slug'])
            resident_serializer.update(resident, resident_validated_data)
        children = validated_data.pop('children', [])
        for child_validated_data in children:
            child = instance.children.get(
                slug=child_validated_data['slug'])
            child.full_name = child.get('full_name')
            child.first_name, child.middle_initial, child.last_name = \
                full_name_natural_split(child.full_name)
            child.date_of_birth = child_validated_data.get('date_of_birth')
            child.save()
        instance.save()
        return instance


class ApplicationSummarySerializer(serializers.ModelSerializer):
    """
    Summary information about an ``Application``.
    """
    status = EnumField(choices=Application.STATUS)
    lihtc_property = serializers.SlugRelatedField(slug_field='slug',
        queryset=Property.objects.all())

    class Meta: #pylint:disable=old-style-class,no-init
        model = Application
        fields = ('created_at', 'slug', 'printable_name', 'status',
            'lihtc_property', 'unit_number')
        read_only_fields = ('created_at', 'slug',
            'lihtc_property', 'unit_number')
