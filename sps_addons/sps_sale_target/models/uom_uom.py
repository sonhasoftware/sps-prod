# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Uom(models.Model):
    _inherit = 'uom.uom'

    category_id = fields.Many2one('uom.category', 'Danh mục', required=False, ondelete='cascade')

    @api.model
    def create(self, vals):
        category_id = self.env['uom.category'].create({
            'name': vals['name']
        })
        vals['category_id'] = category_id.id
        res = super(Uom, self).create(vals)
        return res

    @api.constrains('name')
    def check_name(self):
        exists = self.env['uom.uom'].search(
            [('name', '=', self.name), ('id', '!=', self.id)])
        if exists:
            raise ValidationError('Tên đơn vị tính ' + self.name + ' đã tồn tại.')
