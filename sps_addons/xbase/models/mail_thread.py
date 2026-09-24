# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.base.models.ir_actions import IrActions as BaseIrActions
from odoo.exceptions import MissingError, AccessError
from collections import defaultdict


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_compute_author(self, author_id=None, email_from=None, raise_exception=True):
        return super(MailThread, self)._message_compute_author(author_id, email_from, raise_exception=False)
