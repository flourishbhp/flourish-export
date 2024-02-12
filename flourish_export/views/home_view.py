import threading
from django.contrib import messages
from django.views.generic import TemplateView
from edc_base.view_mixins import EdcBaseViewMixin
from edc_navbar import NavbarViewMixin

from ..admin_export_helper import AdminExportHelper
from ..tasks import generate_exports
from ..identifiers import ExportIdentifier
from ..models import ExportFile
from .listboard_view_mixin import ListBoardViewMixin


class HomeView(ListBoardViewMixin, EdcBaseViewMixin,
               NavbarViewMixin, TemplateView):

    template_name = 'flourish_export/home.html'
    navbar_name = 'flourish_export'
    navbar_selected_item = 'study_data_export'
    identifier_cls = ExportIdentifier
    admin_helper_cls = AdminExportHelper

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        download = self.request.GET.get('download')

        if download == '3':   
            self.generate_export(app_label='flourish_caregiver')
        elif download == '4':
            self.generate_export(app_label='flourish_child')

        caregiver_crf_exports = ExportFile.objects.filter(
            description='Flourish Caregiver Export(s)').order_by('-uploaded_at')[:10]

        child_crf_exports = ExportFile.objects.filter(
            description='Flourish Child Export(s)').order_by('-uploaded_at')[:10]
        context.update(
            caregiver_crf_exports=caregiver_crf_exports,
            child_crf_exports=child_crf_exports)
        return context

    def acquire_export_lock(self, app_label, ):
        thread_name = f'{app_label}_export'
        threads = threading.enumerate()
        active_download = False

        for thread in threads:
            if thread.name == thread_name:
                active_download = True
                messages.add_message(
                    self.request,
                    messages.INFO,
                    f'Download for {app_label.replace("_", " ").capitalize()} that was '
                    'initiated is still running. Please wait until an export is fully prepared.')

        if not active_download:
            self.admin_helper_cls().start_export_thread(
                thread_name,
                self.generate_export,
                app_label)
            messages.add_message(
                self.request,
                messages.INFO,
                f'{app_label.replace("_", " ").capitalize()} export has been initiated, '
                'an email will be sent once download completes.')

    def generate_export(self, app_label, ):
        app_list = self.admin_helper_cls().get_app_list(app_label)
        app_list = self.admin_helper_cls().remove_exclude_models(app_list)
        user_emails = [self.request.user.email]

        generate_exports.delay(app_list, True, user_emails)
