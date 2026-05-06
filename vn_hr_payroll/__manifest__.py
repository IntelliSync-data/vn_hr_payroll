{
    "name": "Vietnam HR Payroll",
    "version": "19.0.0.0.0",
    "category": "ISD Modules",
    "summary": "Vietnam Payroll & Salary Management for Odoo Community",
    "description": """
Vietnam HR Payroll for Odoo Community
=====================================

This module adds payroll features for Vietnam:
* Vietnamese salary structure
* Social Insurance (BHXH)
* Health Insurance (BHYT)
* Unemployment Insurance (BHTN)
* Personal Income Tax (PIT)
* Payslip report

Supports:
* Standard deductions for personal and dependants
* Progressive tax calculation
* Insurance caps
* Union fees
    """,
    "author": "Manus AI",
    "website": "https://intellisyncdata.com",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "hr_contract",
        "mail",
        "web"
    ],
    "external_dependencies": {
        "python": ["pypdf"],
    },
    "data": [
        "security/vn_hr_payroll_groups.xml",
        "security/ir.model.access.csv",
        "data/vn_payroll_base_data.xml",
        "data/vn_freelancer_payroll_data.xml",
        "data/vn_second_job_payroll_data.xml",
        "data/vn_pit_tax_table_data.xml",
        "data/vn_freelancer_tax_table_data.xml",
        "data/vn_payroll_config_data.xml",
        "data/vn_payslip_sequence.xml",
        "views/hr_contract_views.xml",
        "views/vn_payslip_views.xml",
        "views/vn_payroll_config_views.xml",
        "views/vnpayroll_structure_type_views.xml",
        "views/vnpayroll_structure_views.xml",
        "views/vnpayroll_salary_rule_category_views.xml",
        "views/vnpayroll_salary_rule_views.xml",
        "views/vn_freelancer_tax_table_views.xml",
        "views/vn_payslip_force_delete_wizard_views.xml",
        "views/vn_payroll_user_permission_views.xml",
        "views/payslip_schedule_views.xml",
        "data/payslip_schedule_cron.xml",
        "views/vn_hr_payroll_menu.xml",
        "views/vn_hr_payroll_assets.xml",
        "views/payslip_download_error_template.xml",
        "report/vn_payslip_report_templates.xml",
        "report/vn_payslip_reports.xml"
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
