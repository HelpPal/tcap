# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import logging

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, UpdateView

from ..forms import DemographicProfileForm, ResidentCreateForm
from ..mixins import ApplicationMixin, ResidentMixin
from ..models import Resident, ApplicationResident

LOGGER = logging.getLogger(__name__)


class DemographicProfileView(ResidentMixin, UpdateView):

    queryset = Resident.objects.all()
    form_class = DemographicProfileForm
    template_name = 'tcapp/tenant/demographic_profile.html'

    def get_object(self, queryset=None):
        return self.resident

    def form_valid(self, form):
        return super(DemographicProfileView, self).form_valid(form)

    def get_success_url(self):
        return reverse('application_detail',
            args=(self.application.lihtc_property, self.application,))


class ResidentCreateView(ApplicationMixin, CreateView):
    """
    Display the cover used to gather information about one tenant
    who is part of a household.
    """
    form_class = ResidentCreateForm
    template_name = 'tcapp/tenant/resident.html'

    def form_invalid(self, form):
        return super(ResidentCreateView, self).form_invalid(form)

    def form_valid(self, form):
        with transaction.atomic():
            result = super(ResidentCreateView, self).form_valid(form)
            ApplicationResident.objects.create(
                application=self.application,
                resident=self.object,
                relation_to_head=form.cleaned_data['relation_to_head'])
        return result

    def get_success_url(self):
        messages.success(self.request, "Successfuly added resident.")
        if self.object.is_adult:
            return reverse('tenant_contact',
                args=(self.application.lihtc_property, self.object,))
        if self.application:
            return reverse('application_detail',
                args=(self.application.lihtc_property, self.application,))
        return reverse('application_base')


class ResidentUpdateView(ResidentMixin, UpdateView):

    form_class = ResidentCreateForm
    template_name = 'tcapp/tenant/resident.html'

    def get_context_data(self, **kwargs):
        context = super(ResidentUpdateView, self).get_context_data(**kwargs)
        self.update_context_urls(context, {
            'api_application_resident': reverse('api_application_resident',
                args=(self.application.lihtc_property, self.application,
                      self.resident))})
        return context

    def get_initial(self):
        kwargs = super(ResidentUpdateView, self).get_initial()
        rel = get_object_or_404(ApplicationResident,
            application=self.application,
            resident=self.resident)
        kwargs.update({'relation_to_head': rel.relation_to_head})
        return kwargs

    def get_object(self, queryset=None):
        return self.resident

    def get_success_url(self):
        messages.success(self.request, "Successfuly updated resident.")
        return reverse('demographic_profile',
            args=(self.application.lihtc_property, self.object,))
