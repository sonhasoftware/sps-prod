# -*- coding: utf-8 -*-
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class AccountSaving(models.Model):
    _name = 'account.saving'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tiền gửi tiết kiệm'
    _order = 'create_date desc'
    _rec_name = 'number_contract'

    date_sent = fields.Date(string='Ngày gửi', required=True, default=fields.Date.context_today)
    period = fields.Integer(string='Kỳ hạn', required=True)
    date_type = fields.Selection([
        ('year', 'Năm'),
        ('month', 'Tháng')
    ], string='Năm/Tháng', required=True, default='month')
    content = fields.Char(string='Nội dung')
    number_contract = fields.Char(string='Số hợp đồng', required=True)
    user_id = fields.Many2one('res.users', string='Người tạo', readonly=True, default=lambda self: self.env.user)
    diary_id = fields.Many2one('account.journal', string='Sổ nhật ký', required=True)
    bank_id = fields.Many2one('res.bank', string='Ngân hàng', readonly=True)
    code_money = fields.Many2one('code.money', string="Mã khoản tiền")
    license_type = fields.Selection([
        ('tax', 'Thuế'),
        ('internal', 'Nội bộ')
    ], string='Phân loại chứng từ', default='tax', required=True)
    value_deposits = fields.Float(string='Gía trị tiền gửi', required=True)
    interest_rate = fields.Float(string='Lãi suất(%/năm)', required=True)
    date_settlement = fields.Date(string='Ngày tất toán', required=True)
    amount_settlement = fields.Float(string='Số tiền tất toán')
    note = fields.Char(string='Ghi chú')
    method_settlement = fields.Selection([
        ('collect', 'Thu tiền về tài khoản'),
        ('renew_G', 'Tái tục tiền gốc'),
        ('renew_G&L', 'Tái tục cả gốc và lãi')
    ], string='Phương thức tất toán', required=True)
    account_deposit_id = fields.Many2one('account.account', string='Tài khoản tiền gửi', required=True)
    account_interest_id = fields.Many2one('account.account', string='Tài khoản lãi tiền gửi', required=True)
    payment_id = fields.Many2one('account.payment', string='Phiếu chi', copy=False, readonly=True)
    receipts_id = fields.Many2one('account.payment', string='Phiếu thu', copy=False, readonly=True)
    receipts_deposit_id = fields.Many2one('account.payment', string='Phiếu thu lãi', copy=False, readonly=True)
    renewals_id = fields.Many2one('account.saving', string='Phiếu tái tục', readonly=True, copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('official', 'Chính thức'),
        ('settled', 'Đã tất toán')
    ], string='Trạng thái', default="draft")

    _sql_constraints = [
        ('number_contract', 'UNIQUE(number_contract)', 'Số hợp đồng phải là duy nhất')
    ]

    @api.onchange('date_settlement', 'date_sent', 'interest_rate', 'value_deposits')
    def onc_amount_settlement(self):
        for r in self:
            if r.date_settlement and r.date_sent and r.interest_rate and r.value_deposits:
                r.amount_settlement = r.value_deposits + r.value_deposits * (
                            r.date_settlement - r.date_sent).days / 365 * r.interest_rate / 100
            else:
                r.amount_settlement = 0

    @api.depends('period', 'date_sent')
    @api.onchange('period', 'date_sent')
    def onc_date_settlement(self):
        for r in self:
            if r.period and r.date_sent:
                if r.date_type == 'month':
                    r.date_settlement = r.date_sent + relativedelta(months=+r.period)
                else:
                    r.date_settlement = r.date_sent + relativedelta(months=+(r.period * 12))
            else:
                r.date_settlement = False

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, number_contract=_("%s (Sao chep)") % (self.number_contract))
        return super(AccountSaving, self).copy(default)

    @api.onchange('diary_id')
    def onchange_account(self):
        for r in self:
            if r.diary_id:
                r.bank_id = r.diary_id.bank_account_id.bank_id.id

    def unlink(self):
        for r in self:
            if r.state == "draft":
                rtn = super(AccountSaving, self).unlink()
                return rtn
            else:
                raise UserError("Chỉ có thể xoá bản ghi ở trạng thái nháp")

    def action_done(self):
        payment_line = []
        for r in self:
            if r.period == 0:
                raise UserError("Kỳ hạn không thể = 0")
            payment_line.append((0, 0, {
                'account_id': r.account_deposit_id.id,
                'content': r.content,
                'amount': r.value_deposits
            }))
            payment_id = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'x_pay_cost': True,
                'journal_id': r.diary_id.id,
                # 'partner_bank_id': r.bank_id.id,
                'ref': r.content,
                'date': r.date_sent,
                'x_payment_line_ids': payment_line,
                'x_code_money': r.code_money.id,
                'x_license_type': r.license_type,
                'amount': r.value_deposits
            })
            payment_id.action_post()
            r.state = 'official'
            r.payment_id = payment_id.id

    def action_settlement(self):
        if self.date_settlement > fields.Date.today():
            raise ValidationError('Chưa đến kỳ hạn tất toán vui lòng thử lại sau.')
        payment_vals = {}
        payment_lines = []
        payment_vals_lai = {}
        payment_lines_lai = []
        for r in self:
            if r.method_settlement == 'collect':
                payment_lines.append((0, 0, {
                    'account_id': r.account_deposit_id.id,
                    'content': ('Tất toán tiền gốc theo hợp đồng gửi tiết kiệm số ' + r.number_contract),
                    'amount': r.value_deposits
                }))
                payment_lines_lai.append((0, 0, {
                    'account_id': r.account_interest_id.id,
                    'content': ('Tất toán tiền lãi theo hợp đồng gửi tiết kiệm số ' + r.number_contract),
                    'amount': r.amount_settlement - r.value_deposits
                }))
                payment_vals = {
                    'payment_type': 'inbound',
                    'x_pay_cost': True,
                    'journal_id': r.diary_id.id,
                    'ref': r.content,
                    'date': r.date_settlement,
                    'x_origin_saving_id': r.id,
                    'x_payment_line_ids': payment_lines,
                    'x_code_money': r.code_money.id,
                    'x_license_type': r.license_type,
                    'amount': r.value_deposits
                }
                payment_vals_lai = {
                    'payment_type': 'inbound',
                    'x_pay_cost': True,
                    'journal_id': r.diary_id.id,
                    'ref': r.content,
                    'date': r.date_settlement,
                    'x_origin_saving_id': r.id,
                    'x_payment_line_ids': payment_lines_lai,
                    'x_code_money': self.env['code.money'].search([('code_money', '=', 'RIN')]).id,
                    'x_license_type': r.license_type,
                    'amount': (r.amount_settlement - r.value_deposits)
                }
            if r.method_settlement == 'renew_G':
                payment_lines.append((0, 0, {
                    'account_id': r.account_deposit_id.id,
                    'content': r.number_contract,
                    'amount': r.value_deposits
                }))
                payment_lines_lai.append((0, 0, {
                    'account_id': r.account_interest_id.id,
                    'content': r.number_contract,
                    'amount': r.amount_settlement - r.value_deposits
                }))
                payment_vals = {
                    'payment_type': 'inbound',
                    'x_pay_cost': True,
                    'journal_id': r.diary_id.id,
                    'ref': r.content,
                    'x_origin_saving_id': r.id,
                    'date': r.date_settlement,
                    'x_payment_line_ids': payment_lines,
                    'x_code_money': r.code_money.id,
                    'x_license_type': r.license_type,
                    'amount': r.value_deposits
                }
                payment_vals_lai = {
                    'payment_type': 'inbound',
                    'x_pay_cost': True,
                    'journal_id': r.diary_id.id,
                    'ref': r.content,
                    'date': r.date_settlement,
                    'x_origin_saving_id': r.id,
                    'x_payment_line_ids': payment_lines_lai,
                    'x_code_money': self.env['code.money'].search([('code_money', '=', 'RIN')]).id,
                    'x_license_type': r.license_type,
                    'amount': (r.amount_settlement - r.value_deposits)
                }
                new = r.copy(default={'date_sent': datetime.today()})
                r.renewals_id = new.id
                new.onc_date_settlement()
            if r.method_settlement == 'renew_G&L':
                payment_lines.append((0, 0, {
                    'account_id': r.account_deposit_id.id,
                    'content': r.number_contract,
                    'amount': r.value_deposits
                }))
                payment_lines_lai.append((0, 0, {
                    'account_id': r.account_interest_id.id,
                    'content': r.number_contract,
                    'amount': r.amount_settlement - r.value_deposits
                }))
                payment_vals = {
                    'payment_type': 'inbound',
                    'x_pay_cost': True,
                    'journal_id': r.diary_id.id,
                    'ref': r.content,
                    'x_origin_saving_id': r.id,
                    'date': r.date_settlement,
                    'x_payment_line_ids': payment_lines,
                    'x_code_money': r.code_money.id,
                    'x_license_type': r.license_type,
                    'amount': r.value_deposits
                }
                payment_vals_lai = {
                    'payment_type': 'inbound',
                    'x_pay_cost': True,
                    'journal_id': r.diary_id.id,
                    'ref': r.content,
                    'date': r.date_settlement,
                    'x_origin_saving_id': r.id,
                    'x_payment_line_ids': payment_lines_lai,
                    'x_code_money': self.env['code.money'].search([('code_money', '=', 'RIN')]).id,
                    'x_license_type': r.license_type,
                    'amount': (r.amount_settlement - r.value_deposits)
                }
                new = r.copy(default={'date_sent': datetime.today(), 'value_deposits': r.amount_settlement})
                r.renewals_id = new.id
                new.onc_date_settlement()
                new.onc_amount_settlement()
            receipts_id = self.env['account.payment'].create(payment_vals)
            receipts_id.action_post()
            receipts_lai_id = self.env['account.payment'].create(payment_vals_lai)
            receipts_lai_id.action_post()
            r.state = 'settled'
            r.receipts_id = receipts_id.id
            r.receipts_deposit_id = receipts_lai_id.id


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    x_origin_saving_id = fields.Many2one('account.saving', string='phiếu gửi tiết kiệm')
    reconciled_invoices_count = fields.Integer(search='_search_reconciled_invoices', string='Số lượng đối soát')

    def _search_reconciled_invoices(self, operator, value):
        self._cr.execute('''
                         SELECT payment.id,
                                ARRAY_AGG(DISTINCT invoice.id) AS invoice_ids,
                                invoice.move_type
                         FROM account_payment payment
                                  JOIN account_move move ON move.id = payment.move_id
                                  JOIN account_move_line line ON line.move_id = move.id
                                  JOIN account_partial_reconcile part ON
                             part.debit_move_id = line.id
                                 OR
                             part.credit_move_id = line.id
                                  JOIN account_move_line counterpart_line ON
                             part.debit_move_id = counterpart_line.id
                                 OR
                             part.credit_move_id = counterpart_line.id
                                  JOIN account_move invoice ON invoice.id = counterpart_line.move_id
                                  JOIN account_account account ON account.id = line.account_id
                         WHERE account.internal_type IN ('receivable', 'payable')
                           AND line.id != counterpart_line.id
                AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                         GROUP BY payment.id, invoice.move_type
                         ''', )
        query_res = self._cr.dictfetchall()
        ids = []
        for res in query_res:
            if res['move_type'] in self.env['account.move'].get_sale_types(True):
                if res.get('invoice_ids', []):
                    ids.append(res['id'])

        return [('id', 'in', ids)]
