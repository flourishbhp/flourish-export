from django.views.generic import TemplateView
from edc_base.view_mixins import AdministrationViewMixin
from edc_base.view_mixins import EdcBaseViewMixin


class AdministrationView(EdcBaseViewMixin,
                         AdministrationViewMixin, TemplateView):
    pass
