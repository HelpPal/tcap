# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import logging
from collections import OrderedDict

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic import DetailView, ListView
from extra_views.contrib.mixins import SearchableListMixin

from ..forms import ProjectSearchForm
from ..mixins import PropertyMixin
from ..models import Property, PropertyAMIUnits


LOGGER = logging.getLogger(__name__)


class ProjectDetailView(PropertyMixin, DetailView):
    """
    Public information about a LIHTC property.
    """

    template_name = 'tcapp/project/project.html'

    def get_context_data(self, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        limits = OrderedDict()
        for ami_units in PropertyAMIUnits.objects.filter(
                lihtc_property=self.project).order_by('-ami_percentage'):
            income_limits = []
            for income_limit in self.project.county.current_income_limits:
                income_limits += [
                    (income_limit.family_size,
                     income_limit.as_percent(ami_units.ami_percentage))]
            rent_limits = []
            for rent_limit in self.project.county.current_rent_limits:
                rent_limits += [
                    (rent_limit.nb_bedrooms,
                     rent_limit.as_percent(ami_units.ami_percentage))]
            limits[ami_units.ami_percentage] = {
                'income': income_limits, 'rent': rent_limits}
        if not limits:
            # If we don't know the AMI units mix, defaults to 60% limits.
            ami_percentage = 60
            income_limits = []
            for income_limit in self.project.county.current_income_limits:
                income_limits += [
                    (income_limit.family_size,
                     income_limit.as_percent(ami_percentage))]
            rent_limits = []
            for rent_limit in self.project.county.current_rent_limits:
                rent_limits += [
                    (rent_limit.nb_bedrooms,
                     rent_limit.as_percent(ami_percentage))]
            limits[ami_percentage] = {
                'income': income_limits, 'rent': rent_limits}
        context.update({
            'limits': limits,
            'application_url': self.request.build_absolute_uri(reverse(
                'application_wizard', args=(self.project,)))
        })
        return context


class ProjectListMixin(object):

    @staticmethod
    def get_queryset():
        return Property.objects.all()


class ProjectSearchView(SearchableListMixin, ProjectListMixin, ListView):
    """
    Search for a project based on its TCC number.
    """

    form_class = ProjectSearchForm
    paginate_by = 25

    # XXX q="San Francisco" often written San+Francisco
    search_fields = [('tcac_number', 'startswith'),
                     'name',
                     'locality']
    template_name = 'tcapp/project/index.html'

    def get_search_query(self):
        if not hasattr(self, '_query'):
            form = self.form_class(data=self.request.GET)
            form.is_valid()
            self._query = form.cleaned_data.get('q', None)
        return self._query

    def get_context_data(self, **kwargs):
        context = super(ProjectSearchView, self).get_context_data(**kwargs)
        if self.get_search_query():
            context.update({'query': self.get_search_query()})
        return context

    def get(self, request, *args, **kwargs):
        status = 404
        self.object_list = []
        if self.get_search_query() is not None:
            self.object_list = self.get_queryset()
            status = 404 if self.object_list.count() == 0 else None
            if self.object_list.count() == 1:
                return HttpResponseRedirect(reverse(
                    'project_detail', args=(self.object_list.get(),)))
        context = self.get_context_data()
        return self.render_to_response(context, status=status)
