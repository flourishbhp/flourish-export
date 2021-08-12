from django.views.generic import TemplateView
from edc_base.view_mixins import EdcBaseViewMixin
from edc_navbar import NavbarViewMixin


class HomeView(EdcBaseViewMixin, NavbarViewMixin, TemplateView):

    template_name = 'flourish_export/home.html'
    navbar_name = 'flourish_export'
    navbar_selected_item = 'study_data_export'
