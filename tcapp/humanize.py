# Copyright (c) 2018, TeaCapp LLC
#   All rights reserved.

from __future__ import unicode_literals

from django.utils import six


def as_money(value, currency='usd', whole_dollars=False, show_unit=True):
    assert isinstance(value, six.integer_types)
    currency = currency.lower()
    cents = value % 100
    if whole_dollars and cents > 50:
        value += 100
    if show_unit:
        result = '${:,}'.format(value / 100)
    else:
        result = '{:,}'.format(value / 100)
    if not whole_dollars:
        result += '.%02d' % cents
    return result


def as_percentage(value):
    assert isinstance(value, six.integer_types)
    frac = value % 100
    result = '{:,}'.format(value / 100)
    result += '.%02d%%' % frac
    return result
