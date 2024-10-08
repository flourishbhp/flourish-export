import shutil, os
from celery import shared_task, group, chain
from celery.exceptions import SoftTimeLimitExceeded
from django.apps import apps as django_apps
from django.core.mail import send_mail
from django.conf import settings
from edc_base.utils import get_utcnow

from flourish_caregiver.admin_site import flourish_caregiver_admin
from flourish_child.admin_site import flourish_child_admin
from flourish_facet.admin_site import flourish_facet_admin
from flourish_prn.admin_site import flourish_prn_admin

from .admin_export_helper import AdminExportHelper
from .models import ExportFile

admin_export_helper_cls = AdminExportHelper()


@shared_task
def run_exports(model_cls, app_label, full_export=False):
    """ Executes the csv model export method from admin export action(s) and writes response
        content to an excel file.
        @param model_cls: Specific model class definition
        @param app_label: Specific app label for the model class
    """
    admin_site_map = {'flourish_child': flourish_child_admin,
                      'flourish_caregiver': flourish_caregiver_admin,
                      'flourish_prn': flourish_prn_admin,
                      'flourish_facet': flourish_facet_admin}

    model_cls = django_apps.get_model(model_cls)
    app_admin_site = admin_site_map.get(app_label, None)

    model_admin_cls = app_admin_site._registry.get(model_cls, None)

    queryset = model_cls.objects.all()

    if not model_admin_cls:
        print(f'Model class not registered {model_cls._meta.verbose_name}')
    elif not queryset.exists():
        print(f'Empty queryset returned for {model_cls._meta.verbose_name}')
    else:
        file_path = f'media/admin_exports/{app_label}_{get_utcnow().date()}'

        if full_export:
            file_path = f'media/admin_exports/flourish_{get_utcnow().date()}'

        if hasattr(model_admin_cls, 'export_as_csv'):
            """
            Can be used to exclude some models not needed in the exports
            by excluding the mixin from the model admin of interest
            """
            response = model_admin_cls.export_as_csv(
                request=None, queryset=queryset)

            if response:
                if response.status_code == 200:
                    content_type = response._headers.get('content-type', ('', ''))[1]
                    file_ext = 'csv' if content_type == admin_export_helper_cls.csv_content_type else 'xlsx'
                    if not os.path.exists(file_path):
                        os.makedirs(file_path)
                    with open(f'{file_path}/{model_admin_cls.get_export_filename()}.{file_ext}', 'wb') as file:
                        file.write(response.content)
                else:
                    response.raise_for_status()
            else:
                print(f'Empty response returned for {model_cls._meta.verbose_name}')


@shared_task(bind=True, soft_time_limit=21000, time_limit=21600)
def generate_exports(self, app_list, create_zip=False, full_export=False, user_emails=[],
                     export_identifier=None):

    app_labels = set()

    # Create a list to store the group of export tasks
    export_tasks = []

    try:
        for _, model_cls in app_list.items():
            app_label = model_cls.split('.')[0]
            app_labels.add(app_label)

            # Call the export_data task asynchronously and store the task
            export_tasks.append(run_exports.si(model_cls, app_label, full_export))

        # Group all export tasks together
        export_group = group(export_tasks)

        # Change app_labels to list for serialization
        app_labels = list(app_labels) if not full_export else ['flourish', ]
        # Chain additional task for zipping and sending an email after exports are complete.
        if create_zip:
            chain(export_group,
                  zip_and_send_email.si(app_labels, user_emails, export_identifier)).delay()
        else:
            export_group.delay()
    except SoftTimeLimitExceeded:
        self.update_state(state='FAILURE')
        new_soft_time_limit = self.request.soft_time_limit + 3600
        new_time_limit = self.request.time_limit + 3600
        self.retry(countdown=10, max_retries=3, soft_time_limit=new_soft_time_limit, time_limit=new_time_limit)


@shared_task
def zip_and_send_email(app_labels, user_emails, export_identifier):
    for app_label in app_labels:
        create_zip_and_email(app_label, export_identifier, user_emails)


def create_zip_and_email(app_label, export_identifier, user_emails):
    zip_folder = f'admin_exports/{app_label}_{get_utcnow().date()}'
    dir_to_zip = f'{settings.MEDIA_ROOT}/{zip_folder}'
    archive_name = f'{dir_to_zip}_{export_identifier}'

    # Zip the exported files
    if not os.path.isfile(dir_to_zip):
        shutil.make_archive(archive_name, 'zip', dir_to_zip)

    try:
        pending_export = ExportFile.objects.get(
            export_identifier=export_identifier)
    except ExportFile.DoesNotExist:
        raise Exception(f'{export_identifier} model obj does not exist')
    else:
        description = pending_export.description
        subject = f'{export_identifier} {description}'
        message = (f'{export_identifier} {description} have been successfully '
                   'generated and ready for download. This is an automated message.')

        try:
            send_mail(subject=subject,
                      message=message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=user_emails,
                      fail_silently=False)
        except Exception as e:
            print(f'Error sending email: {str(e)}')

        pending_export.download_complete = True
        pending_export.document = f'{zip_folder}_{export_identifier}.zip'
        pending_export.datetime_completed = get_utcnow()
        pending_export.save()
