# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrJob(models.Model):
    _inherit = 'hr.job'

    # x_training_items = fields.Many2many('hr.training.item', 'training_item_job_rel', 'job_id', 'item_id', 'Training items')
    x_training_items = fields.One2many('hr.training.item.require', 'job_id', 'Training items', copy=1)
