from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPayslipBalance(models.TransientModel):
    _name = 'wizard.report.payslip.balance'
    _description = 'Report payslip balance'
    year = fields.Integer('Year', default=fields.Date.today().year)

    def process(self):
        return self.env['hr.payslip'].get_excel_report_balance(self.year)
