# -*- coding: utf-8 -*-
from datetime import timedelta, date, datetime
from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from reportlab import xrange
from odoo import fields, api, models, tools


class SaleAnnual(models.Model):
    _name = 'sale.annual'
    _description = 'Báo cáo phân tích doanh số'

    master_key = fields.Integer('Master Key', index=True)
    classification = fields.Char('Phân loại')
    t1 = fields.Float()
    t2 = fields.Float()
    t3 = fields.Float()
    t4 = fields.Float()
    t5 = fields.Float()
    t6 = fields.Float()
    t7 = fields.Float()
    t8 = fields.Float()
    t9 = fields.Float()
    t10 = fields.Float()
    total = fields.Float('Total', compute='compute_amount')

    def _prepare_value_year(self):
        vals = {}
        time_now = datetime.now()
        context = self.env.context
        year = context.get('year')
        start_time =datetime(year, 1, 1)   if year else time_now - relativedelta(years=4)

        for years_diff in range(10):
            target_year = start_time.year + years_diff
            vals[f'm{years_diff + 1}'] = str(target_year)
        return vals

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        label = self._prepare_value_year()
        res = super(SaleAnnual, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                 toolbar=toolbar,
                                                                 submenu=submenu)
        if view_type == 'tree':
            fields = res.get('fields')
            if fields:
                res['fields']['t1']['string'] = label['m1']
                res['fields']['t2']['string'] = label['m2']
                res['fields']['t3']['string'] = label['m3']
                res['fields']['t4']['string'] = label['m4']
                res['fields']['t5']['string'] = label['m5']
                res['fields']['t6']['string'] = label['m6']
                res['fields']['t7']['string'] = label['m7']
                res['fields']['t8']['string'] = label['m8']
                res['fields']['t9']['string'] = label['m9']
                res['fields']['t10']['string'] = label['m10']

        return res

    def compute_amount(self):
        for r in self:
            r.total = r.t1 + r.t2 + r.t3 + r.t4 + r.t5 + r.t6 + r.t7 + r.t8 + r.t9 + r.t10