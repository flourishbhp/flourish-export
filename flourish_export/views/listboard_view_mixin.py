import datetime
import os
import shutil
import threading
import time

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from edc_base.utils import get_utcnow

from ..export_data_mixin import ExportDataMixin
from ..export_methods import ExportMethods
from ..export_model_lists import (
    caregiver_crfs_list, child_crf_list, child_model_list, caregiver_model_list,
    death_report_prn_model_list, offstudy_prn_model_list)
from ..export_model_lists import follow_model_list
from ..export_non_crfs import ExportNonCrfData
from ..models import ExportFile


class ListBoardViewMixin:

    def export_caregiver_data(self, export_path=None):
        """Export all caregiver CRF data.
        """
        export_crf_data = ExportDataMixin(export_path=export_path)
        export_crf_data.export_crfs(
            crf_list=caregiver_crfs_list,
            crf_data_dict=ExportMethods().caregiver_crf_data_dict,
            study='flourish_caregiver')

    def export_child_data(self, export_path=None):
        """Export child data.
        """
        export_crf_data = ExportDataMixin(export_path=export_path)
        export_crf_data.export_crfs(
            crf_list=child_crf_list,
            crf_data_dict=ExportMethods().child_crf_data,
            study='flourish_child')

    def export_non_crf_data(self, export_path=None):
        """Export both child and caregiver non CFR data.
        """
        non_crf_data = ExportNonCrfData(export_path=export_path)

        non_crf_data.child_non_crf(child_model_list=child_model_list)
        non_crf_data.death_report(death_report_prn_model_list=death_report_prn_model_list)
        non_crf_data.caregiver_non_crfs(
            caregiver_model_list=caregiver_model_list,
            study='flourish_caregiver')

        non_crf_data.follow_models(
            follow_model_list=follow_model_list,
            study='flourish_follow')

        non_crf_data.child_visit()
        non_crf_data.caregiver_visit()

        non_crf_data.offstudy(offstudy_prn_model_list=offstudy_prn_model_list)

    def export_requisitions(self, caregiver_export_path=None, child_export_path=None):
        """Export child and caregiver requisitions.
        """
        pass

    def download_all_data(self):
        """Export all data.
        """

        export_identifier = self.identifier_cls().identifier
        thread_name = 'flourish_all_export'
        last_doc = ExportFile.objects.filter(
            description='Flourish All Export', download_complete=True).order_by(
                'created').last()

        if last_doc:
            download_time = last_doc.download_time
        else:
            download_time = 0.0
        options = {
            'description': 'Flourish All Export',
            'study': 'flourish',
            'export_identifier': export_identifier,
            'download_time': download_time
        }
        doc = ExportFile.objects.create(**options)
        try:
            start = time.perf_counter()
            today_date = datetime.datetime.now().strftime('%Y%m%d')

            zipped_file_path = 'documents/' + export_identifier + \
                '_flourish_all_export_' + today_date + '.zip'
            dir_to_zip = settings.MEDIA_ROOT + '/documents/' + \
                export_identifier + '_flourish_all_export_' + today_date

            export_path = dir_to_zip + '/caregiver/'
            self.export_caregiver_data(export_path=export_path)
            export_path = dir_to_zip + '/child/'
            self.export_child_data(export_path=export_path)

            export_path = dir_to_zip + '/non_crf/'
            self.export_non_crf_data(export_path=export_path)

            # caregiver_export_path = dir_to_zip + '/caregiver/'
            # child_export_path = dir_to_zip + '/child/'
            #
            # self.export_requisitions(
            # caregiver_export_path=caregiver_export_path,
            # child_export_path=child_export_path)

            doc.document = zipped_file_path
            doc.save()

            # Zip the file

            self.zipfile(
                thread_name=thread_name,
                dir_to_zip=dir_to_zip, start=start,
                export_identifier=export_identifier,
                doc=doc)
        except Exception as e:
            raise e

    def download_child_data(self):
        """Export all data.
        """

        export_identifier = self.identifier_cls().identifier
        thread_name = 'flourish_child_crf_export'
        last_doc = ExportFile.objects.filter(
            description='Flourish Child CRF Export', download_complete=True).order_by(
                'created').last()

        if last_doc:
            download_time = last_doc.download_time
        else:
            download_time = 0.0
        options = {
            'description': 'Flourish Child CRF Export',
            'study': 'flourish',
            'export_identifier': export_identifier,
            'download_time': download_time
        }
        doc = ExportFile.objects.create(**options)
        try:
            start = time.perf_counter()
            today_date = datetime.datetime.now().strftime('%Y%m%d')

            zipped_file_path = f'documents/{export_identifier}_flourish_child_export_{today_date}.zip'
            dir_to_zip = settings.MEDIA_ROOT + \
                f'/documents/{export_identifier}_flourish_child_export_{today_date}'

            export_path = dir_to_zip + '/child/'
            self.export_child_data(export_path=export_path)

            doc.document = zipped_file_path
            doc.save()

            # Zip the file

            self.zipfile(
                thread_name=thread_name,
                dir_to_zip=dir_to_zip, start=start,
                export_identifier=export_identifier,
                doc=doc)
        except Exception as e:
            raise e

    def download_caregiver_data(self):
        """Export caregiver data.
        """

        export_identifier = self.identifier_cls().identifier
        thread_name = 'flourish_caregiver_crf_export'
        last_doc = ExportFile.objects.filter(
            description='Flourish Caregiver CRF Export', download_complete=True).order_by(
                'created').last()

        if last_doc:
            download_time = last_doc.download_time
        else:
            download_time = 0.0
        options = {
            'description': 'Flourish Caregiver CRF Export',
            'study': 'flourish',
            'export_identifier': export_identifier,
            'download_time': download_time
        }
        doc = ExportFile.objects.create(**options)
        try:
            start = time.perf_counter()
            today_date = datetime.datetime.now().strftime('%Y%m%d')

            zipped_file_path = f'documents/{export_identifier}_flourish_caregiver_export_{today_date}.zip'
            dir_to_zip = settings.MEDIA_ROOT + \
                f'/documents/{export_identifier}_flourish_caregiver_export_{today_date}'

            export_path = dir_to_zip + '/caregiver/'
            self.export_caregiver_data(export_path=export_path)

            doc.document = zipped_file_path
            doc.save()

            # Zip the file

            self.zipfile(
                thread_name=thread_name,
                dir_to_zip=dir_to_zip, start=start,
                export_identifier=export_identifier,
                doc=doc)
        except Exception as e:
            raise e

    def download_non_crf_data(self):
        """Export all data.
        """

        export_identifier = self.identifier_cls().identifier
        thread_name = 'flourish_non_crf_export',
        last_doc = ExportFile.objects.filter(
            description='Flourish Non CRF Export',
            download_complete=True).order_by('created').last()

        if last_doc:
            download_time = last_doc.download_time
        else:
            download_time = 0.0
        options = {
            'description': 'Flourish Non CRF Export',
            'study': 'flourish',
            'export_identifier': export_identifier,
            'download_time': download_time
        }
        doc = ExportFile.objects.create(**options)
        try:
            start = time.perf_counter()
            today_date = datetime.datetime.now().strftime('%Y%m%d')

            zipped_file_path = f'documents/{export_identifier}_flourish_non_crf_export_{today_date}.zip'
            dir_to_zip = settings.MEDIA_ROOT + \
                f'/documents/{export_identifier}_flourish_non_crf_export_{today_date}'

            export_path = dir_to_zip + '/non_crf/'
            self.export_non_crf_data(export_path=export_path)

            doc.document = zipped_file_path
            doc.save()

            # Zip the file

            self.zipfile(
                thread_name=thread_name,
                dir_to_zip=dir_to_zip, start=start,
                export_identifier=export_identifier,
                doc=doc)
        except Exception as e:
            raise e

    def zipfile(
            self, thread_name=None, dir_to_zip=None, start=None,
            export_identifier=None, doc=None):
        """Zip file.
        """
        # Zip the file

        doc.download_complete = True
        doc.save()

        if not os.path.isfile(dir_to_zip):
            shutil.make_archive(dir_to_zip, 'zip', dir_to_zip)
            # Create a document object.

            end = time.perf_counter()
            download_time = end - start
            try:
                doc = ExportFile.objects.get(
                    export_identifier=export_identifier)
            except ExportFile.DoesNotExist:
                raise ValidationError('Export file is missing for id: ',
                                      export_identifier)
            else:
                doc.download_time = download_time
                doc.save()

            # Notify user the download is done
            subject = export_identifier + ' ' + doc.description
            message = (export_identifier + doc.description
                       + ' export files have been successfully generated and '
                       'ready for download. This is an automated message.')
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,  # FROM
                recipient_list=[self.request.user.email],  # TO
                fail_silently=False)
            threading.Thread(target=self.stop_main_thread, args=(thread_name,))

    def is_clean(self, description=None):

        current_file = ExportFile.objects.filter(
            description=description,
            download_complete=False).order_by('created').last()
        if current_file:
            time_now = (get_utcnow() - current_file.created).total_seconds()

            if time_now <= current_file.download_time:
                messages.add_message(
                    self.request, messages.INFO,
                    (f'Download for {description} that was initiated is still running '
                     'please wait until an export is fully prepared.'))
                return False

        # Delete any other extra failed files
        docs = ExportFile.objects.filter(download_complete=False)
        for doc in docs:
            if doc.created.date() < get_utcnow().date():
                doc.delete()
        return True
