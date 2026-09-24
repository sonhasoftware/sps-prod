from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPayslipYear(models.TransientModel):
    _name = 'wizard.report.payslip.year'
    _description = 'Report payslip year'
    year = fields.Integer('Year', default=fields.Date.today().year)

    def process(self):
        return self.env['hr.payslip'].get_excel_report_year(self.year)
