{
    'name': 'Datamart',
    'version': '1.0',
    'summary': 'Definition of the Financial Credit',
    'description': 'Definition of the Financial Credit',
    'author': 'Mastermind Software Services',
    'depends': ['analytic','account','extenss_financial_product'],
    'application': True,
    'website': 'https://www.mss.mx',
    'category': 'Uncategorized',
    'data': [
            'data/ir_sequence_data.xml',
            'data/generate_accounting_cron.xml',
            'security/extenss_datamart_security.xml',
            'security/ir.model.access.csv',
            'views/datamart_menu.xml',
            'views/datamart_view.xml',
            ],
}