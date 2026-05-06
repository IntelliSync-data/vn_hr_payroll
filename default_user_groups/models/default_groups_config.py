# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import json


class DefaultGroupsConfig(models.TransientModel):
    _name = 'default.groups.config'
    _description = 'Default Groups Configuration'

    default_user_group_ids = fields.Many2many(
        'res.groups',
        string='Default User Groups',
        help='Groups that will be automatically assigned to new users when they are created or invited.',
        domain="[('category_id', '!=', False)]"
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'default_user_group_ids' in fields:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            default_groups_json = IrConfigParameter.get_param('default_user_groups.group_ids_json', '[]')
            try:
                group_ids = json.loads(default_groups_json)
                if group_ids:
                    existing_groups = self.env['res.groups'].browse(group_ids).exists()
                    res['default_user_group_ids'] = [(6, 0, existing_groups.ids)]
            except (json.JSONDecodeError, TypeError):
                pass
        return res

    def action_save(self):
        """Save default groups configuration"""
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        group_ids = self.default_user_group_ids.ids
        IrConfigParameter.set_param('default_user_groups.group_ids_json', json.dumps(group_ids))
        
        group_names = self.default_user_group_ids.mapped('name')
        message = _('Default groups saved: %s') % ', '.join(group_names) if group_names else _('Default groups cleared.')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
            }
        }

    def action_reset(self):
        """Reset default groups configuration"""
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('default_user_groups.group_ids_json', '[]')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Default user groups configuration has been reset.'),
                'type': 'info',
            }
        }