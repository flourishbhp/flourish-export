from django.conf import settings
from edc_navbar import NavbarItem, site_navbars, Navbar


no_url_namespace = True if settings.APP_NAME == 'flourish_export' else False

flourish_export = Navbar(name='flourish_export')

flourish_export.append_item(
    NavbarItem(
        name='export_data',
        title='Export Data',
        label='flourish Export Data',
        fa_icon='fa fa-database',
        url_name=settings.DASHBOARD_URL_NAMES[
            'export_listboard_url'],
        no_url_namespace=no_url_namespace))


site_navbars.register(flourish_export)
