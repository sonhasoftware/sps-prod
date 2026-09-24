# -*- coding: utf-8 -*-
from calendar import calendar,monthrange
from datetime import timedelta, datetime,date
from dateutil.relativedelta import relativedelta


from odoo import models, fields, api



class IrSequenceDateRange(models.Model):
    _inherit = 'ir.sequence.date_range'

    @api.model
    def create(self, vals_list):
        date_from = ''
        if isinstance(vals_list['date_from'], str):
                 date_from = datetime.strptime(vals_list['date_from'], "%Y-%m-%d").date()
        else:
                date_from =  vals_list['date_from']
        last_day = monthrange(date_from.year, date_from.month)
        date_to = date(date_from.year, date_from.month, last_day[1])
        vals_list['date_to'] = date_to
        return super().create(vals_list)


        # vals_list['date_to'] = vals_list['date_from'] + relativedelta(months=1)
        # return super().create(vals_list)
