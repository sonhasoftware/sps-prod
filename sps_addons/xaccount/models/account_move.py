# -*- coding: utf-8 -*-
import math
import ast

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_gen_cost_percent = fields.Float('Chi phí quản lý chung (%)', default=0)
    x_gen_cost_tax_id = fields.Many2one('account.tax', 'Thuế chi phí quản lý chung',
                                        domain=[('type_tax_use', '=', 'sale')])
    x_note = fields.Char('Ghi chú')
    x_invoiced = fields.Boolean(string='Đã xuất hóa đơn')
    x_number_invoice = fields.Char(string='Số hóa đơn')
    x_order_id = fields.Many2one('sale.order', string='Số báo giá')
    investor_id = fields.Many2one('res.partner', related='x_order_id.x_investor_id')
    x_project_ids = fields.Many2many('project.project', 'project_invoice_ref', 'invoice_id', 'project_id',
                                     string='Mã dự án',context={'active_test': False,})
    x_date_created = fields.Datetime(string='Ngày tạo', readonly=True, default=fields.Date.context_today)
    x_date_sent = fields.Date(string='Ngày phát hành hóa đơn')
    x_payment_rules = fields.Many2one('account.payment.term', string='Điều khoản thanh toán')
    x_payment_term = fields.Date(string='Hạn thanh toán')
    x_check = fields.Boolean('Check', compute='_compute_check')
    x_payment_ids = fields.One2many('account.payment', 'x_origin_move_id', string='Phiếu thanh toán',
                                    compute='compute_payment', store=True)
    x_payment_count = fields.Integer(string='Số lượng PTT', compute='compute_payment')
    x_payment_latest_date = fields.Date('Ngày nhận tiền', compute='compute_payment_latest_date', store=True)
    x_license_type = fields.Selection([
        ('tax', 'Thuế'),
        ('internal', 'Nội bộ')
    ], string='Phân loại chứng từ', default='tax')
    x_product_sale_ids = fields.Many2many('product.product','product_sale_invoice_rel', string='Product')
    x_project_state = fields.Selection([
        ('Ongoing', 'Ongoing'),
        ('Waiting for payment in time', 'Waiting for payment in time'),
        ('Waiting for payment out time', 'Waiting for payment out time'),
        ('Pending Payment', 'Pending Payment'),
        ('Remaining', 'Remaining'),
        ('Delay', 'Delay'),
        ('Done', 'Done'),
        ('Cancel', 'Cancel'),
    ], string='Trạng thái dự án', default='Ongoing', track_visibility="always")
    account_receivable = fields.Float('Số dư công nợ', compute='compute_account_receivable')
    is_penalty_move = fields.Boolean(compute='_compute_penalty_move', store=True)

    @api.depends('invoice_line_ids','invoice_line_ids.product_id')
    def _compute_penalty_move(self):
        for rec in self:
            if any(product.is_penalty_fee for product in rec.invoice_line_ids.product_id):
                rec.is_penalty_move = True
            else:
                rec.is_penalty_move = False



    def action_view_account_receivable(self):
        self.ensure_one()
        account_move = self.env['account.move.line'].search(
            [('move_id.partner_id', '=', self.partner_id.id), ('move_id.state', '=', 'posted'),
             ('account_id.code', '=', '331')])
        return {
            'name': _('Công nợ NCC'),
            'view_mode': 'tree',
            'domain': [('id', 'in', account_move.ids)],
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',

        }

    def button_debt_collection(self):
        self.ensure_one()
        if self.account_receivable > 0:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Phiếu hoàn ứng'),
                'res_model': 'account.advance.repay',
                'view_mode': 'form',
                'target': 'current',  # Mở trong cửa sổ pop-up
                'context': {
                    'default_repay_type': 'supplier',
                    'default_supplier_id': self.partner_id.id,
                    'default_license_type': 'internal',
                    # Bạn có thể truyền thêm các giá trị mặc định khác nếu cần.
                },
            }

    @api.model
    def _search_default_journal(self, journal_types):
        company_id = self._context.get('default_company_id', self.env.company.id)
        domain = [('company_id', '=', company_id), ('type', 'in', journal_types)]

        journal = None
        if self._context.get('default_currency_id'):
            currency_domain = domain + [('currency_id', '=', self._context['default_currency_id'])]
            journal = self.env['account.journal'].search(currency_domain + [('name', '=', 'TCB')], limit=1)
            if not journal:
                journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain + [('name', '=', 'TCB')], limit=1)
            if not journal:
                journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            company = self.env['res.company'].browse(company_id)

            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        return journal

    def compute_account_receivable(self):
        for rec in self:
            account_receivable = 0
            sql = """
            SELECT 
                SUM(aml.debit) - SUM(aml.credit) AS balance
            FROM 
                account_move_line aml
            LEFT JOIN 
                account_move am ON aml.move_id = am.id
            LEFT JOIN 
                account_account aa ON aa.id = aml.account_id
            WHERE 
                am.partner_id = %s 
                AND am.state = 'posted' 
                AND aa.code = '331';
            """
            # Truyền giá trị rec.partner_id.id vào SQL
            self._cr.execute(sql, (rec.partner_id.id,))
            result = self._cr.dictfetchall()
            if result and result[0].get('balance') is not None:
                account_receivable = result[0]['balance']
            rec.account_receivable = account_receivable


    @api.onchange('x_order_id')
    def onchange_product_sale(self):
        product_ids=[]
        for r in self:
            if r.x_order_id and r.move_type =='out_invoice' :
                for line in r.x_order_id.order_line.filtered(lambda l: l.display_type != 'line_section'):
                    product_ids.append(line.product_id.id)
            r.x_product_sale_ids =[(6, 0, product_ids)]


    @api.depends('x_payment_ids','x_payment_ids.state')
    def compute_payment_latest_date(self):
        for r in self:
            if r.move_type != 'out_invoice':
                r.x_payment_latest_date = False
                continue
            confirmed_payments = r.x_payment_ids.filtered(lambda s: s.state == 'posted')
            if not confirmed_payments:
                r.x_payment_latest_date = False
                continue
            r.x_payment_latest_date = r.x_payment_ids.sorted(key='date', reverse=True)[0].date


    @api.depends('x_payment_ids')
    def compute_payment(self):
        for r in self:
            r.x_payment_count = len(r.x_payment_ids)

    def action_view_payment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_payments")
        payments = self.mapped('x_payment_ids')
        if len(payments) > 1:
            action['domain'] = [('id', 'in', payments.ids)]
        elif payments:
            form_view = [(self.env.ref('account.view_account_payment_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = payments.id
        if self._context.get('move_type') == 'out_invoice':
            action['context'] = dict(default_payment_type='inbound', default_partner_type='customer',
                                     search_default_inbound_filter=1)
        else:
            action['context'] = dict(default_payment_type='outbound', default_partner_type='supplier',
                                     search_default_outbound_filter=1)
        return action


    def so_add_x_project(self):
        # current_project_ids = self.x_project_ids.ids

        # chia lam 2 loai
        # loai 1 la xoa di
        # loai 2 la them vao

        move_lines = []

        # Loai 2 them vao
        for project_id in self.x_project_ids.filtered(lambda i: not i.main_project):
            if project_id.x_project_type == 'service':
                order_id = project_id.x_order_id
                for line in order_id.order_line:
                    if line.display_type == 'line_section':
                        continue
                    account_id = line.product_id.property_account_income_id.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ_id.id
                    move_lines.append((0, 0, {
                        'x_sale_project_id': self.x_order_id.id,
                        'product_id': line.product_id.id,
                        'name': line.product_id.name or '',
                        'account_id': account_id,
                        'x_project_id': project_id.ids[0],
                        'currency_id': line.currency_id.id,
                        'quantity': line.product_uom_qty or 1,
                        'x_price_unit_contract': line.price_unit,
                        'tax_ids': line.tax_id.ids,
                        'product_uom_id': line.product_uom,
                        'exclude_from_invoice_tab': False,
                        'sale_line_ids': [(6, 0, [line.id])]
                    }))
            elif project_id.x_project_type == 'operation':
                order_id = project_id.x_order_id
                for line in order_id.order_line:
                    if line.display_type == 'line_section':
                        continue
                    account_id = line.product_id.property_account_income_id.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ_id.id
                    move_lines.append((0, 0, {
                        'x_sale_project_id': self.x_order_id.id,
                        'product_id': line.product_id.id,
                        'name': line.product_id.name or '',
                        'account_id': account_id,
                        'x_project_id': project_id.ids[0],
                        'currency_id': line.currency_id.id,
                        'quantity': 1,
                        'x_price_unit_contract': line.price_unit,
                        'tax_ids': line.tax_id.ids,
                        'product_uom_id': line.product_uom,
                        'exclude_from_invoice_tab': False,
                        'sale_line_ids': [(6, 0, [line.id])]
                    }))
            else:
                order_line_id = project_id.x_order_line_id
                if not order_line_id:
                    raise UserError('Dự án bạn đang chọn không có dòng báo giá nào')
                account_id = order_line_id.product_id.property_account_income_id.id
                if not account_id:
                    account_id = order_line_id.product_id.categ_id.property_account_income_categ_id.id
                move_lines.append((0, 0, {
                    'x_sale_project_id': self.x_order_id.id,
                    'product_id': order_line_id.product_id.id,
                    'name': order_line_id.product_id.name or '',
                    'account_id': account_id,
                    'x_project_id': project_id.ids[0],
                    'currency_id': order_line_id.currency_id.id,
                    'quantity': 1,
                    'x_price_unit_contract': order_line_id.price_unit,
                    'tax_ids': order_line_id.tax_id.ids,
                    'product_uom_id': order_line_id.product_uom,
                    'exclude_from_invoice_tab': False,
                    'sale_line_ids': [(6, 0, [order_line_id.id])]
                }))


        if not move_lines:
            self.invoice_line_ids = False
        self.invoice_line_ids = move_lines
        self.invoice_line_ids.onchange_work()
        self._onchange_invoice_line_ids()
        self._onchange_recompute_dynamic_lines()
        self.onchange_order_id()

    @api.depends('x_project_ids')
    @api.onchange('x_project_ids')
    def onchange_x_project(self):
        current_project_ids = self._origin.x_project_ids.ids
        new_project_ids = self.x_project_ids.ids

        # chia lam 2 loai
        # loai 1 la xoa di
        # loai 2 la them vao

        move_lines = []

        # Loai 1 xoa di
        for project_id in self._origin.x_project_ids:
            if project_id.id not in new_project_ids:
                for line in self.invoice_line_ids:
                    if line.x_project_id.id == project_id.id:
                        move_lines.append((2, line.id))

        # Loai 2 them vao
        for project_id in self.x_project_ids:
            if project_id.id not in current_project_ids:
                if project_id.x_project_type == 'service':
                    order_id = project_id.x_order_id
                    for line in order_id.order_line:
                        if line.display_type == 'line_section':
                            continue
                        account_id = line.product_id.property_account_income_id.id
                        if not account_id:
                            account_id = line.product_id.categ_id.property_account_income_categ_id.id
                        move_lines.append((0, 0, {
                            'x_sale_project_id': self.x_order_id.id,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name or '',
                            'account_id': account_id,
                            'x_project_id': project_id.ids[0],
                            'currency_id': line.currency_id.id,
                            'quantity': line.product_uom_qty or 1,
                            'x_price_unit_contract': line.price_unit,
                            'tax_ids': line.tax_id.ids,
                            'product_uom_id': line.product_uom,
                            'exclude_from_invoice_tab': False,
                            'sale_line_ids': [(6, 0, [line.id])]
                        }))
                elif project_id.x_project_type == 'operation':
                    order_id = project_id.x_order_id
                    for line in order_id.order_line:
                        if line.display_type == 'line_section':
                            continue
                        account_id = line.product_id.property_account_income_id.id
                        if not account_id:
                            account_id = line.product_id.categ_id.property_account_income_categ_id.id
                        move_lines.append((0, 0, {
                            'x_sale_project_id': self.x_order_id.id,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name or '',
                            'account_id': account_id,
                            'x_project_id': project_id.ids[0],
                            'currency_id': line.currency_id.id,
                            'quantity': 1,
                            'x_price_unit_contract': line.price_unit,
                            'tax_ids': line.tax_id.ids,
                            'product_uom_id': line.product_uom,
                            'exclude_from_invoice_tab': False,
                            'sale_line_ids': [(6, 0, [line.id])]
                        }))
                else:
                    order_line_id = project_id.x_order_line_id
                    if not order_line_id:
                        raise UserError('Dự án bạn đang chọn không có dòng báo giá nào')
                    account_id = order_line_id.product_id.property_account_income_id.id
                    if not account_id:
                        account_id = order_line_id.product_id.categ_id.property_account_income_categ_id.id
                    move_lines.append((0, 0, {
                        'x_sale_project_id': self.x_order_id.id,
                        'product_id': order_line_id.product_id.id,
                        'name': order_line_id.product_id.name or '',
                        'account_id': account_id,
                        'x_project_id': project_id.ids[0],
                        'currency_id': order_line_id.currency_id.id,
                        'quantity': 1,
                        'x_price_unit_contract': order_line_id.price_unit,
                        'tax_ids': order_line_id.tax_id.ids,
                        'product_uom_id': order_line_id.product_uom,
                        'exclude_from_invoice_tab': False,
                        'sale_line_ids': [(6, 0, [order_line_id.id])]
                    }))

        # for project in self.x_project_ids:
        #     if project.x_project_type == 'service':
        #         order_id = project.x_order_id
        #         for line in order_id.order_line:
        #             if line.display_type == 'line_section':
        #                 continue
        #             account_id = line.product_id.property_account_income_id.id
        #             if not account_id:
        #                 account_id = line.product_id.categ_id.property_account_income_categ_id.id
        #             move_lines.append((0, 0, {
        #                 'x_sale_project_id': self.x_order_id.id,
        #                 'product_id': line.product_id.id,
        #                 'name': line.product_id.name or '',
        #                 'account_id': account_id,
        #                 'x_project_id': project.ids[0],
        #                 'currency_id': line.currency_id.id,
        #                 'quantity': line.product_uom_qty or 1,
        #                 'x_price_unit_contract': line.price_unit,
        #                 'tax_ids': line.tax_id.ids,
        #                 'product_uom_id': line.product_uom,
        #                 'exclude_from_invoice_tab': False,
        #                 'sale_line_ids': [(6, 0, [line.id])]
        #             }))
        #     elif project.x_project_type == 'operation':
        #         order_id = project.x_order_id
        #         for line in order_id.order_line:
        #             if line.display_type == 'line_section':
        #                 continue
        #             account_id = line.product_id.property_account_income_id.id
        #             if not account_id:
        #                 account_id = line.product_id.categ_id.property_account_income_categ_id.id
        #             move_lines.append((0, 0, {
        #                 'x_sale_project_id': self.x_order_id.id,
        #                 'product_id': line.product_id.id,
        #                 'name': line.product_id.name or '',
        #                 'account_id': account_id,
        #                 'x_project_id': project.ids[0],
        #                 'currency_id': line.currency_id.id,
        #                 'quantity': 1,
        #                 'x_price_unit_contract': line.price_unit,
        #                 'tax_ids': line.tax_id.ids,
        #                 'product_uom_id': line.product_uom,
        #                 'exclude_from_invoice_tab': False,
        #                 'sale_line_ids': [(6, 0, [line.id])]
        #             }))
        #     else:
        #         order_line_id = project.x_order_line_id
        #         if not order_line_id:
        #             raise UserError('Dự án bạn đang chọn không có dòng báo giá nào')
        #         account_id = order_line_id.product_id.property_account_income_id.id
        #         if not account_id:
        #             account_id = order_line_id.product_id.categ_id.property_account_income_categ_id.id
        #         move_lines.append((0, 0, {
        #             'x_sale_project_id': self.x_order_id.id,
        #             'product_id': order_line_id.product_id.id,
        #             'name': order_line_id.product_id.name or '',
        #             'account_id': account_id,
        #             'x_project_id': project.ids[0],
        #             'currency_id': order_line_id.currency_id.id,
        #             'quantity': 1,
        #             'x_price_unit_contract': order_line_id.price_unit,
        #             'tax_ids': order_line_id.tax_id.ids,
        #             'product_uom_id': order_line_id.product_uom,
        #             'exclude_from_invoice_tab': False,
        #             'sale_line_ids': [(6, 0, [order_line_id.id])]
        #         }))

        # if not move_lines:
        self.invoice_line_ids = False
        self.invoice_line_ids = move_lines
        self.invoice_line_ids.onchange_work()
        self._onchange_invoice_line_ids()
        self._onchange_recompute_dynamic_lines()
        self.onchange_order_id()

    @api.depends('invoice_date', 'x_payment_rules')
    @api.onchange('invoice_date', 'x_payment_rules')
    def onchange_x_payment_term(self):
        if self.invoice_date and self.x_payment_rules:
            number_day = sum(l.days for l in self.x_payment_rules.line_ids)
            date_term = self.invoice_date + relativedelta(days=number_day)
            self.x_payment_term = date_term

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.x_payment_rules = self.partner_id.property_payment_term_id

    @api.onchange('x_order_id')
    def _compute_check(self):
        for r in self:
            if r.move_type == 'out_invoice':
                r.x_gen_cost_percent = self.x_order_id.x_gen_cost_percent
                r.x_gen_cost_tax_id = self.x_order_id.x_gen_cost_tax_id.id
            if r.move_type in ('out_invoice', 'out_refund'):
                r.x_check = False
                for rec in r.invoice_line_ids:
                    if rec.sale_line_ids or rec.x_is_gen_cost:
                        rec.x_sale_project_id = r.x_order_id.id
            else:
                r.x_check = True
                for rec in r.invoice_line_ids:
                    if rec.purchase_line_id.id:
                        rec.x_sale_project_id = rec.purchase_line_id.x_project_id.x_order_id.id

    @api.depends('x_order_id', 'x_gen_cost_percent', 'x_gen_cost_tax_id', 'amount_untaxed', 'invoice_line_ids')
    @api.onchange('x_order_id', 'x_gen_cost_percent', 'x_gen_cost_tax_id', 'amount_untaxed', 'invoice_line_ids')
    def onchange_order_id(self):
        if self.move_type == 'out_invoice':
            amount_untaxed = 0
            default_product = ast.literal_eval(
                self.env['ir.config_parameter'].sudo().get_param('xaccount.gen_cost_default_product'))
            if not default_product:
                raise UserError('Chưa khai báo sản phẩm chi phí quản lý chung trên hệ thống ')
            cost_product = self.env['product.template'].sudo().browse(default_product)
            check_change_only_gen_cost = True
            for l in self.invoice_line_ids.filtered(lambda i: i.product_id.id != cost_product.id):
                if l.x_price_unit_contract != l._origin.x_price_unit_contract or l.x_work != l._origin.x_work or l.quantity != l._origin.quantity:
                    check_change_only_gen_cost = False
                amount_untaxed += l.x_price_unit_contract * l.x_work * 0.01 * l.quantity
            if self.invoice_line_ids.filtered(lambda i: i.product_id.id == cost_product.id):
                if 0 < self.x_gen_cost_percent < 100:
                    old_gen_cost = 0
                    new_gen_cost = 0
                    old_gen_cost_ids = self._origin.invoice_line_ids.filtered(lambda i: i.x_is_gen_cost)
                    if old_gen_cost_ids:
                        old_gen_cost = old_gen_cost_ids[0].x_price_unit_contract
                    new_gen_cost_ids = self.invoice_line_ids.filtered(lambda i: i.x_is_gen_cost)
                    if new_gen_cost_ids:
                        new_gen_cost = new_gen_cost_ids[0].x_price_unit_contract
                    gen_cost_id = self.invoice_line_ids.filtered(lambda i: i.product_id.id == cost_product.id)[0]
                    gen_cost_id.update({
                        'x_sale_project_id': self.x_order_id.id,
                        'x_is_gen_cost': True,
                        'product_id': cost_product.id,
                        'name': cost_product.name or '',
                        'currency_id': self.currency_id.id,
                        'product_uom_id': cost_product.uom_id.id,
                        'account_id': cost_product.categ_id.property_account_income_categ_id.id,
                        'x_price_unit_contract': (amount_untaxed * self.x_gen_cost_percent / (
                                    100 - self.x_gen_cost_percent) or 0) if ((
                                                                                         not new_gen_cost or old_gen_cost == new_gen_cost) or not check_change_only_gen_cost) else new_gen_cost,
                        'exclude_from_invoice_tab': False,
                        'tax_ids': self.x_gen_cost_tax_id.ids,
                    })
            elif 0 < self.x_gen_cost_percent < 100:
                line_vals = {
                    'x_sale_project_id': self.x_order_id.id,
                    'x_is_gen_cost': True,
                    'product_id': cost_product.id,
                    'name': cost_product.name or '',
                    'currency_id': self.currency_id.id,
                    'quantity': 1,
                    'x_work': 100,
                    'product_uom_id': cost_product.uom_id.id,
                    'account_id': cost_product.categ_id.property_account_income_categ_id.id,
                    'x_price_unit_contract': amount_untaxed * self.x_gen_cost_percent / (
                                100 - self.x_gen_cost_percent) or 0,
                    'exclude_from_invoice_tab': False,
                    'tax_ids': self.x_order_id.x_gen_cost_tax_id.ids,
                }

                new_line = self.env['account.move.line'].new(line_vals)
                self.invoice_line_ids += new_line

            self.invoice_line_ids.onchange_work()
            self.sudo()._onchange_invoice_line_ids()
            self.sudo()._onchange_recompute_dynamic_lines()

    def write(self, vals):
        if 'date' in vals:
            vals['name'] = '/'
        return super().write(vals)

    def _compute_name(self):
        moves2reject = self.env['account.move'].browse()
        force_compute = self._context.get('x_force_compute', False)
        for r in self:
            if not isinstance(r.id, int):
                continue
            if r.name and len(r.name) > 1:
                if not force_compute:
                    continue
            if not r.date:
                continue
            if r.move_type == 'in_invoice':
                r.name = self.env['ir.sequence'].next_by_code('xaccount.sequence_name_incoming_invoice', sequence_date=r.date)
                moves2reject |= r
            if r.payment_id:
                journal_type = r.journal_id.type
                if journal_type not in ['bank', 'cash']:
                    continue
                payment_id = r.payment_id
                sequence_code = ''
                if payment_id.payment_type == 'inbound':
                    sequence_code = 'xaccount.sequence_payment_cash_in_name' if journal_type == 'cash' else 'xaccount.sequence_payment_bank_in_name'
                if payment_id.payment_type == 'outbound':
                    sequence_code = 'xaccount.sequence_payment_cash_out_name' if journal_type == 'cash' else 'xaccount.sequence_payment_bank_out_name'
                if sequence_code == '':
                    continue
                time_post = datetime.now()
                if (r.payment_id.name_history and r.payment_id.date and r.payment_id.date.year == time_post.year
                        and r.payment_id.date.month == time_post.month):

                    r.name = r.payment_id.name_history
                else:
                    r.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=r.date)
                moves2reject |= r
        moves2super = self.filtered(lambda x: x.id not in moves2reject.ids)
        return super(AccountMove, moves2super)._compute_name()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'move_type' in res and res['move_type'] == 'in_refund':
            res['name'] = self.env['ir.sequence'].next_by_code('xaccount.sequence_name_incoming_reverse_invoice')
        return res

    def button_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id:
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        name = '/'
        self.write({'state': 'draft', 'is_move_sent': False, 'name':name})



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    x_number_bill = fields.Char(string="Số hóa đơn")
    x_date_bill = fields.Date(string="Ngày hóa đơn")
    x_cost_type_id = fields.Many2one('cost.type', string="Phân loại chi phí")
    x_is_gen_cost = fields.Boolean('dòng chi phí quản lý chung', default = False)
    x_price_unit_contract = fields.Float(string='Đơn giá hợp đồng')
    x_work = fields.Float(string='KL công việc (%)', default=100)
    x_project_id = fields.Many2one('project.project', string='Mã dự án')
    x_sale_project_id = fields.Many2one('sale.order', string='Mã dự án chính')
    is_penalty_move = fields.Boolean(related='product_id.is_penalty_fee', store=True)

    @api.depends('x_work', 'x_price_unit_contract')
    @api.onchange('x_work')
    def onchange_work(self):
        for r in self:
            r.price_unit = r.x_price_unit_contract * r.x_work * 0.01
            r._onchange_price_subtotal()
            r._onchange_mark_recompute_taxes()

    def _prepare_account_move_line(self, move=False):
        res = super(AccountMoveLine, self)._prepare_account_move_line()
        res['x_cost_type_id'] = self.x_cost_type_id.id
        return res

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMoveLine, self).default_get(fields_list)
        if self._context.get('order_id') and self._context.get('default_move_type') == 'out_invoice' :
            res['x_sale_project_id'] = self._context.get('order_id')
        return res

    @api.onchange('x_project_id')
    def onchange_project(self):
        for r in self:
            if r.x_project_id.x_order_line_id:
                r.product_id = r.x_project_id.x_order_line_id.product_id.id
