import datetime
import threading
import time

from django.contrib import messages
from django.views.generic import TemplateView
from edc_base.view_mixins import EdcBaseViewMixin
from edc_navbar import NavbarViewMixin

from ..identifiers import ExportIdentifier
from ..models import ExportFile
from .listboard_view_mixin import ListBoardViewMixin


class HomeView(ListBoardViewMixin, EdcBaseViewMixin,
               NavbarViewMixin, TemplateView):

    template_name = 'flourish_export/home.html'
    navbar_name = 'flourish_export'
    navbar_selected_item = 'study_data_export'
    identifier_cls = ExportIdentifier

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

        if download == '2':
            self.generate_export(thread_name='flourish_non_crf_export',
                                 thread_target=self.download_non_crf_data,
                                 description='Flourish Non CRF Export')
        elif download == '3':
            self.generate_export(thread_name='flourish_caregiver_crf_export',
                                 thread_target=self.download_caregiver_data,
                                 description='Flourish Caregiver CRF Export')
        elif download == '4':
            self.generate_export(thread_name='flourish_child_crf_export',
                                 thread_target=self.download_child_data,
                                 description='Flourish Child CRF Export')
        non_crf_exports = ExportFile.objects.filter(
            description='Flourish Non CRF Export').order_by('-uploaded_at')[:10]
        caregiver_crf_exports = ExportFile.objects.filter(
            description='Flourish Caregiver CRF Export').order_by('-uploaded_at')[:10]

        child_crf_exports = ExportFile.objects.filter(
            description='Flourish Child CRF Export').order_by('-uploaded_at')[:10]
        context.update(
            non_crf_exports=non_crf_exports,
            caregiver_crf_exports=caregiver_crf_exports,
            child_crf_exports=child_crf_exports)
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
                        (f'Download for {description} that was initiated is still running '
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
                        (f'Download for {description}has been initiated, you will receive an email once '
                         'the download is completed. Estimated download time: '
                         f'{last_doc_time} minutes, file generation started at:'
                         f' {start_time}'))
                else:
                    messages.add_message(
                        self.request, messages.INFO,
                        (f'Download for {description} initiated, you will receive an email once '
                         'the download is completed.'))
