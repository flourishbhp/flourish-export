from django.contrib.sites.models import Site
from django.db import models

from edc_base.model_mixins import BaseUuidModel
from edc_base.utils import get_utcnow

from edc_base.sites import SiteModelMixin
from edc_search.model_mixins import SearchSlugManager
from edc_search.model_mixins import SearchSlugModelMixin as Base

from ..identifiers import ExportIdentifier


class ExportFileManager(SearchSlugManager, models.Manager):

    def get_by_natural_key(self, export_identifier):
        return self.get(export_identifier=export_identifier)


class SearchSlugModelMixin(Base):

    def get_search_slug_fields(self):
        fields = super().get_search_slug_fields()
        return fields

    class Meta:
        abstract = True


class ExportFile(SiteModelMixin, SearchSlugModelMixin, BaseUuidModel):

    identifier_cls = ExportIdentifier

    export_identifier = models.CharField(
        verbose_name="Export Identifier",
        max_length=36,
        unique=True,
        editable=False)

    site = models.ForeignKey(
        Site, on_delete=models.PROTECT,
        related_name='django_site',
        null=True, editable=False)

    study = models.CharField(max_length=100, blank=True)

    description = models.CharField(max_length=255, blank=True)

    document = models.FileField(upload_to='documents/')

    uploaded_at = models.DateTimeField(auto_now_add=True)

    download_time = models.DecimalField(
        null=True,
        max_digits=10,
        decimal_places=2)

    datetime_started = models.DateTimeField(default=get_utcnow)

    datetime_completed = models.DateTimeField(default=get_utcnow)

    download_complete = models.BooleanField(
        default=False,)

    def save(self, *args, **kwargs):
        if self.datetime_started and self.datetime_completed:
            difference = self.datetime_completed - self.datetime_started
            self.download_time = round(difference.total_seconds() / 60, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.export_identifier}'

    def natural_key(self):
        return self.export_identifier

    def get_search_slug_fields(self):
        fields = super().get_search_slug_fields()
        fields.append('export_identifier')
        return fields

    @property
    def doc_url(self):
        """Return the file url.
        """
        try:
            return self.document.url
        except ValueError:
            return None
