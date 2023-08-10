from django.apps import apps as django_apps

from .export_methods import ExportMethods


class ExportRequisitionData:
    """Export data.
    """

    def __init__(self, caregiver_export_path=None, child_export_path=None):
        self.caregiver_export_path = caregiver_export_path or django_apps.get_app_config('flourish_export').caregiver_path
        self.child_export_path = child_export_path or django_apps.get_app_config('flourish_export').child_path
        self.export_methods_cls = ExportMethods()