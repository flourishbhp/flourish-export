from django.contrib import messages
from ..models import ExportFile
from ..tasks import generate_exports, generate_metadata


class ExportMethodsViewMixin:

    def create_export_obj(self, app_label, description=None):
        export_identifier = self.export_identifier_cls().identifier

        description = description or f'{app_label.replace("_", " ").title()} Export(s)'
        model_options = {
            'description': description,
            'study': app_label,
            'export_identifier': export_identifier, }

        ExportFile.objects.create(**model_options)
        return export_identifier

    def get_or_create_export_file(self, app_label, description):

        try:
            ExportFile.objects.get(study=app_label,
                                   download_complete=False,
                                   description=description)
        except ExportFile.DoesNotExist:
            return self.create_export_obj(app_label, description)
        else:
            return None

    def generate_apps_metadata(
            self, app_label, user_emails=[], app_labels=[], description=None):
        user_emails = user_emails or [self.request.user.email]

        export_identifier = self.get_or_create_export_file(app_label, description)

        if export_identifier:
            generate_metadata.delay(app_labels, user_emails, export_identifier)
            message = ('Metadata export has been initiated, an email will be '
                       'sent once download completes')
        else:
            message = ('Download for Metadata export that was initiated is still'
                       ' running. Please wait until an export is fully prepared.')
        messages.add_message(self.request, messages.INFO, message)

    def generate_export(
            self, app_label, user_emails=[], flat_exports=False, description=None):
        app_list = self.admin_helper_cls().get_app_list(app_label)
        app_list = self.admin_helper_cls().remove_exclude_models(app_list)
        user_emails = user_emails or [self.request.user.email]

        export_identifier = self.get_or_create_export_file(app_label, description)
        if export_identifier:
            generate_exports.delay(app_list, True, False, flat_exports,
                                   user_emails, export_identifier)
            message = (
                f'{app_label.replace("_", " ").capitalize()} export has been '
                'initiated, an email will be sent once download completes.')
        else:
            message = (f'Download for {app_label.replace("_", " ").capitalize()} '
                       'that was initiated is still running. Please wait until an '
                       'export is fully prepared.')

        messages.add_message(self.request, messages.INFO, message)
