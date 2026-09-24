# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import UserError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'
    _order = 'id desc'

    x_experience =fields.Char('Kinh nghiệm')
    x_dob = fields.Date('Date of birth')
    x_eval_overall = fields.Selection([
        ('1', 'Unsatisfactory'),
        ('2', 'Satisfactory'),
        ('3', 'Outstanding'),
    ], 'Overall impression')
    x_eval_overall_note = fields.Text('Overall impression note')
    x_eval_degree = fields.Selection([
        ('1', 'Unsatisfactory'),
        ('2', 'Satisfactory'),
        ('3', 'Outstanding'),
    ], 'Qualifications')
    x_eval_degree_note = fields.Text('Qualifications note')
    x_eval_experience = fields.Selection([
        ('1', 'Unsatisfactory'),
        ('2', 'Satisfactory'),
        ('3', 'Outstanding'),
    ], 'Experience')
    x_eval_experience_note = fields.Text('Experience note')
    x_eval_language = fields.Selection([
        ('1', 'Unsatisfactory'),
        ('2', 'Satisfactory'),
        ('3', 'Outstanding'),
    ], 'Language and Communication')
    x_eval_language_note = fields.Text('Language and Communication note')
    x_eval_motivation = fields.Selection([
        ('1', 'Unsatisfactory'),
        ('2', 'Satisfactory'),
        ('3', 'Outstanding'),
    ], 'Motivation')
    x_eval_motivation_note = fields.Text('Motivation note')
    x_interview_result = fields.Selection([
        ('4', 'Pending'),
        ('3', 'Not come'),
        ('2', 'A strong candidate, move to next round'),
        ('1', 'A possible candidate, application for filing'),
        ('0', 'Of no further interest'),
    ], 'Interview results')

    x_employment_status = fields.Selection([
        ('1', 'Agree'),
        ('2', 'Refuse'),
        ('3', 'Consider')
    ], string='Employment Status')
    recruit_rq_id = fields.Many2one('hr.recruit.request', 'Recruitment request')
    x_certificate =fields.Selection([
        ('graduate', 'Tốt nghiệp'),
        ('bachelor', 'Cử nhân'),
        ('intermediate', 'Trung cấp'),
        ('doctor', 'Tiến sĩ'),
        ('university', 'Đại học'),
        ('engineer', 'Kĩ sư'),
        ('master', 'Thạc sĩ'),
        ('diploma', 'Cao đẳng'),
        ('other', 'Khác'),
    ], 'Cấp chứng chỉ', default='other')
    x_state_id =fields.Many2one('res.country.state',string='Quê quán')
    x_submission_date =fields.Date('Ngày nộp hồ sơ',default=fields.Date.today())

    x_study_field_id = fields.Many2one('hr.study.field', string='Lĩnh vực nghiên cứu')
    x_study_school_id = fields.Many2one('hr.study.school', string='Trường học')
    x_training_form = fields.Selection([
        ('1', 'Chính quy'),
        ('2', 'Khác'),
        ('3', 'Tại chức'),
        ('4', 'Dạy nghề'),
    ], string='Hình thức đào tạo')

    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.display_name
            else:
                if not applicant.partner_name:
                    raise UserError(_('You must define a Contact Name for this applicant.'))
                new_partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'type': 'private',
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile,
                })
                applicant.partner_id = new_partner_id
                address_id = new_partner_id.address_get(['contact'])['contact']
            if applicant.partner_name or contact_name:
                employee_data = {
                    'default_x_cv_code': applicant.id,
                    'default_name': applicant.partner_name or contact_name,
                    'default_job_id': applicant.job_id.id,
                    'default_job_title': applicant.job_id.name,
                    'address_home_id': address_id,
                    'default_department_id': applicant.department_id.id or False,
                    'default_address_id': applicant.company_id and applicant.company_id.partner_id
                                          and applicant.company_id.partner_id.id or False,
                    'default_work_email': applicant.department_id and applicant.department_id.company_id
                                          and applicant.department_id.company_id.email or False,
                    'default_work_phone': applicant.department_id.company_id.phone,
                    'form_view_initial_mode': 'edit',
                    'default_applicant_id': applicant.ids,
                    'default_certificate':applicant.x_certificate,
                    'default_mobile_phone': applicant.partner_mobile,
                    'default_x_has_degree': True if applicant.type_id.id else False,
                    'default_birthday': applicant.x_dob,
                    'default_country_id': applicant.x_state_id.country_id.id if applicant.x_state_id and applicant.x_state_id.country_id else False,
                    'default_x_study_field_id': applicant.x_study_field_id.id if applicant.x_study_field_id else False,
                    'default_x_study_school_id': applicant.x_study_school_id.id if applicant.x_study_school_id else False,
                    'default_x_training_form': applicant.x_training_form
                }

        dict_act_window = self.env['ir.actions.act_window']._for_xml_id('hr.open_view_employee_list')
        dict_act_window['context'] = employee_data
        return dict_act_window