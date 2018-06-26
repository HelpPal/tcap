# Copyright (c) 2018, TeaCapp LLC
#   All rights reserved.
from __future__ import unicode_literals

from collections import OrderedDict

from django import template
from django.utils import six

from ..models import (ApplicationResident, Asset, Income, Question,
    annualize_income as _annualize_income,
    greater_of_assets as greater_of_assets_base,
    greater_of_annualize_income as greater_of_annualize_income_base,
    sum_greater_of_annualize_income as sum_greater_of_annualize_income_base)
from ..humanize import  as_money

register = template.Library()

@register.filter()
def by_account(object_list, account):
    queryset = object_list.filter(
        lihtc_property__account=account).order_by('effective_date')
    return queryset


@register.filter()
def extra(resident, application):
    return ApplicationResident.objects.filter(
        resident=resident, application=application).first()

@register.filter()
def asset_categories(bogus): #pylint:disable=unused-argument
    return OrderedDict(dict(Asset.CATEGORY))

@register.filter()
def income_limit(application, restriction=None):
    return application.get_income_limit(restriction=restriction)

@register.filter()
def income_periods(bogus): #pylint:disable=unused-argument
    periods = OrderedDict()
    dct = dict(Income.PERIOD)
    for period in [Income.HOURLY,
                   Income.DAILY,
                   Income.WEEKLY,
                   Income.BI_WEEKLY,
                   Income.SEMI_MONTHLY,
                   Income.MONTHLY,
                   Income.YEARLY]:
        periods.update({dct[period]:dct[period]})
    return periods

@register.filter()
def income_period_avgs(bogus): #pylint:disable=unused-argument
    periods = OrderedDict()
    dct = dict(Income.PERIOD)
    for period in [Income.WEEKLY,
                   Income.BI_WEEKLY,
                   Income.SEMI_MONTHLY,
                   Income.MONTHLY,
                   Income.YEARLY]:
        periods.update({dct[period]:dct[period]})
    return periods

@register.filter()
def is_income(answer):
    return answer.question.category == Question.INCOME

@register.filter()
def is_assets(answer):
    return answer.question.category == Question.ASSETS

@register.filter()
def has_implicit_period(verified):
    # Does not include Income.VERIFIED_PERIOD_TO_DATE because we only
    # annualize the sum of all records, not each individual record.
    return verified in [
        Income.VERIFIED_YEAR_TO_DATE,
        Income.VERIFIED_TAX_RETURN]

@register.filter()
def get_asset_category_display(category):
    return dict(Asset.CATEGORY)[category]

@register.filter()
def get_verified_display(verified):
    return dict(Income.VERIFIED)[verified]


@register.filter()
def humanize_list(values):
    return ', '.join([str(value) for value in values])


@register.filter()
def annualize_income(incomes, verified):
    """
    Annualize a list of ``Income`` based on a verification method.
    """
    try:
        return _annualize_income(incomes, verified)
    except ValueError:
        # XXX until we figure out how to report divide by zero
        return six.MAXSIZE

@register.filter()
def greater_of_assets(assets):
    greater_of = greater_of_assets_base(assets)
    if greater_of:
        return greater_of.amount
    return 0

@register.filter()
def greater_of_annualize_income(verifications):
    return greater_of_annualize_income_base(verifications)


@register.filter()
def sum_greater_of_annualize_income(verif_by_sources):
    return sum_greater_of_annualize_income_base(verif_by_sources)


@register.filter()
def humanize_money(value, currency='usd'):
    return as_money(value, currency)


@register.filter()
def humanize_dollars(value):
    return as_money(value, whole_dollars=True)


@register.filter()
def humanize_percentage(value):
    return "%.2f%%" % (float(value) / 100) # XXX lazy use of float


@register.filter()
def sum_amount(incomes):
    """
    Sum a list of period-to-date ``Income``.
    """
    total = 0
    for income in incomes:
        total += income.amount
    return total


@register.filter()
def sum_days(incomes):
    """
    Sum a list of period-to-date ``Income``.
    """
    groups = {}
    for income in incomes:
        if income.group not in groups:
            groups[income.group] = income
    total = 0
    for income in six.itervalues(groups):
        total += income.nb_days
    return total

