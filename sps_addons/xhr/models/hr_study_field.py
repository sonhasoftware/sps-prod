from odoo import api, fields, models


class HrStudyField(models.Model):
    _name = 'hr.study.field'

    name = fields.Char(string='Tên', required=1)

