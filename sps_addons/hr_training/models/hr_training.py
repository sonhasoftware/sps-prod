# -*- coding: utf-8 -*-
import os
import base64
from io import BytesIO
from docxtpl import DocxTemplate

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_TRAINING_REQUIRES = [
    ('0', '0'),
    ('25', '25'),
    ('50', '50'),
    ('75', '75'),
    ('100', '100'),
]


class HrTrainingResultLine(models.Model):
    _name = 'hr.training.result.line'
    _description = 'Training detail'

    training_item_id = fields.Many2one('hr.training.item', 'Training item', required=1)
    training_item_categ_id = fields.Many2one('hr.training.categ', 'Category', related='training_item_id.categ_id', store=1)
    type = fields.Selection([
        ('basic', 'Basic'),
        ('advance', 'Advance'),
    ], 'Type', required=True)
    trainer_id = fields.Many2one('hr.employee', 'Trainer')
    result = fields.Selection(_TRAINING_REQUIRES, 'Result', default='0', required=1)
    document_name = fields.Char('Document name (If any)')
    master_id = fields.Many2one('hr.training.result', 'Master ID', ondelete='cascade')
    trainee_id = fields.Many2one('hr.employee', 'Trainee', related='master_id.trainee_id', store=1)
    trainee_department_id = fields.Many2one('hr.department', "Trainee's department", related='trainee_id.department_id', store=1)
    project_id = fields.Many2one('project.project', 'Department / Project', related='master_id.project_id', store=1)
    date = fields.Date('Training date', related='master_id.date', store=1)
    note = fields.Text('Note')
    type_employee_train  = fields.Selection([
        ('in', 'Nội bộ'),
        ('out', 'Bên ngoài'),
    ], 'Loại người đào tạo', required=True)
    hr_employee_training_out_id = fields.Many2one('hr.employee.training.out',string='Người đào tạo bên ngoài')

    @api.onchange('training_item_id')
    def onchange_training_item_id(self):
        for rec in self:
            if rec.training_item_id.type:
                rec.type = rec.training_item_id.type


class HrTrainingResult(models.Model):
    _name = 'hr.training.result'
    _description = 'Training'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _rec_name = 'trainee_id'

    trainee_id = fields.Many2one('hr.employee', 'Trainee', tracking=1)
    trainee_job_id = fields.Many2one('hr.job', 'Trainee position', related='trainee_id.job_id')
    trainee_department_id = fields.Many2one('hr.department', 'Trainee department', related='trainee_id.department_id')
    project_id = fields.Many2one('project.project', 'From project')
    date = fields.Date('Training date', required=1, tracking=1)
    note = fields.Text('Note')
    lines = fields.One2many('hr.training.result.line', 'master_id', 'Results', copy=1)


    def get_docx_data(self):
        self.ensure_one()
        template = DocxTemplate(os.path.dirname(os.path.realpath(__file__)) + '/../report/templates/TrainingForm.docx')

        template.render({
            'trainee_name': self.trainee_id.name or '',
            'trainee_position': self.trainee_job_id.name or '',
            'trainee_department': self.trainee_department_id.name or '',
            'trainee_project': self.project_id.name or '',
            'details': [{
                'index': index + 1,
                'name': i.training_item_id.name,
                'type': i.type,
                'trainer_id': i.trainer_id.name,
                'date': self.date.strftime('%d-%m-%Y'),
                'document': i.document_name or ''
            } for index, i in enumerate(self.lines)],
        })
        stream = BytesIO()
        template.save(stream)
        data = stream.getvalue()
        attachment_id = self.env['ir.attachment'].create({
            'name': 'TrainingForm_%s_%s.docx' % (self.trainee_id.name, self.date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
            'datas': base64.b64encode(data),
            'type': 'binary',
            'res_model': self._name,
        })
        return attachment_id


class HrTrainingCategory(models.Model):
    _name = 'hr.training.categ'
    _description = 'Training Category'
    _order = 'sequence asc, id desc'

    name = fields.Char('name', required=True)
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence')
    type = fields.Selection([
        ('basic', 'Cơ bản'),
        ('advance', 'Nâng cao'),
    ], 'Loại đào tạo', default='basic')


class HrTrainingItemRequire(models.Model):
    _name = 'hr.training.item.require'
    _description = 'Training Item require'

    job_id = fields.Many2one('hr.job', 'Job position', required=1)
    job_department_id = fields.Many2one('hr.department')
    result_require = fields.Selection(_TRAINING_REQUIRES, 'Result require', default='0', required=1)
    item_id = fields.Many2one('hr.training.item', 'Training item')
    item_categ_id = fields.Many2one('hr.training.categ', 'Category', related='item_id.categ_id')


class HrTrainingItem(models.Model):
    _name = 'hr.training.item'
    _description = 'Training Item'
    _inherit = ['mail.thread']
    _order = 'sequence asc, id desc'

    name = fields.Char('Name', required=True, tracking=True)
    sequence = fields.Integer('Sequence')
    categ_id = fields.Many2one('hr.training.categ', 'Category', required=True, tracking=True)
    # jobs = fields.Many2many('hr.job', 'training_item_job_rel', 'item_id', 'job_id', 'Positions', tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, tracking=True)
    require_ids = fields.One2many('hr.training.item.require', 'item_id', 'Position requires', copy=1)
    type = fields.Selection([
        ('basic', 'Cơ bản'),
        ('advance', 'Nâng cao'),
    ], 'Loại đào tạo', related='categ_id.type')


class HrEmployeeTrainingOut(models.Model):
    _name = 'hr.employee.training.out'
    _rec_name = 'name'

    name = fields.Char('Tên', required=True, tracking=True)
    job_title = fields.Char('Chức danh công việc')
    phone = fields.Char('Điện thoại')
    email = fields.Char('Email')

