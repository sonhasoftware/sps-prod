
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SalePaymentDeposit(models.TransientModel):
    _name = "sale.payment.deposit"
    _description = "Sales Payment Deposit"

    @api.model
    def _default_currency_id(self):
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id', False):
            sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
            return sale_order.currency_id

    @api.model
    def _default_journal_id(self):
        return self.env['account.journal'].search([('type' ,'in',('bank','cash'))],limit=1).id

    @api.model
    def _default_so_id(self):
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id', False):
            sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
            return sale_order.id

    so_id = fields.Many2one('sale.order' ,string='Số báo giá' , readonly=True,default=_default_so_id)
    advance_payment_method = fields.Selection([
        ('percentage', 'Tạm ứng theo %'),
        ('fixed', 'Tạm ứng theo số tiền')
        ], string='Phân loại', default='percentage', required=True,)
    deposit_time = fields.Selection([
        ('0', 'Thanh toán theo hóa đơn'),
        ('1', 'Tạm ứng lần 1'),
        ('2', 'Tạm ứng lần 2'),
        ('3', 'Tạm ứng lần 3'),
        ('4', 'Tạm ứng lần 4'),
        ('5', 'Tạm ứng lần 5'),
        ], string='Lần thanh toán', default='1', required=True)
    fixed_amount = fields.Monetary('Số tiền Tạm ứng')
    percentage = fields.Float('Tỷ lệ Tạm ứng', digits=(100,100) ,help="The percentage of amount to be invoiced in advance, taxes excluded.")
    percentage_amount = fields.Monetary('Số tiền Tạm ứng',compute='compute_percentage_amount')
    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency_id)
    note = fields.Char('Nội dung thanh toán')
    date = fields.Date('Ngày thanh toán', default=fields.date.today())
    journal_id = fields.Many2one("account.journal", string="Nguồn tiền", help="Taxes used for deposits" , default= _default_journal_id ,
                                 domain = [('type' ,'in',('bank','cash'))])

    @api.depends('percentage')
    @api.onchange('percentage')
    def compute_percentage_amount(self):
        self.ensure_one()
        if self.advance_payment_method == 'percentage' and self.percentage > 0:
            self.percentage_amount = self.so_id.amount_total * self.percentage / 100
        else:
            self.percentage_amount = 0

    def create_payment(self):
        self.ensure_one()
        payment_val = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'is_internal_transfer': False,
            'x_pay_cost': False,
            'partner_id': self.so_id.partner_id.id,
            'x_origin_so_id': self.so_id.id,
            'destination_account_id': self.so_id.partner_id.property_account_receivable_id.id,
            'ref': self.note,
            'journal_id': self.journal_id.id,
            'amount': self.fixed_amount if self.advance_payment_method == 'fixed' else self.percentage_amount,
            'x_amount_override': self.fixed_amount if self.advance_payment_method == 'fixed' else self.percentage_amount,
            'x_deposit_time':self.deposit_time
        }
        self.env['account.payment'].create(payment_val)
        if self._context.get('open_payment', False):
            return self.so_id.action_view_payment()
        return {'type': 'ir.actions.act_window_close'}
