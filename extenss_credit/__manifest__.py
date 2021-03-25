{
    'name': 'Credit',
    'version': '1.0',
    'summary': 'Definition of the Financial Credit',
    'description': 'Definition of the Financial Credit',
    'author': 'Mastermind Software Services',
    'depends': ['base','mail','crm','base_automation'],
    'application': False,#True
    'website': 'https://www.mss.mx',
    'category': 'Uncategorized',
        'data': [
        'data/ir_sequence_data.xml',
        'security/extenss_credit_security.xml',
        'security/ir.model.access.csv',
        'data/generating_account_status_cron.xml',
        'data/conciliation_credit_cron.xml',
        'data/expiry_notices_cron.xml',
        'data/base_automation_moras.xml',
        'data/send_expiry_notices_cron.xml',
        'wizards/create_accounting_payment_view.xml',
        'reports/report.xml',
        'reports/account_status.xml',
        'views/credit_portal_template.xml',],

    #          'views/credit_menu.xml',
    #          'views/credit_view.xml',
    'installable': True,
    #'auto_install': False,
}