from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PayrollMixinConfig(models.TransientModel):
    _name = 'hr.payroll.mixin_config'
    _description = 'Payroll addition configs'

    deduction_self = fields.Float('Self tax deduction')
    deduction_dependent = fields.Float('Dependent tax deduction')
    insurance_employee_social = fields.Float('Employee social insurance (%)')
    insurance_employee_health = fields.Float('Employee health insurance (%)')
    insurance_employee_unemployment = fields.Float('Employee unemployment insurance (%)')

    @api.model
    def default_get(self, fields):
        vals = super(PayrollMixinConfig, self).default_get(fields)
        vals['deduction_self'] = self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.deduction_self', 0.0)
        vals['deduction_dependent'] = self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.deduction_dependent', 0.0)
        vals['insurance_employee_social'] = self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.insurance_employee_social', 0.0)
        vals['insurance_employee_health'] = self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.insurance_employee_health', 0.0)
        vals['insurance_employee_unemployment'] = self.env['ir.config_parameter'].sudo().get_param('xhr_payroll.insurance_employee_unemployment', 0.0)
        return vals

    def process(self):
        self.env['ir.config_parameter'].sudo().set_param('xhr_payroll.deduction_self', self.deduction_self)
        self.env['ir.config_parameter'].sudo().set_param('xhr_payroll.deduction_dependent', self.deduction_dependent)
        self.env['ir.config_parameter'].sudo().set_param('xhr_payroll.insurance_employee_social', self.insurance_employee_social)
        self.env['ir.config_parameter'].sudo().set_param('xhr_payroll.insurance_employee_health', self.insurance_employee_health)
        self.env['ir.config_parameter'].sudo().set_param('xhr_payroll.insurance_employee_unemployment', self.insurance_employee_unemployment)
        return True
