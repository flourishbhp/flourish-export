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
    admin_helper_cls = AdminExportHelper
    export_identifier_cls = ExportIdentifier

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
        
    def create_export_obj(self, app_label, ):
        export_identifier = self.export_identifier_cls().identifier

        description = f'{app_label.replace("_", " ").title()} Export(s)'
        model_options = {
            'description': description,
            'study': app_label,
            'export_identifier': export_identifier, }

        ExportFile.objects.create(**model_options)
        return export_identifier
        
    def generate_export(self, app_label, ):
        app_list = self.admin_helper_cls().get_app_list(app_label)
        app_list = self.admin_helper_cls().remove_exclude_models(app_list)
        user_emails = [self.request.user.email]

        try:
            ExportFile.objects.get(study=app_label,
                                   download_complete=False)
        except ExportFile.DoesNotExist:
            export_identifier = self.create_export_obj(app_label)
            generate_exports.delay(app_list, True, user_emails, export_identifier)
            message = (f'{app_label.replace("_", " ").capitalize()} export has been initiated, '
                       'an email will be sent once download completes.')
        else:
            message = (f'Download for {app_label.replace("_", " ").capitalize()} that was '
                        'initiated is still running. Please wait until an export is fully prepared.')
                
        messages.add_message(self.request, messages.INFO, message)
