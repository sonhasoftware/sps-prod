# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ExpertiseType(models.Model):
    _name = 'expertise.type'
    _description = 'Loại chuyên môn'
    _order = 'name asc'

    name = fields.Char('Chuyên môn', required=1)
    active = fields.Boolean('Có hiệu lực', default=1)

    @api.constrains('name')
    def constraint_name(self):
        for r in self:
            if self.search_count([('id', '!=', r.id), ('name', '=', r.name)]):
                raise UserError(_('Đã tồn tại loại chuyên môn có cùng tên %s') % r.name)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _("%s (copy)") % (self.name or '')
        return super(ExpertiseType, self).copy(default)
