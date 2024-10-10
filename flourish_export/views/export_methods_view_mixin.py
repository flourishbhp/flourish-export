from django.contrib import messages
from ..models import ExportFile
from ..tasks import generate_exports


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

    def generate_export(self, app_label, user_emails=[], flat_exports=False):
        app_list = self.admin_helper_cls().get_app_list(app_label)
        app_list = self.admin_helper_cls().remove_exclude_models(app_list)
        user_emails = user_emails or [self.request.user.email]
        description = None
        if flat_exports:
            description = 'Flourish Facet Flat Export(s)'
        

        try:
            ExportFile.objects.get(study=app_label,
                                   download_complete=False,description=description)
        except ExportFile.DoesNotExist:
            export_identifier = self.create_export_obj(app_label, description)
            generate_exports.delay(app_list, True, False, flat_exports,user_emails, export_identifier)
            message = (
                f'{app_label.replace("_", " ").capitalize()} export has been '
                'initiated, an email will be sent once download completes.')
        else:
            message = (f'Download for {app_label.replace("_", " ").capitalize()} '
                       'that was initiated is still running. Please wait until an '
                       'export is fully prepared.')

        messages.add_message(self.request, messages.INFO, message)
