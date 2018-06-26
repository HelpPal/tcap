# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import datetime, json, logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.timezone import utc
from django.views.generic import DetailView, ListView, UpdateView
from django.views.generic.base import TemplateResponseMixin
from deployutils.apps.django.templatetags.deployutils_prefixtags import (
    site_prefixed)

from ..api.applications import ApplicationCreateAPIView
from ..forms import ApplicationForm, ApplicationCreateForm
from ..mixins import ApplicationMixin, CalculationMixin, ManagerMixin
from ..models import (Application, Property, Resident, RentLimit,
    UploadedDocument, UtilityAllowance)
from ..signals import get_lihtc_property_email


LOGGER = logging.getLogger(__name__)


class DocumentReference(object):

    def __init__(self, category, application,
                 tenant=None, source=None, link=""):
        #pylint:disable=too-many-arguments
        self.category = category
        self.application = application
        self.tenant = tenant
        self.source = source
        self.link = link

    @property
    def title(self):
        result = None
        if self.category == UploadedDocument.CONSECUTIVE_PAYSTUBS:
            result = ('3 months of consecutive pay-stubs from %s'
                % self.source.printable_name)
        elif self.category == UploadedDocument.FORM_1040_OR_4506_T:
            result = 'Form 1040 Tax Return, or form 4506-T Did not file taxes'
        elif self.category == UploadedDocument.LEGAL_SEPARATION_AGREEMENT:
            result = "Legal Separation Agreement"
        elif self.category == UploadedDocument.COURT_AWARD:
            result = ("Child or spousal support awarded by court order (%s)"
                % self.source)
        elif self.category == UploadedDocument.TENANT_TICQ:
            result = "Tenant Income Certification Questionnaire (TICQ)*"
        elif self.category == UploadedDocument.DEPENDANT_SUPPORT_AFFIDAVIT:
            result = ("Child/Spousal Support Affidavit from %s"
                % self.source.printable_name)
        elif self.category == UploadedDocument.VERIFICATION_OF_EMPLOYMENT:
            result = ("Verification of Employment from %s"
                % self.source.printable_name)
        elif self.category == UploadedDocument.MARITAL_SEPARATION_AFFIDAVIT:
            result = "Marital Separation Status Affidavit Form"
        elif self.category == UploadedDocument.DEPENDANT_SUPPORT_VERIFICATION:
            result = ("Child or Spousal Support Verification from %s"
                    % self.source.printable_name)
        elif self.category == UploadedDocument.DISABILITY_AID_VERIFICATION:
            result = "Live-in Aide Request for Verification"
        elif self.category == UploadedDocument.STUDENT_AID_VERIFICATION:
            result = "Student Financial Aid Verification"
        elif self.category == UploadedDocument.STUDENT_STATUS_VERIFICATION:
            result = "Student Status Verification"
        elif self.category == UploadedDocument.SINGLE_PARENT_STUDENT_AFFIDAVIT:
            result = "Single Parent Full-time Student Affidavit"
        elif self.category == UploadedDocument.FOSTER_CARE_VERIFICATION:
            result = "Foster Care Verification"
        elif self.category == UploadedDocument.ZERO_INCOME_CERTIFICATION:
            result = "Certification of Zero Income"
        elif self.category == UploadedDocument.UNDER_5000_ASSET_CERTIFICATION:
            result = "Under $5,000 Asset Certification"
        elif self.category == UploadedDocument.INITIAL_APPLICATION:
            result = "Initial Application"
        elif self.category == UploadedDocument.TENANT_INCOME_CERTIFICATION:
            result = "Tenant Income Certification (TIC)"
        elif self.category == UploadedDocument.LEASE:
            result = "Lease"
        elif self.category == UploadedDocument.GOOD_CAUSE_EVICTION_LEASE_RIDER:
            result = "Good Cause Eviction Lease Rider"
        return result


class ApplicationChecklistView(ApplicationMixin, DetailView):

    template_name = 'tcapp/application_checklist.html'
    model = Application

    def get_object(self, queryset=None):
        return self.application

    def get_context_data(self, **kwargs):
        context = super(ApplicationChecklistView, self).get_context_data(
            **kwargs)
        context.update({'tenants': []})
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        adult_born_before = datetime.datetime(
            year=now.year - 18, month=now.month, day=now.day).replace(
                tzinfo=utc)
        for tenant in self.application.applicants.filter(
            date_of_birth__lte=adult_born_before):
            # Supporting documentation required to be in the file.
            documents = []
            if tenant.employee_sources().count() > 0:
                for source in tenant.employee_sources():
                    documents += [DocumentReference(
                        UploadedDocument.CONSECUTIVE_PAYSTUBS,
                        self.application, tenant=tenant, source=source)
                    ]
            if tenant.cash_wages:
                documents += [DocumentReference(
                    UploadedDocument.FORM_1040_OR_4506_T,
                    self.application, tenant=tenant)
                ]
            if tenant.marital_status == Resident.LEGALY_SEPARATED:
                documents += [DocumentReference(
                    UploadedDocument.LEGAL_SEPARATION_AGREEMENT,
                    self.application, tenant=tenant)
                ]
            if tenant.support_awards_sources().count() > 0:
                for source in tenant.support_awards_sources():
                    documents += [DocumentReference(
                        UploadedDocument.COURT_AWARD,
                        self.application, tenant=tenant, source=source)]

            # Forms which are required to be signed and added to the file.
            forms = [
                DocumentReference(
                    UploadedDocument.TENANT_TICQ,
                    self.application,
                    tenant=tenant,
                    link=reverse(
                        'tenant_verification_ticq',
                        args=(self.application.lihtc_property,
                              self.application, tenant,))
                ),
            ]
            if tenant.employee_sources().count() > 0:
                for source in tenant.employee_sources():
                    forms += [DocumentReference(
                        UploadedDocument.VERIFICATION_OF_EMPLOYMENT,
                        self.application,
                        tenant=tenant, source=source,
                        link=reverse('tenant_verification_employment',
                        args=(self.application.lihtc_property,
                              tenant, str(source.slug))))]
            if tenant.is_marital_separation:
                forms += [DocumentReference(
                    UploadedDocument.MARITAL_SEPARATION_AFFIDAVIT,
                    self.application,
                    tenant=tenant,
                    link=reverse('tenant_verification_marital_separation',
                        args=(self.application.lihtc_property, tenant,)))]
            if tenant.child_spousal_support_sources().count() > 0:
                for source in tenant.child_spousal_support_sources():
                    forms += [DocumentReference(
                        UploadedDocument.DEPENDANT_SUPPORT_AFFIDAVIT,
                        self.application,
                        tenant=tenant, source=source,
                        link=reverse(
                        'tenant_verification_child_or_spousal_affidavit',
                        args=(self.application.lihtc_property,
                              tenant, str(source.slug))))]
                for source in tenant.child_spousal_support_sources():
                    forms += [DocumentReference(
                        UploadedDocument.DEPENDANT_SUPPORT_VERIFICATION,
                        self.application,
                        tenant=tenant, source=source,
                        link=reverse(
                            'tenant_verification_child_or_spousal_support',
                            args=(self.application.lihtc_property,
                                  tenant, str(source.id))))]
            if tenant.is_disabled():
                forms += [DocumentReference(
                    UploadedDocument.DISABILITY_AID_VERIFICATION,
                    self.application, tenant=tenant,
                    link=reverse('tenant_verification_live_in_aid',
                        args=(self.application.lihtc_property, tenant,)))]
            if tenant.student_financial_aid():
                forms += [DocumentReference(
                    UploadedDocument.STUDENT_AID_VERIFICATION,
                    self.application, tenant=tenant,
                    link=reverse('tenant_verification_student_financial_aid',
                        args=(self.application.lihtc_property, tenant,)))]
            if tenant.full_time_student:
                forms += [DocumentReference(
                    UploadedDocument.STUDENT_STATUS_VERIFICATION,
                    self.application, tenant=tenant,
                    link=reverse('tenant_verification_student_status',
                        args=(self.application.lihtc_property, tenant,)))]
            if tenant.is_single_parent():
                forms += [DocumentReference(
                    UploadedDocument.SINGLE_PARENT_STUDENT_AFFIDAVIT,
                    self.application, tenant=tenant,
                    link=reverse('tenant_verification_single_parent',
                    args=(self.application.lihtc_property, tenant,)))]
            if tenant.is_foster_care():
                forms += [DocumentReference(
                    UploadedDocument.FOSTER_CARE_VERIFICATION,
                    self.application, tenant=tenant,
                    link=reverse('tenant_verification_foster_care',
                        args=(self.application.lihtc_property, tenant,)))]
            if tenant.total_income == 0:
                forms += [DocumentReference(
                    UploadedDocument.ZERO_INCOME_CERTIFICATION,
                    self.application, tenant=tenant,
                    link=reverse('tenant_verification_zero_income',
                    args=(self.application.lihtc_property, tenant,)))]
            if tenant.cash_value_of_assets < 500000:
                forms += [DocumentReference(
                    UploadedDocument.UNDER_5000_ASSET_CERTIFICATION,
                    self.application, tenant=tenant,
                    link=reverse('tenant_verification_under_5000_assets',
                    args=(self.application.lihtc_property, tenant,)))]
            context['tenants'] += [{
                'printable_name': tenant.printable_name,
                'documents': documents,
                'forms': forms
            }]
        # Forms which are required to be signed by all tenants.
        context['forms'] = [
            DocumentReference(
                UploadedDocument.TENANT_INCOME_CERTIFICATION,
                self.application,
                link=reverse('verification_tic',
                    args=(self.application.lihtc_property, self.application,))),
            DocumentReference(
                UploadedDocument.GOOD_CAUSE_EVICTION_LEASE_RIDER,
                self.application,
                link=reverse('verification_lease_rider',
                    args=(self.application.lihtc_property, self.application,)))
        ]
        return context


class ApplicationDetailView(ApplicationMixin, UpdateView):

    template_name = 'tcapp/application.html'
    model = Application
    form_class = ApplicationForm
    slug_url_kwarg = 'application'

    def get_object(self, queryset=None):
        return self.application

    def get_context_data(self, **kwargs):
        context = super(ApplicationDetailView, self).get_context_data(**kwargs)
        available_limits = list(RentLimit.objects.filter(
                county=self.object.lihtc_property.county).values(
                    'nb_bedrooms', 'full_amount'))
        available_allowances = list(UtilityAllowance.objects.filter(
                lihtc_property=self.object.lihtc_property).values(
                'nb_bedrooms', 'full_amount', 'non_optional_amount'))

        max_bedrooms = None
        for limit in available_limits:
            nb_bedrooms = int(limit['nb_bedrooms'])
            if max_bedrooms is None or nb_bedrooms > max_bedrooms:
                max_bedrooms = nb_bedrooms
        for allowance in available_allowances:
            nb_bedrooms = int(allowance['nb_bedrooms'])
            if max_bedrooms is None or nb_bedrooms > max_bedrooms:
                max_bedrooms = nb_bedrooms

        rent_limits = [{} for _ in range(0, max_bedrooms + 1)]
        for limit in available_limits:
            nb_bedrooms = int(limit['nb_bedrooms'])
            rent_limits[nb_bedrooms]['maximum_federal_lihtc_rent'] \
                = limit['full_amount']

        for allowance in available_allowances:
            nb_bedrooms = int(allowance['nb_bedrooms'])
            rent_limits[nb_bedrooms]['utility_allowance'] \
                = allowance['full_amount']
            rent_limits[nb_bedrooms]['non_optional_charges'] \
                = allowance['non_optional_amount']

        context.update({
            'limits': json.dumps({'rent_100': rent_limits,
                'income_100': self.object.income_limit_100}),
            'application_resident_add': reverse('application_resident_add',
                args=(self.application.lihtc_property, self.application,))})
        return context

    def get_success_url(self):
        messages.success(self.request, "TIC was updated successfuly.")
        return reverse('application_detail',
            args=(self.object.lihtc_property, self.object,))

    def get(self, request, *args, **kwargs):
        if not Resident.objects.filter(applications=self.application).exists():
            return HttpResponseRedirect(
                reverse('application_resident_add', args=(
                    self.application.lihtc_property, self.application,)))
        return super(ApplicationDetailView, self).get(request, *args, **kwargs)


class ApplicationDocumentsView(ApplicationMixin, DetailView):
    """
    Page to upload supporting documents.
    """

    template_name = 'tcapp/application_documents.html'
    model = Application

    def get_object(self, queryset=None):
        return self.application

    def get_context_data(self, **kwargs):
        context = super(ApplicationDocumentsView, self).get_context_data(
            **kwargs)
        context.update({'application_js': self.get_application_context()})
        self.update_context_urls(context, {
            'edit': {'media_upload': site_prefixed("/api/credentials/%s/"
                % str(self.application.lihtc_property))},
            'api_document_upload': reverse('api_document_upload',
                args=(self.application.lihtc_property, self.application))})
        return context


class ApplicationBaseView(ManagerMixin, ListView):

    template_name = 'tcapp/application_list.html'

    def get_queryset(self):
        queryset = Application.objects.filter(
            lihtc_property__account__in=self.managed_accounts)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(ApplicationBaseView, self).get_context_data(**kwargs)
        by_accounts = {}
        for account in self.managed_accounts:
            try:
                project = Property.objects.get(slug=account)
                project.urls = {'api': {'applications': reverse(
                    'api_applications', args=(project,))}}
                by_accounts[account] = {'project': project}
            except Property.DoesNotExist:
                # ``request.user`` could be a manager for tcapp proper.
                pass
        url_projects = reverse('project_search')
        if not self.manages(settings.APP_NAME):
            url_projects = "%s?next=%s" % (
                site_prefixed('logout/'), url_projects)
        context.update({'by_accounts': by_accounts,
            'statuses': [
                (str(status[1]), Application.HUMANIZED_STATUS[status[0]][1])
                for status in Application.STATUS],
            'urls': {'applications': reverse('application_base'),
                     'projects': url_projects}})
        return context


class BottomTurtleMixin(object):

    @staticmethod
    def get_context_data(**kwargs):
        # Bottom turtle for ``PropertyMixin``
        # used through ``ApplicationCreateAPIView``
        return kwargs


class ApplicationView(CalculationMixin, TemplateResponseMixin,
                      ApplicationCreateAPIView, BottomTurtleMixin):
    """
    Display the cover used to gather information about one tenant
    who is part of a household.
    """
    template_name = 'tcapp/tenant/wizard.html'
    form_class = ApplicationCreateForm

    def get_context_data(self, **kwargs):
        context = super(ApplicationView, self).get_context_data(**kwargs)
        context.update({
            'lihtc_property_signed_up': (
                get_lihtc_property_email(self.project)
                    != settings.DEFAULT_FROM_EMAIL),
            'utility_allowances': self.project.utility_allowances.all(),
            'manages_property': self.manages(self.project.slug)})
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        response = super(ApplicationView, self).post(request, *args, **kwargs)
        if response.status_code not in (200, 201):
            return response
        self._application = Application.objects.get(slug=response.data['slug'])
        context = self.get_context_data(**self.kwargs)
        if self.manages(self.application.lihtc_property.slug):
            response.data.update({'location':reverse('calculation',
                args=(self.application.lihtc_property, self.application,))})
            return response
        return TemplateResponse(
            request=self.request,
            template='tcapp/application_summary.html',
            context=context,
            using=self.template_engine,
            content_type=self.content_type)

