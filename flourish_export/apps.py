from django.conf import settings

import datetime

from django.apps import AppConfig as DjangoAppConfig
from edc_base.apps import AppConfig as BaseEdcBaseAppConfig
from edc_device.apps import AppConfig as BaseEdcDeviceAppConfig
from edc_device.constants import CENTRAL_SERVER


class AppConfig(DjangoAppConfig):
    name = 'flourish_export'
    today_date = datetime.datetime.now().strftime('%Y%m%d')
    export_date = '/documents/flourish_export_' + today_date
    caregiver_path = settings.MEDIA_ROOT + export_date + '/caregiver/'
    child_path = settings.MEDIA_ROOT + export_date + '/child/'
    non_crf_path = settings.MEDIA_ROOT + export_date + '/non_crf/'


class EdcBaseAppConfig(BaseEdcBaseAppConfig):
    project_name = 'Flourish Export'
    institution = 'Botswana-Harvard AIDS Institute'


class EdcDeviceAppConfig(BaseEdcDeviceAppConfig):
    device_role = CENTRAL_SERVER
    device_id = '99'
