# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class CodeMoney(models.Model):
    _name = 'code.money'
    _description = 'Mã khoản tiền'

    group_money = fields.Selection([
        ('revenue', 'Khoản thu'),
        ('cost', 'Chi phí'),
        ('saved_money', 'Tiền gửi tiết kiệm'),
    ], string='Nhóm khoản tiền', required=True, default='revenue')
    content = fields.Char(string='Nội dung')
    code_money = fields.Char(string='Mã khoản tiền', required=True)

    _sql_constraints = [
        ('code_money', 'UNIQUE(code_money)', 'Mã khoản tiền không được trùng lặp')
    ]

    def name_get(self):
        res = []
        for record in self:
            name = record.code_money
            if record.content:
                name = '(' + name + ')' + record.content
            res.append((record.id, name))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        if name:
            args += ['|', ('code_money', operator, name),
                     ('content', operator, name)]
            return self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return super(CodeMoney, self)._name_search(name, args, operator, limit, name_get_uid)