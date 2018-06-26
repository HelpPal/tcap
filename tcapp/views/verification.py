#pylint:disable=too-many-lines
# Copyright (c) 2018, TeaCapp LLC
#   All rights reserved.
from __future__ import unicode_literals

import logging

from django.http import Http404, HttpResponse
from django.template import TemplateDoesNotExist
from django.views.generic import TemplateView
from extended_templates.utils import get_template

from ..mixins import (ApplicationMixin, ResidentBaseMixin, ResidentMixin,
    SourceMixin)
from ..models import Answer, Asset, Income, Question, Resident
from ..humanize import as_money, as_percentage
from ..templatetags.tcapptags import humanize_list


LOGGER = logging.getLogger(__name__)

DATETIME_FORMAT = "%m-%d-%Y"
DOB_DATETIME_FORMAT = "%m/%d/%Y"

def _format_date(date_to_format, date_format=DATETIME_FORMAT):
    try:
        return date_to_format.strftime(date_format)
    except ValueError:
        return "invalid-date"


class VerificationFormView(TemplateView):

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        response = HttpResponse(content_type='application/pdf')
        try:
            template = get_template(self.template_name)
            response.write(template.render(context))
            return response
        except TemplateDoesNotExist:
            raise Http404("cannot find template '%s'" % self.template_name)

    @staticmethod
    def get_support(tenant, source=None):
        support_amount = 0
        support_period = Income.MONTHLY
        if source is not None:
            kwargs = {'source': source}
        else:
            kwargs = {}
        incomes = tenant.income.filter(
            question__in=Question.CHILD_SPOUSAL_SUPPORT, **kwargs)
        if incomes.count() == 1:
            # no aggregation necessary.
            support = incomes.get()
            support_amount = support.amount
            support_period = support.period
        elif incomes.count() > 1:
            annual_income = 0
            for income in incomes:
                annual_income += income.annual_income
            support_amount = annual_income / (incomes.count() * 12)
        return support_amount, support_period


class ChildOrSpousalAffidavitView(SourceMixin, VerificationFormView):

    template_name = 'tcapp/forms/child-or-spousal-affidavit.pdf'

    def get_context_data(self, **kwargs):
        #pylint: disable=too-many-locals
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'application-unit-number': self.application.unit_number,
            'tenant-name': self.resident.printable_name
        }

        for idx, dependent in enumerate(self.source.dependents.all()):
            context.update({
                ('child-support-recipient-%d' % idx): dependent.printable_name})

        support_amount, support_period = self.get_support(
            self.resident, source=self.source)
        if support_amount:
            support_source = self.source.name
            context.update({
                'child-support-receive-yes': 1,
                'child-support-amount': as_money(support_amount),
                'child-support-period': dict(Income.PERIOD)[support_period],
                'child-support-source': support_source
            })
        else:
            context.update({'child-support-receive-no': 1})

        entitled_amount = 0
        support_incomes = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.CHILD_SPOUSAL_SUPPORT,
            source=self.source)
        for income in support_incomes:
            if income.court_award in Income.SUPPORT_AWARD_COURT:
                context.update({'child-support-entitled-yes': 1})
                if income.court_award == Income.SUPPORT_AWARD_FULL:
                    entitled_amount = support_amount # XXX
                    entitled_period = support_period # XXX
                    context.update({
                        'child-support-entitled-amount':
                            as_money(entitled_amount),
                        'child-support-entitled-period':
                            dict(Income.PERIOD)[entitled_period]
                    })

        if 'child-support-entitled-yes' in context:
            if support_amount == entitled_amount:
                context.update({'child-support-collect-yes': 1})
                for income in support_incomes:
                    if income.payer == Income.SUPPORT_PAYER_DIRECT:
                        context.update({
                            'child-support-collect-direct-yes': 1,
                            'child-support-collect-source-direct':
                                income.source.name})
                    elif income.payer == Income.SUPPORT_PAYER_COURT_OF_LAW:
                        context.update({
                            'child-support-collect-court-yes': 1,
                            'child-support-collect-source-court':
                                income.source.position})
                    elif income.payer == Income.SUPPORT_PAYER_AGENCY:
                        context.update({
                            'child-support-collect-agency-yes': 1,
                            'child-support-collect-source-agency':
                                income.source.position})
                    else:
                        context.update({
                            'child-support-collect-other-yes': 1,
                            'child-support-collect-source-descr':
                                income.source.position})
            else:
                context.update({'child-support-collect-no': 1})
                for income in support_incomes:
                    context.update({
                        'child-support-collect-source-efforts': income.descr})
        else:
            context.update({'child-support-entitled-no': 1})

        return context


class ChildOrSpousalSupportView(SourceMixin, VerificationFormView):

    template_name = 'tcapp/forms/child-or-spousal-support-verification.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'application-unit-number': self.application.unit_number,
            'property-street-address': lihtc_property.street_address,
            'property-location': lihtc_property.locality,
            'property-region': lihtc_property.region,
            'property-postal-code': lihtc_property.postal_code,
            'tenant-name': self.resident.printable_name,
            'tenant-ssn': self.resident.ssn,
            'child-spousal-support-created-at':
                _format_date(self.application.created_at)
        }
        context.update({
            'child-spousal-support-source-name': self.source.name,
            'child-spousal-support-source-street-address':
                self.sourse.street_address,
            'child-spousal-support-source-location': self.source.locality,
            'child-spousal-support-source-region': self.source.region,
            'child-spousal-support-source-postal-code': self.source.postal_code
        })
        for idx, recipient in enumerate(self.source.recipients):
            context.update({('child-spousal-support-recipient-name-%d' % idx):
                recipient.printable_name})
        support_amount, support_period = self.get_support(
            self.resident, source=self.source)
        if support_amount:
            context.update({
                'child-spousal-support-amount': as_money(support_amount),
                'child-spousal-support-period':
                    dict(Income.PERIOD)[support_period]
            })
        if False: #pylint:disable=using-constant-test
            # XXX find a way to compute those
            if self.resident.child_spousal_support_grant:
                context.update({'child-spousal-support-grant-yes': 1})
            else:
                context.update({'child-spousal-support-grant-no': 1})
            if self.resident.child_spousal_support_chage:
                context.update({'child-spousal-support-change-yes': 1})
            else:
                context.update({'child-spousal-support-change-no': 1})
            context.update({'child-spousal-support-change-descr': ""})
        return context


class EvictionDocsView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/eviction-docs.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'application-unit-number': self.application.unit_number,
            'application-head-name': self.application.head.printable_name
        }
        return context


class FosterCareView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/foster-care-verification.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'property-street-address': lihtc_property.street_address,
            'property-location': lihtc_property.locality,
            'property-region': lihtc_property.region,
            'property-postal-code': lihtc_property.postal_code,
            'tenant-unit-number': self.application.unit_number
        }
        context.update({
            'tenant-name': self.resident.printable_name,
            'tenant-ssn': self.resident.ssn,
            'tenant-street-address': self.resident.street_address,
            'tenant-location': self.resident.locality,
            'tenant-region': self.resident.region,
            'tenant-postal-code': self.resident.postal_code,
        })
        context.update({
            'foster-care-start-at': "", # XXX
            'foster-care-end-at': "", # XXX
            'foster-care-source-name': "", # XXX
            'foster-care-source-street-address': "", # XXX
            'foster-care-source-location': "", # XXX
            'foster-care-source-postal-code': "", # XXX
            'foster-care-source-region': "", # XXX
        })
        if self.resident.foster_care: # XXX
            context.update({'foster-care-yes': 1})
        else:
            context.update({'foster-care-no': 1})
        return context


class InitialApplicationView(ApplicationMixin, VerificationFormView):
# XXX deprecated?
    template_name = 'tcapp/forms/initial-application.pdf'


class LeaseView(ApplicationMixin, VerificationFormView):
# XXX deprecated?
    template_name = 'tcapp/forms/lease.pdf'


class LeaseRiderView(ApplicationMixin, VerificationFormView):

    template_name = 'tcapp/forms/lease-rider.pdf'

    def get_context_data(self, **kwargs):
        context = {}
        return context


class LiveInAidView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/live-in-verification.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'property-street-address': lihtc_property.street_address,
            'property-location': lihtc_property.locality,
            'property-region': lihtc_property.region,
            'property-postal-code': lihtc_property.postal_code,
            'tenant-name': self.resident.printable_name
        }
        context.update({
            'live-in-created-at':
                _format_date(self.application.created_at),
            'live-in-source-name': "",
            'live-in-source-street-address': "",
            'live-in-source-location': "",
            'live-in-source-region': "",
            'live-in-source-postal-code': "",
            'live-in-assistance-nb-hours': "",
        })
        if self.resident.disabled: # XXX
            context.update({'tenant-disabled-yes': 1})
        else:
            context.update({'tenant-disabled-no': 1})
        if self.resident.disabled: # XXX
            context.update({'tenant-require-permanent-yes': 1})
        else:
            context.update({'tenant-require-permanent-no': 1})

        #if self.resident.require_live_in: # XXX
        #    context.update({'tenant-require-live-in-yes': 1})
        #else:
        #    context.update({'tenant-require-live-in-no': 1})
        #if self.resident.nb_live_in_aids_required > 1: # XXX
        #    context.update({
        #        'tenant-require-multiple-aids-yes': 1,
        #        'live-in-assistance-nb-aids':
        #            self.resident.nb_live_in_aids_required
        #    })
        #else:
        #    context.update({'tenant-require-multiple-aids-no': 1})
        return context


class MaritalSeparationView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/marital-seperation-affidavit.pdf'

    def get_context_data(self, **kwargs):
        last_residence = self.resident.past_addresses.order_by(
            '-starts_at').first()
        if last_residence:
            street_address = last_residence.street_address
            locality = last_residence.locality
            region = last_residence.region
            postal_code = last_residence.postal_code
        else:
            street_address = ""
            locality = ""
            region = ""
            postal_code = ""
        context = {
            'tenant-name': self.resident.printable_name,
            'tenant-ssn': self.resident.ssn,
            'tenant-street-address': street_address,
            'tenant-location': locality,
            'tenant-region': region,
            'tenant-postal-code': postal_code
        }
        support_amount, support_period = self.get_support(self.resident)
        if support_amount:
            context.update({
                'child-spousal-support-amount': as_money(support_amount),
                'child-spousal-support-period':
                    dict(Income.PERIOD)[support_period]
            })
        return context


class SingleParentView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/single-parent-affidavit.pdf'

    def get_context_data(self, **kwargs):
        context = {
            'tenant-name': self.resident.printable_name,
            'tenant-ssn': self.resident.ssn,
        }
        current_address = self.resident.current_address
        if current_address:
            context.update({
                'tenant-street-address': current_address.street_address,
                'tenant-location': current_address.locality,
                'tenant-region': current_address.region,
                'tenant-postal-code': current_address.postal_code
            })
        return context


class StudentFinancialAidView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/student-aid-verification.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'property-street-address': lihtc_property.street_address,
            'property-location': lihtc_property.locality,
            'property-region': lihtc_property.region,
            'property-postal-code': lihtc_property.postal_code,
            'application-unit-number': self.application.unit_number,
            'tenant-name': self.resident.printable_name,
            'tenant-ssn': self.resident.ssn
        }
        student_aid_query = self.resident.income.filter(
            question__in=Question.INCOME_STUDENT_FINANCIAL_AID)
        if student_aid_query.count() == 1:
            student_aid = student_aid_query.get()
        else:
            raise RuntimeError()
        context.update({
            'student-aid-source-name': student_aid.printable_name,
            'student-aid-street-address': student_aid.street_address,
            'student-aid-location': student_aid.locality,
            'student-aid-region': student_aid.region,
            'student-aid-postal-code': student_aid.postal_code
        })
        return context


class StudentStatusView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/student-verifcation-auth.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'property-street-address': lihtc_property.street_address,
            'property-location': lihtc_property.locality,
            'property-region': lihtc_property.region,
            'property-postal-code': lihtc_property.postal_code,
            'application-unit-number': self.application.unit_number,
        }
        context.update({
            'student-institution': "", # XXX
            'student-id': "" # XXX
        })
        return context


class TICView(ApplicationMixin, VerificationFormView):

    template_name = 'tcapp/forms/tic.pdf'

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals,too-many-statements
        lihtc_property = self.application.lihtc_property
        tcac_number = lihtc_property.tcac_number
        if tcac_number.startswith('CA-'):
            tcac_number = tcac_number[3:]
        effective_date = _format_date(self.application.effective_date)
        move_in_date = _format_date(self.application.move_in_date)
        context = {
            'property-phone': lihtc_property.phone,
            'initial-certification-yes':
                (1 if self.application.certification_type == 'initial' else 0),
            're-certification': (1 if self.application.certification_type
                == 'recertification' else 0),
            'other-certification':
                (1 if self.application.is_other_certification else 0),
            'other-centification-text': (self.application.certification_type
                if self.application.is_other_certification else ""),
            'property-bin-number': lihtc_property.bin_number,
            'property-name': lihtc_property.name,
            'property-unit-number': self.application.unit_number,
            'property-county': lihtc_property.county,
            'property-tcac-number': tcac_number,
            'property-street-address': lihtc_property.street_address,
            'property-nb-bedrooms': self.application.nb_bedrooms,
            'property-square-footage': self.application.square_footage,
            'effective-date': effective_date,
            'move-in-date': move_in_date,
        }
        for idx, applicant in enumerate(self.application.residents):
            context.update({
                ('resident-last-name-%s' % idx): applicant.resident.last_name,
                ('resident-first-name-%s' % idx): applicant.resident.first_name,
                ('resident-relation-to-head-%s' % idx):
                    applicant.relation_to_head_tic_code,
                ('resident-date-of-birth-%s' % idx):
                    _format_date(applicant.resident.date_of_birth,
                        date_format=DOB_DATETIME_FORMAT),
                ('resident-fulltime-student-%s' % idx):
                    "Y" if applicant.resident.full_time_student else "N",
                ('resident-ssn-last4-%s' % idx): applicant.resident.ssn_last4,
                ('resident-race-%s' % idx): applicant.resident.race_code,
            })
            if applicant.resident.middle_initial:
                context.update({('resident-middle-initial-%s' % idx):
                    applicant.resident.middle_initial})
            if applicant.resident.ethnicity:
                context.update({('resident-ethnicity-%s' % idx):
                    applicant.resident.ethnicity})
            if applicant.resident.disabled:
                context.update({('resident-disabled-%s' % idx):
                    applicant.resident.disabled})

        # income
        for idx, applicant in enumerate(self.application.tenants):
            context.update({
                ('tenant-mbr-%s' % idx): (idx + 1),
                ('tenant-earned-income-%s' % idx): as_money(
                    applicant.resident.earned_income),
                ('tenant-social-security-and-pensions-%s' % idx):
                    as_money(
                        applicant.resident.social_security_and_pensions),
                ('tenant-public-assistance-%s' % idx): as_money(
                    applicant.resident.public_assistance),
                ('tenant-other-income-%s' % idx): as_money(
                    applicant.resident.other_income)
            })
        context.update({
            'total-earned-income': as_money(
                self.application.earned_income, show_unit=False),
            'total-social-security-and-pensions': as_money(
                self.application.social_security_and_pensions, show_unit=False),
            'total-public-assistance': as_money(
                self.application.public_assistance, show_unit=False),
            'total-other-income': as_money(
                self.application.other_income, show_unit=False),
            'total-income': as_money(
                self.application.total_income, show_unit=False)
        })

        # assets
        idx = 0
        for hhmbr, applicant in enumerate(self.application.tenants):
            for asset in applicant.resident.get_greater_of_assets():
                context.update({
                    ('tenant-asset-mbr-%s' % idx): (hhmbr + 1),
                    ('tenant-asset-title-%s' % idx): asset.question.title,
                    ('tenant-asset-current-%s' % idx):
                        "C" if asset.is_current else "I",
                    ('tenant-asset-amount-%s' % idx): as_money(
                        asset.amount),
                    ('tenant-asset-annual-income-%s' % idx): as_money(
                        asset.annual_income),
                })
                idx += 1

        context.update({
            'cash-value-of-assets': as_money(
                self.application.cash_value_of_assets, show_unit=False),
            'annual-income-from-assets': as_money(
                self.application.annual_income_from_assets, show_unit=False),
            'imputed-income-from-assets': as_money(
                self.application.imputed_income_from_assets, show_unit=False),
            'total-income-from-assets': as_money(
                self.application.total_income_from_assets, show_unit=False),
            'total-annual-income': as_money(
                self.application.total_annual_income, show_unit=False)
        })
        if self.application.cash_value_of_assets > 500000:
            context.update({
                'cash-value-of-assets-over-5000': as_money(
                    self.application.cash_value_of_assets)})

        context.update({
            'federal-annual-income-limit': as_money(
                self.application.income_limit, show_unit=False),
            'annual-income-as-move-in': as_money(
                self.application.total_annual_income, show_unit=False), # XXX
            'household-size-as-move-in': self.application.residents.count()
        })
        if self.application.federal_income_restriction == 60:
            context.update({'federal-income-restriction60-yes': 1})
        elif self.application.federal_income_restriction == 50:
            context.update({'federal-income-restriction50-yes': 1})
        else:
            context.update({
                'federal-income-restriction-other-yes': 1,
                'federal-income-restriction-percentage':
                    self.application.federal_income_restriction,
            })

        if self.application.certification_type == 'recertification':
            context.update(
                {'recertification-annual-income-limit': as_money(
                    self.application.income_limit_140)})
            if self.application.is_eligible_140:
                context.update({'income-above-140-no': 1})
            else:
                context.update({'income-above-140-yes': 1})

        # rent
        context.update({
            'tenant-monthly-rent': as_money(
                self.application.monthly_rent, show_unit=False),
            'monthly-utility-allowance': as_money(
                self.application.monthly_utility_allowance, show_unit=False),
            'monthly-other-charges': as_money(
                self.application.monthly_other_charges, show_unit=False),
            'total-monthly-rent': as_money(
                self.application.gross_monthly_rent_for_unit, show_unit=False),
            'federal-monthly-rent-limit': as_money(
                self.application.rent_limit, show_unit=False),
            'federal-monthly-rent-assistance': as_money(
                self.application.federal_rent_assistance, show_unit=False),
            'non-federal-monthly-rent-assistance': as_money(
                self.application.non_federal_rent_assistance, show_unit=False),
            'total-monthly-rent-assistance': as_money(
                self.application.total_rent_assistance, show_unit=False),
            'federal-rent-assistance-program':
                self.application.rent_assistance_source,
        })
        if self.application.federal_rent_restriction == 60:
            context.update({'federal-rent-restriction60-yes': 1})
        elif self.application.federal_rent_restriction == 50:
            context.update({'federal-rent-restriction50-yes': 1})
        else:
            context.update({
                'federal-rent-restriction-other-yes': 1,
                'federal-rent-restriction-percentage':
                    self.application.federal_rent_restriction,
            })

        # student
        if self.application.full_time_student:
            context.update({
                'fulltime-student-yes': 1,
                'fulltime-student-explanation': humanize_list(
                    self.application.student_explanation)})
        else:
            context.update({'fulltime-student-no': 1})

        if self.application.program_tax_credit:
            context.update({'tax-credit-yes': 1})
        if self.application.program_home:
            context.update({'home-yes': 1})
            if self.application.program_home_rate <= 50:
                context.update({'home-less-50-amgi-yes': 1})
            elif self.application.program_home_rate <= 60:
                context.update({'home-less-60-amgi-yes': 1})
            elif self.application.program_home_rate <= 80:
                context.update({'home-less-80-amgi-yes': 1})
            context.update({'home-over-income-yes': 0}) # XXX

        if self.application.program_tax_exempt:
            context.update({'tax-exempt-yes': 1})
            if self.application.program_tax_exempt_rate <= 50:
                context.update({'tax-exempt-less-50-amgi-yes': 1})
            elif self.application.program_tax_exempt_rate <= 60:
                context.update({'tax-exempt-less-60-amgi-yes': 1})
            elif self.application.program_tax_exempt_rate <= 80:
                context.update({'tax-exempt-less-80-amgi-yes': 1})
            context.update({'tax-exempt-over-income-yes': 0}) # XXX

        if self.application.program_ahdp:
            context.update({'ahdp-yes': 1})
            if self.application.program_ahdp_rate <= 50:
                context.update({'ahdp-50-amgi-yes': 1})
            elif self.application.program_ahdp_rate <= 80:
                context.update({'ahdp-80-amgi-yes': 1})
            context.update({'ahdp-over-income-yes': 0}) # XXX

        if self.application.program_other:
            context.update({'other-program-yes': 1,
                'other-program-name': self.application.program_other,
                'other-program-percent': self.application.program_other_rate})
            if self.application.program_other_rate <= 0: # XXX
                context.update({'other-program-percent-yes': 1})
            context.update({'other-program-over-income-yes': 0}) # XXX

        return context


class TICQView(ResidentBaseMixin, VerificationFormView):

    template_name = 'tcapp/forms/tic-questionnaire.pdf'

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals,too-many-statements
        lihtc_property = self.application.lihtc_property
        context = {
            'resident-full-name': self.resident.printable_name,
            'resident-phone': self.resident.phone,
            'initial-certification': (1 if self.application.certification_type
                == 'initial' else 0),
            're-certification': (1 if self.application.certification_type
                == 'recertification' else 0),
            'other-certification':
                (1 if self.application.is_other_certification else 0),
            'property-bin-number': lihtc_property.bin_number,
            'application-unit-number': (self.application.unit_number
                if self.application.unit_number else "")
        }
        self_employed = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_SELF_EMPLOYED)
        if len(self_employed) > 0:
            context.update({
                'self-employed-yes': 1,
                'self-employed-source': (self_employed[0].source.name
                if len(self_employed) > 0 else ""),
                'self-employed-amount': (self_employed[0].monthly_income_display
                if len(self_employed) > 0 else ""),
            })
        else:
            context.update({
                'self-employed-no': 1,
                'self-employed-amount': 0
            })
        employees = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_EMPLOYEE)
        if len(employees) > 0:
            context.update({
                'employee-yes': 1,
                'employee-source-0': (employees[0].source.name
                    if len(employees) > 0 else ""),
                'employee-amount-0': (employees[0].monthly_income_display
                    if len(employees) > 0 else ""),
                'employee-source-1': (employees[1].source.name
                    if len(employees) > 1 else ""),
                'employee-amount-1': (employees[1].monthly_income_display
                    if len(employees) > 1 else ""),
                'employee-source-2': (employees[2].source.name
                    if len(employees) > 2 else ""),
                'employee-amount-2': (employees[2].monthly_income_display
                    if len(employees) > 2 else ""),
            })
        else:
            context.update({
                'employee-no': 1,
                'employee-amount-0': 0
            })
        gifts = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_GIFTS)
        if len(gifts) > 0:
            context.update({
                'gifts-yes': 1,
                'gifts-amount': (gifts[0].monthly_income_display
                    if len(gifts) > 0 else ""),
            })
        else:
            context.update({
                'gifts-no': 1,
                'gifts-amount': 0
            })
        unemployment_benefits = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_UNEMPLOYMENT_BENEFITS)
        if len(unemployment_benefits) > 0:
            context.update({
                'unemployment-benefits-yes': 1,
                'unemployment-benefits-amount': (
                    unemployment_benefits[0].monthly_income_display
                    if len(unemployment_benefits) > 0 else ""),
            })
        else:
            context.update({
                'unemployment-benefits-no': 1,
                'unemployment-benefits-amount': 0
            })
        veteran_benefits = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_VETERAN_BENEFITS)
        if len(veteran_benefits) > 0:
            context.update({
                'veteran-benefits-yes': 1,
                'veteran-benefits-amount': (
                    veteran_benefits[0].monthly_income_display
                    if len(veteran_benefits) > 0 else ""),
            })
        else:
            context.update({
                'veteran-benefits-no': 1,
                'veteran-benefits-amount': 0
            })
        social_security = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_SOCIAL_BENEFITS)
        if len(social_security) > 0:
            context.update({
                'social-security-yes': 1,
                'social-security-amount': (
                    social_security[0].monthly_income_display
                    if len(social_security) > 0 else ""),
            })
        else:
            context.update({
                'social-security-no': 1,
                'social-security-amount': 0
            })
        unearned_income = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_UNEARNED_INCOME)
        if len(unearned_income) > 0:
            context.update({
                'unearned-income-yes': 1,
                'unearned-income-amount': (
                    unearned_income[0].monthly_income_display
                    if len(unearned_income) > 0 else ""),
            })
        else:
            context.update({
                'unearned-income-no': 1,
                'unearned-income-amount': 0
            })
        supplemental_security = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_SUPPLEMENTAL_BENEFITS)
        if len(supplemental_security) > 0:
            context.update({
                'supplemental-security-yes': 1,
                'supplemental-security-amount': (
                    supplemental_security[0].monthly_income_display
                    if len(supplemental_security) > 0 else ""),
            })
        else:
            context.update({
                'supplemental-security-no': 1,
                'supplemental-security-amount': 0})
        disability = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_DISABILITY)
        if len(disability) > 0:
            context.update({
                'disability-yes': 1,
                'disability-amount': (disability[0].monthly_income_display
                    if len(disability) > 0 else ""),
            })
        else:
            context.update({
                'disability-no': 1,
                'disability-amount': 0
            })
        public_assistance = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_PUBLIC_ASSISTANCE)
        if len(public_assistance) > 0:
            context.update({
                'public-assistance-yes': 1,
                'public-assistance-amount': (
                    public_assistance[0].monthly_income_display
                    if len(disability) > 0 else ""),
            })
        else:
            context.update({
                'public-assistance-no': 1,
                'public-assistance-amount': 0
            })
        child_support_payments = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_CHILD_SUPPORT_ENTITLED)
        if len(child_support_payments) > 0:
            child_support_receive = False
            child_support_entitled = False
            child_support_descr = ""
            for support in child_support_payments:
                child_support_descr += (
                    support.descr if support.descr is not None else "")
                child_support_entitled |= (
                    support.court_award in support.SUPPORT_AWARD_COURT)
                child_support_receive |= (
                    support.court_award != support.SUPPORT_AWARD_PARTIAL)
            if child_support_entitled:
                context.update({'child-support-entitled-yes': 1})
            else:
                context.update({'child-support-entitled-no': 1})
            if child_support_receive:
                context.update({'child-support-receive-yes': 1})
            else:
                context.update({'child-support-receive-no': 1})
                if child_support_descr:
                    context.update({
                        'child-support-collect-yes': 1,
                        'child-support-descr': child_support_descr,
                    })
                else:
                    context.update({'child-support-collect-no': 1})
            context.update({
                'child-support-amount-0': (
                    child_support_payments[0].monthly_income_display
                    if len(child_support_payments) > 0 else ""),
                'child-support-amount-1': (
                    child_support_payments[1].monthly_income_display
                    if len(child_support_payments) > 1 else ""),
                'child-support-nb-persons': len(child_support_payments),
            })
        else:
            context.update({
                'child-support-entitled-no': 1,
                'child-support-receive-no': 1,
                'child-support-collect-no': 1,
                'child-support-amount-0': 0
            })

        alimony_support = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_ALIMONY_SUPPORT)
        if len(alimony_support) > 0:
            context.update({
                'alimony-support-yes': 1,
                'alimony-support-amount': (
                    alimony_support[0].monthly_income_display
                    if len(alimony_support) > 0 else "")
            })
        else:
            context.update({
                'alimony-support-no': 1,
                'alimony-support-amount': 0
            })

        trusts = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_TRUSTS)
        if len(trusts) > 0:
            context.update({
                'truts-yes': 1,
                'trusts-source-0': (trusts[0].source.name
                    if len(trusts) > 0 else ""),
                'trusts-amount-0': (trusts[0].monthly_income_display
                    if len(trusts) > 0 else ""),
                'trusts-amount-1': (trusts[1].source.name
                    if len(trusts) > 1 else ""),
                'trusts-source-1': (trusts[1].monthly_income_display
                    if len(trusts) > 1 else ""),
            })
        else:
            context.update({
                'truts-no': 1,
                'trusts-amount-0': 0
            })
        property_income = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_PROPERTY)
        if len(property_income) > 0:
            context.update({
                'property-yes': 1,
                'property-amount': (property_income[0].monthly_income_display
                    if len(property_income) > 0 else ""),
            })
        else:
            context.update({
                'property-no': 1,
                'property-amount': 0
            })
        student_financial_aid = self.resident.income.filter(
            verified=Income.VERIFIED_TENANT,
            question__in=Question.INCOME_STUDENT_FINANCIAL_AID)
        if len(student_financial_aid) > 0:
            context.update({
                'student-financial-aid-yes': 1,
                'student-financial-aid-amount': (
                    student_financial_aid[0].monthly_income_display
                    if len(student_financial_aid) > 0 else ""),
            })
        else:
            context.update({
                'student-financial-aid-no': 1,
                'student-financial-aid-amount': 0
            })
        checking = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT, question__in=Question.CHECKING)
        if len(checking) > 0:
            context.update({
                'checking-yes': 1,
                'checking-source-0': (checking[0].source.name
                    if len(checking) > 0 else ""),
                'checking-amount-0': (as_money(checking[0].amount)
                    if len(checking) > 0 else ""),
                'checking-interest-rate-0': (
                    as_percentage(checking[0].interest_rate)
                    if len(checking) > 0 else ""),
                'checking-source-1': (checking[1].source.name
                    if len(checking) > 1 else ""),
                'checking-amount-1': (as_money(checking[1].amount)
                    if len(checking) > 1 else ""),
                'checking-interest-rate-1': (
                    as_percentage(checking[1].interest_rate)
                    if len(checking) > 1 else ""),
            })
        else:
            context.update({
                'checking-no': 1,
                'checking-amount-0': 0
            })
        savings = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT, question__in=Question.SAVINGS)
        if len(savings) > 0:
            context.update({
                'savings-yes': 1,
                'savings-source-0': (savings[0].source.name
                    if len(savings) > 0 else ""),
                'savings-amount-0': (as_money(savings[0].amount)
                    if len(savings) > 0 else ""),
                'savings-interest-rate-0': (
                    as_percentage(savings[0].interest_rate)
                    if len(savings) > 0 else ""),
                'savings-source-1': (savings[1].source.name
                    if len(savings) > 1 else ""),
                'savings-amount-1': (as_money(savings[1].amount)
                    if len(savings) > 1 else ""),
                'savings-interest-rate-1': (
                    as_percentage(savings[1].interest_rate)
                    if len(savings) > 1 else "")
            })
        else:
            context.update({
                'savings-no': 1,
                'savings-amount-0': 0
            })
        revocable_trust = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.REVOCABLE_TRUST)
        if len(revocable_trust) > 0:
            context.update({
                'revocable-trust-yes': 1,
                'revocable-trust-amount-0': (as_money(revocable_trust[0].amount)
                    if len(revocable_trust) > 0 else ""),
                'revocable-trust-interest-rate-0': (
                    as_percentage(revocable_trust[0].interest_rate)
                    if len(revocable_trust) > 0 else ""),
                'revocable-trust-source-1': (revocable_trust[0].source.name
                    if len(revocable_trust) > 0 else ""),
            })
        else:
            context.update({
                'revocable-trust-no': 1,
                'revocable-trust-amount-0': 0
            })
        real_estate = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.REAL_ESTATE)
        if len(real_estate) > 0:
            context.update({
                'real-estate-yes': 1,
                'real-estate-source':  (real_estate[0].source.name
                    if len(real_estate) > 0 else ""),
                'real-estate-amount': (as_money(real_estate[0].amount)
                    if len(real_estate) > 0 else ""),
            })
        else:
            context.update({
                'real-estate-no': 1,
                'real-estate-amount': 0
            })
        stocks = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.STOCKS)
        if len(stocks) > 0:
            context.update({
                'stocks-yes': 1,
                'stocks-source-0': (stocks[0].source.name
                    if len(stocks) > 0 else ""),
                'stocks-amount-0': (as_money(stocks[0].amount)
                    if len(stocks) > 0 else ""),
                'stocks-interest-rate-0': (
                    as_percentage(stocks[0].interest_rate)
                    if len(stocks) > 0 else ""),
                'stocks-source-1': (stocks[1].source.name
                    if len(stocks) > 1 else ""),
                'stocks-amount-1': (as_money(stocks[1].amount)
                    if len(stocks) > 1 else ""),
                'stocks-interest-rate-1': (
                    as_percentage(stocks[1].interest_rate)
                    if len(stocks) > 1 else ""),
                'stocks-source-2': (stocks[2].source.name
                    if len(stocks) > 2 else ""),
                'stocks-amount-2': (as_money(stocks[2].amount)
                    if len(stocks) > 2 else ""),
                'stocks-interest-rate-2': (
                    as_percentage(stocks[2].interest_rate)
                    if len(stocks) > 2 else ""),
            })
        else:
            context.update({
                'stocks-no': 1,
                'stocks-amount-0': 0
            })
        money_market = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.MONEY_MARKET)
        if len(money_market) > 0:
            context.update({
                'money-market-yes': 1,
                'money-market-source-0': (money_market[0].source.name
                    if len(money_market) > 0 else ""),
                'money-market-amount-0': (as_money(money_market[0].amount)
                    if len(money_market) > 0 else ""),
                'money-market-interest-rate-0': (
                    as_percentage(money_market[0].interest_rate)
                    if len(money_market) > 0 else ""),
                'money-market-source-1': (money_market[1].source.name
                    if len(money_market) > 1 else ""),
                'money-market-amount-1': (as_money(money_market[1].amount)
                    if len(money_market) > 1 else ""),
                'money-market-interest-rate-1': (
                    as_percentage(money_market[1].interest_rate)
                    if len(money_market) > 1 else ""),
                'money-market-source-2': (money_market[2].source.name
                    if len(money_market) > 2 else ""),
                'money-market-amount-2': (as_money(money_market[2].amount)
                    if len(money_market) > 2 else ""),
                'money-market-interest-rate-2': (
                    as_percentage(money_market[2].interest_rate)
                    if len(money_market) > 2 else ""),
            })
        else:
            context.update({
                'money-market-no': 1,
                'money-market-amount-0': 0
            })
        retirement = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.RETIREMENT)
        if len(retirement) > 0:
            context.update({
                'retirement-yes': 1,
                'retirement-source-0': (retirement[0].source.name
                    if len(retirement) > 0 else ""),
                'retirement-amount-0': (as_money(retirement[0].amount)
                    if len(retirement) > 0 else ""),
                'retirement-interest-rate-0': (
                    as_percentage(retirement[0].interest_rate)
                    if len(retirement) > 0 else ""),
                'retirement-source-1': (retirement[1].source.name
                    if len(retirement) > 1 else ""),
                'retirement-amount-1': (as_money(retirement[1].amount)
                    if len(retirement) > 1 else ""),
                'retirement-interest-rate-1': (
                    as_percentage(retirement[1].interest_rate)
                    if len(retirement) > 1 else "")})
        else:
            context.update({
                'retirement-no': 1,
                'retirement-amount-0': 0
            })
        life_insurance = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.LIFE_INSURANCE)
        if len(life_insurance) > 0:
            context.update({
                'life-insurance-yes': 1,
                'life-insurance-count': (life_insurance[0].count
                    if len(life_insurance) > 0 else ""),
                'life-insurance-amount': (as_money(life_insurance[0].amount)
                    if len(life_insurance) > 0 else ""),
            })
        else:
            context.update({
                'life-insurance-no': 1,
                'life-insurance-amount': 0
            })
        cash = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.CASH_ON_HAND)
        if len(cash) > 0:
            context.update({
                'cash-yes': 1,
                'cash-amount': (as_money(cash[0].amount)
                    if len(cash) > 0 else ""),
            })
        else:
            context.update({
                'cash-no': 1,
                'cash-amount': 0
            })
        disposed_assets = self.resident.assets.filter(
            verified=Asset.VERIFIED_TENANT,
            question__in=Question.OWN_OR_DISPOSED_REAL_ESTATE)
        if len(disposed_assets) > 0:
            context.update({
                'disposed-assets-yes': 1,
                'disposed-assets-source-0': (disposed_assets[0].source.name
                    if len(disposed_assets) > 0 else ""),
                'disposed-assets-amount-0': (as_money(disposed_assets[0].amount)
                    if len(disposed_assets) > 0 else ""),
                'disposed-assets-source-1': (disposed_assets[1].source.name
                    if len(disposed_assets) > 1 else ""),
                'disposed-assets-amount-1': (as_money(disposed_assets[1].amount)
                    if len(disposed_assets) > 1 else ""),
            })
        else:
            context.update({
                'disposed-assets-no': 1,
                'disposed-assets-amount-0': 0
            })
        # XXX
        current_full_time_student = self.application.current_full_time_student
        context.update({'fulltime-students-current-%s'
          % ('yes' if current_full_time_student else 'no'): 1})
        past_full_time_student = self.application.past_full_time_student
        context.update({'fulltime-students-past-%s'
          % ('yes' if past_full_time_student else 'no'): 1})
        future_full_time_student = self.application.future_full_time_student
        context.update({'fulltime-students-future-%s'
          % ('yes' if future_full_time_student else 'no'): 1})
        if (current_full_time_student
            or past_full_time_student or future_full_time_student):
            tanf_assistance = Answer.objects.filter(
                resident=self.resident,
                question__in=Question.STUDENT_STATUS_TITLE_IV,
                present=True).exists()
            context.update({'tanf-assistance-%s'
                % ('yes' if tanf_assistance else 'no'): 1})
            job_training_program = Answer.objects.filter(
                resident=self.resident,
                question__in=Question.STUDENT_STATUS_JOB_TRAINING,
                present=True).exists()
            context.update({'job-training-program-%s'
                % ('yes' if job_training_program else 'no'): 1})
            married_filing_jointly = (
                self.resident.marital_status == Resident.MARRIED_FILE_JOINTLY)
            context.update({'married-filing-jointly-%s'
                % ('yes' if married_filing_jointly else 'no'): 1})
            context.update({'single-parent-%s'
                % ('yes' if self.resident.is_single_parent else 'no'): 1})
            context.update({'former-foster-care-%s'
                % ('yes' if self.resident.is_foster_care else 'no'): 1})
        return context


class Under5000AssetsView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/under-5000-assets.pdf'

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-statements
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'property-street-address': lihtc_property.street_address,
            'application-location': lihtc_property.locality,
            'property-region': lihtc_property.region,
            'property-postal-code': lihtc_property.postal_code,
            'application-unit-number': self.application.unit_number,
            'tenant-name': self.resident.printable_name
        }
        if self.resident.assets.count() > 0:
            context.update({'no-assets-no': 1})
        else:
            context.update({'no-assets-yes': 1})

        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(question__in=Question.CHECKING)
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'checking-amount': as_money(total_amount, show_unit=False),
            'checking-interest-rate': as_percentage(total_interest),
            'checking-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(question__in=Question.SAVINGS)
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'savings-amount': as_money(total_amount, show_unit=False),
            'savings-interest-rate': as_percentage(total_interest),
            'savings-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.REVOCABLE_TRUST)
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'trusts-amount':  as_money(total_amount, show_unit=False),
            'trusts-interest-rate': as_percentage(total_interest),
            'trusts-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.REAL_ESTATE)
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'real-estate-amount': as_money(total_amount, show_unit=False),
            'real-estate-interest-rate': as_percentage(total_interest),
            'real-estate-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # descr must match BANK_CATEGORY is Javascript.
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.STOCKS, descr="Stocks")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'stocks-amount': as_money(total_amount, show_unit=False),
            'stocks-interest-rate': as_percentage(total_interest),
            'stocks-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # descr must match BANK_CATEGORY is Javascript.
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.STOCKS, descr="Bonds")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'bonds-amount':  as_money(total_amount, show_unit=False),
            'bonds-interest-rate': as_percentage(total_interest),
            'bonds-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # descr must match BANK_CATEGORY is Javascript.
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.MONEY_MARKET, descr="Money Market")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'money-market-amount': as_money(total_amount, show_unit=False),
            'money-market-interest-rate': as_percentage(total_interest),
            'money-market-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.MONEY_MARKET, descr="CDs")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'cds-amount': as_money(total_amount, show_unit=False),
            'cds-interest-rate': as_percentage(total_interest),
            'cds-annual-income': as_money(total_annual_income, show_unit=False),
        })

        # descr must match BANK_CATEGORY is Javascript.
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.RETIREMENT, descr="401K")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'retire-401k-amount': as_money(total_amount, show_unit=False),
            'retire-401k-interest-rate': as_percentage(total_interest),
            'retire-401k-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # descr must match BANK_CATEGORY is Javascript.
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.RETIREMENT, descr="IRA")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'ira-amount': as_money(total_amount, show_unit=False),
            'ira-interest-rate': as_percentage(total_interest),
            'ira-annual-income': as_money(total_annual_income, show_unit=False),
        })

        # descr must match BANK_CATEGORY is Javascript.
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.RETIREMENT, descr="Lump Sum Pension")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'lump-sum-amount':  as_money(total_amount, show_unit=False),
            'lump-sum-interest-rate': as_percentage(total_interest),
            'lump-sum-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # descr must match BANK_CATEGORY is Javascript.
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.RETIREMENT, descr="Keogh account")
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'keogh-amount': as_money(total_amount, show_unit=False),
            'keogh-interest-rate': as_percentage(total_interest),
            'keogh-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        queryset = self.resident.assets.filter(
            question__in=Question.DISPOSED_ASSETS)
        if queryset.exists():
            context.update({
                'disposed-assets-yes': 1,
                'disposed-assets-amount':  as_money(
                    total_amount, show_unit=False),
            })
        else:
            context.update({'disposed-assets-no': 1})

        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.LIFE_INSURANCE)
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'life-insurance-amount': as_money(total_amount, show_unit=False),
            'life-insurance-interest-rate': as_percentage(total_interest),
            'life-insurance-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # XXX Safety deposit box
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        context.update({
            'safety-deposit-amount': as_money(total_amount, show_unit=False),
            'safety-deposit-interest-rate': as_percentage(total_interest),
            'safety-deposit-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # XXX EBT/Debit Visa or MC
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        context.update({
            'ebt-amount': as_money(total_amount, show_unit=False),
            'ebt-interest-rate': as_percentage(total_interest),
            'ebt-annual-income': as_money(total_annual_income, show_unit=False),
        })

        # XXX Capital investments
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        context.update({
            'capital-investments-amount': as_money(
                total_amount, show_unit=False),
            'capital-investments-interest-rate': as_percentage(total_interest),
            'capital-investments-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # XXX Personal property
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        context.update({
            'personal-property-amount': as_money(total_amount, show_unit=False),
            'personal-property-interest-rate': as_percentage(total_interest),
            'personal-property-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        #XXX Pensions
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        context.update({
            'pension-source': "",
            'pension-amount': as_money(total_amount, show_unit=False),
            'pension-interest-rate': as_percentage(total_interest),
            'pension-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        # XXX Other
        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        context.update({
            'other-source': "",
            'other-amount': as_money(total_amount, show_unit=False),
            'other-interest-rate': as_percentage(total_interest),
            'other-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        total_amount = 0
        total_interest = 0
        total_annual_income = 0
        queryset = self.resident.assets.filter(
            question__in=Question.CASH_ON_HAND)
        if queryset.exists():
            for asset in queryset:
                total_amount += asset.amount
                total_interest += asset.interest_rate
                total_annual_income += asset.annual_income
            total_interest = total_interest / queryset.count()
        context.update({
            'cash-amount': as_money(total_amount, show_unit=False),
            'cash-interest-rate': as_percentage(total_interest),
            'cash-annual-income': as_money(
                total_annual_income, show_unit=False),
        })

        context.update({
            'total-assets-annual-income': as_money(
                self.application.annual_income_from_assets, show_unit=False)
        })

        return context


class VerificationEmploymentView(SourceMixin, VerificationFormView):

    template_name = 'tcapp/forms/verification-employment.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'property-street-address': lihtc_property.street_address,
            'property-location': lihtc_property.locality,
            'property-region': lihtc_property.region,
            'property-postal-code': lihtc_property.postal_code,
            'application-unit-number': self.application.unit_number,
            'tenant-name': self.resident.printable_name,
            'tenant-ssn': self.resident.ssn,
            'employee-created-at':
                _format_date(self.application.effective_date)
        }

        context.update({
            'employee-source-name':
              self.source.name if self.source.name else "",
            'employee-source-street-address':
              self.source.street_address if self.source.street_address else "",
            'employee-source-location':
              self.source.locality if self.source.locality else "",
            'employee-source-region':
              self.source.region if self.source.region else "",
            'employee-source-postal-code':
              self.source.postal_code if self.source.postal_code else "",
            'employee-source-phone':
              self.source.phone if self.source.phone else "",
            'employee-source-email':
              self.source.email if self.source.email else "",
#            'employer-tenant-name': self.resident.printable_name,
#            'employer-source-position': self.source.position,
#            'employer-source-name': self.source.name,
#            'employer-source-street-address': self.source.street_address,
#            'employer-source-location': self.source.locality,
#            'employer-source-region': self.source.region,
#            'employer-source-postal-code': self.source.postal_code,
#            'employer-source-phone': self.source.phone,
#            'employer-source-fax': "", # XXX
#            'employer-source-email': self.source.email,
#            'employer-additionnal-remarks': "" # XXX
        })

        # Convienience in testing:
        # context.update(self.fill_employer_section())
        return context


    def fill_employer_section(self):
        #pylint:disable=too-many-statements
        context = {}
        context.update({
            'employee-source-starts-at': "", # XXX
            'employee-source-ends-at': "", # XXX
            'employee-source-current-yes': "", # XXX
            'employee-source-current-no': "", # XXX
        })
        employee_regular = self.resident.income.filter(
            source=self.source, category=Income.REGULAR,
            verified=Income.VERIFIED_EMPLOYER).first()
        if employee_regular:
            context.update({
                'employee-amount': as_money(employee_regular.amount),
                'employee-avg-week': employee_regular.period_per_avg
            })
            if employee_regular.period == Income.HOURLY:
                context.update({'employee-period-hourly-yes': 1})
            elif employee_regular.period == Income.WEEKLY:
                context.update({'employee-period-weekly-yes': 1})
            elif employee_regular.period == Income.BI_WEEKLY:
                context.update({'employee-period-bi-weekly-yes': 1})
            elif employee_regular.period == Income.BI_WEEKLY:
                context.update({'employee-period-semi-monthly-yes': 1})
            elif employee_regular.period == Income.SEMI_MONTHLY:
                context.update({'employee-period-semi-monthly-yes': 1})
            elif employee_regular.period == Income.MONTHLY:
                context.update({'employee-period-monthly-yes': 1})
            elif employee_regular.period == Income.YEARLY:
                context.update({'employee-period-yearly-yes': 1})
            else:
                context.update({
                    'employee-period-other-yes': 1,
                    'employee-period-other': "" # XXX
                })

        employee_overtime = self.resident.income.filter(
            source=self.source, category=Income.OVERTIME,
            verified=Income.VERIFIED_EMPLOYER).first()
        if employee_overtime:
            context.update({
                'employee-overtime-amount': as_money(employee_overtime.amount),
                'employee-overtime-avg-week':  employee_overtime.period_per_avg
            })
        employee_shift_differential = self.resident.income.filter(
            source=self.source, category=Income.SHIFT_DIFFERENTIAL,
            verified=Income.VERIFIED_EMPLOYER).first()
        if employee_shift_differential:
            context.update({
                'employee-shift_differential-amount':
                    as_money(employee_shift_differential.amount),
                'employee-shift_differential-avg-week':
                    employee_shift_differential.period_per_avg
            })

        employee_bonuses = self.resident.income.filter(
            source=self.source, category=Income.BONUSES,
            verified=Income.VERIFIED_EMPLOYER).first()
        if employee_bonuses:
            context.update({
                'employee-bonuses-amount': as_money(employee_bonuses.amount)
            })
            if employee_bonuses.period == Income.HOURLY:
                context.update({'employee-bonuses-hourly-yes': 1})
            elif employee_bonuses.period == Income.WEEKLY:
                context.update({'employee-bonuses-weekly-yes': 1})
            elif employee_bonuses.period == Income.BI_WEEKLY:
                context.update({'employee-bonuses-bi-weekly-yes': 1})
            elif employee_bonuses.period == Income.BI_WEEKLY:
                context.update({'employee-bonuses-semi-monthly-yes': 1})
            elif employee_bonuses.period == Income.SEMI_MONTHLY:
                context.update({'employee-bonuses-semi-monthly-yes': 1})
            elif employee_bonuses.period == Income.MONTHLY:
                context.update({'employee-bonuses-monthly-yes': 1})
            elif employee_bonuses.period == Income.YEARLY:
                context.update({'employee-bonuses-yearly-yes': 1})
            else:
                context.update({
                    'employee-bonuses-other-yes': 1,
                    'employee-bonuses-period-other': "" # XXX
                })

        employee_regular = self.resident.income.filter(
            source=self.source, category=Income.REGULAR,
            verified=Income.VERIFIED_YEAR_TO_DATE).first()
        if employee_regular:
            context.update({
                'employee-ytd-earnings': "", # XXX
                'employee-ytd-starts-at-day':
                    employee_regular.starts_at.day,
                'employee-ytd-starts-at-month':
                    employee_regular.starts_at.month,
                'employee-ytd-starts-at-year':
                    employee_regular.starts_at.year,
                'employee-ytd-ends-at-day':
                    employee_regular.ends_at.day,
                'employee-ytd-ends-at-month':
                    employee_regular.ends_at.month,
                'employee-ytd-ends-at-year':
                    employee_regular.ends_at.year,
            })

        context.update({
#            'employee-anticipated-pay-rate-change': 0, # XXX
            'employee-anticipated-pay-rate-change-effective-at': "", #XXX
#            'employee-layoff-period': 0 # XXX
        })
        return context


class ZeroIncomeView(ResidentMixin, VerificationFormView):

    template_name = 'tcapp/forms/zero-income.pdf'

    def get_context_data(self, **kwargs):
        lihtc_property = self.application.lihtc_property
        context = {
            'property-name': lihtc_property.name,
            'property-location': lihtc_property.locality,
            'application-unit-number': self.application.unit_number,
            'tenant-name': self.resident.printable_name,
        }
        # XXX There is no question about seeking employment
        # in the wizard questionnaire.
        # context.update({'no-income-seeking-employment-yes': 1})
        # context.update({'no-income-seeking-employment-no': 1})
        context.update({'rent-funds-source': ""}) # XXX
        return context

