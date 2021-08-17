import datetime
import re
import threading
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.constants import LOOKUP_SEP
from django.utils.decorators import method_decorator

from edc_base.view_mixins import EdcBaseViewMixin
from edc_dashboard.view_mixins import ListboardFilterViewMixin, SearchFormViewMixin
from edc_dashboard.views import ListboardView
from edc_navbar import NavbarViewMixin

from ..identifiers import ExportIdentifier
from ..model_wrappers import ExportFileModelWrapper
from ..models import ExportFile
from .listboard_view_mixin import ListBoardViewMixin


class ListBoardView(NavbarViewMixin, EdcBaseViewMixin, ListBoardViewMixin,
                    ListboardFilterViewMixin, SearchFormViewMixin, ListboardView):

    listboard_template = 'export_listboard_template'
    listboard_url = 'export_listboard_url'
    listboard_panel_style = 'info'
    listboard_fa_icon = "fa-user-plus"

    model = 'flourish_export.exportfile'
    model_wrapper_cls = ExportFileModelWrapper
    identifier_cls = ExportIdentifier
    navbar_name = 'flourish_export'
    navbar_selected_item = 'export_data'
    ordering = '-modified'
    paginate_by = 10
    search_form_url = 'export_listboard_url'
    description_queryset_lookups = []

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def stop_main_thread(self, thread_name):
        """Stop export file generation thread.
        """
        time.sleep(20)
        threads = threading.enumerate()
        threads = [t for t in threads if t.is_alive()]
        for thread in threads:
            if thread.name == thread_name:
                thread._stop()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        download = self.request.GET.get('download')

        if download == '1':
            self.generate_export(thread_name='flourish_all_export',
                                 thread_target=self.download_all_data,
                                 description='Flourish All Export')

        context.update(export_add_url=self.model_cls().get_absolute_url())
        return context

    def generate_export(self, thread_name=None, active_download=False,
                        thread_target=None, description=None):

        threads = threading.enumerate()

        if threads:
            for thread in threads:
                if thread.name == thread_name:
                    active_download = True
                    messages.add_message(
                        self.request, messages.INFO,
                        ('Download that was initiated is still running '
                         'please wait until an export is fully prepared.'))

        if not active_download:
            is_clean = self.is_clean(description=description)
            if is_clean:

                download_thread = threading.Thread(
                    name=thread_name, target=thread_target,
                    daemon=True)
                download_thread.start()
                last_doc = ExportFile.objects.filter(
                    description=description,
                    download_complete=True).order_by('created').last()

                if last_doc:
                    start_time = datetime.datetime.now().strftime(
                        "%d/%m/%Y %H:%M:%S")
                    last_doc_time = round(
                        float(last_doc.download_time) / 60.0, 2)

                    messages.add_message(
                        self.request, messages.INFO,
                        ('Download initiated, you will receive an email once '
                         'the download is completed. Estimated download time: '
                         f'{last_doc_time} minutes, file generation started at:'
                         f' {start_time}'))
                else:
                    messages.add_message(
                        self.request, messages.INFO,
                        ('Download initiated, you will receive an email once '
                         'the download is completed.'))

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
