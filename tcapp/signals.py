# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.dispatch import Signal, receiver
from extended_templates.backends import get_email_backend


#pylint: disable=invalid-name
application_created = Signal(providing_args=["application", "url"])

def get_lihtc_property_email(lihtc_property):
    to_emails = [settings.DEFAULT_FROM_EMAIL]
    try:
        # XXX Hack to read a property e-mail address that can be updated
        #     through an organization profile page.
        with connection.cursor() as cursor:
            cursor.execute("SELECT auth_user.email FROM auth_user INNER JOIN saas_role ON auth_user.id = saas_role.user_id INNER JOIN saas_organization ON saas_role.organization_id = saas_organization.id WHERE saas_role.role_description_id = 1 AND slug='%s'" % lihtc_property.slug) #pylint:disable=line-too-long
            to_emails = [row[0] for row in cursor.fetchall()]
    except OperationalError:
        pass
    return to_emails


# We insure the method is only bounded once no matter how many times
# this module is loaded by using a dispatch_uid as advised here:
#   https://docs.djangoproject.com/en/dev/topics/signals/
@receiver(application_created, dispatch_uid="application_created_notice")
def application_created_notice(sender, application, url, **kwargs):
    #pylint:disable=unused-argument
    get_email_backend().send(
        recipients=get_lihtc_property_email(application.lihtc_property),
        reply_to=settings.DEFAULT_FROM_EMAIL,
        template='notification/application_created.eml',
        context={'site': application.lihtc_property,
            'provider': {
                'email': settings.DEFAULT_FROM_EMAIL,
                'phone': "17084622842"},
            'application': application,
            'back_url': url})
