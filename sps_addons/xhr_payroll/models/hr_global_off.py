# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from dateutil.rrule import rrule, WEEKLY, SA
from datetime import datetime
class GlobalOff(models.Model):
    _name = 'hr.global.off'
    _inherit = ['mail.thread']
    _description = 'Global time off config'

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char('name', required=1, tracking=1)
    date_start = fields.Date('Start date', required=1, tracking=1)
    date_end = fields.Date('End date', required=1, tracking=1)
    number_of_days = fields.Float('Number of days', compute='compute_nghi_le', store=1)
    active = fields.Boolean('Active', default=1, tracking=1)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    saturdays = fields.Float('Số T7', compute='compute_nghi_le', store=True, readonly=False)

    @api.depends('date_start', 'date_end')
    def compute_nghi_le(self):
        for rec in self:
            rec.number_of_days = 0
            if rec.date_start and rec.date_end and rec.date_start <= rec.date_end:
                rec.number_of_days = (rec.date_end - rec.date_start).days + 1
                saturdays = list(rrule(WEEKLY, dtstart=rec.date_start, until=rec.date_end, byweekday=SA))
                rec.saturdays = len(saturdays)

    # @api.depends('date_start', 'date_end')
    # def compute_number_of_days(self):
    #     for r in self:
    #         if r.date_start and r.date_end:
    #             r.number_of_days = (r.date_end - r.date_start).days + 1
    #         else:
    #             r.number_of_days = 0
