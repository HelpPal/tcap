# Copyright (c) 2016, TeaCapp LLC
#   All rights reserved.

import os

from django_assets import Bundle, register
from django.conf import settings

#pylint: disable=invalid-name

# All the CSS we need for the entire app. This tradeoff between
# bandwidth and latency is good as long as we have a high and consistent
# utilization of all the CSS tags for all pages on the site.
css_base = Bundle(
    Bundle(
        os.path.join(settings.BASE_DIR,
            'assets/less/base/tcapp-bootstrap.less'),
        filters='less', output='cache/bootstrap.css',
        debug=False),
        'vendor/font-awesome.css',
    filters='cssmin', output='cache/teacapp.css')
register('css_base', css_base)

css_email = Bundle(
    os.path.join(settings.BASE_DIR, 'assets/less/email/email.less'),
    filters=['less', 'cssmin'],
    output='cache/email.css', debug=False)
register('css_email', css_email)


# Minimal, jquery always active on the site
js_base = Bundle(
    'vendor/jquery.js',
    'vendor/bootstrap.js',
    filters='yui_js', output='cache/base.js')
register('js_base', js_base)

js_angular = Bundle(
    'vendor/moment.js',
    'vendor/angular.min.js', # XXX pre-minified or runs into errors
    'vendor/ui-bootstrap-tpls.js',
    filters='jsmin', output='cache/angular.js')
register('js_angular', js_angular)

# Application javascript
js_tcapp = Bundle(
    'vendor/djaodjin-resources.js',
    'vendor/djaodjin-postal.js',
    'vendor/dropzone.js', # XXX After djaodjin-postal.js or error
    'js/djaodjin-upload.js',
    'js/tcapp.js',
    filters='rjsmin', output='cache/tcapp.js')
register('js_tcapp', js_tcapp)
