from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
import pandas as pd, datetime, os

from .export_methods import ExportMethods
from .export_model_lists import exclude_fields, exclude_m2m_fields


class ExportNonCrfData:
    """Export data.
    """

    def __init__(self, export_path=None):
        self.export_path = export_path or django_apps.get_app_config('flourish_export').non_crf_path
        if not os.path.exists(self.export_path):
            os.makedirs(self.export_path)
        self.export_methods_cls = ExportMethods()
        self.rs_cls = django_apps.get_model('edc_registration.registeredsubject')
        self.appointment_cls = django_apps.get_model('edc_appointment.appointment')

    def caregiver_non_crfs(self, caregiver_model_list=None, exclude=None):
        """E.
        """
        for model_name in caregiver_model_list:
            if 'registeredsubject' == model_name:
                model_cls = self.rs_cls
            elif 'appointment' == model_name:
                model_cls = self.appointment_cls
            else:
                model_cls = django_apps.get_model('flourish_caregiver', model_name)
            objs = model_cls.objects.all()
            count = 0
            models_data = []

            for obj in objs:
                data = self.export_methods_cls.fix_date_format(self.export_methods_cls.non_crf_obj_dict(obj=obj))
                if exclude:
                    exclude_fields.append(exclude)
                    
                for e_fields in exclude_fields:
                    try:
                        del data[e_fields]
                    except KeyError:
                        pass
                models_data.append(data)
                count += 1
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            fname = 'flourish_caregiver_' + model_name + '_' + timestamp + '.csv'
            final_path = self.export_path + fname
            df_crf = pd.DataFrame(models_data)
            df_crf.rename(columns={'subject_identifier':
                                   'subject_identifier'}, inplace=True)
            df_crf.to_csv(final_path, encoding='utf-8', index=False)

    def caregiver_m2m_non_crf(self, caregiver_many_to_many_non_crf=None):
        """.
        """

        for crf_infor in caregiver_many_to_many_non_crf:
            crf_name, mm_field = crf_infor
            crf_cls = django_apps.get_model('flourish_caregiver', crf_name)
            count = 0
            mergered_data = []
            crf_objs = crf_cls.objects.all()
            for crf_obj in crf_objs:
                mm_objs = getattr(crf_obj, mm_field).all()
                if mm_objs:
                    for mm_obj in mm_objs:
                        mm_data = {mm_field: mm_obj.short_name}

                        crfdata = self.export_methods_cls.non_crf_obj_dict(obj=crf_obj)

                        # Merged many to many and CRF data
                        data = self.export_methods_cls.fix_date_format({**crfdata, **mm_data})
                        for e_fields in exclude_m2m_fields:
                            try:
                                del data[e_fields]
                            except KeyError:
                                pass
                        mergered_data.append(data)
                        count += 1
                else:
                    crfdata = self.export_methods_cls.fix_date_format(
                        self.export_methods_cls.non_crf_obj_dict(obj=crf_obj))
                    for e_fields in exclude_fields:
                        try:
                            del crfdata[e_fields]
                        except KeyError:
                            pass
                    mergered_data.append(crfdata)
                    count += 1
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            fname = 'flourish_caregiver_' + crf_name + '_' + 'merged' '_' + mm_field + '_' + timestamp + '.csv'
            final_path = self.export_path + fname
            df_crf_many2many = pd.DataFrame(mergered_data)
            df_crf_many2many.to_csv(final_path, encoding='utf-8', index=False)

    def child_non_crf(self, child_model_list=None):
        """.
        """
        for model_name in child_model_list:
            model_cls = django_apps.get_model('flourish_child', model_name)
            objs = model_cls.objects.all()
            count = 0
            models_data = []
            for obj in objs:
                data = obj.__dict__
                data = self.export_methods_cls.encrypt_values(data, obj.__class__)
                try:
                    rs = self.rs_cls.objects.get(subject_identifier=obj.subject_identifier)
                except self.rs_cls.DoesNotExist:
                    if not 'dob' in data:
                        data.update(dob=None)
                    if not 'gender' in data:
                        data.update(gender=None)
                    data.update(
                        relative_identifier=None,
                        screening_age_in_years=None,
                        registration_datetime=None
                    )
                else:
                    if not 'dob' in data:
                        data.update(dob=rs.dob)
                    if not 'gender' in data:
                        data.update(gender=rs.gender)
                    if not 'screening_identifier' in data:
                        data.update(screening_identifier=rs.screening_identifier)
                    data.update(
                        relative_identifier=rs.relative_identifier,
                        screening_age_in_years=rs.screening_age_in_years,
                        registration_datetime=rs.registration_datetime
                    )
                last_data = self.export_methods_cls.fix_date_format(data)
                for e_fields in exclude_fields:
                    try:
                        del last_data[e_fields]
                    except KeyError:
                        pass
                models_data.append(last_data)
                count += 1
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            fname = 'flourish_child_' + model_name + '_' + timestamp + '.csv'
            final_path = self.export_path + fname
            df_crf = pd.DataFrame(models_data)
            df_crf.to_csv(final_path, encoding='utf-8', index=False)

    def offstudy(self, offstudy_prn_model_list=None):
        """Export off study forms.
        """

        for model_name in offstudy_prn_model_list:
            model_cls = django_apps.get_model('flourish_prn', model_name)
            objs = model_cls.objects.all()
            count = 0
            models_data = []
            for obj in objs:
                data = obj.__dict__
                data = self.export_methods_cls.encrypt_values(data, obj.__class__)
                try:
                    rs = self.rs_cls.objects.get(subject_identifier=obj.subject_identifier)
                except self.rs_cls.DoesNotExist:
                    raise ValidationError('Registered subject can not be missing')
                else:
                    if not 'dob' in data:
                        data.update(dob=rs.dob)
                    if not 'gender' in data:
                        data.update(gender=rs.gender)
                    if not 'screening_identifier' in data:
                        data.update(screening_identifier=rs.screening_identifier)
                    data.update(
                        relative_identifier=rs.relative_identifier,
                        screening_age_in_years=rs.screening_age_in_years,
                        registration_datetime=rs.registration_datetime
                    )
                last_data = self.export_methods_cls.fix_date_format(data)
                for e_fields in exclude_fields:
                    try:
                        del last_data[e_fields]
                    except KeyError:
                        pass
                models_data.append(last_data)
                count += 1
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            fname = 'flourish_prn_' + model_name + '_' + timestamp + '.csv'
            final_path = self.export_path + fname
            df_crf = pd.DataFrame(models_data)
            df_crf.to_csv(final_path, encoding='utf-8', index=False)

    def death_report(self, death_report_prn_model_list=None):
        # Export child Non CRF data
        for model_name in death_report_prn_model_list:
            model_cls = django_apps.get_model('flourish_prn', model_name)
            objs = model_cls.objects.all()
            count = 0
            models_data = []
            for obj in objs:
                data = obj.__dict__
                try:
                    rs = self.rs_cls.objects.get(subject_identifier=obj.subject_identifier)
                except self.rs_cls.DoesNotExist:
                    raise ValidationError('Registered subject can not be missing')
                else:
                    if not 'dob' in data:
                        data.update(dob=rs.dob)
                    if not 'gender' in data:
                        data.update(gender=rs.gender)
                    if not 'screening_identifier' in data:
                        data.update(screening_identifier=rs.screening_identifier)
                    data.update(
                        relative_identifier=rs.relative_identifier,
                        screening_age_in_years=rs.screening_age_in_years,
                        registration_datetime=rs.registration_datetime
                    )
                data = self.export_methods_cls.encrypt_values(data, obj.__class__)
                last_data = self.export_methods_cls.fix_date_format(data)
                for e_fields in exclude_fields:
                    try:
                        del last_data[e_fields]
                    except KeyError:
                        pass
                models_data.append(last_data)
                count += 1
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            fname = 'flourish_prn_' + model_name + '_' + timestamp + '.csv'
            final_path = self.export_path + fname
            df_crf = pd.DataFrame(models_data)
            df_crf.to_csv(final_path, encoding='utf-8', index=False)

    def caregiver_visit(self):

        caregiver_visits = django_apps.get_model('flourish_caregiver.maternalvisit').objects.all()
        data = []
        for mv in caregiver_visits:
            d = mv.__dict__
            d = self.export_methods_cls.fix_date_format(d)
            for e_fields in exclude_fields:
                try:
                    del d[e_fields]
                except KeyError:
                    pass
            data.append(d)
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        fname = 'flourish_caregiver_maternal_visit' + '_' + timestamp + '.csv'
        final_path = self.export_path + fname
        df_crf = pd.DataFrame(data)
        df_crf.to_csv(final_path, encoding='utf-8', index=False)

    def child_visit(self):

        child_visits = django_apps.get_model('flourish_child.childvisit').objects.all()
        data = []
        for mv in child_visits:
            d = mv.__dict__
            d = self.export_methods_cls.fix_date_format(d)
            for e_fields in exclude_fields:
                try:
                    del d[e_fields]
                except KeyError:
                    pass
            data.append(d)
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        fname = 'flourish_child_child_visit' + '_' + timestamp + '.csv'
        final_path = self.export_path + fname
        df_crf = pd.DataFrame(data)
        df_crf.to_csv(final_path, encoding='utf-8', index=False)
