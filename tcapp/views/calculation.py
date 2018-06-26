# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import logging

from django import forms
from django.core.urlresolvers import reverse
from django.views.generic.edit import UpdateView

from ..mixins import CalculationMixin
from ..models import Application
from ..serializers import EnumField

LOGGER = logging.getLogger(__name__)


class HouseholdCalculationForm(forms.ModelForm):

    status = forms.CharField()

    class Meta:
        model = Application
        fields = ('status',)

    def clean_status(self):
        field = EnumField(choices=Application.STATUS)
        self.cleaned_data['status'] = field.to_internal_value(
            self.cleaned_data['status'])
        return self.cleaned_data['status']


class HouseholdCalculation(CalculationMixin, UpdateView):

    template_name = 'tcapp/calculation.html'
    model = Application
    form_class = HouseholdCalculationForm

    def get_object(self, queryset=None):
        return self.application

    def get_context_data(self, **kwargs):
        context = super(HouseholdCalculation, self).get_context_data(**kwargs)
        context.update({
            'manages_property': self.manages(
                self.application.lihtc_property.slug)})
        return context

    def get_success_url(self):
        if self.application.status == Application.STATUS_VERIFICATION:
            return reverse('application_detail',
                args=(self.application.lihtc_property, self.application))
        return reverse('application_base')
