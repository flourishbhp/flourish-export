from django.conf import settings
from edc_model_wrapper import ModelWrapper


class ExportFileModelWrapper(ModelWrapper):

    model = 'flourish_export.exportfile'
    next_url_attrs = ['export_identifier']
    next_url_name = settings.DASHBOARD_URL_NAMES.get(
        'export_listboard_url')

    @property
    def file_url(self):
        """Return the file url.
        """
        try:
            return self.object.document.url
        except ValueError:
            return None

    @property
    def files_generation_time(self):
        """return file generation time in minutes
        """
        download_time = self.object.download_time
        if download_time:
            return round(float(self.object.download_time) / 60.0, 2)
        return None
