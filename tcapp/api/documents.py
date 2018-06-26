# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

import hashlib, logging, os

from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from rest_framework import parsers, status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from ..mixins import ApplicationMixin
from ..models import Resident, Source, UploadedDocument
from ..serializers import UploadedDocumentSerializer

#pylint:disable=no-name-in-module,import-error
from django.utils.six.moves.urllib.parse import urlparse, urlunparse

#pylint:disable=old-style-class

LOGGER = logging.getLogger(__name__)


class DocumentUploadView(ApplicationMixin, ListAPIView):

    parser_classes = (parsers.FormParser, parsers.MultiPartParser,
        parsers.JSONParser)

    serializer_class = UploadedDocumentSerializer

    def get_queryset(self):
        return UploadedDocument.objects.filter(application=self.application)

    def post(self, request, *args, **kwargs):
        #pylint:disable=too-many-locals,too-many-statements
        try:
            category = int(request.data.get('category', None))
        except (TypeError, ValueError):
            category = UploadedDocument.OTHER
        try:
            source = Source.objects.get(slug=request.data.get('source'))
        except (Source.DoesNotExist, KeyError):
            source = None
        tenant = request.data.get('tenant', None)
        if tenant:
            tenant = get_object_or_404(Resident, slug=tenant)

        location = request.data.get('location', None)
        if location and 'aws.com/' in location:
            import boto
            from storages.backends.s3boto import S3BotoStorage
            parts = urlparse(location)
            bucket_name = parts.netloc.split('.')[0]
            name = parts.path
            if bucket_name.startswith('s3-'):
                name_parts = name.split('/')
                if name_parts and not name_parts[0]:
                    name_parts.pop(0)
                bucket_name = name_parts[0]
                name = '/'.join(name_parts[1:])
            if name.startswith('/'):
                # we rename leading '/' otherwise S3 copy triggers a 404
                # because it creates an URL with '//'.
                name = name[1:]
            kwargs = {}
            for key in ['access_key', 'secret_key', 'security_token']:
                if key in self.request.session:
                    kwargs[key] = self.request.session[key]
            LOGGER.debug("attempting to access '%s' in bucket '%s'"\
                " with credentials %s", name, bucket_name, kwargs)
            s3_storage = S3BotoStorage(bucket=bucket_name, **kwargs)

            ext = os.path.splitext(name)[1]
            if ext in ['.pdf']:
                metadata = {'Content-Type': 'application/pdf'}
            elif ext in ['.jpg']:
                metadata = {'Content-Type': 'image/jpeg'}
            elif ext in ['.png']:
                metadata = {'Content-Type': 'image/png'}
            else:
                metadata = None
            if s3_storage.url(name) != location:
                LOGGER.warning("re-computed url (%s) != location (%s)",
                s3_storage.url(name), location)
            with s3_storage.open(name) as uploaded_file:
                key_name = "%s/%s%s" % (self.application.slug,
                    hashlib.sha256(uploaded_file.read()).hexdigest(), ext)
            kwargs = {}
            if 'access_key' in self.request.session:
                kwargs['aws_access_key_id'] = self.request.session['access_key']
            if 'secret_key' in self.request.session:
                kwargs['aws_secret_access_key'] \
                    = self.request.session['secret_key']
            if 'security_token' in self.request.session:
                kwargs['security_token'] \
                    = self.request.session['security_token']
            conn = boto.connect_s3(**kwargs)
            bucket = conn.get_bucket(bucket_name)
            key = bucket.get_key(name)
            key.copy(bucket_name, key_name,
                metadata=metadata, preserve_acl=True, encrypt_key=True)
            bucket.delete_key(key)
            location = s3_storage.url(key_name)

        elif 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            # tentatively extract file extension.
            parts = os.path.splitext(
                force_text(uploaded_file.name.replace('\\', '/')))
            ext = parts[-1].lower() if len(parts) > 1 else ""
            key_name = "%s/%s%s" % (self.application.slug,
                hashlib.sha256(uploaded_file.read()).hexdigest(), ext)
            location = self.request.build_absolute_uri(default_storage.url(
                default_storage.save(key_name, uploaded_file)))

        else:
            return Response({'details': "no location or file specified."},
                status=status.HTTP_400_BAD_REQUEST)

        parts = urlparse(location)
        UploadedDocument.objects.get_or_create(application=self.application,
            url=urlunparse((parts.scheme, parts.netloc, parts.path,
            "", "", "")), defaults={'category': category, 'resident': tenant,
            'source': source})
        return Response({'location': location}, status=status.HTTP_201_CREATED)

