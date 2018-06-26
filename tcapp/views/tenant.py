# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import datetime, json, logging

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, UpdateView
from deployutils.apps.django.templatetags.deployutils_prefixtags import (
    site_prefixed)

from ..forms import SourceForm, TenantContactForm
from ..mixins import PropertyMixin, ResidentMixin
from ..models import (ApplicationResident, Asset, Income, Question, Source,
    UploadedDocument)
from ..serializers import (AssetSerializer, HousingHistorySerializer,
    IncomeSerializer, SourceSerializer, UploadedDocumentSerializer)
from ..utils import datetime_or_now, validate_redirect

LOGGER = logging.getLogger(__name__)


class AssetsVerificationView(ResidentMixin, TemplateView):
    """
    List all assets that must be verified.
    """
    model = Asset
    template_name = 'tcapp/asset_verification.html'

    def get_context_data(self, **kwargs):
        context = super(AssetsVerificationView, self).get_context_data(**kwargs)
        context.update({'by_source': self.resident.assets_by_source()})
        return context


class IncomeVerificationView(ResidentMixin, TemplateView):
    """
    List all income sources that must be verified.
    """
    template_name = 'tcapp/tenant/income_verification.html'

    def get_context_data(self, **kwargs):
        context = super(IncomeVerificationView, self).get_context_data(**kwargs)
        context.update({'by_questions': self.resident.income_by_source()})
        return context


class TenantContactView(ResidentMixin, PropertyMixin, UpdateView):
    """
    Ask the tenant about its contact information (email, phone, address).
    """

    form_class = TenantContactForm
    template_name = 'tcapp/tenant/contact.html'

    def get_context_data(self, **kwargs):
        context = super(TenantContactView, self).get_context_data(**kwargs)
        rel = ApplicationResident.objects.filter(
            application=self.application,
            resident=self.resident).first()
        if rel:
            relation_to_head = rel.get_relation_to_head_display()
        else:
            relation_to_head = None
        context.update({
            'lihtc_property': self.application.lihtc_property,
            'application_js': self.get_application_context(tenants=[{
                "slug": self.resident.slug,
                "email": self.resident.email,
                "phone": self.resident.phone,
                "relation_to_head": relation_to_head,
                "past_addresses":
                HousingHistorySerializer(many=True).to_representation(
                    self.resident.past_addresses)}]),
            })
        return context

    def get_initial(self):
        kwargs = super(TenantContactView, self).get_initial()
        kwargs.update({'country': "US", 'region': "CA"})
        return kwargs

    def get_object(self, queryset=None):
        return self.resident

    def get_success_url(self):
        if self.application:
            return reverse('application_detail', args=(self.application,))
        return reverse('application_base')


class UpdateAssetsView(ResidentMixin, TemplateView):
    """
    Create or update an Asset data point.
    """
    slug_url_kwarg = 'entry'
    slug_field = 'slug'
    template_name = 'tcapp/tenant/asset_detail.html'

    def get_context_data(self, **kwargs):
        context = super(UpdateAssetsView, self).get_context_data(**kwargs)
        assets = []
        source = {}
        group = self.kwargs.get(self.slug_url_kwarg, None)
        self.update_context_urls(context, {
            'edit': {'media_upload': site_prefixed("/api/credentials/%s/"
                % str(self.application.lihtc_property))},
            'api_document_upload': reverse('api_document_upload',
                args=(self.application.lihtc_property, self.application))})
        if group is not None:
            self.update_context_urls(context, {
                'asset': reverse('tenant_asset_entry',
                    args=(self.application.lihtc_property,
                    self.resident, group))})
        if group is not None:
            assets = self.get_queryset().filter(slug=group)
            # Find supporting documentation.
            documents = UploadedDocument.objects.filter(
                application=self.application,
                resident=self.resident,
                source__in=[asset.source for asset in assets])
        if assets:
            source.update(SourceSerializer().to_representation(
                assets[0].source))
            source.update({
                'verified': Asset.VERIFIED_SLUG[assets[0].verified],
                'docs': UploadedDocumentSerializer(many=True).to_representation(
                    documents)})
            assets = AssetSerializer(many=True).to_representation(assets)
        else:
            assets = [AssetSerializer().to_representation(Asset(
                category=Asset.BANK_CHECKING,
                resident=self.resident, source=None))]
        # Avoid an error on the way back because `{'question': null}`.
        for asset in assets:
            if 'question' in asset and not asset['question']:
                del asset['question']

        if 'verified' not in source:
            context.update({
                'sources': json.dumps(SourceSerializer(
                    many=True).to_representation(Source.objects.filter(
                        resident=self.resident).order_by('-pk').distinct()))})
            self.update_context_urls(context, {
                'add_source': "%s?next=%s" % (reverse('tenant_asset_source_new',
                    args=(self.application.lihtc_property, self.resident,)),
                    self.request.path)})
            source.update({'verified': ""})
        source.update({"assets": assets})
        rel = ApplicationResident.objects.filter(
            application=self.application, resident=self.resident).first()
        if rel:
            relation_to_head = rel.get_relation_to_head_display()
        else:
            relation_to_head = None
        context.update({
            'lihtc_property': self.application.lihtc_property,
            'application_js': self.get_application_context(tenants=[{
                "slug": self.resident.slug,
                "email": self.resident.email,
                "phone": self.resident.phone,
                "relation_to_head": relation_to_head,
                "fiduciaries": [source]}]),
            })
        return context

    def get_queryset(self):
        return Asset.objects.filter(resident=self.resident)

    def get_success_url(self):
        return reverse('assets_verification',
            args=(self.application.lihtc_property, self.resident,))


class SourceFormMixin(ResidentMixin):

    template_name = 'tcapp/tenant/source.html'

    @property
    def source(self):
        if not hasattr(self, '_source'):
            self._source = get_object_or_404(Source,
                pk=self.kwargs.get('source'))
        return self._source


class UpdateIncomeSourceView(SourceFormMixin, UpdateView):

    form_class = SourceForm
    slug_url_kwarg = 'source'

    def form_valid(self, form):
        self.created = bool(form.instance.pk is None)
        return super(UpdateIncomeSourceView, self).form_valid(form)

    def get_success_url(self):
        next_url = validate_redirect(self.request)
        if next_url:
            return next_url
        return reverse('income_verification',
            args=(self.application.lihtc_property, self.resident,))

    def get_context_data(self, **kwargs):
        context = super(UpdateIncomeSourceView, self).get_context_data(**kwargs)
        next_url = validate_redirect(self.request)
        if next_url:
            context.update({REDIRECT_FIELD_NAME: next_url})
        context.update({
            'application_js': self.get_application_context(tenants=[{
                'income': {
                    'source':  SourceSerializer().to_representation(self.object)
                }}])})
        return context

    def get_initial(self):
        kwargs = super(UpdateIncomeSourceView, self).get_initial()
        kwargs.update({'resident': self.resident,
            'country': "US", 'region': "CA"})
        return kwargs

    def get_queryset(self):
        # Without distinct, the inner join Django creates will return
        # the same ``Source`` row multiple times.
        return Source.objects.filter(resident=self.resident).distinct()

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if slug:
            try:
                # Get the single item from the filtered queryset
                obj = queryset.filter(slug=slug).get()
            except queryset.model.DoesNotExist:
                #pylint:disable=protected-access
                raise Http404("No %(verbose_name)s found matching the query" %
                          {'verbose_name': queryset.model._meta.verbose_name})
        else:
            obj = Source(country="US", region="CA")
        return obj


class UpdateIncomeView(ResidentMixin, TemplateView):
    """
    There are two types of questions in the TIC Questionnaire:
        - income from multiple sources (ex: W2)
        - income from a known source (ex: Social Security)
    """

    slug_url_kwarg = 'entry'
    slug_field = 'slug'
    template_name = 'tcapp/tenant/income/index.html'

    @staticmethod
    def get_default_question():
        return Question.objects.none()

    def get_entry_slug(self):
        if self.question.pk in Question.CHILD_SPOUSAL_SUPPORT:
            return 'support_payments'
        return self.question.slug

    def get_entry_title(self):
        if self.question.pk in Question.CHILD_SPOUSAL_SUPPORT:
            return 'Support payments'
        return self.question.title

    def get_entry_position(self):
        if self.question.pk in Question.CHILD_SPOUSAL_SUPPORT:
            return 'Enforcement agency'
        return "Position/Job title"

    @property
    def question(self):
        if not hasattr(self, '_question'):
            income = self.get_queryset().first()
            if income:
                self._question = income.question
            else:
                self._question = self.get_default_question()
        return self._question

    def get_template_names(self):
        if self.question.pk in Question.INCOME_EMPLOYEE:
            return 'tcapp/tenant/income/employee.html'
        elif self.question.pk in Question.CHILD_SPOUSAL_SUPPORT:
            return 'tcapp/tenant/income/support_payments.html'
        elif self.question.pk in Question.INCOME_OTHERS:
            return 'tcapp/tenant/income/others.html'

        return super(UpdateIncomeView, self).get_template_names()

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-statements
        context = super(UpdateIncomeView, self).get_context_data(**kwargs)
        incomes = []
        source = {'avg_per_year': 1}
        group = self.kwargs.get(self.slug_url_kwarg, None)
        today = datetime_or_now(datetime.date.today())
        beg_of_year = datetime_or_now(datetime.date(today.year, 1, 1))
        self.update_context_urls(context, {
            'edit': {'media_upload': site_prefixed("/api/credentials/%s/"
                % str(self.application.lihtc_property))},
            'api_document_upload': reverse('api_document_upload',
                args=(self.application.lihtc_property, self.application))})
        if group is not None:
            income_url = reverse('tenant_income_entry',
                args=(self.application.lihtc_property, self.resident, group))
        else:
            income_url = self.request.path
        self.update_context_urls(context, {'income': income_url})
        categories = []
        if self.question.pk in Question.INCOME_EMPLOYEE:
            categories = Income.EMPLOYEE_CATEGORY
        elif self.question.pk in Question.CHILD_SPOUSAL_SUPPORT:
            for category in Question.CHILD_SPOUSAL_SUPPORT:
                if self.get_queryset().filter(category=category).exists():
                    categories = [category]
                    break
            if not categories:
                categories = [Question.CHILD_SPOUSAL_SUPPORT[0]]
        elif self.question.pk in Question.INCOME_TRUSTS:
            for category in Income.TRUSTS_CATEGORY:
                if self.get_queryset().filter(category=category).exists():
                    categories = [category]
                    break
            if not categories:
                categories = [Income.PENSIONS]
        else:
            categories = [Income.OTHER]
        for category in categories:
            income = None
            if group is not None:
                try:
                    income = self.get_queryset().get(category=category)
                    # Find supporting documentation.
                    documents = UploadedDocument.objects.filter(
                        application=self.application,
                        resident=self.resident,
                        source=income.source)
                    source.update(SourceSerializer().to_representation(
                        income.source))
                    source.update({
                        'verified': Income.VERIFIED_SLUG[income.verified],
                        'starts_at': datetime_or_now(
                            income.starts_at).isoformat(),
                        'ends_at': datetime_or_now(
                            income.ends_at).isoformat(),
                        'cash_wages': income.cash_wages,
                        'docs': UploadedDocumentSerializer(
                            many=True).to_representation(documents)})
                    incomes.append(
                        IncomeSerializer().to_representation(income))
                except Income.DoesNotExist:
                    income = None
            if income is None:
                incomes.append(
                    IncomeSerializer().to_representation(
                        Income(resident=self.resident,
                            question=self.question,
                            source=None,
                            period=Income.MONTHLY,
                            verified=Income.VERIFIED_EMPLOYER,
                            category=category,
                            starts_at=beg_of_year, ends_at=today)))

        if 'verified' not in source:
            context.update({
                'sources': json.dumps(SourceSerializer(
                    many=True).to_representation(Source.objects.filter(
                    resident=self.resident).order_by('-pk').distinct()))})
            self.update_context_urls(context, {
                'add_source': "%s?next=%s" % (
                    reverse('tenant_income_source_new',
                        args=(self.application.lihtc_property,
                              self.resident,)),
                    self.request.path)})
            source.update({'verified': ""})
        source.update({"incomes": incomes})
        rel = ApplicationResident.objects.filter(
            application=self.application,
            resident=self.resident).first()
        if rel:
            relation_to_head = rel.get_relation_to_head_display()
        else:
            relation_to_head = None
        context.update({
            'entry_position': self.get_entry_position(),
            'entry_title': self.get_entry_title(),
            'entry_slug': self.get_entry_slug(),
            'lihtc_property': self.application.lihtc_property,
            'application_js': self.get_application_context(tenants=[{
                "slug": self.resident.slug,
                "email": self.resident.email,
                "phone": self.resident.phone,
                "relation_to_head": relation_to_head,
                self.get_entry_slug(): [source]}]),
            })
        return context

    def get_queryset(self):
        group = self.kwargs.get(self.slug_url_kwarg, None)
        if group is None:
            return Income.objects.none()
        return Income.objects.filter(resident=self.resident, group=group)


class SelfEmployedIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for a self-employed source.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(pk=Question.INCOME_SELF_EMPLOYED[0])


class EmployeeIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for a W2 employee source.
    """
    template_name = 'tcapp/tenant/income/employee.html'

    @staticmethod
    def get_default_question():
        return Question.objects.get(pk=Question.INCOME_EMPLOYEE[0])


class OthersIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for gifts from a source.
    """
    template_name = 'tcapp/tenant/income/others.html'

    @staticmethod
    def get_default_question():
        return Question.objects.get(pk=Question.INCOME_GIFTS[0])


class UnemployedBenefitsIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for unemployed benefits.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_UNEMPLOYMENT_BENEFITS[0])


class VeteranBenefitsIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for veteran benefits.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_VETERAN_BENEFITS[0])


class SocialBenefitsIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for social security benefits.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_SOCIAL_BENEFITS[0])


class SupplementalBenefitsIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for SSI income.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_SUPPLEMENTAL_BENEFITS[0])


class DisabilityBenefitsIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for disability income.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_DISABILITY[0])


class PublicAssistanceIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for public assistance income.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_PUBLIC_ASSISTANCE[0])


class UnearnedIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for unearned income.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_UNEARNED_INCOME[0])


class ChildAlimonySupportIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for child or alimony income.
    """
    template_name = 'tcapp/tenant/income/support.html'

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_ALIMONY_SUPPORT[0])


class SudentFinancialAidIncomeCreateView(UpdateIncomeView):
    """
    Create a new ``Income`` calculation for student financial aid income.
    """

    @staticmethod
    def get_default_question():
        return Question.objects.get(
            pk=Question.INCOME_STUDENT_FINANCIAL_AID[0])
