from django.views.generic import TemplateView
from edc_base.view_mixins import EdcBaseViewMixin
from edc_navbar import NavbarViewMixin

from ..admin_export_helper import AdminExportHelper
from ..identifiers import ExportIdentifier
from ..models import ExportFile
from .listboard_view_mixin import ListBoardViewMixin
from .export_methods_view_mixin import ExportMethodsViewMixin


class HomeView(ExportMethodsViewMixin,
               ListBoardViewMixin, EdcBaseViewMixin,
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
