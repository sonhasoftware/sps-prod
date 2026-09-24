# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.constrains('date_done')
    def update_po_state(self):
        self._cr.execute('update stock_picking set date_done=%s where id in %s', [
            datetime.now(),
            tuple(self.ids + [0, 0])
        ])
        self.env['purchase.order'].state_wait_license(self.ids)
        self.env['purchase.order'].state_done(self.ids)
        self.env['purchase.order'].state_to_late(self.ids)



