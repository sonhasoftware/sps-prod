from odoo import api, fields, models, _
from datetime import datetime,date

class WageCostRel(models.Model):
    _name = 'wage.cost.actual'
    _description = 'Chi phí nhân công'
    _order = 'date_to desc'

    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    employee_id = fields.Many2one('hr.employee', string='Nhân viên')
    unit_price = fields.Float('Đơn giá nhân công')
    payslip_id = fields.Many2one('hr.payslip', 'Phiếu lương')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Trạng thái', related='payslip_id.state')

    # cập nhật chi phí nhân công cho tất cả bản ghi chi phí nhân công thỏa mãn điều kiện
    def update_project_wage_cost(self, rec=None):
        if rec:
            month = str(rec.date_from.month)
            year = rec.date_from.year
            wage_costs = self.env['project.wage.cost'].search(
                [('employee_id', '=', rec.employee_id.id), ('year', '=', year), ('month', '=', month)])
            for wage in wage_costs:
                wage.wage_cost_id = rec.id
        else:
            for rec in self:
                month = str(rec.date_from.month)
                year = rec.date_from.year
                wage_costs = self.env['project.wage.cost'].search(
                    [('employee_id', '=', rec.employee_id.id), ('year', '=', year), ('month', '=', month)])
                for wage in wage_costs:
                    wage.wage_cost_id = rec.id

    @api.model
    def create(self, vals):
        res = super(WageCostRel, self).create(vals)
        self.update_project_wage_cost(res)
        return res

    def write(self, vals):
        res = super(WageCostRel, self).write(vals)
        self.update_project_wage_cost()
        return res


class ProjectMember(models.Model):
    _name = 'project.wage.cost'
    _description = 'Chi phí nhân công của dự án'

    """
        {
            'id_employee': {
                year: {
                    month: {
                        'hour': 3,
                        'hour_converted': 1,
                        'wage_cost_id': 3, # chi phi don gia nhan cong
                    }
                }
            }
        }
    """

    project_id = fields.Many2one('project.project', 'Dự án')
    employee_id = fields.Many2one('hr.employee', 'Tên nhân viên', required=1)
    # job_id = fields.Many2one('hr.job', 'Chức danh', related='employee_id.job_id')
    # department_id = fields.Many2one('hr.department', 'Phòng ban', related='employee_id.department_id')
    start_date = fields.Date('Ngày bắt đầu')
    end_date = fields.Date('Ngày kết thúc')
    wage_cost_id = fields.Many2one('wage.cost.actual', 'Chi phí nhân công')
    unit_price = fields.Float(related='wage_cost_id.unit_price', string='Đơn giá nhân công', store=True)
    # estimate_wage_cost_id = fields.Many2one('wage.cost.actual', 'Chi phí nhân công tạm tính')
    # estimate_unit_price = fields.Float(related='estimate_wage_cost_id.unit_price', string='Đơn giá nhân công tạm tính', store=True)
    hour_converted = fields.Float('Giờ công quy đổi')
    hour = fields.Float('Giờ công hỗ trợ đi lại')
    work_hour = fields.Float('Giờ công tính chi phí', compute='compute_cost', store=True)
    cost = fields.Float('Chi phí theo giờ công', compute='compute_cost', store=True)
    # estimate_cost = fields.Float('Chi phí theo giờ công tạm tính', compute='compute_cost', store=True)
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
    ], 'Tháng', default=str(fields.Date.today().month))
    year = fields.Integer('Năm', default=fields.Date.today().year)
    monthly_efficiency = fields.Float('HSLĐ tháng (%)',compute='_compute_monthly_efficiency')
    standard_efficiency = fields.Float('HSLĐ định mức (%)',compute='_compute_standard_efficiency')
    costing_hours = fields.Float('Costing hours', readonly=1)

    def _compute_monthly_efficiency(self):
        for rec in self:
            sql = f'''
                        SELECT  
                            view_base.employee_id,
                            view_base.name_employee,
                            coalesce(view_base.hour_project, 0) as hour_project,
                            coalesce(view_base.hour, 0) as hour,
                            coalesce(view_trocapdilai.sogiotrocapdilai_project, 0) as sogiotrocapdilai_project,
                            coalesce(view_trocapdilai.sogiotrocapdilai, 0) as sogiotrocapdilai,
                            coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong, 0) as sogiohotroluongbuducong,
                            -- Công thức tính hiệu quả
                            round(
                                ((coalesce(view_base.hour_project, 0) + coalesce(view_trocapdilai.sogiotrocapdilai_project, 0)) / 
                                 NULLIF((coalesce(view_base.hour, 0) + coalesce(view_sogiohotroluongbuducong.sogiohotroluongbuducong, 0) + coalesce(view_trocapdilai.sogiotrocapdilai, 0)), 0) * 100)::numeric, 2
                            ) as hieuqua
                        FROM
                            (-- Giờ chấm công
                            SELECT  
                                view_detail.year_chamcong,
                                view_detail.month_chamcong,
                                view_detail.employee_id,
                                view_detail.name_employee,
                                sum(view_detail.hour) as hour,
                                sum(view_detail.hour_project) as hour_project
                            FROM
                                (SELECT 
                                    extract('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                    extract('month' from hr_work_entry.x_date) as month_chamcong,
                                    hr_work_entry.employee_id,
                                    hr_employee.name as name_employee,
                                    hr_work_entry_line.hour, 
                                    (CASE WHEN project_project.x_project_type IN ('service', 'maintainance', 'operation') 
                                          THEN hr_work_entry_line.hour 
                                          ELSE 0 END) as hour_project
                                FROM hr_work_entry_line
                                LEFT JOIN hr_work_entry ON hr_work_entry_line.entry_id = hr_work_entry.id
                                LEFT JOIN project_project ON hr_work_entry_line.project_id = project_project.id
                                LEFT JOIN hr_employee ON hr_work_entry.employee_id = hr_employee.id 
                                                      AND hr_employee.active = True
                                WHERE hr_work_entry.employee_id = {rec.employee_id.id}
                                ) as view_detail
                            GROUP BY view_detail.year_chamcong, view_detail.month_chamcong, 
                                     view_detail.employee_id, view_detail.name_employee
                            ) as view_base
                        LEFT JOIN 
                            (-- Giờ hỗ trợ lương bù đủ công
                            SELECT  
                                extract('year' from hr_payslip.date_from)::character varying as year_payslip,
                                extract('month' from hr_payslip.date_from) as month_payslip,
                                hr_payslip.employee_id,
                                hr_payslip_input.amount as sogiohotroluongbuducong
                            FROM hr_payslip
                            LEFT JOIN hr_payslip_input ON hr_payslip.id = hr_payslip_input.payslip_id 
                            WHERE hr_payslip_input.input_type_id = 13
                              AND hr_payslip.employee_id = {rec.employee_id.id}
                            ) as view_sogiohotroluongbuducong
                        ON view_base.year_chamcong = view_sogiohotroluongbuducong.year_payslip 
                           AND view_base.month_chamcong = view_sogiohotroluongbuducong.month_payslip 
                           AND view_base.employee_id = view_sogiohotroluongbuducong.employee_id
                        LEFT JOIN 
                            (-- Giờ trợ cấp đi lại
                            SELECT
                                view_detail.year_chamcong,
                                view_detail.month_chamcong,
                                view_detail.employee_id,
                                sum(view_detail.hour) as sogiotrocapdilai,
                                sum(view_detail.sogiotrocapdilai_project) as sogiotrocapdilai_project
                            FROM
                                (SELECT 
                                    extract('year' from hr_work_entry.x_date)::character varying as year_chamcong,
                                    extract('month' from hr_work_entry.x_date) as month_chamcong,
                                    hr_work_entry.employee_id,
                                    hr_work_entry_allowance.hour,
                                    (CASE WHEN project_project.x_project_type IN ('service', 'maintainance', 'operation') 
                                          THEN hr_work_entry_allowance.hour 
                                          ELSE 0 END) as sogiotrocapdilai_project
                                FROM hr_work_entry_allowance
                                LEFT JOIN hr_work_entry ON hr_work_entry_allowance.entry_id = hr_work_entry.id
                                LEFT JOIN project_project ON hr_work_entry_allowance.project_id = project_project.id
                                LEFT JOIN hr_employee ON hr_work_entry.employee_id = hr_employee.id 
                                                      AND hr_employee.active = True
                                WHERE hr_work_entry.employee_id = {rec.employee_id.id}
                                ) as view_detail
                            GROUP BY view_detail.year_chamcong, view_detail.month_chamcong, view_detail.employee_id
                            ) as view_trocapdilai
                        ON view_base.year_chamcong = view_trocapdilai.year_chamcong 
                           AND view_base.month_chamcong = view_trocapdilai.month_chamcong 
                           AND view_base.employee_id = view_trocapdilai.employee_id
                        WHERE view_base.year_chamcong = '{rec.year}' 
                          AND view_base.month_chamcong = {rec.month}
                          AND view_base.employee_id = {rec.employee_id.id}
                    '''

            self._cr.execute(sql)
            result = self._cr.dictfetchone()
            rec.monthly_efficiency = result.get('hieuqua', 0.0)

    def _compute_standard_efficiency(self):
        for rec in self:
            rec.standard_efficiency = 0
            target = self.env['annual.labor.productivity.target'].search([('employee_id','=',rec.employee_id.id),
                                                                          ('year','=', rec.year)])
            if target:
                rec.standard_efficiency = target.target

    @api.depends('hour_converted', 'hour', 'unit_price', 'costing_hours')
    def compute_cost(self):
        for rec in self:
            rec.work_hour = rec.costing_hours + rec.hour
            rec.cost = rec.work_hour * rec.unit_price
            if rec.monthly_efficiency > 0 and rec.standard_efficiency >0:
                rec.cost = rec.work_hour * rec.unit_price * rec.standard_efficiency / rec.monthly_efficiency
            # rec.estimate_cost = rec.work_hour * rec.estimate_unit_price
