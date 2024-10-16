import shutil
import os
from celery import shared_task, group, chain
from celery.exceptions import SoftTimeLimitExceeded
from django.apps import apps as django_apps
from django.core.mail import send_mail
from django.conf import settings
from edc_base.utils import get_utcnow
import logging
from flourish_caregiver.admin_site import flourish_caregiver_admin
from flourish_child.admin_site import flourish_child_admin
from flourish_facet.admin_site import flourish_facet_admin
from flourish_prn.admin_site import flourish_prn_admin

from .admin_export_helper import AdminExportHelper
from .models import ExportFile

admin_export_helper_cls = AdminExportHelper()
logger = logging.getLogger('celery_progress')

admin_site_map = {'flourish_child': flourish_child_admin,
                  'flourish_caregiver': flourish_caregiver_admin,
                  'flourish_prn': flourish_prn_admin,
                  'flourish_facet': flourish_facet_admin}

@shared_task
def run_exports(model_cls, app_label, full_export=False):
    """ Executes the csv model export method from admin export action(s) and writes response
        content to an excel file.
        @param model_cls: Specific model class definition
        @param app_label: Specific app label for the model class
    """

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
                    filename = f'{file_path}/{model_admin_cls.get_export_filename()}'
                    save_csv_to_file(response, filename)
                else:
                    response.raise_for_status()
            else:
                print(f'Empty response returned for {model_cls._meta.verbose_name}')


@shared_task(bind=True, soft_time_limit=21000, time_limit=21600)
def generate_exports(self, app_list, create_zip=False, full_export=False, flat_exports=None, user_emails=[],
                     export_identifier=None):

    app_labels = set()

    # Create a list to store the group of export tasks
    export_tasks = []
    try:
        for _, model_cls in app_list.items():
            app_label = model_cls.split('.')[0]
            app_labels.add(app_label)
            if not flat_exports:
                # Call the export_data task asynchronously and store the task
                export_tasks.append(run_exports.si(model_cls, app_label, full_export))

        # Group all export tasks together
        export_group = group(export_tasks)

        # Change app_labels to list for serialization
        app_labels = list(app_labels) if not full_export else ['flourish', ]
        # Chain additional task for zipping and sending an email after exports are complete.

        if flat_exports:
            if create_zip:
                final_chain = chain(generate_flat_exports.si(app_list, app_labels, create_zip),
                                    zip_and_send_email.si(app_labels, user_emails, export_identifier, flat_exports))
            else:
                final_chain = generate_flat_exports(app_list, app_labels, create_zip)
            final_chain.delay()
        else:
            # Handle regular exports and their zipping/emailing
            if create_zip:
                final_chain = chain(export_group, zip_and_send_email.si(
                    app_labels, user_emails, export_identifier))
            else:
                final_chain = export_group

            final_chain.delay()
    except SoftTimeLimitExceeded:
        self.update_state(state='FAILURE')
        new_soft_time_limit = self.request.soft_time_limit + 3600
        new_time_limit = self.request.time_limit + 3600
        self.retry(countdown=10, max_retries=3,
                   soft_time_limit=new_soft_time_limit, time_limit=new_time_limit)


@shared_task
def generate_flat_exports(app_list, app_labels, create_zip=False):
    for app_label in app_labels:
        file_path = f'media/admin_exports/{app_label}_flat_{get_utcnow().date()}'
        response = None
        suffix_list = ['_subject_identifier', '_hiv_status', '_study_status']
        model_groups = {
            "child": {},
            "caregiver": {}
        }

        for name, model in app_list.items():
            if 'child' in name.lower() or 'infant' in name.lower():
                model_groups["child"][name] = model
            else:
                model_groups["caregiver"][name] = model

        write_function = admin_export_helper_cls.write_to_csv if create_zip else admin_export_helper_cls.write_to_excel

        for name, models in model_groups.items():
            participant_data = {}
            for _, model_cls in models.items():
                model = django_apps.get_model(model_cls)
                app_admin_site = admin_site_map.get(app_label, None)
                model_admin_cls = app_admin_site._registry.get(model, None)
                model_name = model.__name__.lower()
                if not hasattr(model_admin_cls, 'get_flat_model_data'):
                    continue
                model_data = model_admin_cls.get_flat_model_data(model)

                for record in model_data:
                    subject_identifier = record.get(f'{model_name}_subject_identifier')
                    if subject_identifier not in participant_data:
                        participant_data[subject_identifier] = {}
                    participant_data[subject_identifier].update(record)

            flat_participant_data = [data for data in participant_data.values()]

            if flat_participant_data:
                flat_participant_data = remove_duplicate_fields(flat_participant_data, suffix_list)
                filename = f'{file_path}/{admin_export_helper_cls.get_export_filename(app_label,name)}'
                response = write_function(records=flat_participant_data,
                                            app_label=app_label, export_type=name)

                if response and response.status_code == 200:
                    save_csv_to_file(response, filename)
                else:
                    response.raise_for_status()


@shared_task
def zip_and_send_email(app_labels, user_emails, export_identifier, flat_exports=None):
    for app_label in app_labels:
        create_zip_and_email(app_label, export_identifier, user_emails, flat_exports)


def create_zip_and_email(app_label, export_identifier, user_emails, flat_exports=None):
    if flat_exports:
        zip_folder = f'admin_exports/{app_label}_flat_{get_utcnow().date()}'
    else:
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


def save_csv_to_file(response, filename):
    """ Save response content to the specified file. """
    content_type = response._headers.get('content-type', ('', ''))[1]
    file_ext = 'csv' if content_type == admin_export_helper_cls.csv_content_type else 'xlsx'
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    with open(f'{filename}.{file_ext}', 'wb') as file:
        file.write(response.content)

def remove_duplicate_fields(records, suffix_list):
    # Loop over each record in flat_participant_data
    for record in records:
        # Create a set to track encountered suffixes
        encountered_suffixes = set()

        # Create a list of keys to remove to avoid modifying the dictionary while iterating
        keys_to_remove = []

        for key in list(record.keys()):
            # Check if the key ends with any suffix in suffix_list
            for suffix in suffix_list:
                if key.endswith(suffix):
                    # If suffix has already been encountered, mark the key for removal
                    if suffix in encountered_suffixes:
                        keys_to_remove.append(key)
                    else:
                        # Add suffix to encountered set for the first time
                        encountered_suffixes.add(suffix)

        # Remove duplicate keys
        for key in keys_to_remove:
            del record[key]

    return records
