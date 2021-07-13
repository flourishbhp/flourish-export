from datetime import timedelta
import datetime
import re
import threading
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
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

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def stop_main_thread(self):
        """Stop export file generation thread.
        """
        time.sleep(20)
        threads = threading.enumerate()
        threads = [t for t in threads if t.is_alive()]
        for thread in threads:
            if thread.name == 'flourish_export':
                thread._stop()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        download = self.request.GET.get('download')

        if download == '1':
            self.generate_export(thread_name='flourish_export',
                                 thread_target=self.download_all_data,
                                 study_name='flourish')

        context.update(export_add_url=self.model_cls().get_absolute_url())
        return context

    def generate_export(self, thread_name=None, active_download=False,
                        thread_target=None, study_name=None):

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
            is_clean = self.is_clean(study_name=study_name)
            if is_clean:

                download_thread = threading.Thread(
                    name=thread_name, target=thread_target,
                    daemon=True)
                download_thread.start()

                last_doc = ExportFile.objects.filter(
                    study=study_name,
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
        if kwargs.get('export_identifier'):
            options.update(
                {'export_identifier': kwargs.get('export_identifier')})
        return options

    def extra_search_options(self, search_term):
        q = Q()
        if re.match('^[A-Z]+$', search_term):
            q = Q(first_name__exact=search_term)
        return q
