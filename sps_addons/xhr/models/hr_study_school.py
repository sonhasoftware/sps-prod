from odoo import api, fields, models


class HrStudySchool(models.Model):
    _name = 'hr.study.school'

    name = fields.Char(string='Tên', required=1)

