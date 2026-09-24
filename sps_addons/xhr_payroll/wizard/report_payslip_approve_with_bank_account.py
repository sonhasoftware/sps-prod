from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPayslipApproveWithBankAccount(models.TransientModel):
    _name = 'wizard.report.payslip.approve.with.bank.account'
    _description = 'Report payslip approve with bank account'
    #
    # def _get_bank_name(self):
    #     query="""
    #             drop sequence if exists mysequence;
    #             CREATE SEQUENCE mysequence
    #             INCREMENT 1
    #             START 1;
    #             select nextval('mysequence') as id, he.x_bank_name as name from hr_employee he where x_bank_name is not null
    #     """
    #     self._cr.execute(query)
    #     lists = self._cr.dictfetchall()
    #     lst = []
    #     for l in lists:
    #         id = l['id']
    #         name = l['name']
    #         lst.append((id, name))
    #     return lst

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
    # bank = fields.Many2one('employee.bank', string='tên ngân hàng')

    def process(self):
        return self.env['hr.payslip'].get_excel_report_approve_with_bank_account(self.month, self.year)
