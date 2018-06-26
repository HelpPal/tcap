# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.
from __future__ import unicode_literals

import json

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils import six
from django.utils.dateparse import parse_datetime
from deployutils.apps.django.redirects import redirect_or_denied
from deployutils.apps.django import mixins as deployutils_mixins
from deployutils.apps.django.templatetags.deployutils_prefixtags import (
    site_prefixed)

from .models import (Answer, Application, Income, Property, Question,
    Resident, Source)
from .serializers import UploadedDocumentSerializer


class ManagerMixin(deployutils_mixins.AccessiblesMixin):

    @staticmethod
    def update_context_urls(context, urls):
        if 'urls' in context:
            for key, val in six.iteritems(urls):
                if key in context['urls']:
                    if isinstance(val, dict):
                        context['urls'][key].update(val)
                    else:
                        # Because organization_create url is added in this mixin
                        # and in ``OrganizationRedirectView``.
                        context['urls'][key] = val
                else:
                    context['urls'].update({key: val})
        else:
            context.update({'urls': urls})
        return context


class ApplicationBaseMixin(ManagerMixin):

    @property
    def application(self):
        if not hasattr(self, '_application'):
            application_slug = self.kwargs.get('application', None)
            if application_slug:
                self._application = get_object_or_404(
                    Application, slug=application_slug)
                if not self.manages(self._application.lihtc_property.account):
                    raise PermissionDenied("%s is not a manager for %s"
                        % (self.request.user,
                        self._application.lihtc_property.account))
            else:
                self._application = None
        return self._application

    def get_context_data(self, **kwargs):
        context = super(ApplicationBaseMixin, self).get_context_data(**kwargs)
        if self.application:
            # application can be None when ApplicationView is used
            # to display the estimates.
            context.update({'application': self.application})
            self.update_context_urls(context, {
                'application': {
                    'calculation': reverse('calculation',
                        args=(self.application.lihtc_property,
                            self.application,)),
                    'application_detail': reverse('application_detail',
                        args=(self.application.lihtc_property,
                            self.application,)),
                    'printable_forms': reverse('application_checklist',
                        args=(self.application.lihtc_property,
                            self.application,)),
                    'supporting_documents': reverse('application_documents',
                        args=(self.application.lihtc_property,
                            self.application,)),
                    'resident_add': reverse('application_resident_add',
                        args=(self.application.lihtc_property,
                            self.application,))
                }
            })
        return context

    def get_application_context(self, tenants=None, docs=None):
        if tenants is None:
            tenants = []
        if docs is None:
            docs = []
        else:
            docs = UploadedDocumentSerializer(context={'request': self.request},
                many=True).to_representation(docs)
        return json.dumps({
            'slug': self.application.slug,
            'lihtc_property': self.application.lihtc_property.slug,
            'applicants': tenants,
            'docs': docs})


class ApplicationMixin(ApplicationBaseMixin):

    @staticmethod
    def fail_requires_subscription(request, application):
        for organization in request.session.get('roles', {}).get('manager', []):
            if organization.get('slug') == application.lihtc_property.slug:
                for subscription in organization.get('subscriptions', []):
                    if application.created_at < parse_datetime(
                            subscription['ends_at']):
                        return None
        return site_prefixed('/pricing/')

    def dispatch(self, *args, **kwargs):
        # We only access to applications if there is a current or past
        # subscription at the time the application was created.
        application = self.application
        if application:
            redirect_url = self.fail_requires_subscription(self.request,
                application=application)
            if redirect_url:
                return redirect_or_denied(self.request, redirect_url,
                    descr="%(organization)s was not subscribed at the time"\
                        " application %(application)s was created." % {
                            'organization': application.lihtc_property,
                            'application': application})
        return super(ApplicationMixin, self).dispatch(*args, **kwargs)


class PropertyMixin(ManagerMixin):

    model = Property
    slug_url_kwarg = 'project'

    @property
    def project(self):
        if not hasattr(self, '_project'):
            self._project = get_object_or_404(
                Property, slug=self.kwargs.get(self.slug_url_kwarg))
        return self._project

    def get_context_data(self, **kwargs):
        context = super(PropertyMixin, self).get_context_data(**kwargs)
        context.update({
            'lihtc_property': self.project,
            'is_manager': (
                self.manages(self.project.slug) or self.manages('tcapp'))})
        return context


class ResidentAbstractMixin(object):
    # XXX only one application per resident so far. As a result
    #     we override the ``application`` property.

    @property
    def resident(self):
        if not hasattr(self, '_resident'):
            self._resident = get_object_or_404(
                Resident, slug=self.kwargs.get('resident'))
        return self._resident

    @property
    def application(self):
        if not hasattr(self, '_application'):
            self._application = self.resident.applications.all().first()
            if not self.manages(self._application.lihtc_property.account):
                raise PermissionDenied("%s is not a manager for %s"
                    % (self.request.user,
                       self._application.lihtc_property.account))
        return self._application

    def get_context_data(self, **kwargs):
        context = super(ResidentAbstractMixin, self).get_context_data(**kwargs)
        context.update({
            'resident': self.resident,
            'answers': Answer.objects.populate(self.resident)})
        self.update_context_urls(context, {
            'resident': {
                'resident_update': reverse('resident_update',
                    args=(self.application.lihtc_property, self.resident,)),
                'tenant_contact': reverse('tenant_contact',
                    args=(self.application.lihtc_property, self.resident,)),
                'demographic_profile': reverse('demographic_profile',
                    args=(self.application.lihtc_property, self.resident,)),
                'income_verification': reverse('income_verification',
                    args=(self.application.lihtc_property, self.resident,)),
                'tenant_income_source_base': reverse(
                    'tenant_income_source_base',
                    args=(self.application.lihtc_property, self.resident,)),
                'assets_verification': reverse('assets_verification',
                    args=(self.application.lihtc_property, self.resident,)),
            }
        })
        return context


class ResidentBaseMixin(ResidentAbstractMixin, ApplicationBaseMixin):

    pass

class ResidentMixin(ResidentAbstractMixin, ApplicationMixin):

    pass


class QuestionMixin(ResidentMixin):

    @property
    def question(self):
        if not hasattr(self, '_question'):
            self._question = get_object_or_404(Question,
                rank=self.kwargs.get('question'))
        return self._question


class CalculationMixin(ApplicationBaseMixin):
    """
    Information used in an application to calculate income and assets.
    """

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-nested-blocks
        context = super(CalculationMixin, self).get_context_data(**kwargs)
        if self.application:
            for app_tenant in self.application.tenants:
                income_iter = Income.objects.filter(
                    resident=app_tenant.resident).order_by(
                    'question', 'source', 'verified').iterator()
                group_by = {}
                questions = Question.objects.filter(
                    category=Question.INCOME).order_by('id')
                for question in questions:
                    group_by[question] = {}
                try:
                    income = next(income_iter)
                    for question in group_by:
                        while income.question_id <= question.id:
                            # If not source, make one up.
                            source = (income.source
                                if income.source else 'no-source')
                            if source not in group_by[question]:
                                group_by[question][source] = {}
                            if (income.verified
                                not in group_by[question][source]):
                                group_by[question][source][income.verified] = []
                            group_by[question][source][income.verified] \
                                += [income]
                            income = next(income_iter)
                except StopIteration:
                    pass
                setattr(app_tenant.resident, 'by_questions', group_by)
        return context


class SourceMixin(ResidentMixin):
    """
    Source of income.
    """

    @property
    def source(self):
        if not hasattr(self, '_source'):
            self._source = get_object_or_404(
                Source, resident=self.resident, slug=self.kwargs.get('source'))
        return self._source
