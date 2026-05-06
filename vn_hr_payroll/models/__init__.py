# -*- coding: utf-8 -*-

from . import ir_attachment
from . import hr_contract # If this is a custom model specific to vn_hr_payroll
from . import salary_rule_category
from . import salary_rule
from . import payroll_structure_type
from . import payroll_structure
from . import vn_pit_tax_table   # If this is a custom model specific to vn_hr_payroll
from . import vn_freelancer_tax_table  # Import the freelancer tax table model
from . import vn_payslip         # If this is a custom model specific to vn_hr_payroll
from . import vn_payroll_config  # Import the payroll config model
from . import payslip_schedule   # Import the payslip schedule model
from . import vn_payslip_force_delete_wizard  # Import the force delete wizard
from . import vn_payroll_user_permission  # Import the user permission management model
