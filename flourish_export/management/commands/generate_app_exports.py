from django.core.management.base import BaseCommand, CommandError

from flourish_export.views.export_methods_view_mixin import ExportMethodsViewMixin


class Command(BaseCommand):
    help = ('Run export method from model admin to generate '
            'csv data for all CRF and non-CRF models.')

    def add_arguments(self, parser):
        parser.add_argument(
            'args',
            metavar='app_label',
            nargs='*',
            help='Exports data for a specified app_label')

        parser.add_argument(
            '--emails',
            type=str,
            nargs="+",
            required=True,
            help='Email address to send notification to')

    def handle(self, *args, **kwargs):
        export_helper_cls = ExportMethodsViewMixin()

        if not args:
            # Get all CRF models from `flourish_caregiver` and `flourish_child`
            # app configs, update to dictionary {model_name: models_cls} key,
            # value pair.
            args = ('flourish_caregiver', 'flourish_child', 'flourish_prn', )

        emails = kwargs['emails']
        # Check args defined for specific app_label and/or model name(s)
        for model_args in args:
            try:
                export_helper_cls.generate_export(
                    app_label=model_args, user_emails=emails)
            except Exception as e:
                raise CommandError(str(e))
