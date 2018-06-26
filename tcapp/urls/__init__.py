# Copyright (c) 2017, TeaCapp LLC
#   All rights reserved.

from django.conf import settings
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.views.static import serve as static_serve

from ..urlbuilders import url_prefixed
from ..views.application import (ApplicationView, ApplicationBaseView,
    ApplicationChecklistView, ApplicationDetailView, ApplicationDocumentsView)
from ..views.project import ProjectDetailView, ProjectSearchView
from ..views.resident import (DemographicProfileView, ResidentCreateView,
    ResidentUpdateView)
from ..views.tenant import (
    UpdateAssetsView, AssetsVerificationView, IncomeVerificationView,
    UpdateIncomeView,
    SelfEmployedIncomeCreateView,
    EmployeeIncomeCreateView,
    OthersIncomeCreateView,
    UnemployedBenefitsIncomeCreateView,
    VeteranBenefitsIncomeCreateView,
    SocialBenefitsIncomeCreateView,
    SupplementalBenefitsIncomeCreateView,
    DisabilityBenefitsIncomeCreateView,
    PublicAssistanceIncomeCreateView,
    ChildAlimonySupportIncomeCreateView,
    SudentFinancialAidIncomeCreateView,
    UpdateIncomeSourceView, TenantContactView)
from ..views.calculation import HouseholdCalculation
from ..views.downloads import IncomeReportCSVView
from ..views.verification import (InitialApplicationView,
    LeaseView, LeaseRiderView, VerificationEmploymentView,
    ZeroIncomeView, ChildOrSpousalSupportView, ChildOrSpousalAffidavitView,
    FosterCareView, LiveInAidView, MaritalSeparationView, SingleParentView,
    StudentFinancialAidView, StudentStatusView, TICView, TICQView,
    Under5000AssetsView)

if settings.DEBUG: #pylint: disable=no-member
    from django.contrib import admin
    from django.views.defaults import page_not_found, server_error
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    import debug_toolbar

    admin.autodiscover()
    urlpatterns = staticfiles_urlpatterns()
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^media/(?P<path>.*)$',
            static_serve, {'document_root': settings.MEDIA_ROOT}),
        url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
        url(r'^admin/', include(admin.site.urls)),
        url(r'^404/$', page_not_found),
        url(r'^500/$', server_error),
    ]
else:
    urlpatterns = [
        url(r'^%s(?P<path>.*)$' % settings.STATIC_URL[1:], # remove leading '/'
            static_serve, {'document_root': settings.STATIC_ROOT}),
        url(r'^media/(?P<path>.*)$',
            static_serve, {'document_root': settings.MEDIA_ROOT}),
    ]


urlpatterns += [
    url_prefixed(r'api/', include('tcapp.urls.api')),
    url_prefixed(r'projects/(?P<project>%s)/application/' % settings.SLUG_RE,
         ApplicationView.as_view(), name='application_wizard'),
    url_prefixed(r'projects/(?P<project>%s)/' % settings.SLUG_RE,
        ProjectDetailView.as_view(), name='project_detail'),
    url_prefixed(r'projects/',
        ProjectSearchView.as_view(), name='project_search'),

    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/source/new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        UpdateIncomeSourceView.as_view(), name='tenant_asset_source_new'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/assets/new/' % (
            settings.SLUG_RE, settings.SLUG_RE),
        UpdateAssetsView.as_view(), name='tenant_assets_entry_new'),
    url_prefixed(
      r'app/(?P<project>%s)/verification/(?P<resident>%s)/assets/(?P<entry>%s)/'
        % (settings.SLUG_RE, settings.SLUG_RE, settings.SLUG_RE),
        UpdateAssetsView.as_view(), name='tenant_asset_entry'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<resident>%s)/assets/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        AssetsVerificationView.as_view(),
        name='assets_verification'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/source/new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        UpdateIncomeSourceView.as_view(), name='tenant_income_source_new'),
    url_prefixed(
    r'app/(?P<project>%s)/verification/(?P<resident>%s)/source/(?P<source>%s)/'
        % (settings.SLUG_RE, settings.SLUG_RE, settings.SLUG_RE),
        UpdateIncomeSourceView.as_view(), name='tenant_income_source'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/source/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        TemplateView.as_view(), name='tenant_income_source_base'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/selfemployed-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        SelfEmployedIncomeCreateView.as_view(),
        name='tenant_income_entry_selfemployed_new'),
    url_prefixed(
      r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/employee-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        EmployeeIncomeCreateView.as_view(),
        name='tenant_income_entry_employee_new'),
    url_prefixed(
      r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/others-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        OthersIncomeCreateView.as_view(),
        name='tenant_income_entry_gifts_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/unemployment-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        UnemployedBenefitsIncomeCreateView.as_view(),
        name='tenant_income_entry_unemployment_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/veteran-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        VeteranBenefitsIncomeCreateView.as_view(),
        name='tenant_income_entry_veteran_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/socialsecurity-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        SocialBenefitsIncomeCreateView.as_view(),
        name='tenant_income_entry_socialsecurity_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/supplemental-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        SupplementalBenefitsIncomeCreateView.as_view(),
        name='tenant_income_entry_supplemental_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/disability-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        DisabilityBenefitsIncomeCreateView.as_view(),
        name='tenant_income_entry_disability_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/'\
'publicassistance-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        PublicAssistanceIncomeCreateView.as_view(),
        name='tenant_income_entry_publicassistance_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/support-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        ChildAlimonySupportIncomeCreateView.as_view(),
        name='tenant_income_entry_support_new'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/'\
'studentfinancialaid-new/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        SudentFinancialAidIncomeCreateView.as_view(),
        name='tenant_income_entry_studentfinancialaid_new'),
    url_prefixed(
    r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/(?P<entry>%s)/'
        % (settings.SLUG_RE, settings.SLUG_RE, settings.SLUG_RE),
        UpdateIncomeView.as_view(), name='tenant_income_entry'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<resident>%s)/income/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        IncomeVerificationView.as_view(),
        name='income_verification'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/employment/(?P<source>%s)/'
        % (settings.SLUG_RE, settings.SLUG_RE, settings.SLUG_RE),
        VerificationEmploymentView.as_view(),
        name='tenant_verification_employment'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/employment/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        VerificationEmploymentView.as_view(),
        name='tenant_verification_employment_base'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/zero-income/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        ZeroIncomeView.as_view(),
        name='tenant_verification_zero_income'),
    url_prefixed(
r'app/(?P<project>%s)/verification/(?P<resident>%s)/support/'\
'(?P<source>%s)/affidavit/'
        % (settings.SLUG_RE, settings.SLUG_RE, settings.SLUG_RE),
        ChildOrSpousalAffidavitView.as_view(),
        name='tenant_verification_child_or_spousal_affidavit'),
    url_prefixed(
    r'app/(?P<project>%s)/verification/(?P<resident>%s)/support/(?P<source>%s)/'
        % (settings.SLUG_RE, settings.SLUG_RE, settings.SLUG_RE),
        ChildOrSpousalSupportView.as_view(),
        name='tenant_verification_child_or_spousal_support'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/foster-care/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        FosterCareView.as_view(),
        name='tenant_verification_foster_care'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/live-in-aid/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        LiveInAidView.as_view(),
        name='tenant_verification_live_in_aid'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/marital-separation/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        MaritalSeparationView.as_view(),
        name='tenant_verification_marital_separation'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/single-parent/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        SingleParentView.as_view(),
        name='tenant_verification_single_parent'),
    url_prefixed(
    r'app/(?P<project>%s)/verification/(?P<resident>%s)/student-financial-aid/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        StudentFinancialAidView.as_view(),
        name='tenant_verification_student_financial_aid'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<resident>%s)/student-status/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        StudentStatusView.as_view(),
        name='tenant_verification_student_status'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<application>%s)/tic/download/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        TICView.as_view(), name='verification_tic'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<application>%s)/tic/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        ApplicationDetailView.as_view(), name='application_detail'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<application>%s)/forms/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        ApplicationChecklistView.as_view(), name='application_checklist'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<application>%s)'\
        '/documents/' % (settings.SLUG_RE, settings.SLUG_RE),
        ApplicationDocumentsView.as_view(), name='application_documents'),
    url_prefixed(
    r'app/(?P<project>%s)/verification/(?P<application>%s)/initial-application/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        InitialApplicationView.as_view(),
        name='verification_initial_application'),
    url_prefixed(
        r'app/(?P<project>%s)/verification/(?P<application>%s)/lease-rider/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        LeaseRiderView.as_view(), name='verification_lease_rider'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<application>%s)/lease/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        LeaseView.as_view(), name='verification_lease'),
    url_prefixed(
    r'app/(?P<project>%s)/verification/(?P<resident>%s)/under-5000-assets/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        Under5000AssetsView.as_view(),
        name='tenant_verification_under_5000_assets'),
  url_prefixed(r'app/(?P<project>%s)/verification/(?P<resident>%s)/demoprofile/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        DemographicProfileView.as_view(), name='demographic_profile'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<resident>%s)/contact/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        TenantContactView.as_view(), name='tenant_contact'),
    url_prefixed(r'app/(?P<project>%s)/verification/(?P<resident>%s)/' %
        (settings.SLUG_RE, settings.SLUG_RE),
        ResidentUpdateView.as_view(), name='resident_update'),
    url_prefixed(r'app/(?P<project>%s)/report/' %
        settings.SLUG_RE,
        IncomeReportCSVView.as_view(), name='income_report'),
    url_prefixed(r'app/(?P<project>%s)/(?P<application>%s)/'\
        'calculation/(?P<resident>%s)/ticq/' % (
            settings.SLUG_RE, settings.SLUG_RE, settings.SLUG_RE),
        TICQView.as_view(), name='tenant_verification_ticq'),
    url_prefixed(r'app/(?P<project>%s)/(?P<application>%s)/calculation/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        HouseholdCalculation.as_view(), name='calculation'),
    url_prefixed(r'app/(?P<project>%s)/(?P<application>%s)/add/'
        % (settings.SLUG_RE, settings.SLUG_RE),
        ResidentCreateView.as_view(), name='application_resident_add'),
    url_prefixed(r'app/',
        ApplicationBaseView.as_view(), name='application_base'),

    # URL to download theme to install on proxy.
    url(r'^(?P<path>themes/.*)$', static_serve,
        {'document_root': settings.HTDOCS}),

    # dummy, served by session front-end
    url_prefixed(r'contact/', TemplateView.as_view(), name='contact'),
    url_prefixed(r'docs/w2-employee/', TemplateView.as_view(
        template_name='docs/w2-employee.html'), name='presentations'),
    url_prefixed(r'$', TemplateView.as_view(template_name='index.html'),
             name='snaplines_page'),

    # Otherwise we can't run the casperjs tests without a proxy firewall.
    url_prefixed(r'', include('deployutils.apps.django.mockup.urls')),
]
