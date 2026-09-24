# -*- coding: utf-8 -*-
import base64
import datetime
import os
from datetime import date

import openpyxl
from openpyxl.styles import NamedStyle, Font, Side, PatternFill
from openpyxl.writer.excel import save_virtual_workbook
from six import BytesIO
from odoo.addons.num2currency import num999, num2word
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    display_date = fields.Date(string='Ngày', compute='_compute_display_date',
                                inverse='_inverse_display_date', store=True)
    project_state = fields.Selection([
        ('Ongoing', 'Ongoing'),
        ('Waiting for payment in time', 'Waiting for payment in time'),
        ('Waiting for payment out time', 'Waiting for payment out time'),
        ('Pending Payment', 'Pending Payment'),
        ('Remaining', 'Remaining'),
        ('Delay', 'Delay'),
        ('Done', 'Done'),
        ('Cancel', 'Cancel'),
    ], string='Trạng thái dự án', default='Ongoing', track_visibility="always")
    x_origin_so_id = fields.Many2one('sale.order', 'Báo giá gốc')
    expected_date = fields.Date('Ngày dự kiến nhận tiền')
    invoice_number = fields.Char('Số hóa đơn')
    invoice_date = fields.Date('Ngày xuất hóa đơn')
    advance_request_date = fields.Date('Ngày gửi hồ sơ tạm ứng')
    report_amount = fields.Float()
    x_deposit_time = fields.Selection([
        ('0', 'Thanh toán theo hóa đơn'),
        ('1', 'Đặt cọc lần 1'),
        ('2', 'Đặt cọc lần 2'),
        ('3', 'Đặt cọc lần 3'),
        ('4', 'Đặt cọc lần 4'),
        ('5', 'Đặt cọc lần 5'),
    ], string='Lần thanh toán', default='0')
    x_note = fields.Char('Ghi chú')
    x_approved_state = fields.Selection([
        ('wait_accountant', 'Chờ kế toán duyệt'),
        ('wait_bod', 'Chờ BOD duyệt'),
        ('approved', 'Đã duyệt')], string='Trạng thái duyệt', default=False, readonly=True, tracking=True)
    x_origin_advance_id = fields.Many2one('account.advance', 'Tạm ứng gốc', copy=False)
    x_origin_repay_id = fields.Many2one('account.advance.repay', 'Hoàn ứng gốc', copy=False)
    x_origin_move_id = fields.Many2one('account.move', string='Hóa đơn gốc', copy=False)
    x_pay_cost = fields.Boolean('Khoản thu/chi khác', default=False)
    x_code_money = fields.Many2one('code.money', 'Mã khoản tiền')
    x_license_type = fields.Selection([
        ('tax', 'Thuế'),
        ('internal', 'Nội bộ ')], string='Phân loại chứng từ')
    x_total_line = fields.Float('Tổng cộng', compute="_compute_total_payment_line", store=True)
    x_total_project_repay = fields.Float('Tổng cộng', compute="_compute_total_project_repay")
    x_total_project_line = fields.Float('Tổng cộng', compute="_compute_total_project_line")
    x_receiver = fields.Char(string='Người nhận/nộp')
    x_address = fields.Char(string='Địa chỉ')
    x_payment_line_ids = fields.One2many('payment.line', 'payment_id', 'Chi tiết', copy=True)
    x_project_detail_ids = fields.One2many('project.detail', 'payment_id', 'Chi tiết dự án', copy=True)
    x_project_repay_ids = fields.One2many('project.repay.detail', 'payment_id', 'Hoàn ứng theo dự án', readonly=True,
                                          store=True)
    form_view_ref = fields.Char(compute='_compute_can_move_view')
    form_view_context = fields.Char(compute='_compute_can_move_view')
    x_number_invoice = fields.Char(
        string='Số hóa đơn',
        related='x_origin_move_id.x_number_invoice',
        readonly=True
    )
    x_date_sent = fields.Date(
        string='Ngày phát hành hóa đơn',
        related='x_origin_move_id.x_date_sent',
        readonly=True
    )
    x_amount_override = fields.Monetary(string="Override Amount", currency_field='currency_id',
                                        help="Override the computed amount.", tracking=True)
    time_draft = fields.Datetime()
    name_history = fields.Char(copy=False)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for record in self:
            if record.partner_id:
                record.x_address = record.partner_id.name
            else:
                record.x_address = ''

    @api.depends('x_project_detail_ids', 'x_project_detail_ids.amount_total', 'x_pay_cost', 'x_amount_override')
    @api.onchange('x_project_detail_ids', 'x_project_detail_ids.amount_total', 'x_pay_cost', 'x_amount_override')
    def _compute_total_project_line(self):
        for r in self:
            r.x_total_project_line = 0
            if not r.x_pay_cost:
                if r.x_project_detail_ids:
                    r.x_total_project_line = sum(line.amount_total for line in r.x_project_detail_ids)


    @api.depends('x_project_repay_ids', 'x_project_repay_ids.amount_repay', 'x_pay_cost', 'x_amount_override')
    @api.onchange('x_project_repay_ids', 'x_project_repay_ids.amount_repay', 'x_pay_cost', 'x_amount_override')
    def _compute_total_project_repay(self):
        for r in self:
            r.x_total_project_repay = 0
            if r.x_project_repay_ids:
                r.x_total_project_repay = sum(line.amount_repay for line in r.x_project_repay_ids)


    @api.onchange('x_payment_line_ids', 'x_payment_line_ids.amount', 'x_pay_cost', 'x_amount_override')
    def _compute_total_payment_line(self):
        for r in self:
            if r.x_amount_override and r.x_pay_cost and not r.x_payment_line_ids:
                r.x_total_line = 0
                continue

            if r.x_pay_cost:
                if r.x_payment_line_ids:
                    r.x_total_line = sum(line.amount for line in r.x_payment_line_ids)
                    r.amount = r.x_total_line
                else:
                    r.x_total_line = 0
                    r.amount = 0
            else:
                r.x_total_line = 0

    # @api.depends('x_project_detail_ids', 'x_project_repay_ids')
    # @api.onchange('x_project_detail_ids', 'x_project_repay_ids')
    # def _compute_total_project(self):
    #     for r in self:
    #         if r.x_project_detail_ids:
    #             r.x_total_project_line = sum(line.amount_total for line in r.x_project_detail_ids)
    #             advance_lines = self.x_project_detail_ids.advance_line_id
    #             project_details = self.x_project_detail_ids
    #             for i in range(len(advance_lines)):
    #                 advance_lines[i].amount = project_details[i].amount_total
    #             r.amount = r.x_total_project_line
    #         else:
    #             r.x_total_project_line = 0
    #         if r.x_project_repay_ids:
    #             r.x_total_project_repay = sum(line.amount_repay for line in r.x_project_repay_ids)
    #             r.amount = r.x_total_project_repay
    #         else:
    #             r.x_total_project_repay = 0
    #
    # @api.depends('x_payment_line_ids', 'x_payment_line_ids.amount')
    # @api.onchange('x_payment_line_ids', 'x_payment_line_ids.amount')
    # def compute_total_line(self):
    #     for r in self:
    #         if r.x_payment_line_ids:
    #             r.x_total_line = sum(line.amount for line in r.x_payment_line_ids)
    #             r.amount = sum(line.amount for line in r.x_payment_line_ids)
    #             r.write({'amount_total': r.amount})
    #             r.write({'amount_total_signed': r.amount})
    #         else:
    #             r.x_total_line = 0

    @api.depends('x_origin_move_id')
    def _compute_can_move_view(self):
        type_invocie = 'out_refund'
        for record in self:
            if record.x_origin_move_id.move_type == 'out_invoice':
                type_invocie = 'out_invoice'
            elif record.x_origin_move_id.move_type in ('in_invoice', 'in_refund'):
                type_invocie = 'vendor'
            record.form_view_ref = {
                'out_invoice': 'xaccount.view_move_form_inherit',
                'out_refund': 'account.view_move_form',
                'vendor': 'xaccount.view_move_form_vendor',
            }.get(type_invocie)
            record.form_view_context = {
                'out_invoice': 'out_invoice',
                'out_refund': 'out_refund',
                'vendor': 'in_invoice',
            }.get(type_invocie)

    @api.depends('date')
    def _compute_display_date(self):
        for r in self:
            if r.x_origin_so_id and not r.display_date:
                r.display_date = False
            else:
                r.display_date = r.date

    def _inverse_display_date(self):
        for r in self:
            if r.display_date:
                r.date = r.display_date

    def action_post(self):
        for r in self:
            if r.x_origin_so_id and not r.display_date:
                raise UserError('Bạn chưa điền ngày thanh toán')
        res = super().action_post()
        for r in self:
            if not r.x_code_money or not r.x_license_type:
                raise UserError('Bạn chưa điền thông tin mã khoản tiền hoặc phân loại chứng từ')
            if not r.journal_id.x_charge_user_id.id:
                raise UserError('Bạn chưa điền thông tin người phụ trách')
            if r.journal_id.x_charge_user_id.id != self.env.uid:
                raise UserError('Bạn không phải là người phụ trách của nguồn tiền %s' % (r.journal_id.name))
            if r.x_origin_repay_id and r.x_origin_repay_id.state == 'paid':
                self.x_origin_repay_id.sudo().write({'state': 'paid_done'})
            if r.x_origin_advance_id and r.x_origin_advance_id.state == 'bod_approved':
                self.x_origin_advance_id.sudo().write({'state': 'payment'})

        # Reconcile invoice in case payment created from invoice
        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
        for r in self:
            if not r.x_origin_move_id:
                continue
            to_reconcile = [x for x in r.x_origin_move_id.line_ids.filtered_domain(domain)]
            for payment, lines in zip(r, to_reconcile):
                if payment.state != 'posted':
                    continue

                payment_lines = payment.line_ids.filtered_domain(domain)
                for line in to_reconcile:
                    for account in payment_lines.account_id:
                        (payment_lines + line) \
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                            .reconcile()

        return res

    def _synchronize_from_moves(self, changed_fields):
        # if self.x_pay_cost:
        #     return
        payments_to_sync = self.browse()
        for r in self:
            if not r.x_pay_cost:
                payments_to_sync |= r
        return super(AccountPayment, payments_to_sync)._synchronize_from_moves(changed_fields)

    def _synchronize_to_moves(self, changed_fields):
        payments_to_sync = self.browse()
        for r in self:
            if not r.x_pay_cost:
                payments_to_sync |= r
        return super(AccountPayment, payments_to_sync)._synchronize_to_moves(changed_fields)

    def _prepare_move_line_default_vals_pay_cost(self, write_off_line_vals=None):
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                self.journal_id.display_name))

        # Compute amounts.
        write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
            write_off_amount_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = 0.0

        write_off_balance = self.currency_id._convert(
            write_off_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else:  # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }

        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name[
                '%s-%s' % (self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name or default_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.journal_id.default_account_id.id,
            },
        ]
        for r in self.x_payment_line_ids:
            line_vals_list.append(
                # Receivable / Payable.
                {
                    'name': default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': r.amount if self.payment_type == 'outbound' else 0,
                    'credit': r.amount if self.payment_type == 'inbound' else 0,
                    'partner_id': self.partner_id.id,
                    'account_id': r.account_id.id,
                })

        return line_vals_list

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        if self.x_pay_cost:
            return self._prepare_move_line_default_vals_pay_cost(write_off_line_vals)
        return super()._prepare_move_line_default_vals(write_off_line_vals)

    def unlink(self):
        for r in self:
            if r.x_origin_advance_id:
                r.x_origin_advance_id.sudo().write({'state': 'approved'})
            if r.x_origin_repay_id:
                r.x_origin_repay_id.sudo().write({'state': 'approved'})
        return super(AccountPayment, self).unlink()

    def get_job_description(self):
        time_now = self.date
        self.ensure_one()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '%s..%stemplates%sprint_account.xlsx' % (os.sep, os.sep, os.sep))
        ws = wb['Sheet1']
        sql = f'''
                    SELECT
                    aa.code,
                    payment_type,
                    ap.amount AS tien,
                    ap.x_receiver AS nguoi_nhan,
                    ap.x_address AS dia_chi,
                    rp.display_name AS ten,
                    am.ref,
                    SUM(aml.debit) debit,
                    SUM(aml.credit) credit,
                    ap.x_receiver,
                    ap.x_address,
                    ap.create_date :: DATE,
                    am.NAME 
                FROM
                    account_payment ap
                    LEFT JOIN account_move am ON ap.move_id = am.
                    ID LEFT JOIN account_move_line aml ON aml.move_id = am.
                    ID LEFT JOIN account_advance_repay aar ON ap.x_origin_repay_id = aar.id
                    LEFT JOIN res_users ru ON aar.employee_id = ru.ID 
                    LEFT JOIN res_partner rp ON ap.partner_id = rp.id
                    LEFT JOIN account_account aa on aa.id = aml.account_id
                WHERE
                    ap.ID = {self.id}
                GROUP BY aa.code,
                    payment_type,
                    ap.amount,
                    ap.x_receiver,
                    ap.x_address,
                    rp.NAME,
                    am.ref,
                    ap.x_receiver,
                    ap.x_address,
                    ap.create_date :: DATE,
                    am.NAME, 
                    rp.display_name
                ORDER BY credit
        '''
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()

        highlight = NamedStyle(name="highlight")
        highlight.font = Font(name='Times New Roman', size=12)
        redFill = PatternFill(start_color='FFFFFF',
                              end_color='FFFFFF',
                              fill_type='solid')

        highlight1 = NamedStyle(name='highlight1')
        highlight1.font = Font(name='Times New Roman', size=12)
        highlight1.number_format = '#,##0'

        list_debit = {}
        list_credit = {}
        for r in recs:
            if r['debit'] > 0:
                list_debit[r['code']] = r['debit']
            if r['credit'] > 0:
                list_credit[r['code']] = r['credit']
            ws.cell(21, 1).value = "Hoàng Văn Phong"
            ws.cell(49, 1).value = "Hoàng Văn Phong"
            ws.cell(10, 2).value = r['dia_chi']
            ws.cell(38, 2).value = r['dia_chi']
            ws.cell(11, 2).value = r['ref']
            ws.cell(39, 2).value = r['ref']
            ws.cell(12, 2).value, ws.cell(12, 2).style = r['tien'], highlight1
            ws.cell(12, 3).value = ' VNĐ'
            ws.cell(40, 2).value, ws.cell(40, 2).style = r['tien'], highlight1
            ws.cell(40, 3).value = ' VNĐ'
            ws.cell(13, 3).value = num2word(r['tien']) + ' đồng'
            ws.cell(41, 3).value = num2word(r['tien']) + ' đồng'
            ws.cell(4, 6).value = 'PHIẾU THU' if r['payment_type'] == 'inbound' else 'PHIẾU CHI'
            ws.cell(33, 6).value = 'PHIẾU THU' if r['payment_type'] == 'inbound' else 'PHIẾU CHI'
            ws.cell(37, 4).value = r['nguoi_nhan']
            ws.cell(9, 4).value = r['nguoi_nhan']
            ws.cell(5, 5).value = time_now
            ws.cell(34, 5).value = time_now
            ws.cell(21, 6).value = r['nguoi_nhan']
            ws.cell(49, 6).value = r['nguoi_nhan']
            ws.cell(21, 9).value = r['ten']
            ws.cell(49, 9).value = r['ten']
            ws.cell(15, 10).value = time_now
            ws.cell(43, 10).value = time_now
            ws.cell(7, 12).value = r['name']
            ws.cell(35, 12).value = r['name']
            ws.cell(21, 9).value = self.env.user.name
            ws.cell(49, 9).value = self.env.user.name
            ws.cell(9, 1).value = 'Họ và tên người nộp tiền: ' if r[
                                                                      'payment_type'] == 'inbound' else 'Họ và tên người nhận tiền: '
            ws.cell(37, 1).value = 'Họ và tên người nộp tiền: ' if r[
                                                                       'payment_type'] == 'inbound' else 'Họ và tên người nhận tiền: '
            ws.cell(11, 1).value = 'Lý do nộp: ' if r['payment_type'] == 'inbound' else 'Lý do chi:'
            ws.cell(39, 1).value = 'Lý do nộp: ' if r['payment_type'] == 'inbound' else 'Lý do chi:'
            ws.cell(16, 6).value = 'Người nộp tiền ' if r['payment_type'] == 'inbound' else 'Người nhận tiền'
            ws.cell(44, 6).value = 'Người nộp tiền ' if r['payment_type'] == 'inbound' else 'Người nhận tiền'
            ws.cell(23, 1).value = 'Đã nộp đủ số tiền (viết bằng chữ): ' if r[
                                                                                'payment_type'] == 'inbound' else 'Đã nhận đủ số tiền (viết bằng chữ): '
            ws.cell(51, 1).value = 'Đã nộp đủ số tiền (viết bằng chữ): ' if r[
                                                                                'payment_type'] == 'inbound' else 'Đã nhận đủ số tiền (viết bằng chữ): '

        if recs[0]['payment_type'] == 'inbound':
            column1 = 8
            column2 = 36
            check_column = True
            for a, b in list_debit.items():
                if check_column:
                    ws.cell(column1, 11).value, ws.cell(column1, 11).style, ws.cell(column1,
                                                                                    11).fill = 'Nợ', highlight, redFill
                ws.cell(column1, 12).value, ws.cell(column1, 12).style, ws.cell(column1,
                                                                                12).fill = a, highlight, redFill
                ws.cell(column1, 13).value, ws.cell(column1, 13).style, ws.cell(column1,
                                                                                13).fill = b, highlight1, redFill
                if column2:
                    ws.cell(column2, 11).value, ws.cell(column2, 11).style, ws.cell(column2,
                                                                                    11).fill = 'Nợ', highlight, redFill
                    check_column = False
                ws.cell(column2, 12).value, ws.cell(column2, 12).style, ws.cell(column2,
                                                                                12).fill = a, highlight, redFill
                ws.cell(column2, 13).value, ws.cell(column2, 13).style, ws.cell(column2,
                                                                                13).fill = b, highlight1, redFill
                column1 += 1
                column2 += 1
            check_column = True
            for x, y in list_credit.items():
                if check_column:
                    ws.cell(column1, 11).value, ws.cell(column1, 11).style, ws.cell(column1,
                                                                                    11).fill = 'Có', highlight, redFill
                ws.cell(column1, 12).value, ws.cell(column1, 12).style, ws.cell(column1,
                                                                                12).fill = x, highlight, redFill
                ws.cell(column1, 13).value, ws.cell(column1, 13).style, ws.cell(column1,
                                                                                13).fill = y, highlight1, redFill
                if check_column:
                    ws.cell(column2, 11).value, ws.cell(column2, 11).style, ws.cell(column2,
                                                                                    11).fill = 'Có', highlight, redFill
                    check_column = False
                ws.cell(column2, 12).value, ws.cell(column2, 12).style, ws.cell(column2,
                                                                                12).fill = x, highlight, redFill
                ws.cell(column2, 13).value, ws.cell(column2, 13).style, ws.cell(column2,
                                                                                13).fill = y, highlight1, redFill
                column1 += 1
                column2 += 1
        else:
            column1 = 8
            column2 = 36
            check_column = True
            for x, y in list_debit.items():
                if check_column:
                    ws.cell(column1, 11).value, ws.cell(column1, 11).style, ws.cell(column1,
                                                                                    11).fill = 'Nợ:', highlight, redFill
                ws.cell(column1, 12).value, ws.cell(column1, 12).style, ws.cell(column1,
                                                                                12).fill = x, highlight, redFill
                ws.cell(column1, 13).value, ws.cell(column1, 13).style, ws.cell(column1,
                                                                                13).fill = y, highlight1, redFill
                if check_column:
                    ws.cell(column2, 11).value, ws.cell(column2, 11).style, ws.cell(column2,
                                                                                    11).fill = 'Nợ:', highlight, redFill
                    check_column = False
                ws.cell(column2, 12).value, ws.cell(column2, 12).style, ws.cell(column2,
                                                                                12).fill = x, highlight, redFill
                ws.cell(column2, 13).value, ws.cell(column2, 13).style, ws.cell(column2,
                                                                                13).fill = y, highlight1, redFill
                column1 += 1
                column2 += 1
            check_column = True
            for a, b in list_credit.items():
                if check_column:
                    ws.cell(column1, 11).value, ws.cell(column1, 11).style, ws.cell(column1,
                                                                                    11).fill = 'Có:', highlight, redFill
                ws.cell(column1, 12).value, ws.cell(column1, 12).style, ws.cell(column1,
                                                                                12).fill = a, highlight, redFill
                ws.cell(column1, 13).value, ws.cell(column1, 13).style, ws.cell(column1,
                                                                                13).fill = b, highlight1, redFill
                if check_column:
                    ws.cell(column2, 11).value, ws.cell(column2, 11).style, ws.cell(column2,
                                                                                    11).fill = 'Có:', highlight, redFill
                    check_column = False
                ws.cell(column2, 12).value, ws.cell(column2, 12).style, ws.cell(column2,
                                                                                12).fill = a, highlight, redFill
                ws.cell(column2, 13).value, ws.cell(column2, 13).style, ws.cell(column2,
                                                                                13).fill = b, highlight1, redFill
                column1 += 1
                column2 += 1
        stream = BytesIO(save_virtual_workbook(wb))
        xls = stream.getvalue()

        attachment_id = self.env['ir.attachment'].create({
            'name': 'Mẫu in phiếu thu chi.xlsx',
            'datas': base64.b64encode(xls),
            'type': 'binary',
        })
        return attachment_id

    def action_send_approved(self):
        for r in self:
            r.x_approved_state = 'wait_accountant'

    def action_accountant_approved(self):
        for r in self:
            r.x_approved_state = 'wait_bod'

    def action_bod_approved(self):
        for r in self:
            r.x_approved_state = 'approved'

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['name'] = '/'
        res = super(AccountPayment, self).copy(default=default)
        if not self.x_origin_advance_id and not self.x_origin_repay_id and not self.x_origin_move_id and not self.x_origin_saving_id and not self.x_origin_so_id:
            return res
        else:
            default['x_payment_line_ids'] = False
            default['x_project_detail_ids'] = False
            return res

    def write(self, vals):
        # Cập nhật project details khi thay đổi amount
        if vals.get('x_amount_override') and not vals.get('amount'):
            vals['amount'] = vals['x_amount_override']
        elif vals.get('amount') and not vals.get('x_amount_override'):
            vals['x_amount_override'] = vals['amount']

        if len(self) == 1 and vals.get('amount') and self.x_origin_move_id and not self.x_pay_cost:
            self._update_project_details_proportion(vals['amount'])
            
        if len(self) == 1 and len(vals) > 0 and vals.get('journal_id') and self.move_id:
            journal_update = self.env['account.journal'].browse(vals['journal_id'])
            del vals['journal_id']
            self._cr.execute(
                f''' update account_move set journal_id = {journal_update.id} where id = {self.move_id.id}  ''')
            self._cr.execute(
                f''' update account_move_line set journal_id = {journal_update.id} where move_id = {self.move_id.id}  ''')
            if self.payment_type == 'inbound':
                self._cr.execute(f''' update account_move_line set account_id = {journal_update.default_account_id.id} 
                                        where move_id = {self.move_id.id} and debit > 0 ''')
            if self.payment_type == 'outbound':
                self._cr.execute(f''' update account_move_line set account_id = {journal_update.default_account_id.id} 
                                                        where move_id = {self.move_id.id} and credit > 0 ''')
            self.move_id.with_context(x_force_compute=True)._compute_name()
            return super(AccountPayment, self).write(vals)
        elif len(self) == 1 and len(vals) > 0 and vals.get('date') and self.move_id:
            self.move_id.with_context(x_force_compute=True)._compute_name()
            return super(AccountPayment, self).write(vals)
        else:
            return super(AccountPayment, self).write(vals)

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        res.move_id.name = '/'
        res.move_id._compute_name()
        
        # Tự động tính toán project details khi tạo payment cho invoice
        if res.x_origin_move_id and not res.x_pay_cost and not res.x_project_detail_ids:
            res._compute_project_details_from_invoice()
        
        return res

    def _compute_project_details_from_invoice(self):
        """Tự động tính toán project details từ invoice lines khi tạo payment"""
        self.ensure_one()
        if not self.x_origin_move_id:
            return
            
        # Lấy các invoice lines có project
        invoice_lines = self.x_origin_move_id.line_ids.filtered(
            lambda line: line.x_sale_project_id and 
            line.exclude_from_invoice_tab != True and 
            (line.credit > 0 if self.x_origin_move_id.move_type == 'out_invoice' else line.debit > 0)
        )
        
        if not invoice_lines:
            return
            
        # Gộp theo code_project
        project_amounts = {}
        # Map code_project -> set project.project id (để điền project_id khi 1:1)
        code_project_projects = {}
        for line in invoice_lines:
            project_id = line.x_sale_project_id.id
            if project_id not in project_amounts:
                project_amounts[project_id] = 0
            project_amounts[project_id] += line.price_total
            code_project_projects.setdefault(project_id, set())
            # Ưu tiên project trên invoice line, fallback về PO line (phiếu thanh toán PO
            # nhiều khi invoice line thiếu x_project_id nhưng dòng PO gốc vẫn có)
            proj = line.x_project_id or line.purchase_line_id.x_project_id
            if proj:
                code_project_projects[project_id].add(proj.id)
        
        # Tạo project details đã gộp
        project_amount_list = []
        for project_id, total_amount in project_amounts.items():
            # Tính số tiền theo tỷ lệ của payment so với tổng invoice
            amount_proportion = (self.amount / self.x_origin_move_id.amount_total) * total_amount
            project_amount_list.append((project_id, amount_proportion))

        currency = self.currency_id or self.company_id.currency_id
        if currency:
            raw_amounts = [amount for _, amount in project_amount_list]
            rounded_amounts = [currency.round(amount) for amount in raw_amounts]
            target_sum = currency.round(self.amount)
            rounded_sum = sum(rounded_amounts)
            if rounded_amounts:
                adjustment = target_sum - rounded_sum
                if adjustment:
                    rounded_amounts[-1] = currency.round(rounded_amounts[-1] + adjustment)
            final_amounts = rounded_amounts
        else:
            final_amounts = [amount for _, amount in project_amount_list]

        project_details = []
        for (project_id, _), amount in zip(project_amount_list, final_amounts):
            detail_vals = {
                'code_project': project_id,
                'amount_total': amount,
            }
            # Chỉ điền project_id khi code_project ứng đúng 1 project (1:1)
            proj_set = code_project_projects.get(project_id)
            if proj_set and len(proj_set) == 1:
                detail_vals['project_id'] = next(iter(proj_set))
            project_details.append((0, 0, detail_vals))

        if project_details:
            self.write({'x_project_detail_ids': project_details})

    def _update_project_details_proportion(self, new_amount):
        """Cập nhật project details theo tỷ lệ mới khi thay đổi amount"""
        self.ensure_one()
        if not self.x_project_detail_ids or not self.amount:
            return
            
        # Tính tỷ lệ thay đổi dựa trên amount hiện tại
        ratio = new_amount / self.amount
        
        # Cập nhật từng project detail theo tỷ lệ
        for detail in self.x_project_detail_ids:
            detail.amount_total = detail.amount_total * ratio

    def action_draft(self):
        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError('Bạn không đủ quyền hạn để thực hiện hành động này, hãy liên hệ với kế toán trưởng !')
        else:
            self.write({
                'time_draft':datetime.datetime.now(),
                'name_history':self.name
            })
            return super(AccountPayment, self).action_draft()


class PaymentLine(models.Model):
    _name = 'payment.line'
    x_sale_project_id = fields.Many2one('sale.order', string='Mã dự án chính')
    project_id = fields.Many2one('project.project', string='Mã dự án')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    cost_type_id = fields.Many2one('cost.type', string="Phân loại chi phí")
    payment_id = fields.Many2one('account.payment', 'Phiếu thanh toán')
    partner_id = fields.Many2one('res.partner', 'Đối tác')
    content = fields.Char('Nội dung')
    tax_percent = fields.Float(string="Thuế (%)")
    amount = fields.Float('Số tiền')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)


class ProjectDetail(models.Model):
    _name = 'project.detail'
    _description = 'Chi tiết dự án'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    payment_id = fields.Many2one('account.payment', 'Phiếu thanh toán')
    code_project = fields.Many2one('sale.order', 'Mã dự án chính')
    project_id = fields.Many2one('project.project', string='Mã dự án')
    cost_type_id = fields.Many2one('cost.type', string="Phân loại chi phí")
    tax_percent = fields.Float(string="Thuế (%)")
    amount_total = fields.Float(string='Số tiền', tracking=True)
    advance_line_id = fields.Many2one('account.advance.line', string='Advance Lines')

    def write(self, vals):
        super().write(vals)
        if set(vals) & set(self._get_tracked_fields()):
            self._track_changes(self.payment_id)
        return super(ProjectDetail, self).write(vals)

    def _track_changes(self, field_to_track):
        if self.message_ids:
            message_id = field_to_track.message_post(
                body=f'{self._description}: {self.code_project.name}').id
            trackings = self.env['mail.tracking.value'].sudo().search(
                [('mail_message_id', '=', self.message_ids[0].id)])
            for tracking in trackings:
                tracking.copy({'mail_message_id': message_id})


class ProjectRepayDetail(models.Model):
    _name = 'project.repay.detail'
    _description = 'Hoàn ứng theo dự án'

    payment_id = fields.Many2one('account.payment', 'Phiếu thanh toán')
    main_project = fields.Many2one('sale.order', 'Mã dự án chính')
    amount_repay = fields.Float(string='Số tiền')


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    x_origin_move = fields.Many2one('account.move', string='Hóa đơn gốc')
    x_note = fields.Char('Ghi chú')

    @api.depends('company_id', 'source_currency_id')
    def _compute_journal_id(self):
        for wizard in self:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', wizard.company_id.id),
                ('name', '=', 'TCB')
            ]
            journal = None
            if wizard.source_currency_id:
                journal = self.env['account.journal'].search(
                    domain + [('currency_id', '=', wizard.source_currency_id.id)], limit=1)
            if not journal:
                journal = self.env['account.journal'].search(domain, limit=1)
            if not journal:
                journal = self.env['account.journal'].search(
                    [('type', 'in', ('bank', 'cash')), ('company_id', '=', wizard.company_id.id)], limit=1)
            wizard.journal_id = journal


    def default_get(self, fields_list):
        res = super(AccountPaymentRegister, self).default_get(fields_list)
        active_ids = self._context.get('active_ids', [])
        if self._context.get('active_model') == 'account.move' and len(active_ids) == 1:
            move = self.env['account.move'].browse(active_ids)
            res['x_origin_move'] = move.id
            res['x_note'] = move.x_note or ''
        return res

    def _create_payment_vals_from_wizard(self):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_id': self.payment_method_id.id,
            'destination_account_id': self.line_ids[0].account_id.id,
            'x_origin_move_id': self.x_origin_move.id,
            'x_note': self.x_note,
            'x_license_type': self.x_origin_move and self.x_origin_move.x_license_type or False,
            'x_amount_override': self.amount,
        }

        if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
            payment_vals['write_off_line_vals'] = {
                'name': self.writeoff_label,
                'amount': self.payment_difference,
                'account_id': self.writeoff_account_id.id,
            }
        return payment_vals

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)

        to_reconcile = []
        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            payment_vals_list = [payment_vals]
            to_reconcile.append(batches[0]['lines'])
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

            payment_vals_list = []
            for batch_result in batches:
                payment_vals_list.append(self._create_payment_vals_from_batch(batch_result))
                to_reconcile.append(batch_result['lines'])

        payments = self.env['account.payment'].create(payment_vals_list)
        return payments


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    def create(self, vals_list):
        res = super(AccountPartialReconcile, self).create(vals_list)

        # Commit ngay sau khi tạo reconcile để SQL có thể thấy dữ liệu
        self._cr.commit()

        # Lấy danh sách payment_id từ các reconcile vừa tạo
        affected_payments = set()
        for re in res:
            # Lấy payment_id từ debit_move_id
            if re.debit_move_id.payment_id:
                affected_payments.add(re.debit_move_id.payment_id.id)

            # Lấy payment_id từ credit_move_id
            if re.credit_move_id.payment_id:
                affected_payments.add(re.credit_move_id.payment_id.id)

        # Xử lý từng payment bị ảnh hưởng
        for payment_id in affected_payments:

            sql = '''
                WITH project_lines AS (
                    SELECT
                        apr.id AS reconcile_id,
                        apr.amount AS reconcile_amount,
                        COALESCE(aml3.x_sale_project_id, aml4.x_sale_project_id) AS sale_project_id,
                        COALESCE(aml3.x_project_id, pol3.x_project_id, aml4.x_project_id, pol4.x_project_id) AS project_id,
                        COALESCE(aml3.credit, aml4.debit, 0) AS project_line_amount
                    FROM account_partial_reconcile apr
                    LEFT JOIN account_move_line aml ON aml.id = apr.debit_move_id
                    LEFT JOIN account_payment ap ON ap.id = aml.payment_id
                    LEFT JOIN account_move am ON am.id = aml.move_id AND ap.id IS NULL
                    LEFT JOIN account_move_line aml3 ON aml3.move_id = am.id AND aml3.exclude_from_invoice_tab IS NOT TRUE AND aml3.credit > 0
                    LEFT JOIN purchase_order_line pol3 ON pol3.id = aml3.purchase_line_id
                    LEFT JOIN account_move_line aml2 ON aml2.id = apr.credit_move_id
                    LEFT JOIN account_payment ap2 ON ap2.id = aml2.payment_id
                    LEFT JOIN account_move am2 ON am2.id = aml2.move_id AND ap2.id IS NULL
                    LEFT JOIN account_move_line aml4 ON aml4.move_id = am2.id AND aml4.exclude_from_invoice_tab IS NOT TRUE AND aml4.debit > 0
                    LEFT JOIN purchase_order_line pol4 ON pol4.id = aml4.purchase_line_id
                    WHERE COALESCE(ap.id, ap2.id) = %s
                      AND COALESCE(aml3.x_sale_project_id, aml4.x_sale_project_id) IS NOT NULL
                ),
                project_totals AS (
                    SELECT
                        reconcile_id,
                        SUM(project_line_amount) AS total_line_amount
                    FROM project_lines
                    GROUP BY reconcile_id
                )
                SELECT
                    %s AS payment_id,
                    pl.sale_project_id,
                    CASE WHEN COUNT(DISTINCT pl.project_id) FILTER (WHERE pl.project_id IS NOT NULL) = 1
                         THEN MAX(pl.project_id) FILTER (WHERE pl.project_id IS NOT NULL)
                         ELSE NULL END AS project_id,
                    SUM(pl.reconcile_amount * pl.project_line_amount / NULLIF(pt.total_line_amount, 0)) AS amount_reconcile
                FROM project_lines pl
                JOIN project_totals pt ON pt.reconcile_id = pl.reconcile_id
                GROUP BY pl.sale_project_id
                ORDER BY pl.sale_project_id
                '''
            self._cr.execute(sql, (payment_id, payment_id))
            recs = self._cr.dictfetchall()

            if recs:
                # Kiểm tra payment có thỏa mãn điều kiện xử lý không
                payment = self.env['account.payment'].sudo().browse(payment_id)
                if payment.x_project_detail_ids and payment.x_origin_advance_id:
                    # Bỏ qua payment có cả x_origin_advance_id và x_project_detail_ids
                    continue

                # Update x_project_detail_ids from reconcile summary
                lists = [(5, 0)]  # Clear existing lines
                raw_amounts = [r['amount_reconcile'] for r in recs]
                currency = payment.currency_id or payment.company_id.currency_id
                if currency:
                    rounded_amounts = [currency.round(amount) for amount in raw_amounts]
                    target_sum = currency.round(sum(raw_amounts))
                    rounded_sum = sum(rounded_amounts)
                    if rounded_amounts:
                        adjustment = target_sum - rounded_sum
                        if adjustment:
                            rounded_amounts[-1] = currency.round(rounded_amounts[-1] + adjustment)
                    values_to_use = rounded_amounts
                else:
                    values_to_use = raw_amounts

                for r, amount in zip(recs, values_to_use):
                    detail_vals = {
                        'code_project': r['sale_project_id'],
                        'amount_total': amount
                    }
                    # Chỉ điền project_id khi reconcile suy ra đúng 1 project (1:1)
                    if r.get('project_id'):
                        detail_vals['project_id'] = r['project_id']
                    lists.append((0, 0, detail_vals))
                payment.update({'x_project_detail_ids': lists})

        return res


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    x_charge_user_id = fields.Many2one('res.users', 'Người phụ trách')
    code = fields.Char(size=6)

