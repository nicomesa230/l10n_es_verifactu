{
    'name': 'Spanish VeriFactu',
    'version': '1.0',
    'summary': 'Integración con VeriFactu para facturación electrónica en España',
    'category': 'Localization/Spain',
    'description': """
    Este módulo integra Odoo con VeriFactu, permitiendo generar un hash único para cada factura,
    incluir un código QR con datos clave y preparar el sistema para el envío a la AEAT conforme a la normativa española.
    """,
    'author': 'Nico Mesa',
    'website': 'https://github.com/nicomesa230/l10n_es_verifactu',
    'depends': ['account','web','base'],
    'data': [
        'security/ir.model.access.csv',
        'views/generate_qr.xml',
        'views/account_move_verifactu.xml',
        'views/verifactu_signature_views.xml',
        'views/verifactu_signature_menu.xml',
        'views/res_config_settings_view.xml',
        'views/res_config_settings_menu.xml',
        'views/res_company_views.xml',
        'views/verifactu_status_wizard.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
