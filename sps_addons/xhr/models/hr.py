# -*- coding: utf-8 -*-
import os
import base64
from io import BytesIO
from docxtpl import DocxTemplate

from odoo.osv import expression
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Contract(models.Model):
    _inherit = 'hr.contract'

    x_insurance_wage = fields.Monetary('Insurance wage', required=True, tracking=True,
                                       help="Employee's insurance wage.")
    x_allowance_phone = fields.Monetary('Telephone allowance', tracking=True)
    x_gasoline_standard = fields.Float('Standard gasoline (liter)', tracking=True)
    # Giữ lại 2 cột cũ trong DB (ẩn khỏi view) để an toàn dữ liệu & lịch sử thuế.
    # Từ 01/07/2026 gộp thành KPI định mức (kpi_norm) — xem bang_luong_moi_spec.md.
    x_allowance_lunch = fields.Float('Lunch allowance', tracking=True)
    x_allowance_home = fields.Float('Home allowance', tracking=True)
    kpi_norm = fields.Monetary('KPI định mức', tracking=True,
                               help="Định mức lương hiệu suất công việc (KPI). "
                                    "Gộp từ phụ cấp ăn trưa + nhà ở.")

    x_type_employee = fields.Selection([
        ('1', 'Official staff'), ('2', 'Collaborators'), ('3', 'Probationary staff')
    ], string='Type Employee')
    x_ot_allowed = fields.Boolean('OT Salary?')
    x_contract_type = fields.Selection([
        ('hdtv', 'HĐTV'),
        ('hdth', 'HĐLĐ có thời hạn'),
        ('hdldvth', 'HĐLĐ vô thời hạn'),
        ('hddv', 'HĐDV'),
        ('hdkt', 'HĐKT'),
        ('hdnt', 'HĐNT'),
        ('plhd', 'PLHĐ'),
    ], 'Contract type')
    x_drafting_department_id = fields.Many2one('hr.department', 'Drafting department')
    x_sign_job_id = fields.Many2one('hr.job', 'Signer')
    x_contract_duration = fields.Char('Contract duration')

    @api.onchange('x_insurance_wage', 'kpi_norm')
    def onchange_compute_wage(self):
        self.wage = self.x_insurance_wage + self.kpi_norm

    @api.model
    def create(self, vals):
        res = super(Contract, self).create(vals)
        self.env['hr.history.job'].create(
            {'employee_id': res.employee_id.id if res.employee_id else False,
             'contract_id': res.id,
             'manager_id': res.employee_id.parent_id.id if res.employee_id and res.employee_id.parent_id else False,
             'resource_type': res.employee_id.x_resource_type if res.employee_id else False})
        return res

    def unlink(self):
        history_job_ids = self.env['hr.history.job'].search([('contract_id', '=', self.id)])
        for history_job_id in history_job_ids:
            history_job_id.unlink()
        return super(Contract, self).unlink()

    def update_history_job(self):
        contract_ids = self.env['hr.contract'].search([])
        HistoryJob = self.env['hr.history.job']
        for rec in contract_ids:
            history_job_id = HistoryJob.search([('manager_id', '=', rec.id)])
            if not history_job_id:
                HistoryJob.create(
                    {'employee_id': rec.employee_id.id if rec.employee_id else False,
                     'contract_id': rec.id,
                     'manager_id': rec.employee_id.parent_id.id if rec.employee_id and rec.employee_id.parent_id else False,
                     'resource_type': rec.employee_id.x_resource_type if rec.employee_id else False})


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    mobile_phone = fields.Char('Mobile Phone')


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        domain="[('partner_id', '=', address_home_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups=None,
        tracking=True,
        help='Employee bank salary account')
    x_code = fields.Char('Employee code', copy=False, tracking=1)
    x_project_id = fields.Many2one('project.project', 'Project', tracking=1)
    # Profile
    x_has_cv = fields.Boolean('Curriculum vitae', default=False, tracking=1)
    x_has_birth_cert = fields.Boolean('Birth certificate', default=False, tracking=1)
    x_has_medical_exam = fields.Boolean('Medical examination certificate', default=False, tracking=1)
    x_has_id_card = fields.Boolean('ID card', default=False, tracking=1)
    x_has_registration_book = fields.Boolean('Registration book', default=False, tracking=1)
    x_has_degree = fields.Boolean('Degree', default=False, tracking=1)
    x_has_portrait = fields.Boolean('Portrait', default=False, tracking=1)
    x_note = fields.Text('Note', tracking=1)
    # Other
    x_onboard_date = fields.Date('Onboard date', tracking=1)
    x_quit_date = fields.Date('Quit date', tracking=1)
    # Private
    x_identification_issue_date = fields.Date('Issue date', tracking=1)
    x_identification_issue_by = fields.Char('Issue by', tracking=1)
    x_ethnic = fields.Char('Ethnic', tracking=1)
    x_living = fields.Char('Place of living', tracking=1)
    x_training_form = fields.Selection([
        ('1', 'Formal'),
        ('2', 'Connected'),
        ('3', 'In office'),
        ('4', 'Intermediate'),
    ], 'Forms of training')
    x_household_address = fields.Char('Household address')
    # Dependant
    x_depend_ids = fields.One2many('hr.employee.depend', 'employee_id', 'Dependants')
    x_emergency_ids = fields.One2many('hr.employee.emergency', 'employee_id', 'Emergencies')
    # Account
    x_tax_number = fields.Char('Personal tax number')
    x_bank_account = fields.Char('Bank account', tracking=1)
    x_bank_name = fields.Char('Bank name', tracking=1)
    x_bank_branch = fields.Char('Bank branch', tracking=1)
    x_bank_account_holder = fields.Char('Account holder', tracking=1)
    x_salary_hold = fields.Boolean('Hold salary', tracking=1)
    # Social insurance
    x_insurance_number = fields.Char('Social insurance book number', tracking=1)
    x_insurance_place = fields.Char('Place of social insurance book', tracking=1)
    # Working hours
    x_calendar_type = fields.Selection([
        ('fix', 'Fix by calendar'),
        ('plan', 'Fix by plan'),
        ('dynamic', 'Dynamic input'),
    ], 'Work hour type', default='fix', required=1)
    x_employee_type = fields.Selection([
        ('employee', 'Employee'),
        ('intern', 'Intern'),
    ], 'Employee type')


class Employee(models.Model):
    _inherit = 'hr.employee'

    x_cv_code = fields.Many2one('hr.applicant', 'CV ứng tuyển')
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        domain="[('partner_id', '=', address_home_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups=None,
        tracking=True,
        help='Employee bank salary account')
    certificate = fields.Selection([
        ('graduate', 'Vocational School'),
        ('bachelor', 'High School'),
        ('intermediate', 'Intermediate School'),
        ('doctor', 'Doctor'),
        ('university', 'University'),
        ('engineer', 'Engineer'),
        ('master', 'Master'),
        ('diploma', 'Diploma'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other', groups="hr.group_hr_user", tracking=True)
    x_code = fields.Char('Employee code', copy=False, tracking=1)
    x_project_id = fields.Many2one('project.project', 'Project', tracking=1)
    # Profile
    x_has_cv = fields.Boolean('Curriculum vitae', default=False, tracking=1)
    x_has_birth_cert = fields.Boolean('Birth certificate', default=False, tracking=1)
    x_has_medical_exam = fields.Boolean('Medical examination certificate', default=False, tracking=1)
    x_has_id_card = fields.Boolean('ID card', default=False, tracking=1)
    x_has_registration_book = fields.Boolean('Registration book', default=False, tracking=1)
    x_has_degree = fields.Boolean('Degree', default=False, tracking=1)
    x_has_portrait = fields.Boolean('Portrait', default=False, tracking=1)
    x_note = fields.Text('Note', tracking=1)
    # Other
    x_onboard_date = fields.Date('Onboard date', tracking=1)
    x_quit_date = fields.Date('Quit date', tracking=1)
    # Private
    x_identification_issue_date = fields.Date('Issue date', tracking=1)
    x_identification_issue_by = fields.Char('Issue by', tracking=1, default='Cục CS QLHC về TTXH')
    x_ethnic = fields.Char('Ethnic', tracking=1)
    x_ethnic_id = fields.Many2one('hr.employee.ethnic', 'Dân tộc', tracking=1)
    x_living = fields.Char('Place of living', tracking=1)
    x_training_form = fields.Selection([
        ('1', 'Formal'),
        ('2', 'Connected'),
        ('3', 'In office'),
        ('4', 'Intermediate'),
    ], 'Forms of training')
    x_household_address = fields.Char('Household address')
    # Dependant
    x_depend_ids = fields.One2many('hr.employee.depend', 'employee_id', 'Dependants')
    x_emergency_ids = fields.One2many('hr.employee.emergency', 'employee_id', 'Emergencies')
    # Account
    x_tax_number = fields.Char('Personal tax number')
    x_bank_account_holder = fields.Char('Account holder', tracking=1)
    x_bank_account = fields.Char('Bank account', tracking=1)
    x_bank_name = fields.Char('Bank name', tracking=1)
    x_bank_branch = fields.Char('Bank branch', tracking=1)
    x_salary_hold = fields.Boolean('Hold salary', tracking=1)
    # Social insurance
    x_insurance_number = fields.Char('Social insurance book number', tracking=1)
    x_insurance_place = fields.Char('Place of social insurance book', tracking=1)
    # Working hours
    x_calendar_type = fields.Selection([
        ('fix', 'Fix by calendar'),
        ('plan', 'Fix by plan'),
        ('dynamic', 'Dynamic input'),
    ], 'Work hour type', default='fix', required=1)
    x_employee_type = fields.Selection([
        ('employee', 'Employee'),
        ('intern', 'Intern'),
    ], 'Employee type')
    x_place_of_birth_id = fields.Many2one('res.country.state', string='Nơi sinh')
    x_history_job_ids = fields.One2many('hr.history.job', 'employee_id', string='Lịch sử chức vụ')
    x_study_field_id = fields.Many2one('hr.study.field', string='Lĩnh vực nghiên cứu')
    x_study_school_id = fields.Many2one('hr.study.school', string='Trường học')

    _sql_constraints = [
        ('x_code_uniq', 'unique (x_code, company_id)', 'The code of the employee must be unique per company!'),
    ]

    # @api.onchange('x_employee_type')
    # def onchange_fill_employee_code(self):
    #     if self.x_employee_type:
    #         year = fields.Date.today().year
    #         try:
    #             id = int(self.id)
    #         except:
    #             id = 0
    #         count = self.sudo().search_count([
    #             ('create_date', 'like', '%s-%s' % (year, '%')),
    #             ('x_employee_type', '=',  self.x_employee_type),
    #             ('id', '!=',  id),
    #         ])
    #         seq = str(count + 1)
    #         seq = '0' * (3 - len(seq)) + seq
    #         self.x_code = '%s%s-%s' % (
    #             'P' if self.x_employee_type == 'employee' else 'I',
    #             str(year)[2:],
    #             seq
    #         )


class EmployeeEmergency(models.Model):
    _name = 'hr.employee.emergency'
    _description = 'Employee emergency'
    _order = 'sequence asc, id asc'

    employee_id = fields.Many2one('hr.employee', 'Employee', copy=False)
    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char('Name', required=1)
    relation = fields.Char('Relationship')
    dob = fields.Date('Date of birth')
    phone = fields.Char('Phone')


class EmployeeDepend(models.Model):
    _name = 'hr.employee.depend'
    _description = 'Employee dependant'
    _order = 'sequence asc, id asc'

    employee_id = fields.Many2one('hr.employee', 'Employee', copy=False)
    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char('Name', required=1)
    relation = fields.Char('Relationship')
    dob = fields.Date('Date of birth')
    tax_number = fields.Char('Tax number')
    is_depend = fields.Boolean('Là người phụ thuộc')
    mobile_phone = fields.Char('Số điện thoại')


class HrDepartmentBlock(models.Model):
    _name = 'hr.department.block'
    _description = 'Department block'

    name = fields.Char('Name', required=1)


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    x_block_id = fields.Many2one('hr.department.block', 'Block')

    _sql_constraints = [
        ('name_uniq', 'unique (name, company_id)', 'The name of the department must be unique per company!'),
    ]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _("%s (copy)") % (self.name or '')
        return super(HrDepartment, self).copy(default)


class HrJobMission(models.Model):
    _name = 'hr.job.mission'
    _description = 'Position mission'
    _order = 'sequence asc, id asc'

    name = fields.Char('Name', required=1)
    content = fields.Text('Content')
    job_id = fields.Many2one('hr.job', 'Position')
    sequence = fields.Integer('Sequence', default=1)


class HrJobRequire(models.Model):
    _name = 'hr.job.require'
    _description = 'Position require'
    _order = 'sequence asc, id asc'

    name = fields.Char('Name', required=1)
    content = fields.Text('Content')
    job_id = fields.Many2one('hr.job', 'Position')
    sequence = fields.Integer('Sequence', default=1)


class HrJob(models.Model):
    _inherit = 'hr.job'

    department_id = fields.Many2one('hr.department', string='Department', ondelete='restrict',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    x_mission_ids = fields.One2many('hr.job.mission', 'job_id', 'Missions', copy=1)
    x_require_ids = fields.One2many('hr.job.require', 'job_id', 'Requires', copy=1)
    x_responsible_id = fields.Many2one('hr.job', 'Responsible')
    x_work_location = fields.Char('Work location')

    def get_job_description(self):
        self.ensure_one()
        template = DocxTemplate(os.path.dirname(os.path.realpath(__file__)) + '/../report/templates/JD.docx')

        template.render({
            'name': self.name,
            'description': self.description,
            'department': self.department_id.name,
            'responsible': self.x_responsible_id.name,
            'work_location': self.x_work_location,
            'missions': [{'name': i.name, 'content': i.content.replace('\t', '    ') or ''} for i in self.x_mission_ids],
            'requires': [{'name': i.name, 'content': i.content.replace('\t', '    ') or ''} for i in self.x_require_ids],
        })
        stream = BytesIO()
        template.save(stream)
        data = stream.getvalue()
        attachment_id = self.env['ir.attachment'].create({
            'name': 'JD %s.docx' % self.name,
            'datas': base64.b64encode(data),
            'type': 'binary',
            'res_model': self._name,
        })
        return attachment_id
