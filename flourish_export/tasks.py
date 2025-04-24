import shutil
import os

import logging
import pandas as pd
import redis
import re
import django_rq
from rq import Retry

from celery import shared_task, group, chain
from celery.exceptions import SoftTimeLimitExceeded
from django.apps import apps as django_apps
from django.core.mail import send_mail
from django.conf import settings
from django.db.models.fields.related import (ForeignKey, ManyToManyField,
                                             ManyToOneRel, OneToOneRel)
from edc_base.utils import get_utcnow

from flourish_caregiver.admin_site import flourish_caregiver_admin
from flourish_child.admin_site import flourish_child_admin
from flourish_facet.admin_site import flourish_facet_admin
from flourish_prn.admin_site import flourish_prn_admin

from .admin_export_helper import AdminExportHelper
from .models import ExportFile


r = redis.StrictRedis(host='localhost', port=6379, db=0)

admin_export_helper_cls = AdminExportHelper()
logger = logging.getLogger('celery_progress')

admin_site_map = {'flourish_child': flourish_child_admin,
                  'flourish_caregiver': flourish_caregiver_admin,
                  'flourish_prn': flourish_prn_admin,
                  'flourish_facet': flourish_facet_admin}


def run_exports(model_cls, app_label, export_date, full_export=False):
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
        return
    elif not queryset.exists():
        print(f'Empty queryset returned for {model_cls._meta.verbose_name}')
        return

    file_path = f'media/admin_exports/{app_label}_{export_date}'

    if full_export:
        file_path = f'media/admin_exports/flourish_{export_date}'

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
            print(f'Empty response for batch in {model_cls._meta.verbose_name}')
    else:
        print(f'No export method available for {model_cls._meta.verbose_name}')


@shared_task()
def run_metadata_exports(label_lower, filename, app_label):
    app_admin_site = admin_site_map.get(app_label, None)

    if not label_lower and not filename:
        return

    sheet_name = label_lower.split('.')[1]
    sheet_name = re.sub(r'[\\/*?:"<>|]', '_', sheet_name)
    sheet_name = sheet_name[:30]
    records = []

    model_cls = django_apps.get_model(label_lower)
    model_admin_cls = app_admin_site._registry.get(model_cls, None)

    exclude_fields = getattr(
        model_admin_cls, 'exclude_fields', []) + admin_export_helper_cls.exclude_fields
    custom_form_labels = []
    if model_admin_cls:
        custom_form_labels = getattr(
            model_admin_cls, 'custom_form_labels', [])

    form_fields = model_cls._meta.get_fields()

    audit_fields = []

    for field in form_fields:
        if field.name in exclude_fields:
            continue
        if field.name in admin_export_helper_cls.audit_fields:
            audit_fields.append(field)
            continue
        if isinstance(field, (ForeignKey, ManyToOneRel, OneToOneRel, )):
            continue
        append_field_details(records, field, custom_form_labels)

    for field in audit_fields:
        append_field_details(records, field, custom_form_labels)

    # Ensure directory exists, or create it
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory)

    df = pd.DataFrame(records)

    lock = r.lock(f'{filename}_lock', timeout=30)
    if lock.acquire(blocking=True):
        try:
            # Check if the file exists
            if not os.path.exists(filename):
                # If the file doesn't exist, create it and write the DataFrame to a new sheet
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # Write data to excel file
                with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    if sheet_name in writer.sheets:
                        df.to_excel(writer, sheet_name=sheet_name, index=False, header=False,
                                    startrow=writer.sheets[sheet_name].max_row)
                    else:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
        finally:
            lock.release()
    else:
        print('Could not acquire lock for the file.')


def append_field_details(records, field, custom_form_labels):
    choices = None

    if isinstance(field, ManyToManyField):
        related_model_cls = field.related_model
        _qs = related_model_cls.objects.all()
        choices = [(qs.short_name, qs.name) for qs in _qs]

    custom_field_label = ''
    for custom_label in custom_form_labels:
        custom_field = getattr(custom_label, 'field', None)
        _custom_field_label = getattr(custom_label, 'label', None)

        if custom_field == field.name:
            custom_field_label = _custom_field_label
            break

    try:
        records.append({'Variable Name': field.name,
                        'Variable Label Baseline': field.verbose_name,
                        'Variable Label FollowUp': custom_field_label,
                        'Field Type': field.get_internal_type(),
                        'Choices': field.flatchoices or choices,
                        'Max Length': field.max_length,
                        'Nullable': field.null,
                        'Blank': field.blank,
                        'Editable': field.editable})
    except AttributeError:
        pass
    return records


def generate_exports(app_list, create_zip=False, full_export=False,
                     flat_exports=None, user_emails=[], export_identifier=None,
                     queue_name='exports'):

    app_labels = set()
    _queue = django_rq.get_queue(queue_name)
    # Create a list to store the group of export tasks
    export_tasks = []

    export_date = get_utcnow().strftime('%Y-%m-%d_%H-%M-%S')

    for model_cls in app_list.values():
        app_label = model_cls.split('.')[0]
        app_labels.add(app_label)
        if not flat_exports:
            # Chunking logic for large exports
            _job = _queue.enqueue(
                run_exports,
                model_cls,
                app_label,
                export_date,
                full_export,
                retry=Retry(max=3)
            )
            export_tasks.append(_job)

    # Change app_labels to list for serialization
    app_labels = list(app_labels) if not full_export else ['flourish', ]

    # Wait for all export tasks to complete
    if flat_exports:
        _task = _queue.enqueue(
            generate_flat_exports,
            app_list,
            app_labels,
            export_date,
            create_zip,
        )
        _task.result  # Blocks until the task is completed

    else:
        for task in export_tasks:
            task.result

    # Handle post-export operations (i.e. zip and send email notification)
    if create_zip:
        _queue.enqueue(
            zip_and_send_email,
            app_labels,
            user_emails,
            export_date,
            export_identifier
        )


@shared_task(bind=True, soft_time_limit=21000, time_limit=21600)
def generate_metadata(self, app_labels, user_emails, export_identifier):
    export_tasks = []
    file_path = f'media/admin_exports/flourish_metadata_{get_utcnow().date()}'

    # Check directory already exists and remove along with its contents
    remove_existing_dir(file_path)

    try:
        for app_label in app_labels:
            filename = f'{file_path}/{app_label}.xlsx'
            app_models = admin_export_helper_cls.get_app_list(app_label).values()
            for model_cls in app_models:
                _exclude = admin_export_helper_cls.exclude_rel_models(model_cls)
                if _exclude:
                    continue
                label_lower = model_cls._meta.label_lower
                export_tasks.append(
                    run_metadata_exports.si(label_lower, filename, app_label))
        export_group = group(export_tasks)

        final_chain = chain(export_group, zip_and_send_email_task.si(
            ['flourish_metadata', ], user_emails, export_identifier))

        final_chain.delay()
    except SoftTimeLimitExceeded:
        self.update_state(state='FAILURE')
        new_soft_time_limit = self.request.soft_time_limit + 3600
        new_time_limit = self.request.time_limit + 3600
        self.retry(countdown=10, max_retries=3,
                   soft_time_limit=new_soft_time_limit, time_limit=new_time_limit)


def generate_flat_exports(app_list, app_labels, export_date, create_zip=False):
    for app_label in app_labels:
        file_path = f'media/admin_exports/{app_label}_flat_{export_date}'
        response = None
        suffix_list = ['_subject_identifier', '_hiv_status', '_study_status']
        model_groups = {
            "child": {},
            "caregiver": {}
        }

        for name, model_cls in app_list.items():
            partipant_type = None
            if 'child' in name.lower() or 'infant' in name.lower():
                partipant_type = 'child'
            else:
                partipant_type = 'caregiver'

            model = django_apps.get_model(model_cls)
            app_admin_site = admin_site_map.get(app_label, None)
            model_admin_cls = app_admin_site._registry.get(model, None)
            model_name = model.__name__.lower()
            if not hasattr(model_admin_cls, 'get_flat_model_data'):
                continue
            model_data = model_admin_cls.get_flat_model_data(model)

            for record in model_data:
                subject_identifier = record.get(f'{model_name}_subject_identifier')
                if subject_identifier not in model_groups[partipant_type]:
                    model_groups[partipant_type][subject_identifier] = {}
                model_groups[partipant_type][subject_identifier].update(record)

        write_function = (admin_export_helper_cls.write_to_csv
                          if create_zip else admin_export_helper_cls.write_to_excel)

        for export_type, participant_data in model_groups.items():
            flat_participant_data = participant_data.values()

            if flat_participant_data:
                flat_participant_data = remove_duplicate_fields(
                    flat_participant_data, suffix_list)
                filename = (
                    f'{file_path}/{admin_export_helper_cls.get_export_filename(app_label,export_type)}')
                response = write_function(records=flat_participant_data,
                                          app_label=app_label,
                                          export_type=export_type)

                if response and response.status_code == 200:
                    save_csv_to_file(response, filename)
                else:
                    response.raise_for_status()


@shared_task
def zip_and_send_email_task(app_labels, user_emails, export_identifier, flat_exports=None):
    for app_label in app_labels:
        create_zip_and_email(app_label, export_identifier, user_emails, flat_exports)


def zip_and_send_email(app_labels, user_emails, export_identifier,
                       export_date, flat_exports=None):
    for app_label in app_labels:
        create_zip_and_email(
            app_label, export_identifier, user_emails, export_date, flat_exports)


def create_zip_and_email(app_label, export_identifier,
                         user_emails, export_date, flat_exports=None):
    if flat_exports:
        zip_folder = f'admin_exports/{app_label}_flat_{export_date}'
    else:
        zip_folder = f'admin_exports/{app_label}_{export_date}'

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


def remove_existing_dir(file_path):
    if os.path.exists(file_path) and os.path.isdir(file_path):
        shutil.rmtree(file_path)
        print(f'The directory {file_path} has been deleted')
    else:
        print(f'The directory {file_path} does not exist')
