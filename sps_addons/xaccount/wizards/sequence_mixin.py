
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SequenceMixin(models.AbstractModel):
    _inherit = 'sequence.mixin'

    def _set_next_sequence(self):
        if self._name == 'account.move' and len(self) == 1 and (self.move_type == 'in_invoice' or self.payment_id):
            return
        return super(SequenceMixin, self)._set_next_sequence()
