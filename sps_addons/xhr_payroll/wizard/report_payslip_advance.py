from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPayslipAdvance(models.TransientModel):
    _name = 'wizard.report.payslip.advance'
    _description = 'Report payslip advance'
    date_from = fields.Date(default=fields.date.today())
    date_to = fields.Date(default=fields.date.today())

    def process(self):
        return self.env['hr.payslip'].get_excel_report_advance(self.date_from, self.date_to)
