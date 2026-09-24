from odoo import api, models, fields
from odoo.exceptions import ValidationError

class ReportPayslipYear(models.TransientModel):
    _name = 'wizard.report.payslip.salary'
    _description = 'Report payslip salary'

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
    ], 'Month', default=str(fields.Date.today().month))
    year = fields.Integer('Year', default=fields.Date.today().year)
    month_to = fields.Selection([
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
    ], 'Month', default=str(fields.Date.today().month))
    year_to = fields.Integer('Year', default=fields.Date.today().year)


    show_draft_payslip = fields.Boolean('Hiển thị phiếu lương nháp', default=False)

    @api.constrains('month', 'year','month_to','year_to')
    def validate_time(self):
        for rec in self:
            ctx = self.env.context
            if ctx.get('view') == 'view_wizard_report_payslip_salary':
                if rec.year_to == rec.year and int(rec.month_to) < int(rec.month):
                    raise ValidationError('Tháng đến phải lớn hơn hoặc bằng tháng từ')
                if rec.year_to < rec.year:
                    raise  ValidationError('Năm đến phải lớn hoặc bằng năm từ')


    def process(self):
        # Bảng lương mới (SALARY NEW) từ 01/07/2026 - thay báo cáo cũ.
        return self.env['hr.payslip'].get_excel_report_salary_new(self.month, self.year, self.show_draft_payslip)

    def process_old(self):
        return self.env['hr.payslip'].get_excel_report_salary(self.month, self.year, self.show_draft_payslip,self.month_to,self.year_to)

    def process_new(self):
        # Bảng chi phí nhân công có thêm 2 cột: Khấu hao CCDC + Đơn giá nhân công (template riêng)
        return self.env['hr.payslip'].get_excel_report_salary_new(
            self.month, self.year, self.show_draft_payslip, with_cost=True)

    def process_kpi(self):
        # Báo cáo KPI - mẫu 'Lương KPI'
        return self.env['hr.payslip'].get_excel_report_kpi(
            self.month, self.year, self.show_draft_payslip)

    def process_meal(self):
        # Báo cáo hỗ trợ ăn trưa - mẫu 'TIỀN ĂN CA'
        return self.env['hr.payslip'].get_excel_report_meal(
            self.month, self.year, self.show_draft_payslip)
