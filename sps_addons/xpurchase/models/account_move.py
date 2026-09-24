from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.constrains('payment_state')
    def check_state(self):
        po2update = self.env['purchase.order']
        for r in self:
            if r.payment_state is not False:
                self._cr.execute(f'''update account_move 
                                            set payment_state = '{r.payment_state}'
                                            where id = {r.id}''')

            for invoice_line_id in r.invoice_line_ids:
                po2update += invoice_line_id.purchase_line_id.order_id

            payment_id = self.env['account.payment'].search([('move_id', '=', r.id)])
            po2update += payment_id.x_origin_advance_id.po_id
            if po2update:
                for po2 in po2update:
                    po2.calculate_line_percent()
