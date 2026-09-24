# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrRecruitRequest(models.Model):
    _name = 'hr.recruit.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Recruitment request'
    _order = 'id desc'
    # _rec_name = 'job_id'

    x_degree = fields.Many2one('hr.recruitment.degree', 'Bằng cấp')
    job_id = fields.Many2one('hr.job', 'Position')
    department_id = fields.Many2one('hr.department', 'Department')
    project_id = fields.Many2one('project.project', 'Project')
    quantity = fields.Integer('Recruitment quantity', default=1)
    report_to_id = fields.Many2one('hr.job', 'Report to')
    employee_count = fields.Integer('Number of employee')
    budget = fields.Selection([
        ('in', 'In budget'),
        ('out', 'Out of budget'),
    ], 'Recruitment budget', default='in')
    budget_reason = fields.Text('Budget reason')
    reason_replace = fields.Boolean('Replace')
    reason_add = fields.Boolean('Add')
    contract_type = fields.Selection([
        ('full_time', 'Full time'),
        ('part_time', 'Part time'),
    ], 'Contract type', default='full_time')
    work_location_official = fields.Boolean('Official location')
    work_location_project = fields.Boolean('Project location')
    working_hours = fields.Selection([
        ('44', '44hrs'),
        ('48', '48hrs'),
    ], 'Working hours', default='44')
    allowance_phone = fields.Boolean('Phone allowance')
    allowance_phone_value = fields.Char('Phone allowance value')
    allowance_oil = fields.Boolean('Oil allowance')
    allowance_oil_value = fields.Char('Oil allowance value')
    allowance_other = fields.Boolean('Other allowance')
    allowance_other_note = fields.Text('Other allowance note')
    allowance_other_value = fields.Char('Other allowance value')
    income = fields.Char('Income')
    income_value = fields.Float('Ngân sách tuyển dụng')
    income_type = fields.Selection([
        ('all', 'All in one'),
        ('ot_extra', 'OT income'),
    ], 'Income type')
    income_probation = fields.Float('Income probation', default=85.0)
    date_start = fields.Date('Start working date')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], 'Gender')
    age_from = fields.Integer('Age from')
    age_to = fields.Integer('Age to')
    degree = fields.Char('Degree')
    experience_required = fields.Selection([
        ('0', 'No'),
        ('1', 'Yes'),
    ], 'Experience required')
    experience_value = fields.Integer('Experience year')
    english_requires = fields.Selection([
        ('fluent', 'Fluent'),
        ('basic', 'Basic'),
        ('no', 'No'),
    ], 'English requires')
    other_requires = fields.Text('Other requires')
    source_internal = fields.Boolean('Internal source')
    source_sps_web = fields.Boolean('SPS web source')
    source_buy = fields.Boolean('Buy source')
    source_website = fields.Boolean('Recruiment website source')
    requester_uid = fields.Many2one('res.users', 'Requester')
    verifier_uid = fields.Many2one('res.users', 'Verifier')
    hr_uid = fields.Many2one('res.users', 'HR')
    approver_uid = fields.Many2one('res.users', 'Approver')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approval_department', 'Department Approved'),
        ('approval_hr', 'HR Approved'),
        # ('approval_bod', 'BOD Approved'),
        ('doing', 'Doing'),
        ('done', 'Done'),
        ('over_deadline', 'Over deadline'),
        ('canceled', 'Canceled'),
    ], 'State', default='draft', copy=0, tracking=1)
    is_department_approvable = fields.Boolean('Department approvable?', compute='compute_is_approvable')
    is_hr_approvable = fields.Boolean('HR approvable?', compute='compute_is_approvable')
    remark = fields.Char('Ghi chú')

    @api.depends('department_id')
    @api.onchange('department_id')
    def compute_is_approvable(self):
        current_employee_id = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self._uid)
        ], limit=1)
        for r in self:
            try:
                rec_department_manager_employee_id = r.department_id.manager_id.id
            except:
                rec_department_manager_employee_id = False
            is_department_approvable = current_employee_id and current_employee_id.id == rec_department_manager_employee_id
            r.is_department_approvable = is_department_approvable
            r.is_hr_approvable = (not is_department_approvable and r.state == 'confirm') or r.state == 'approval_department'

    def action_approval_bod(self):
        if self.state == 'approval_hr':
            self.state = 'doing'

    def action_approval_hr(self):
        if self.state in ['confirm', 'approval_department']:
            self.state = 'approval_hr'

    def action_approval_department(self):
        if self.state == 'confirm':
            self.state = 'approval_department'

    def action_confirm(self):
        self.state = 'confirm'

    def action_reject(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'canceled'

    def schedule_update_state(self):
        today = fields.Date.today()
        signed_state_id = self.env.ref('hr_recruitment.stage_job5')
        for r in self.search([
            ('state', '=', 'doing'),
        ]):
            # Đếm số đã tuyển thành công
            contract_count = self.env['hr.applicant'].sudo().search_count([
                ('recruit_rq_id', '=', r.id),
                ('stage_id', '=', signed_state_id.id)
            ])
            if r.quantity <= contract_count:
                r.state = 'done'
            else:
                if r.date_start and r.date_start < today:
                    r.state = 'over_deadline'

    def name_get(self):
        result = []
        for record in self:
            if record.project_id:
                name = (record.project_id.name, record.job_id.name)
                result.append((record.id, str(record.id) + ' - ' + "/".join(name)))
            elif record.job_id:
                result.append((record.id, str(record.id) + ' - ' + record.job_id.name))
            else:
                result.append((record.id, str(record.id)))
        return result

    @api.depends('job_id')
    @api.onchange('job_id')
    def onchange_department(self):
        for r in self:
            if r.job_id:
                r.department_id = r.job_id.department_id.id
            else:r.department_id=False