# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

from __future__ import unicode_literals

import json, logging

from django.db import transaction
from rest_framework import status
from rest_framework.generics import (get_object_or_404, CreateAPIView,
    DestroyAPIView)
from rest_framework.response import Response

from ..mixins import ApplicationMixin, ResidentMixin
from ..models import ApplicationResident, Resident
from ..serializers import ResidentSerializer

#pylint:disable=old-style-class

LOGGER = logging.getLogger(__name__)


class ApplicationResidentAPIView(ResidentMixin, DestroyAPIView):
    """
    Removes a resident from an application.
    """

    def get_object(self):
        return get_object_or_404(ApplicationResident.objects.all(),
            application__slug=self.kwargs.get('application'),
            resident__slug=self.kwargs.get('resident'))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        LOGGER.info("%s removed resident '%s' from application '%s'.",
            request.user, self.kwargs.get('resident'),
            self.kwargs.get('application'))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResidentCreateAPIView(ApplicationMixin, CreateAPIView):

    serializer_class = ResidentSerializer

    def perform_create(self, serializer):
        LOGGER.info(json.dumps(self.request.data, indent=2))
        with transaction.atomic():
            children = serializer.validated_data.get('children')
            relation_to_head = serializer.validated_data['relation_to_head']
            resident = serializer.save()
            ApplicationResident.objects.create(
                application=self.application,
                resident=resident,
                relation_to_head=relation_to_head)
            for child in children:
                child_resident = Resident.objects.create(
                    last_name=child.get('last_name'),
                    first_name=child.get('first_name'),
                    middle_initial=child.get('middle_initial'),
                    date_of_birth=child.get('date_of_birth'))
                ApplicationResident.objects.create(
                    application=self.application,
                    resident=child_resident,
                    relation_to_head=child.get('relation_to_head'))
