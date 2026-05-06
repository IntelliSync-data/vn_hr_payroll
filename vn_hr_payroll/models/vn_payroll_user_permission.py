# -*- coding: utf-8 -*-

from odoo import models, fields, api


class VnPayrollUserPermission(models.Model):
    _name = 'vn.payroll.user.permission'
    _description = 'Vietnam Payroll User Permission Management'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')

    # Permission fields for each menu
    can_view_payslips = fields.Boolean(string='Payslips', default=False)
    can_view_schedules = fields.Boolean(string='Payslip Schedules', default=False)
    can_view_settings = fields.Boolean(string='Payroll Settings', default=False)
    can_view_pit_table = fields.Boolean(string='PIT Tax Table', default=False)
    can_view_structure_types = fields.Boolean(string='Structure Types', default=False)
    can_view_freelancer_tax = fields.Boolean(string='Freelancer Tax Table', default=False)
    can_view_structures = fields.Boolean(string='Structures', default=False)
    can_view_rule_categories = fields.Boolean(string='Rule Categories', default=False)
    can_view_rules = fields.Boolean(string='Rules', default=False)

    _sql_constraints = [
        ('user_unique', 'unique(user_id)', 'This user already has a permission record!')
    ]

    @api.model
    def default_get(self, fields_list):
        """Load permissions from user's current groups"""
        res = super().default_get(fields_list)
        if 'user_id' in res and res['user_id']:
            user = self.env['res.users'].browse(res['user_id'])
            res.update(self._get_permissions_from_groups(user))
        return res

    @api.model
    def create(self, vals):
        """Override create to sync groups when creating permission record"""
        record = super().create(vals)
        record._sync_user_groups()
        return record

    def write(self, vals):
        """Override write to sync groups when updating permissions"""
        res = super().write(vals)
        self._sync_user_groups()
        return res

    def _sync_user_groups(self):
        """Sync user groups based on permission settings"""
        for record in self:
            user = record.user_id
            if not user:
                continue

            # Get all payroll groups
            group_base = self.env.ref('vn_hr_payroll.group_vn_payroll_user', raise_if_not_found=False)
            group_payslips = self.env.ref('vn_hr_payroll.group_vn_payroll_user_payslips', raise_if_not_found=False)
            group_schedules = self.env.ref('vn_hr_payroll.group_vn_payroll_user_schedules', raise_if_not_found=False)
            group_settings = self.env.ref('vn_hr_payroll.group_vn_payroll_user_settings', raise_if_not_found=False)
            group_pit_table = self.env.ref('vn_hr_payroll.group_vn_payroll_user_pit_table', raise_if_not_found=False)
            group_structure_types = self.env.ref('vn_hr_payroll.group_vn_payroll_user_structure_types', raise_if_not_found=False)
            group_freelancer_tax = self.env.ref('vn_hr_payroll.group_vn_payroll_user_freelancer_tax', raise_if_not_found=False)
            group_structures = self.env.ref('vn_hr_payroll.group_vn_payroll_user_structures', raise_if_not_found=False)
            group_rule_categories = self.env.ref('vn_hr_payroll.group_vn_payroll_user_rule_categories', raise_if_not_found=False)
            group_rules = self.env.ref('vn_hr_payroll.group_vn_payroll_user_rules', raise_if_not_found=False)

            # Build list of groups to add/remove
            groups_to_add = []
            groups_to_remove = []

            # Check each permission and update groups accordingly
            if record.can_view_payslips and group_payslips:
                groups_to_add.append(group_payslips.id)
            elif group_payslips:
                groups_to_remove.append(group_payslips.id)

            if record.can_view_schedules and group_schedules:
                groups_to_add.append(group_schedules.id)
            elif group_schedules:
                groups_to_remove.append(group_schedules.id)

            if record.can_view_settings and group_settings:
                groups_to_add.append(group_settings.id)
            elif group_settings:
                groups_to_remove.append(group_settings.id)

            if record.can_view_pit_table and group_pit_table:
                groups_to_add.append(group_pit_table.id)
            elif group_pit_table:
                groups_to_remove.append(group_pit_table.id)

            if record.can_view_structure_types and group_structure_types:
                groups_to_add.append(group_structure_types.id)
            elif group_structure_types:
                groups_to_remove.append(group_structure_types.id)

            if record.can_view_freelancer_tax and group_freelancer_tax:
                groups_to_add.append(group_freelancer_tax.id)
            elif group_freelancer_tax:
                groups_to_remove.append(group_freelancer_tax.id)

            if record.can_view_structures and group_structures:
                groups_to_add.append(group_structures.id)
            elif group_structures:
                groups_to_remove.append(group_structures.id)

            if record.can_view_rule_categories and group_rule_categories:
                groups_to_add.append(group_rule_categories.id)
            elif group_rule_categories:
                groups_to_remove.append(group_rule_categories.id)

            if record.can_view_rules and group_rules:
                groups_to_add.append(group_rules.id)
            elif group_rules:
                groups_to_remove.append(group_rules.id)

            # Add base group if user has any permissions
            if groups_to_add and group_base:
                groups_to_add.append(group_base.id)
            elif group_base and not groups_to_add:
                groups_to_remove.append(group_base.id)

            # Update user groups
            if groups_to_add:
                user.write({'groups_id': [(4, gid) for gid in groups_to_add]})
            if groups_to_remove:
                user.write({'groups_id': [(3, gid) for gid in groups_to_remove]})

    def _get_permissions_from_groups(self, user):
        """Get permission settings from user's current groups"""
        group_payslips = self.env.ref('vn_hr_payroll.group_vn_payroll_user_payslips', raise_if_not_found=False)
        group_schedules = self.env.ref('vn_hr_payroll.group_vn_payroll_user_schedules', raise_if_not_found=False)
        group_settings = self.env.ref('vn_hr_payroll.group_vn_payroll_user_settings', raise_if_not_found=False)
        group_pit_table = self.env.ref('vn_hr_payroll.group_vn_payroll_user_pit_table', raise_if_not_found=False)
        group_structure_types = self.env.ref('vn_hr_payroll.group_vn_payroll_user_structure_types', raise_if_not_found=False)
        group_freelancer_tax = self.env.ref('vn_hr_payroll.group_vn_payroll_user_freelancer_tax', raise_if_not_found=False)
        group_structures = self.env.ref('vn_hr_payroll.group_vn_payroll_user_structures', raise_if_not_found=False)
        group_rule_categories = self.env.ref('vn_hr_payroll.group_vn_payroll_user_rule_categories', raise_if_not_found=False)
        group_rules = self.env.ref('vn_hr_payroll.group_vn_payroll_user_rules', raise_if_not_found=False)

        return {
            'can_view_payslips': group_payslips in user.groups_id if group_payslips else False,
            'can_view_schedules': group_schedules in user.groups_id if group_schedules else False,
            'can_view_settings': group_settings in user.groups_id if group_settings else False,
            'can_view_pit_table': group_pit_table in user.groups_id if group_pit_table else False,
            'can_view_structure_types': group_structure_types in user.groups_id if group_structure_types else False,
            'can_view_freelancer_tax': group_freelancer_tax in user.groups_id if group_freelancer_tax else False,
            'can_view_structures': group_structures in user.groups_id if group_structures else False,
            'can_view_rule_categories': group_rule_categories in user.groups_id if group_rule_categories else False,
            'can_view_rules': group_rules in user.groups_id if group_rules else False,
        }

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to auto-create records for users with payroll access"""
        # Get all users with Vietnam Payroll User or Manager group
        group_user = self.env.ref('vn_hr_payroll.group_vn_payroll_user', raise_if_not_found=False)
        group_manager = self.env.ref('vn_hr_payroll.group_vn_payroll_manager', raise_if_not_found=False)

        if group_user or group_manager:
            groups_domain = []
            if group_user:
                groups_domain.append(('groups_id', 'in', group_user.id))
            if group_manager:
                groups_domain.append(('groups_id', 'in', group_manager.id))

            users_with_access = self.env['res.users'].search(['|'] + groups_domain) if len(groups_domain) > 1 else self.env['res.users'].search(groups_domain)

            # Auto-create permission records for users without one
            for user in users_with_access:
                existing = self.search([('user_id', '=', user.id)], limit=1)
                if not existing:
                    # Create record with current permissions from groups
                    perms = self._get_permissions_from_groups(user)
                    perms['user_id'] = user.id
                    self.sudo().create(perms)

        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def get_or_create_for_user(self, user_id):
        """Get or create permission record for a user"""
        permission = self.search([('user_id', '=', user_id)], limit=1)
        if not permission:
            user = self.env['res.users'].browse(user_id)
            perms = self._get_permissions_from_groups(user)
            perms['user_id'] = user_id
            permission = self.create(perms)
        return permission
