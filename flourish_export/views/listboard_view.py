import re
import django_rq

from rq import Retry
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.constants import LOOKUP_SEP
from django.utils.decorators import method_decorator

from edc_base.view_mixins import EdcBaseViewMixin
from edc_dashboard.view_mixins import ListboardFilterViewMixin, SearchFormViewMixin
from edc_dashboard.views import ListboardView
from edc_navbar import NavbarViewMixin

from ..admin_export_helper import AdminExportHelper
from ..identifiers import ExportIdentifier
from ..model_wrappers import ExportFileModelWrapper
from ..models import ExportFile
from ..tasks import generate_exports
from .listboard_view_mixin import ListBoardViewMixin
from .export_methods_view_mixin import ExportMethodsViewMixin


class ListBoardView(NavbarViewMixin, EdcBaseViewMixin, ExportMethodsViewMixin,
                    ListBoardViewMixin, ListboardFilterViewMixin,
                    SearchFormViewMixin, ListboardView):

    listboard_template = 'export_listboard_template'
    listboard_url = 'export_listboard_url'
    listboard_panel_style = 'info'
    listboard_fa_icon = "fa-user-plus"

    model = 'flourish_export.exportfile'
    model_wrapper_cls = ExportFileModelWrapper
    export_identifier_cls = ExportIdentifier
    admin_helper_cls = AdminExportHelper
    navbar_name = 'flourish_export'
    navbar_selected_item = 'export_data'
    ordering = '-modified'
    paginate_by = 10
    search_form_url = 'export_listboard_url'
    description_queryset_lookups = []

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        download = self.request.GET.get('download')

        if download == '1':
            self.generate_export()

        context.update(export_add_url=self.model_cls().get_absolute_url())
        return context

    def generate_app_list(self, app_label, existing_app_list):
        """ Get the app list mapping for the specific app_label and update
            the models to the main app list.
        """
        app_list = self.admin_helper_cls().get_app_list(app_label)
        app_list = self.admin_helper_cls().remove_exclude_models(app_list)
        existing_app_list.update(app_list)

    def generate_export(self):
        app_list = {}
        app_labels = ['flourish_caregiver', 'flourish_child', 'flourish_prn', ]
        user_emails = [self.request.user.email, ]

        for app_label in app_labels:
            self.generate_app_list(app_label, app_list)
        try:
            ExportFile.objects.get(study='flourish',
                                   description='Flourish All Export',
                                   download_complete=False)
        except ExportFile.DoesNotExist:
            export_identifier = self.create_export_obj(
                app_label='flourish', description='Flourish All Export')

            queue = django_rq.get_queue('full_exports')
            queue.enqueue(
                generate_exports,
                app_list=app_list,
                create_zip=True,
                full_export=True,
                user_emails=user_emails,
                export_identifier=export_identifier,
                queue_name='full_exports',
                retry=Retry(max=5),  # Retry failed tasks up to 5 times
            )

            message = (
                f'Full flourish data export has been '
                'initiated, an email will be sent once download completes.')
        else:
            message = (f'Download for flourish full data export '
                       'that was initiated is still running. Please wait until an '
                       'export is fully prepared.')
        messages.add_message(self.request, messages.INFO, message)

    def get_queryset_filter_options(self, request, *args, **kwargs):
        options = super().get_queryset_filter_options(request, *args, **kwargs)
        options = self.add_description_filter_options(
            options=options, **kwargs)
        if kwargs.get('export_identifier'):
            options.update(
                {'export_identifier': kwargs.get('export_identifier')})
        return options

    @property
    def description_lookup_prefix(self):
        description_lookup_prefix = LOOKUP_SEP.join(self.description_queryset_lookups)
        return f'{description_lookup_prefix}__' if description_lookup_prefix else ''

    def add_description_filter_options(self, options=None, **kwargs):
        """Updates the filter options to limit the description for all data
        download.
        """
        description = 'Flourish All Export'
        options.update(
            {f'{self.description_lookup_prefix}description': description})
        return options

    def extra_search_options(self, search_term):
        q = Q()
        if re.match('^[A-Z]+$', search_term):
            q = Q(first_name__exact=search_term)
        return q
