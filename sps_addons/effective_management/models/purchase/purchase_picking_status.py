# -*- coding: utf-8 -*-

from datetime import timedelta, date, datetime
from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from reportlab import xrange
from odoo import fields, api, models, tools



class PurchasePickingStatus(models.Model):
    _name = 'purchase.picking.status'
    _description = 'Báo cáo giao hàng'

    master_key = fields.Integer('Master Key', index=True)
    classification = fields.Char('Phân loại')
    t1 = fields.Integer('Jan')
    t2 = fields.Integer('Feb')
    t3 = fields.Integer('Mar')
    t4 = fields.Integer('Apr')
    t5 = fields.Integer('May')
    t6 = fields.Integer('Jun')
    t7 = fields.Integer('Jul')
    t8 = fields.Integer('Aug')
    t9 = fields.Integer('Sep')
    t10 = fields.Integer('Oct')
    t11 = fields.Integer('Nov')
    t12 = fields.Integer('Dec')
    total = fields.Integer('Tổng cộng', compute='compute_amount')
    rate = fields.Float('Tỷ lệ (%)', compute='compute_amount')

    # def _prepare_value_month(self):
    #     vals = {}
    #     time_now = datetime.now()
    #     start_time = time_now - relativedelta(years=1)
    #     list_month = OrderedDict(
    #         ((start_time + timedelta(_)).strftime(r"%b-%y"), None) for _ in xrange((time_now - start_time).days)).keys()
    #     list_month = list(list_month)
    #     for v in range(1, 13):
    #         vals.update({'m%s' % (v): list_month[v]})
    #     return vals
    #
    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     label = self._prepare_value_month()
    #     res = super(PurchasePickingStatus, self).fields_view_get(view_id=view_id, view_type=view_type,
    #                                                                 toolbar=toolbar,
    #                                                                 submenu=submenu)
    #     if view_type == 'tree':
    #         fields = res.get('fields')
    #         if fields:
    #             res['fields']['t1']['string'] = label['m1']
    #             res['fields']['t2']['string'] = label['m2']
    #             res['fields']['t3']['string'] = label['m3']
    #             res['fields']['t4']['string'] = label['m4']
    #             res['fields']['t5']['string'] = label['m5']
    #             res['fields']['t6']['string'] = label['m6']
    #             res['fields']['t7']['string'] = label['m7']
    #             res['fields']['t8']['string'] = label['m8']
    #             res['fields']['t9']['string'] = label['m9']
    #             res['fields']['t10']['string'] = label['m10']
    #             res['fields']['t11']['string'] = label['m11']
    #             res['fields']['t12']['string'] = label['m12']
    #     return res

    def compute_amount(self):
        total_rate = 0.0
        for r in self:
            if r.classification == 'Số hạng mục đặt hàng':
                a = r.t1 + r.t2 + r.t3 + r.t4 + r.t5 + r.t6 + r.t7 + r.t8 + r.t9 + r.t10 + r.t11 + r.t12
                total_rate = a
                r.total = a
                r.rate = 100
            else:
                b = r.t1 + r.t2 + r.t3 + r.t4 + r.t5 + r.t6 + r.t7 + r.t8 + r.t9 + r.t10 + r.t11 + r.t12
                r.total = b
                r.rate = round((b/total_rate)*100,2) if total_rate !=0 else 100
