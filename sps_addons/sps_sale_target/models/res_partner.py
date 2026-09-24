# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_source = fields.Char(
        string="Customer Source",
        copy=False
    )    
    customer_status = fields.Many2many(
        comodel_name='res.partner.status',
        string='Status'
    )
    ref = fields.Char(string='Reference', index=True, copy=False)

    def name_get(self):
        return [(r.id, r.name) for r in self]

    @api.model
    def default_get(self, fields_list):
        res = super(ResPartner, self).default_get(fields_list)
        if self._context.get('xx_parent_id'):
            res['parent_id'] = self._context.get('xx_parent_id')
        return res

    @api.constrains('parent_id', 'ref')
    def _check_ref(self):
        for r in self.filtered(lambda s: s.ref):
            if self.search_count([('ref', '=', r.ref), ('id', '!=', r.id)]):
                raise ValidationError(_("Reference on top layer contact should be unique!"))

    @api.constrains('parent_id', 'vat')
    def _check_vat(self):
        for r in self.filtered(lambda s: s.vat):
            var = self.search([('vat', '=', r.vat), ('id', '!=', r.id),('parent_id','=',False)])
            if var and r.parent_id.id != var.id:
                raise ValidationError(_("V.A.T on top layer contact should be unique!"))


class ResPartnerStatus(models.Model):
    _name = 'res.partner.status'
    _description = 'Res Partner Status'
    
    name = fields.Char(
        string='Name',
        required=True,
        copy=False
    )

    _sql_constraints = [
        (
            "name_uniq",
            "UNIQUE(name)",
            "Name should be unique!"
        )
    ]
