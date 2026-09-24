# -*- coding: utf-8 -*-
import ast
import math
from calendar import monthrange
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_contract_status= fields.Selection([
        ('1', 'N/A'),
        ('2', 'Pending'),
        ('3', 'Yes'),
        ('4', 'Cancel'),
        ], string='Tình trạng hợp đồng', default='1')
    x_invoice_frequency = fields.Many2one('sale.frequency', string='Tần suất hóa đơn')
    x_payment_ids = fields.One2many('account.payment', 'x_origin_so_id', string='Phiếu đặt cọc')
    x_payment_count = fields.Integer('SL đặt cọc' , compute='compute_payment_count')
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
    x_is_warranty = fields.Boolean('Báo giá bảo hành')

    def compute_payment_count(self):
        payment_obj = self.env['account.payment']
        for r in self:
            r.x_payment_count = payment_obj.search_count([('x_origin_so_id', '=', r.id)])

    def action_view_payment(self):
        payments = self.mapped('x_payment_ids')
        return {
            'name': ('Các phiếu Tạm ứng/Đặt cọc'),
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payments.ids)],
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
        }

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('xaccount.view_move_form_inherit').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or
                                                   self.env['account.move'].default_get(
                                                       ['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action

    def check_line(self):
        for order in self:
            for line in order.order_line:
                if line.display_type == 'line_section' or not line.parent_id:
                    continue
                else:
                    self._cr.execute(f'''select * from sale_order_line where id != {line.id} and parent_id = {line.parent_id.id} and product_id ={line.product_id.id} and order_id = {line.order_id.id} ''')
                    res = self._cr.dictfetchall()
                if res:
                    raise ValidationError("Mỗi hạng mục tổng không được có trùng lặp hạng mục báo giá")
                else:
                    continue

    def compute_number_invoice(self):
        number_invoice = 0
        if self.work_time_unit == 'day' and self.x_invoice_frequency.type == 'D' or self.work_time_unit == 'month' and self.x_invoice_frequency.type == 'M' or self.work_time_unit == 'year' and self.x_invoice_frequency.type == 'Y':
            number_invoice = int(round(self.work_time / self.x_invoice_frequency.timeline, 0))

        if self.work_time_unit == 'day' and self.x_invoice_frequency.type == 'W':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline * 7), 0))

        if self.work_time_unit == 'day' and self.x_invoice_frequency.type == 'M':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline * 30), 0))
        if self.work_time_unit == 'day' and self.x_invoice_frequency.type == 'Y':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline * 365), 0))

        if self.work_time_unit == 'month' and self.x_invoice_frequency.type == 'W':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline / 4), 0))

        if self.work_time_unit == 'month' and self.x_invoice_frequency.type == 'D':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline / 30), 0))

        if self.work_time_unit == 'month' and self.x_invoice_frequency.type == 'Y':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline * 12), 0))

        if self.work_time_unit == 'year' and self.x_invoice_frequency.type == 'M':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline / 12), 0))

        if self.work_time_unit == 'year' and self.x_invoice_frequency.type == 'D':
            number_invoice = int(round(self.work_time / (self.x_invoice_frequency.timeline / 365), 0))

        if number_invoice <= 0:
            number_invoice=1
        return number_invoice

    def action_invoice_custom(self):
        global number_invoice, date_new
        # res = super(SaleOrder, self).action_confirm()
        for order in self:
            order.check_line()
            if order.project_type == 'service':
              order._create_invoices()
              for invoice in order.invoice_ids:
                  invoice.onchange_x_payment_term()
            else:
                number_invoice = self.compute_number_invoice()
                journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
                if not journal:
                    raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                    self.company_id.name, self.company_id.id))
                today = order.date_order.date()
                if self.x_invoice_frequency.type == 'D' or self.x_invoice_frequency.type == 'W':
                    raise UserError(_('Thời hạn của tần suất hóa đơn quá ngắn'))
                if self.x_invoice_frequency.type == 'M':
                    date_new = date(today.year, today.month, 1) + relativedelta(months=self.x_invoice_frequency.timeline)
                if self.x_invoice_frequency.type == 'Y':
                    date_new = date(today.year, today.month, 1) + relativedelta(years=self.x_invoice_frequency.timeline)
                endmonth = monthrange(date_new.year, date_new.month)
                date_invoice = datetime(date_new.year, date_new.month, endmonth[1])
                privew_date = None
                for x in range(1, number_invoice+1):
                    if x == 1:
                        if number_invoice !=1:
                            projects = self.env['project.project'].search([('x_order_id', '=', self.id),('active','in',(True,False)), ('x_date_plan_end', '<=', date_invoice),('is_merge_project','=',False),('main_project','=',False)])
                        else:
                            projects = self.env['project.project'].search([('x_order_id', '=', self.id), ('active', 'in', (True, False)), ('is_merge_project', '=', False),('main_project','=',False)])
                    elif x == number_invoice:
                        projects = self.env['project.project'].search(
                            [('x_order_id', '=', self.id),('active','in',(True,False)), ('x_date_plan_end', '>', privew_date),('is_merge_project','=',False),('main_project','=',False)])
                    else:
                        projects = self.env['project.project'].search([('x_order_id', '=', self.id),('is_merge_project','=',False),('active','in',(True,False)),('main_project','=',False),('x_date_plan_end','<=', date_invoice),('x_date_plan_end', '>', privew_date)])
                    if len(projects) == 0:
                        privew_date = date_invoice
                        next_date = date_invoice + relativedelta(months=self.x_invoice_frequency.timeline)
                        end_next_month = monthrange(next_date.year, next_date.month)
                        date_invoice = datetime(next_date.year, next_date.month, end_next_month[1])
                        continue

                    # Cu chua thay doi
                    # invoice_vals = {
                    #     'ref': self.client_order_ref or '',
                    #     'move_type': 'out_invoice',
                    #     'narration': self.note,
                    #     'x_order_id': self.id,
                    #     'invoice_date': date_invoice,
                    #     'x_project_ids': [(6, 0, [projects.ids[x] for x in range(0, len(projects))])],
                    #     'x_gen_cost_percent': self.x_gen_cost_percent,
                    #     'x_gen_cost_tax_id': self.x_gen_cost_tax_id,
                    #     'currency_id': self.pricelist_id.currency_id.id,
                    #     'campaign_id': self.campaign_id.id,
                    #     'medium_id': self.medium_id.id,
                    #     'source_id': self.source_id.id,
                    #     'invoice_user_id': self.user_id and self.user_id.id,
                    #     'team_id': self.team_id.id,
                    #     'partner_id': self.partner_invoice_id.id,
                    #     'partner_shipping_id': self.partner_shipping_id.id,
                    #     'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.partner_invoice_id.id)).id,
                    #     'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
                    #     'journal_id': journal.id,  # company comes from the journal
                    #     'invoice_origin': self.name,
                    #     'x_payment_rules': self.payment_term_id.id,
                    #     'payment_reference': self.reference,
                    #     'transaction_ids': [(6, 0, self.transaction_ids.ids)],
                    #     'invoice_line_ids': [],
                    #     'company_id': self.company_id.id,
                    #
                    # }
                    # privew_date = date_invoice
                    # next_date = date_invoice + relativedelta(months=self.x_invoice_frequency.timeline)
                    # end_next_month = monthrange(next_date.year, next_date.month)
                    # date_invoice = datetime(next_date.year, next_date.month, end_next_month[1])
                    # moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice',check_move_validity=False).create(invoice_vals)
                    # moves.onchange_x_project()

                    # Moi thay doi
                    invoice_vals = {
                        'ref': self.client_order_ref or '',
                        'move_type': 'out_invoice',
                        'narration': self.note,
                        'x_order_id': self.id,
                        'invoice_date': date_invoice,
                        'x_gen_cost_percent': self.x_gen_cost_percent,
                        'x_gen_cost_tax_id': self.x_gen_cost_tax_id,
                        'currency_id': self.pricelist_id.currency_id.id,
                        'campaign_id': self.campaign_id.id,
                        'medium_id': self.medium_id.id,
                        'source_id': self.source_id.id,
                        'invoice_user_id': self.user_id and self.user_id.id,
                        'team_id': self.team_id.id,
                        'partner_id': self.partner_invoice_id.id,
                        'partner_shipping_id': self.partner_shipping_id.id,
                        'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                            self.partner_invoice_id.id)).id,
                        'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
                        'journal_id': journal.id,  # company comes from the journal
                        'invoice_origin': self.name,
                        'x_payment_rules': self.payment_term_id.id,
                        'payment_reference': self.reference,
                        'transaction_ids': [(6, 0, self.transaction_ids.ids)],
                        'invoice_line_ids': [],
                        'company_id': self.company_id.id,
                        'x_payment_term': date_invoice + relativedelta(
                            day=self.payment_term_id.line_ids[0].days if self.payment_term_id.line_ids else 0),
                    }
                    privew_date = date_invoice
                    next_date = date_invoice + relativedelta(months=self.x_invoice_frequency.timeline)
                    end_next_month = monthrange(next_date.year, next_date.month)
                    date_invoice = datetime(next_date.year, next_date.month, end_next_month[1])
                    new_x_project_ids = [(6, 0, [projects.ids[x] for x in range(0, len(projects))])]
                    moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice',
                                                                         check_move_validity=False).create(invoice_vals)
                    moves.x_project_ids = new_x_project_ids
                    moves.so_add_x_project()
                order.update_name(order.id)
                order.update({'invoice_status': 'no'})
        # return res

    def update_name(self, invoice_id):
        self.ensure_one()
        invoice=self.env['account.move'].search([('x_order_id','=',invoice_id)])
        for r in invoice:
            r.update({'name': '/'})

    def compute_date_invoice(self):
        if self.prepare_time_unit == 'day':
            prepare_time = relativedelta(days=self.prepare_time)
        elif self.prepare_time_unit == 'month':
            prepare_time = relativedelta(months=self.prepare_time)
        else:
            prepare_time = relativedelta(years=self.prepare_time)
        if self.work_time_unit == 'day':
            work_time = relativedelta(days=self.work_time)
        elif self.work_time_unit == 'month':
            work_time = relativedelta(months=self.work_time)
        else:
            work_time = relativedelta(years=self.work_time)
        date_invoice = self.date_order + prepare_time + work_time
        return date_invoice

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()

        if self.project_type in ('service', 'maintainance'):
            if self.x_project_count ==0:
                raise UserError('Báo giá chưa có dự án nào')
            date_invoice = self.compute_date_invoice()
            projects = self.env['project.project'].search([('x_order_id', '=', self.id),('active','in',(True,False)),('is_merge_project','=',False)])
            line_gen_cost = []
            amount_untaxed= 0
            res = ast.literal_eval(self.env['ir.config_parameter'].sudo().get_param('xaccount.gen_cost_default_product'))
            if not res:
                raise UserError('Chưa khai báo sản phẩm chi phí quản lý chung trên hệ thống ')
            cost_product = self.env['product.template'].sudo().browse(res)
            for line in self.order_line:
                amount_untaxed += line.price_subtotal
            line_gen_cost.append((0, 0, {
                'display_type': False,
                'x_is_gen_cost': True,
                'product_id': cost_product.id,
                'name': cost_product.name or '',
                'currency_id': self.currency_id.id,
                'quantity': 1,
                'product_uom_id': cost_product.uom_id.id,
                'account_id': cost_product.categ_id.property_account_income_categ_id.id,
                'x_price_unit_contract': amount_untaxed * self.x_gen_cost_percent / (100-self.x_gen_cost_percent) or 0,
                'price_unit': amount_untaxed * self.x_gen_cost_percent / (100-self.x_gen_cost_percent) or 0,
                'tax_ids': [(6, 0, self.x_gen_cost_tax_id.ids)],
                'exclude_from_invoice_tab': False,
            }))
            invoice_vals.update({
                'invoice_date': date_invoice,
                'x_order_id': self.id,
                'x_project_ids': [(6, 0, [projects.ids[0]])],
                'x_payment_rules': self.payment_term_id.id,
                'x_gen_cost_percent': self.x_gen_cost_percent,
                'x_gen_cost_tax_id': self.x_gen_cost_tax_id,
                'invoice_line_ids' : line_gen_cost
            })
        return invoice_vals

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for line in self.order_line:
            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                continue
            if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    # Keep down payment lines separately, to put them together
                    # at the end of the invoice, in a specific dedicated section.
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)

        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added to the returned invoice line
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'x_price_unit_contract': self.price_unit,
            'tax_ids': [(6, 0, self.tax_id.ids)],
            'analytic_account_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.id)],
        }
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gen_cost_default_product_id = fields.Many2one(
        'product.template',
        'Gen cost Product',
        domain="[('type', '=', 'service')]",
        help='Sản phẩm chi phí quản lý chung,sử dụng khi lên hóa đơn',
        config_parameter='xaccount.gen_cost_default_product')