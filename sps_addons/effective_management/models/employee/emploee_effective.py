# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class EmployeeEffective(models.Model):
    _name = 'employee.effective.value'
    _description = 'Báo cáo hiệu quả nhân viên'
    _order = 'id'

    master_key = fields.Integer('Master Key', index=True)
    classification = fields.Char('Phân loại')
    name = fields.Char('Tên nhân viên')
    t1 = fields.Float('Jan')
    t2 = fields.Float('Feb')
    t3 = fields.Float('Mar')
    t4 = fields.Float('Apr')
    t5 = fields.Float('May')
    t6 = fields.Float('Jun')
    t7 = fields.Float('Jul')
    t8 = fields.Float('Aug')
    t9 = fields.Float('Sep')
    t10 = fields.Float('Oct')
    t11 = fields.Float('Nov')
    t12 = fields.Float('Dec')
    total = fields.Float('Total')

    def sort_by_classification(self, data):
        def extract_sort_key(item):
            s = item.get("classification", "")
            m = re.match(r"(\d+)", s)
            prefix = int(m.group(1)) if m else 999999
            return (prefix, s)
        return sorted(data, key=extract_sort_key)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                     orderby=orderby, lazy=lazy)
        res_sort = self.sort_by_classification(res)
        return res_sort