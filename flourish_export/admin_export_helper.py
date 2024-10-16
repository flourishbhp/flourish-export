import datetime
import pandas as pd
from django.apps import apps as django_apps
from django.core.management.base import CommandError
from django.db.models.fields.reverse_related import OneToOneRel
from django.http import HttpResponse
from django.utils import timezone
from edc_base.model_mixins import ListModelMixin
from io import BytesIO


class AdminExportHelper:
    """ Flourish export methods to be re-used in the export model admin mixin.
    """

    exclude_fields = ['_state', 'hostname_created', 'hostname_modified',
                      'revision', 'device_created', 'device_modified', 'id',
                      'site_id', 'modified', 'form_as_json', 'slug', ]

    @property
    def get_model_fields(self):
        return [field for field in self.model._meta.get_fields()
                if field.name not in self.exclude_fields and not isinstance(field,
                                                                            OneToOneRel)]

    def m2m_data_dict(self, obj, field, inline_count=None):
        """ Retrieve all choice variables for m2m field and assign either 0 or 1
            indicating selection of the variable response or not respectively.
            @param obj: parent model obj
            @param field: m2m field
            @param inline_count: if m2m_field is of inline model, indicates the count.
            @return: complete data indicating responses for the m2m field.
        """
        m2m_data = {}
        model_cls = field.related_model
        choices = self.m2m_list_data(model_cls)
        key_manager = getattr(obj, field.name)
        for choice in choices:
            field_name = f'{choice}__{inline_count}' if inline_count else choice
            m2m_data[field_name] = 0
            try:
                key_manager.get(short_name=choice)
            except model_cls.DoesNotExist:
                continue
            else:
                m2m_data[field_name] = 1
        return m2m_data

    def m2m_list_data(self, model_cls=None):
        qs = model_cls.objects.order_by(
            'created').values_list('short_name', flat=True)
        return list(qs)

    def inline_data_dict(self, obj, field):
        """ Retrieves all inline responses provided for parent model, and flattens
            the data appending '__count' to indicate number of instance of the inline.
            @param obj: parent model obj
            @param field: inline field
            @return: flattened data retrieved from the inline model instances.
        """
        data = {}
        related_field_name = getattr(obj, f'{field.related_name}', None)
        key_manager = getattr(obj, f'{field.name}_set', related_field_name)
        field_id = field.field.attname
        exclude_fields = self.exclude_fields + [field_id,]
        if key_manager:
            inline_values = key_manager.all()
            for _count, obj in enumerate(inline_values):
                inline_data = obj.__dict__
                inline_data = {f'{key}__{_count}': value for key,
                               value in inline_data.items() if key not in exclude_fields}
                m2m_fields = obj._meta.many_to_many
                for field in m2m_fields:
                    inline_data.update(self.m2m_data_dict(obj, field, str(_count)))
                data.update(inline_data)
        return data

    def write_to_excel(self, app_label=None, records=[], export_type=None):
        excel_buffer = BytesIO()
        writer = pd.ExcelWriter(excel_buffer, engine='openpyxl')

        df = pd.DataFrame(records)
        df.to_excel(writer, sheet_name=f'{self.model.__name__}', index=False)

        # Save and close the workbook
        writer.close()

        # Seek to the beginning and read to copy the workbook to a variable in memory
        excel_buffer.seek(0)
        workbook = excel_buffer.read()

        # Create an HTTP response with the Excel file as an attachment
        response = HttpResponse(
            workbook,
            content_type=self.excel_content_type
        )
        filename = self.get_export_filename(app_label, export_type)
        response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'
        return response

    @property
    def excel_content_type(self):
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def write_to_csv(self, records=[], app_label=None, export_type=None):
        """ Write data to csv format and returns response
        """
        df = pd.DataFrame(records)
        response = HttpResponse(content_type=self.csv_content_type)

        # Determine the filename based on app_label and export_type
        filename = self.get_export_filename(app_label, export_type)
        # Set the response header for CSV download
        response['Content-Disposition'] = f'attachment; filename={filename}.csv'
        df.to_csv(path_or_buf=response, index=False)

        return response

    @property
    def csv_content_type(self):
        return 'text/csv'

    def fix_date_formats(self, data={}):
        for key, value in data.items():
            if isinstance(value, datetime.datetime):
                if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
                    value = timezone.make_naive(value)
                value = value.strftime('%Y/%m/%d')
            if isinstance(value, datetime.date):
                value = value.strftime('%Y/%m/%d')
            data[key] = value
        return data

    def remove_exclude_fields(self, data={}):
        for e_field in self.exclude_fields:
            try:
                del data[e_field]
            except KeyError:
                pass
        return data

    def get_export_filename(self, app_label=None, export_type=None):
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        if hasattr(self, 'model') and self.model is not None:
            filename = "%s-%s" % (self.model.__name__, date_str)
        else:
            # If self.model doesn't exist, use app_label and export_type
            if app_label and export_type:
                filename = "%s_%s_%s" % (app_label, export_type, date_str)
            else:
                raise ValueError(
                    "Either self.model must exist, or app_label and export_type must be provided.")
        return filename

    def get_app_list(self, app_label=None):
        """ Returns all models registered to a specific app_label
            @param app_label: installed app label
            @return: list of all registered models 
        """
        try:
            app_config = django_apps.get_app_config(app_label)
        except LookupError as e:
            raise CommandError(str(e))
        else:
            return app_config.models

    def exclude_rel_models(self, model_cls):
        """ Restrict the export to only CRFs and enrolment forms, excludes m2m,
            inlines and any other relationship models that will be included as
            part of the main parent data.
            @param app_list: dictionary of model_name: model_cls
        """
        exclude = False
        # Check model class is m2m, skip
        if issubclass(model_cls, ListModelMixin):
            exclude = True
        intermediate_model = model_cls._meta.verbose_name.endswith(
            'relationship') or model_cls._meta.verbose_name.startswith(
            'historical')
        if intermediate_model:
            exclude = True
        return exclude

    def remove_exclude_models(self, app_list):
        app_list = {key: value._meta.label_lower for key,
                    value in app_list.items() if not self.exclude_rel_models(value)}
        return app_list

