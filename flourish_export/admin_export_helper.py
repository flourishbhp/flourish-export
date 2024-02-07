import datetime
import pandas as pd

from django.db.models.fields.reverse_related import OneToOneRel
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO

class AdminExportHelper:
    """ Flourish export methods to be re-used in the export model admin mixin.
    """

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
                inline_data = {f'{key}__{_count}': value for key, value in inline_data.items() if key not in exclude_fields}
                m2m_fields = obj._meta.many_to_many
                for field in m2m_fields:
                    inline_data.update(self.m2m_data_dict(obj, field, str(_count)))
                data.update(inline_data)
        return data

    def write_to_excel(self, records=[]):
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
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        response['Content-Disposition'] = f'attachment; filename={self.get_export_filename()}.xlsx'
        return response

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

    def get_export_filename(self):
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        filename = "%s-%s" % (self.model.__name__, date_str)
        return filename
