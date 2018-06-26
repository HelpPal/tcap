# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import re

from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import PrependedText
from crispy_forms.layout import Div, Field, Layout, Submit
from django import forms
from django.core.exceptions import ValidationError

from .serializers import EnumField
from .models import (Answer, Application, ApplicationResident, Income,
    Source, Resident, UtilityAllowance)


class ApplicationForm(forms.ModelForm):

    effective_date = forms.DateTimeField(input_formats=['%m-%d-%Y'])
    move_in_date = forms.DateTimeField(input_formats=['%m-%d-%Y'])
    unit_number = forms.CharField(label='Unit Number')
    nb_bedrooms = forms.IntegerField(label='# Bedrooms',
        widget=forms.widgets.NumberInput(attrs={'ng-model': 'nb_bedrooms'}))
    square_footage = forms.IntegerField(label='Square Footage')
    monthly_rent = forms.DecimalField(label="Tenant Paid Monthly Rent",
        widget=forms.widgets.NumberInput(attrs={
        'ng-model': 'monthly_rent'}))
    federal_rent_assistance = forms.DecimalField(
        label='Federal Rent Assistance',
        widget=forms.widgets.NumberInput(attrs={
        'ng-model': 'federal_rent_assistance'}))
    rent_assistance_source = forms.ChoiceField(
        label="* Source of Federal Assistance", required=False,
        widget=forms.RadioSelect,
        choices=Application.FEDERAL_RENT_ASSISTANCE_SOURCE)
    non_federal_rent_assistance = forms.DecimalField(
        label='Non-Federal Rent Assistance',
        widget=forms.widgets.NumberInput(attrs={
        'ng-model': 'non_federal_rent_assistance'}))
    program_tax_credit = forms.BooleanField(
        label='a. Tax Credit', required=False)
    program_home = forms.BooleanField(label='b. HOME', required=False)
    program_home_rate = forms.IntegerField(required=False)
    program_tax_exempt = forms.BooleanField(
        label='c. Tax Exempt', required=False)
    program_tax_exempt_rate = forms.IntegerField(required=False)
    program_ahdp = forms.BooleanField(
        label='d. AHDP', required=False)
    program_ahdp_rate = forms.IntegerField(required=False)
    program_other = forms.BooleanField(
        label='e. Other', required=False)
    program_other_rate = forms.IntegerField(required=False)

    class Meta:
        model = Application
        fields = ('certification_type', 'effective_date', 'move_in_date',
            'unit_number', 'nb_bedrooms', 'square_footage',
            'household_vacant', 'federal_income_restriction',
            'monthly_rent', 'federal_rent_restriction',
            'federal_rent_assistance', 'rent_assistance_source',
            'non_federal_rent_assistance',
            'program_tax_credit',
            'program_home', 'program_home_rate',
            'program_tax_exempt', 'program_tax_exempt_rate',
            'program_ahdp', 'program_ahdp_rate',
            'program_other', 'program_other_rate')

    def clean_monthly_rent(self):
        amount = self.cleaned_data['monthly_rent']
        self.cleaned_data['monthly_rent'] = int(amount * 100)
        return self.cleaned_data['monthly_rent']

    def clean_federal_rent_assistance(self):
        amount = self.cleaned_data['federal_rent_assistance']
        self.cleaned_data['federal_rent_assistance'] = int(amount * 100)
        return self.cleaned_data['federal_rent_assistance']

    def clean_non_federal_rent_assistance(self): #pylint:disable=invalid-name
        amount = self.cleaned_data['non_federal_rent_assistance']
        self.cleaned_data['non_federal_rent_assistance'] = int(amount * 100)
        return self.cleaned_data['non_federal_rent_assistance']

    def clean_rent_assistance_source(self):
        try:
            federal_rent_assistance = int(
                self.cleaned_data['federal_rent_assistance'])
        except (TypeError, ValueError):
            federal_rent_assistance = None
        if federal_rent_assistance:
            if not self.cleaned_data['rent_assistance_source']:
                raise ValidationError('This field is required')
        else:
            self.cleaned_data['rent_assistance_source'] = 0
        return self.cleaned_data['rent_assistance_source']

    def clean_program_home_rate(self):
        try:
            program_home = bool(self.cleaned_data['program_home'])
        except (TypeError, ValueError):
            program_home = None
        if program_home:
            if not self.cleaned_data['program_home_rate']:
                raise ValidationError('This field is required')
            try:
                self.cleaned_data['program_home_rate'] \
                    = int(self.cleaned_data['program_home_rate'])
            except (TypeError, ValueError):
                self.cleaned_data['program_home_rate'] = 0
        return self.cleaned_data['program_home_rate']

    def clean_program_tax_exempt_rate(self):
        try:
            program_tax_exempt = bool(
                self.cleaned_data['program_tax_exempt'])
        except (TypeError, ValueError):
            program_tax_exempt = None
        if program_tax_exempt:
            if not self.cleaned_data['program_tax_exempt_rate']:
                raise ValidationError('This field is required')
            try:
                self.cleaned_data['program_tax_exempt_rate'] \
                    = int(self.cleaned_data['program_tax_exempt_rate'])
            except (TypeError, ValueError):
                self.cleaned_data['program_tax_exempt_rate'] = 0
        return self.cleaned_data['program_tax_exempt_rate']

    def clean_program_ahdp_rate(self):
        try:
            program_ahdp = bool(self.cleaned_data['program_ahdp'])
        except (TypeError, ValueError):
            program_ahdp = None
        if program_ahdp:
            if not self.cleaned_data['program_ahdp_rate']:
                raise ValidationError('This field is required')
            try:
                self.cleaned_data['program_ahdp_rate'] \
                    = int(self.cleaned_data['program_ahdp_rate'])
            except (TypeError, ValueError):
                self.cleaned_data['program_ahdp_rate'] = 0
        return self.cleaned_data['program_ahdp_rate']

    def clean_program_other_rate(self):
        try:
            program_other = bool(self.cleaned_data['program_other'])
        except (TypeError, ValueError):
            program_other = None
        if program_other:
            if not self.cleaned_data['program_other_rate']:
                raise ValidationError('This field is required')
            try:
                self.cleaned_data['program_other_rate'] \
                    = int(self.cleaned_data['program_other_rate'])
            except (TypeError, ValueError):
                self.cleaned_data['program_other_rate'] = 0
        return self.cleaned_data['program_other_rate']

    def clean(self):
        errors = []
        if not (self.cleaned_data['program_tax_credit']
            or self.cleaned_data['program_home']
            or self.cleaned_data['program_tax_exempt']
            or self.cleaned_data['program_ahdp']
            or self.cleaned_data['program_other']):
            missing_error = ValidationError(
                "Program type missing", code='missing')
            errors += [missing_error]
            self.add_error('program_tax_credit', missing_error)
            self.add_error('program_home', missing_error)
            self.add_error('program_tax_exempt', missing_error)
            self.add_error('program_ahdp', missing_error)
            self.add_error('program_other', missing_error)
        if len(errors) > 0:
            raise ValidationError(errors)
        return self.cleaned_data

    def save(self, commit=True):
        # XXX Not sure why those don't automatically get assigned
        # with the rest of the form fields.
        self.instance.effective_date = self.cleaned_data['effective_date']
        self.instance.move_in_date = self.cleaned_data['move_in_date']

        # XXX because those are stored and not automatically recomputed.
        available_allowance = UtilityAllowance.objects.filter(
            lihtc_property=self.instance.lihtc_property,
            nb_bedrooms=self.cleaned_data['nb_bedrooms']).values(
                'full_amount', 'non_optional_amount').first()
        if available_allowance:
            self.instance.monthly_utility_allowance \
                = available_allowance['full_amount']
            self.instance.monthly_other_charges \
                = available_allowance['non_optional_amount']

        # XXX Hack to avoid adding 'False' as a string.
        if self.cleaned_data['program_other']:
            self.instance.program_other = self.cleaned_data['program_other']
        else:
            self.instance.program_other = ""
        return super(ApplicationForm, self).save(commit=commit)


class ApplicationCreateForm(forms.Form):
    """
    Used to pass hidden field when creating new applications.
    """
    application = forms.CharField()



class DemographicProfileForm(forms.ModelForm):
    """
    Form to gather demographic profiles for the State statistics.
    """

    class Meta:
        model = Resident
        fields = ('race', 'ethnicity', 'disabled')

    def __init__(self, *args, **kwargs):
        super(DemographicProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = '.'
        self.helper.add_input(Submit('submit', 'Next'))


class AnswerFormMixin(object):

    YES_NO = ((True, 'Yes'), (False, 'No'))

    def add_present(self):
        self.fields['present'] = forms.ChoiceField(choices=self.YES_NO,
            widget=forms.RadioSelect, label="")


class IncomeProjectionForm(forms.ModelForm):

    amount = forms.DecimalField(required=False)

    class Meta:
        model = Income
        fields = ('amount', 'period')

    def __init__(self, *args, **kwargs):
        if 'amount' in kwargs['initial']:
            kwargs['initial']['amount'] \
                = float(kwargs['initial']['amount']) / 100
        super(IncomeProjectionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(PrependedText('amount', '$'), css_class='col-sm-6'),
                Div(Field('period'), css_class='col-sm-6'), css_class="row"))

    def clean_amount(self):
        try:
            amount = float(self.cleaned_data['amount'])
            self.cleaned_data['amount'] = int(amount * 100)
        except (TypeError, ValueError):
            self.cleaned_data['amount'] = 0
        return self.cleaned_data['amount']


class SingleIncomeForm(AnswerFormMixin, IncomeProjectionForm):
    """
    We already know the source (i.e. benefits).
    """

    def __init__(self, *args, **kwargs):
        super(SingleIncomeForm, self).__init__(*args, **kwargs)
        self.add_present()


class SourceForm(forms.ModelForm):

    class Meta:
        model = Source
        fields = ('name', 'position', 'email', 'phone',
            'street_address', 'locality', 'region', 'postal_code', 'country')

    def save(self, commit=True):
        self.instance.resident = self.initial['resident']
        return super(SourceForm, self).save(commit)


class SourcedIncomeForm(IncomeProjectionForm):

    class Meta:
        model = Income
        fields = ('category', 'period', 'amount')


class WagesProjectionForm(SourcedIncomeForm):
    """
    W2 employee
    """

    starts_at = forms.DateTimeField(input_formats=['%m-%d-%Y'],
        label="From", required=False)
    ends_at = forms.DateTimeField(input_formats=['%m-%d-%Y'],
        label="To", required=False)
    period_per_avg = forms.DecimalField(
        label="Period to average", required=False)
    avg_per_year = forms.DecimalField(
        label="Average per year", required=False)
    verified = forms.ChoiceField(choices=Income.VERIFIED,
        label="Verification")
    period = forms.CharField(required=False)

    class Meta:
        model = Income
        fields = ('category', 'period', 'amount', 'period_per_avg',
            'avg_per_year', 'starts_at', 'ends_at', 'verified',
            'source', 'question')

    def __init__(self, *args, **kwargs):
        if 'period_per_avg' in kwargs['initial']:
            kwargs['initial']['period_per_avg'] \
                = float(kwargs['initial']['period_per_avg']) / 100
        if 'avg_per_year' in kwargs['initial']:
            kwargs['initial']['avg_per_year'] \
                = float(kwargs['initial']['avg_per_year']) / 100
        super(WagesProjectionForm, self).__init__(*args, **kwargs)
        self.fields['source'].required = False
        if self.instance is None:
            self.submit_title = 'Create'

    def clean_period_per_avg(self):
        try:
            period_per_avg \
                = float(self.cleaned_data['period_per_avg'])
            self.cleaned_data['period_per_avg'] \
                = int(period_per_avg * 100)
        except (TypeError, ValueError):
            self.cleaned_data['period_per_avg'] = 0
        return self.cleaned_data['period_per_avg']

    def clean_avg_per_year(self):
        try:
            avg_per_year = float(self.cleaned_data['avg_per_year'])
            self.cleaned_data['avg_per_year'] = int(avg_per_year * 100)
        except (TypeError, ValueError):
            self.cleaned_data['avg_per_year'] = 0
        return self.cleaned_data['avg_per_year']

    def clean_period(self):
        self.cleaned_data['period'] = EnumField(
            Income.PERIOD).to_internal_value(self.cleaned_data['period'])
        return self.cleaned_data['period']


class ProjectSearchForm(forms.Form):

    query_regex = r'CA-(\d{2}|\d{4})-(\d+)'

    #pylint:disable=invalid-name
    q = forms.CharField(max_length=50, label="TCC Number",
        help_text="Please enter the TCC Number you are looking for.",
        widget=forms.TextInput(
            attrs={'placeholder': 'CA-0000-00000'}))

    def __init__(self, *args, **kwargs):
        super(ProjectSearchForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Search'))

    def clean_q(self):
        look = re.match(self.query_regex, self.cleaned_data['q'].upper())
        if look:
            year = look.group(1)
            num = look.group(2)
            if len(year) == 2:
                year = '20%s' % year
            self.cleaned_data['q'] = 'CA-%s-%s' % (year, num)
        return self.cleaned_data['q']


class ResidentCreateForm(forms.ModelForm):

    date_of_birth = forms.DateTimeField(
        input_formats=['%m-%d-%Y'], required=True)
    ssn = forms.CharField(label="Social Security Number", required=False,
        widget=forms.PasswordInput())
    relation_to_head = forms.ChoiceField(label="Relation to Head of Household",
        choices=ApplicationResident.RELATION_TO_HEAD)

    class Meta:
        model = Resident
        fields = ('first_name', 'last_name', 'middle_initial',
            'date_of_birth', 'ssn',
        )


class TenantContactForm(forms.ModelForm):
    """
    Form to enter a tenant contact information (email, phone, address).
    """

    class Meta:
        model = Resident
        fields = ('email', 'phone')

    def __init__(self, *args, **kwargs):
        super(TenantContactForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(Div(Field('email'), css_class='col-sm-6'),
                Div(Field('phone'), css_class='col-sm-6'),
                css_class="row"))


class AnswerForm(forms.ModelForm):

    YES_NO = ((True, 'Yes'), (False, 'No'))

    present = forms.ChoiceField(widget=forms.RadioSelect, choices=YES_NO,
        label="")

    class Meta:
        model = Answer
        fields = ('present',)

    def __init__(self, *args, **kwargs):
        super(AnswerForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = '.'
        self.helper.form_show_labels = False
        self.helper.add_input(Submit('submit', 'Next >>'))

    def clean_present(self):
        present = self.cleaned_data['present']
        self.cleaned_data['present'] = bool(present.lower() == 'true')
        return self.cleaned_data['present']

    def save(self, commit=True):
        self.instance.question = self.initial['question']
        self.instance.resident = self.initial['resident']
        return super(AnswerForm, self).save(commit)


