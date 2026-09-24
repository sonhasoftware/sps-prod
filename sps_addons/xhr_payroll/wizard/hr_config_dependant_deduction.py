from odoo import api, models, fields, _
from odoo.exceptions import UserError


class HrConfigDependantDeduction(models.TransientModel):
    _name = 'hr.config.dependant.deduction'
    _description = 'Change dependant deduction'

    x_dependent_deduction = fields.Float('Dependent deduction')

    @api.model
    def default_get(self, fields):
        vals = super(HrConfigDependantDeduction, self).default_get(fields)
        vals['x_dependent_deduction'] = self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.dependent_deduction', 0.0)
        return vals

    def process(self):
        self.env['ir.config_parameter'].sudo().set_param('xhr_payroll.dependent_deduction', self.x_dependent_deduction)
        return True
