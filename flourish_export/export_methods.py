import datetime

from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django_crypto_fields.fields import (
    EncryptedCharField, EncryptedDecimalField, EncryptedIntegerField,
    EncryptedTextField, FirstnameField, IdentityField, LastnameField)
from pytz import timezone
import re

encrypted_fields = [
    EncryptedCharField, EncryptedDecimalField, EncryptedIntegerField,
    EncryptedTextField, FirstnameField, IdentityField, LastnameField]


class ExportMethods:
    """Export FLourish data.
    """

    def __init__(self):
        self.antenatal_enrollment_cls = django_apps.get_model('flourish_caregiver.antenatalenrollment')
        self.rs_cls = django_apps.get_model('edc_registration.registeredsubject')
        self.subject_consent_csl = django_apps.get_model('flourish_caregiver.subjectconsent')
        self.subject_screening_csl = django_apps.get_model('flourish_caregiver.subjectscreening')

    def encrypt_values(self, obj_dict=None, obj_cls=None):
        """Ecrypt values for fields that are encypted.
        """
        result_dict_obj = {**obj_dict}
        for key, value in obj_dict.items():
            for f in obj_cls._meta.get_fields():
                if key == f.name and type(f) in encrypted_fields:
                    new_value = f.field_cryptor.encrypt(value)
                    result_dict_obj[key] = new_value
        return result_dict_obj

    def fix_date_format(self, obj_dict=None):
        """Change all dates into a format for the export
        and split the time into a separate value.

        Format: m/d/y
        """

        result_dict_obj = {**obj_dict}
        for key, value in obj_dict.items():
            if isinstance(value, datetime.datetime):
                value = value.astimezone(timezone('Africa/Gaborone'))
                time_value = value.time().strftime('%H:%M:%S.%f')
                time_variable = None
                if 'datetime' in key:
                    time_variable = re.sub('datetime', 'time', key)
                else:
                    time_variable = key + '_time'
                value = value.strftime('%m/%d/%Y')
                new_key = re.sub('time', '', key)
                result_dict_obj[new_key] = value
                del result_dict_obj[key]
                result_dict_obj[time_variable] = time_value
            elif isinstance(value, datetime.date):
                value = value.strftime('%m/%d/%Y')
                result_dict_obj[key] = value
        return result_dict_obj

    def caregiver_crf_data_dict(self, crf_obj=None):
        """Return a crf obj dict adding extra required fields.
        """

        data = crf_obj.__dict__
        data = self.encrypt_values(obj_dict=data, obj_cls=crf_obj.__class__)
        data.update(
            caregiver_subject_identifier=crf_obj.maternal_visit.subject_identifier,
            visit_datetime=crf_obj.maternal_visit.report_datetime,
            last_alive_date=crf_obj.maternal_visit.last_alive_date,
            reason=crf_obj.maternal_visit.reason,
            survival_status=crf_obj.maternal_visit.survival_status,
            visit_code=crf_obj.maternal_visit.visit_code,
            visit_code_sequence=crf_obj.maternal_visit.visit_code_sequence,
            study_status=crf_obj.maternal_visit.study_status,
            appt_status=crf_obj.maternal_visit.appointment.appt_status,
            appt_datetime=crf_obj.maternal_visit.appointment.appt_datetime,
        )
        try:
            ae = self.antenatal_enrollment_cls.objects.get(subject_identifier=crf_obj.maternal_visit.subject_identifier)
        except self.antenatal_enrollment_cls.DoesNotExist:
            raise ValidationError('AntenatalEnrollment can not be missing')
        else:
            data.update(enrollment_hiv_status=ae.current_hiv_status)
        try:
            rs = self.rs_cls.objects.get(subject_identifier=crf_obj.maternal_visit.subject_identifier)
        except self.rs_cls.DoesNotExist:
            raise ValidationError('RegisteredSubject can not be missing')
        else:
            data.update(
                screening_age_in_years=rs.screening_age_in_years,
                registration_status=rs.registration_status,
                dob=rs.dob,
                gender=rs.gender,
                subject_type=rs.subject_type,
                registration_datetime=rs.registration_datetime,
            )
        return data

    def child_crf_data(self, crf_obj=None):
        """Return a dictionary for a crf object with additional participant information.
        """

        data = crf_obj.__dict__
        data = self.encrypt_values(obj_dict=data, obj_cls=crf_obj.__class__)
        data.update(
            child_subject_identifier=crf_obj.child_visit.subject_identifier,
            visit_datetime=crf_obj.child_visit.report_datetime,
            last_alive_date=crf_obj.child_visit.last_alive_date,
            reason=crf_obj.child_visit.reason,
            survival_status=crf_obj.child_visit.survival_status,
            visit_code=crf_obj.child_visit.visit_code,
            visit_code_sequence=crf_obj.child_visit.visit_code_sequence,
            study_status=crf_obj.child_visit.study_status,
            appt_status=crf_obj.child_visit.appointment.appt_status,
            appt_datetime=crf_obj.child_visit.appointment.appt_datetime,
        )
        try:
            rs = self.rs_cls.objects.get(subject_identifier=crf_obj.child_visit.subject_identifier)
        except self.rs_cls.DoesNotExist:
            raise ValidationError('RegisteredSubject can not be missing')
        else:
            data.update(
                screening_age_in_years=rs.screening_age_in_years,
                registration_status=rs.registration_status,
                dob=rs.dob,
                gender=rs.gender,
                subject_type=rs.subject_type,
                registration_datetime=rs.registration_datetime,
                caregiver_identifier=rs.relative_identifier
            )
        return data

    def non_crf_obj_dict(self, obj=None):
        """Return a dictionary of non crf object.
        """

        data = obj.__dict__
        data = self.encrypt_values(obj_dict=data, obj_cls=obj.__class__)
        subject_consent = self.subject_consent_csl.objects.filter(subject_identifier=obj.subject_identifier).last()
        if subject_consent:
            if 'dob' not in data:
                data.update(dob=subject_consent.dob)
            if 'gender' in data:
                data.update(gender=subject_consent.gender)
            if 'screening_identifier' not in data:
                data.update(screening_identifier=subject_consent.screening_identifier)
            try:
                subject_screening = self.subject_screening_csl.objects.get(
                    screening_identifier=subject_consent.screening_identifier)
            except self.subject_screening_csl.DoesNotExist:
                raise ValidationError('Subject Screening can not be missing')
            else:
                data.update(
                    screening_age_in_years=subject_screening.age_in_years
                )
        else:
            if 'screening_identifier' not in data:
                data.update(screening_identifier=None)
            data.update(
                screening_age_in_years=None,
                dob=None,
                gender=None,

            )
        if 'registration_datetime' not in data:
            try:
                rs = self.rs_cls.objects.get(subject_identifier=obj.subject_identifier)
            except self.rs_cls.DoesNotExist:
                data.update(
                    registration_datetime=None,
                    screening_datetime=None
                )
            else:
                data.update(
                    registration_datetime=rs.registration_datetime,
                    screening_datetime=rs.screening_datetime
                )
        return data
