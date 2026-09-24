from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPayslipApprove(models.TransientModel):
    _name = 'wizard.report.payslip.approve'
    _description = 'Report payslip approve'

    month = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
    ], 'Month', default=fields.Date.today().month)
    year = fields.Integer('Year', default=fields.Date.today().year)

    def process(self):
        return self.env['hr.payslip'].get_excel_report(self.month, self.year)
