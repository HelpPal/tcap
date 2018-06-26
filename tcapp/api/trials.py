# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import logging

from django.conf import settings as django_settings
from extended_templates.backends import get_email_backend
from rest_framework import serializers
from rest_framework.generics import CreateAPIView

from ..mixins import PropertyMixin

#pylint:disable=old-style-class

LOGGER = logging.getLogger(__name__)


class RequestDemoSerializer(serializers.Serializer):

    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15)
    body = serializers.CharField(max_length=500)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class RequestDemoAPIView(PropertyMixin, CreateAPIView):

    serializer_class = RequestDemoSerializer

    def perform_create(self, serializer):
        get_email_backend().send(
            recipients=[admin[1] for admin in django_settings.ADMINS],
            reply_to=serializer.validated_data['email'],
            template='notification/request_demo.eml',
            context={'project': self.project,
                'email': serializer.validated_data['email'],
                'phone': serializer.validated_data['phone'],
                'body': serializer.validated_data['body']})
