from odoo import api, fields, models


class HistoryJob(models.Model):
    _name = 'hr.history.job'


    employee_id = fields.Many2one('hr.employee')
    contract_id = fields.Many2one('hr.contract', string='Hợp đồng', required=True)
    job_id = fields.Many2one('hr.job', string='Chức vụ')
    company_id = fields.Many2one(related="contract_id.company_id")
    department_id = fields.Many2one('hr.department', 'Phòng ban',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    manager_id = fields.Many2one('hr.employee', string='Người quản lý')
    resource_type = fields.Selection([
        ('seniorengsub', 'Kỹ sư / Giám sát cao cấp'),
        ('engsub', 'Kỹ sư / Giám sát'),
        ('teamleader', 'Trưởng nhóm'),
        ('technician', 'Kỹ thuật viên'),
        ('internship', 'Thực tập sinh'),
    ], string='Loại nguồn lực')
    employee_type = fields.Selection(related="contract_id.x_type_employee", string='Loại nhân viên')
    date_start = fields.Date(related="contract_id.date_start", string='Ngày bắt đầu')
    date_end = fields.Date(related="contract_id.date_end", string='Ngày kết thúc')
    currency_id = fields.Many2one(related='company_id.currency_id')
    wage = fields.Monetary(related="contract_id.wage", string='Tiền công/tiền lương	')

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        self.job_id = self.contract_id.job_id.id if self.contract_id.job_id else False
        self.department_id = self.contract_id.department_id.id if self.contract_id.department_id else False
