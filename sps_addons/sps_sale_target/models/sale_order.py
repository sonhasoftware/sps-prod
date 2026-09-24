# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.models import NewId

TIME_UNIT_SELECTABLE = [
    ('day', 'Ngày'),
    ('month', 'Tháng'),
    ('year', 'Năm')
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_investor_id = fields.Many2one(comodel_name='res.partner', string='Chủ đầu tư')
    x_amount_estimate = fields.Float('Tổng dự toán', compute='compute_amount_estimate')
    x_inquiry_date = fields.Date ('Ngày yêu cầu', required=True, default=fields.date.today())
    x_date_warranty_expire = fields.Date('Ngày hết hạn bảo hành')
    x_expertise_ids = fields.Many2many('expertise.type', 'sale_order_expertise_ref', 'sale_odder_id',
                                       'expertise_type_id', string='Chuyên môn')
    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=False,)
    x_warranty_period = fields.Float('Thời hạn bảo hành')
    x_warranty_period_unit = fields.Selection(
        selection=TIME_UNIT_SELECTABLE,
        required=True,
        default='month',
        string='warranty Time Unit'
    )
    request_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Request Customer',
        copy=False,
    )
    work_content = fields.Text(
        string="Content"
    )
    location_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer Location',
        copy=False
    )
    project_type = fields.Selection(
        selection=[
            ('maintainance', 'Maintenance'),
            ('service', 'Services'),
            ('operation', 'Facility Management')
        ],
        string='Project Type',
        required=True,
        default='service'
    )
    work_scope = fields.Text(
        string='Scope'
    )
    work_note = fields.Text(
        string='Work Note'
    )
    solution_maker = fields.Many2one(
        comodel_name='res.users',
        string='Solution Maker/Estimator'
    )
    order_note = fields.Char(
        string='Order Note'
    )
    prepare_time = fields.Float(
        string='Prepare Time',
        digits=(4, 2)
    )
    work_time = fields.Float(
        string='Work Time',
        digits=(4, 2)
    )
    prepare_time_unit = fields.Selection(
        selection=TIME_UNIT_SELECTABLE,
        required=True,
        default='month',
        string='Prepare Time Unit'
    )
    work_time_unit = fields.Selection(
        selection=TIME_UNIT_SELECTABLE,
        required=True,
        default='month',
        string='Work Time Unit'
    )
    profit_formula_id = fields.Many2one(
        'profit.formula.config',
        string='Income taxes',
        default=lambda self: self.env['profit.formula.config'].search([], order='sequence, id', limit=1),
    )
    income_tax = fields.Monetary(
        string='Income Tax',
        currency_field='currency_id',
        compute='compute_profit',
    )
    profit_after_tax = fields.Monetary(
        string='Profit After Tax',
        currency_field='currency_id',
        default=0.0
    )
    sale_estimates_line_ids = fields.One2many(
        comodel_name='sale.project.line',
        inverse_name='sale_order_id',
        string='Order Estimates Line',
        copy=1
    )
    count_project_line = fields.Integer('Count Project Line', copy=0, readonly=1)
    cr = fields.Float('CR (%)')
    tp = fields.Float('TP (%)')
    overhead_cost = fields.Float('Overhead Cost (%)')
    cr_amount = fields.Float('CR', compute='compute_cr', inverse="_inverse_cr")
    tp_amount = fields.Float('TP', compute='compute_tp', inverse="_inverse_tp")
    overhead_cost_amount = fields.Float('Overhead Cost', compute='compute_overhead_cost', inverse="_inverse_overhead_cost")
    x_partner_ref = fields.Char('Mã khách hàng', related='partner_id.ref')

    x_gen_cost_percent = fields.Float('Chi phí quản lý chung (%)', default=0)
    x_gen_cost_tax_id = fields.Many2one('account.tax', 'Thuế chi phí quản lý chung',
                                        domain=[('type_tax_use', '=', 'sale')])
    x_gen_cost = fields.Monetary('Chi phí quản lý chung')
    r_maintenace = fields.Boolean(string='R-Maintenace', default=False)
    e_fm = fields.Boolean(string='E-FM', default=False)

    @api.depends('amount_untaxed', 'cr')
    def compute_cr(self):
        for rec in self:
            rec.cr_amount = rec.cr * rec.amount_untaxed / 100

    @api.depends('amount_untaxed', 'overhead_cost')
    def compute_overhead_cost(self):
        for rec in self:
            rec.overhead_cost_amount = rec.overhead_cost * rec.amount_untaxed / 100

    @api.depends('amount_untaxed', 'tp')
    def compute_tp(self):
        for rec in self:
            rec.tp_amount = rec.tp * rec.amount_untaxed / 100

    def _inverse_cr(self):
        for rec in self:
            rec.cr = rec.cr_amount / rec.amount_untaxed * 100 if rec.amount_untaxed else 0

    def _inverse_tp(self):
        for rec in self:
            rec.tp = rec.tp_amount / rec.amount_untaxed * 100 if rec.amount_untaxed else 0

    def _inverse_overhead_cost(self):
        for rec in self:
            rec.overhead_cost = rec.overhead_cost_amount / rec.amount_untaxed * 100 if rec.amount_untaxed else 0

    def action_mark_sent(self):
        for r in self:
            if r.project_type == 'maintainance':
                for rec in r.order_line.filtered(lambda rec: rec.display_type not in ['line_section']):
                    if rec.product_id.x_manage_frequency is False or rec.product_id.x_frequency_id.id is False:
                        raise UserError(_('Chưa chọn quản lý tần suất và tần suất cho sản phẩm %s') % rec.product_id.name)
            if r.state == 'draft':
                r.state = 'sent'

    @api.model
    def default_get(self, fields_list):
        res = super(SaleOrder, self).default_get(fields_list)
        taxes = self.env['account.tax'].sudo().search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 10),
        ], limit=1)
        if taxes:
            res['x_gen_cost_tax_id'] = taxes[0].id
        return res

    def get_general_cost(self, amount_untaxed):
        if 0 <= self.x_gen_cost_percent < 100:
            return amount_untaxed / (100 - self.x_gen_cost_percent) * self.x_gen_cost_percent
        else:
            return 0

    @api.depends('order_line.price_total', 'x_gen_cost_percent', 'x_gen_cost_tax_id')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            general_cost = order.get_general_cost(amount_untaxed)
            if order.x_gen_cost_tax_id:
                general_cost_tax = order.x_gen_cost_tax_id._compute_amount(base_amount=general_cost, price_unit=general_cost)
            else:
                general_cost_tax = 0
            order.update({
                'amount_untaxed': amount_untaxed + general_cost,
                'amount_tax': amount_tax + general_cost_tax,
                'amount_total': amount_untaxed + general_cost + amount_tax + general_cost_tax,
                'x_gen_cost': general_cost,
            })

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['name'] = "%s (sao chép)" % (self.name)
        res = super(SaleOrder, self).copy(default)
        res._update_order_line_and_quotes()
        return res

    # @api.constrains('partner_id')
    # def compute_store_name(self):
    #     today = date.today()
    #     dt_from = today - relativedelta(days=1)
    #     dt_from = dt_from.strftime('%Y-%m-%d 17:00:00')
    #     dt_to = today.strftime('%Y-%m-%d 17:00:00')
    #     print(dt_to, dt_from)
    #     for r in self.sorted(key='id'):
    #         latest_order_id = self.sudo().search([
    #             ('partner_id', '=', r.partner_id.id),
    #             ('date_order', '>=', dt_from),
    #             ('date_order', '<', dt_to),
    #             ('id', '!=', r.id),
    #         ], order='id desc', limit=1)
    #         if latest_order_id:
    #             try:
    #                 n = int(latest_order_id.name.split('_')[2]) + 1
    #             except:
    #                 n = 1
    #             n = f'{n:02}'
    #             r.name = '%s_%s_%s' % (
    #                 r.partner_id.ref or 'UNK',
    #                 '%s%02d%02d' % (str(today.year)[2:], today.month, today.day),
    #                 n
    #             )
    #         else:
    #             r.name = '%s_%s_%s' % (
    #                 r.partner_id.ref or 'UNK',
    #                 '%s%02d%02d' % (str(today.year)[2:], today.month, today.day),
    #                 '01'
    #             )

    @api.depends('amount_untaxed', 'sale_estimates_line_ids', 'order_line', 'cr', 'tp', 'overhead_cost')
    @api.onchange('amount_untaxed', 'sale_estimates_line_ids', 'order_line', 'cr', 'tp', 'overhead_cost')
    def compute_amount_estimate(self):
        for r in self:
            r.x_amount_estimate = sum(x.predicted_price * x.order_line_id.product_uom_qty for x in self.sale_estimates_line_ids.filtered(lambda s: s.type == 'quote'))

    @api.constrains('amount_untaxed', 'sale_estimates_line_ids', 'order_line', 'cr', 'tp', 'overhead_cost', 'profit_formula_id')
    @api.onchange('amount_untaxed', 'sale_estimates_line_ids', 'order_line', 'cr', 'tp', 'overhead_cost', 'profit_formula_id')
    def compute_profit(self):
        for r in self:
            if r.profit_formula_id:
                r.income_tax = r.profit_formula_id.compute_profit(r)
                r.profit_after_tax = r.amount_untaxed - r.x_amount_estimate - r.cr_amount - r.tp_amount - r.overhead_cost_amount - r.income_tax
            else:
                xx = sum(x.predicted_price * x.order_line_id.product_uom_qty for x in r.sale_estimates_line_ids.filtered(lambda s: s.type == 'quote'))
                r.income_tax = (r.amount_untaxed - xx - r.amount_untaxed * r.overhead_cost * 0.01) * 0.2
                r.profit_after_tax = (r.amount_untaxed - xx - r.amount_untaxed * r.overhead_cost * 0.01) * 0.8 - r.amount_untaxed * (r.cr + r.tp) * 0.01

    @api.onchange('sale_estimates_line_ids')
    def onchange_set_sequence(self):
        self.count_project_line = len(self.sale_estimates_line_ids)
        predicted_price, retail_price_unit, current_quote = 0, 0, self.sale_estimates_line_ids.sorted('sequence')[:1]
        for line in self.sale_estimates_line_ids.sorted('sequence'):
            if line.type == 'estimate':
                predicted_price += line._compute_predicted_price()
                retail_price_unit += line._compute_retail_price_unit()
            if line.type == 'quote':
                if current_quote:
                    if predicted_price and retail_price_unit:
                        current_quote._update_pseudo_record(predicted_price, retail_price_unit)
                    else:
                        current_quote._update_pseudo_record(current_quote._compute_predicted_price(), current_quote._compute_retail_price_unit())
                predicted_price, retail_price_unit, current_quote = 0, 0, line
        if current_quote and predicted_price and retail_price_unit:
            current_quote._update_pseudo_record(predicted_price, retail_price_unit)

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        vals['name'] = _('New')
        return res
    def write(self, vals):
        res = super().write(vals)
        if self._context.get('update_order_line_and_quotes', True):
            for r in self:
                r._update_order_line_and_quotes()
        return res

    def _update_order_line_and_quotes(self):
        self.ensure_one()
        self.sale_estimates_line_ids._compute_price()
        quote_estimates = self.sale_estimates_line_ids.filtered(
            lambda spl: spl.type == 'quote'
        )
        quote_to_create = quote_estimates.filtered(lambda spl: not spl.order_line_id)
        quote_to_remove = self.order_line.filtered(
            lambda sol: not sol.display_type and sol not in quote_estimates.order_line_id
        )
        quote_to_update = quote_estimates.filtered(
            lambda spl: spl.order_line_id in (self.order_line - quote_to_remove)
        )
        for quote in quote_to_create.sorted(key='sequence'):
            new_sol = self.order_line.create({
                'sequence': quote.sequence,
                'order_id': self.id,
                'product_id': quote.product_id.id,
                'name': quote.product_id.name,
                'product_uom_qty': quote.qty,
                'price_unit': quote.retail_price_unit
            })
            quote.write({'order_line_id': new_sol.id})
        for quote in quote_to_update:
            quote.order_line_id.write({
                'product_id': quote.product_id.id,
                'name': quote.product_id.name,
                'product_uom_qty': quote.qty,
                'price_unit': quote.retail_price_unit
            })
        self.with_context(update_order_line_and_quotes=False).write({
            'order_line': [(2, _) for _ in quote_to_remove.ids]
        })

    @api.onchange('partner_id')
    def _onchange_partner_id_domain_context(self):
        """
        Domain & context for request_partner_id, location_partner_id onchange of partner_id
        Allow user to create & write request customer, location following rule:
        - childs of partner_id.
        """
        if self.partner_id and isinstance(self.id, NewId):
            return {
                'domain': {
                    'request_partner_id': [
                        '&', ('type', '=', 'contact'), '|',
                        ('id', 'in', self.partner_id.child_ids.ids),
                        ('id', '=', self.partner_id.id)
                    ],
                    'location_partner_id': [
                        '&', ('type', '=', 'delivery'), '|',
                        ('id', 'in', self.partner_id.child_ids.ids),
                        ('id', '=', self.partner_id.id)
                    ]
                }
            }

    @api.onchange('request_partner_id')
    def _onchange_request_partner_id(self):
        """
        change parent_id follow request_partner_id
        """
        if self.request_partner_id:
            self.partner_id = self.request_partner_id.parent_id.id

    @api.onchange('location_partner_id')
    def _onchange_location_partner_id(self):
        """
        change parent_id follow location_partner_id
        """
        if self.location_partner_id:
            self.partner_id = self.location_partner_id.parent_id.id

    def action_report_quotation_xlsx(self, type):
        if type not in ('boq', 'cover', 'est'):
            return None
        if isinstance(self.id, NewId):
            raise ValidationError(_("Please save your record before print report!"))
        return self.env.ref('sps_sale_target.sale_order_report_xlsx').report_action(
            self, data={"report_type": type}
        )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    parent_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Section',
        compute='_compute_section',
        store=True
    )
    price_unit = fields.Float(
        readonly=True
    )

    _sql_constraints = [
        (
            "parent_product_uniq",
            "UNIQUE(id)",
            'One section should only have one product!'
        )
    ]

    # @api.model
    # def create(self, vals):
    #     return super(SaleOrderLine, self).create(vals)

    def name_get(self):
        res = []
        for r in self:
            res.append((r.id, r.name))
        return res

    @api.depends('sequence')
    def _compute_section(self):
        self = self.order_id.order_line
        for r in self:
            if not r.display_type:
                nearest_section = self.order_id.order_line.filtered(
                    lambda sol: sol.display_type == 'line_section' and
                                sol.sequence < r.sequence
                )
                nearest_section = nearest_section.sorted('sequence', True)[:1]
                if not nearest_section:
                    r.parent_id = False
                else:
                    r.parent_id = nearest_section.id
            else:
                r.parent_id = False


class SaleProjectLine(models.Model):
    _name = 'sale.project.line'
    _description = 'Sale Project Line'

    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        required=True,
        ondelete='cascade',
        readonly=True, copy=0
    )
    sale_order_project_type = fields.Selection(
        related='sale_order_id.project_type',
        readonly=True,
        required=True
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        ondelete='restrict',
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Description',
        related='product_id.product_tmpl_id',
        store=True,
        readonly=True
    )
    order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Quote',
        copy=0
    )
    category = fields.Many2one(
        string='Section',
        related='order_line_id.parent_id',
        store=True,
        readonly=True, copy=0
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit',
        related='product_id.uom_id'
    )
    qty = fields.Float(
        string='Quantity',
        digits=(4, 2)
    )
    materials_price_unit = fields.Float(
        string='Materials Price'
    )
    worker_price_unit = fields.Float(
        string='Worker Price'
    )
    other_price_unit = fields.Float(
        string='Other Price'
    )
    total_price_unit = fields.Float(
        string='Price Unit',
        compute='_compute_price',
        store=True
    )
    predicted_price = fields.Float(
        string='Predicted Price',
        # compute='_compute_price',
        # store=True
    )
    markup_materials = fields.Float(
        string='Markup Materials (%)'
    )
    markup_worker = fields.Float(
        string='Markup Worker (%)'
    )
    markup_other = fields.Float(
        string='Markup Others (%)'
    )
    retail_price_unit = fields.Float(
        string='Retail Price Unit',
        # compute='_compute_price',
        # store=True
    )
    type = fields.Selection(
        selection=[
            ('quote', 'Quote'),
            ('estimate', 'Estimate')
        ],
        string='Type',
        required=True,
        default='estimate'
    )
    sequence = fields.Integer(
        string='Sequence',
        # default=lambda self: self.env['ir.sequence'].next_by_code('increment_estimate_sq')
    )
    note = fields.Char(
        string='Note'
    )
    timeline = fields.Float(
        string='Timeline',
        default=100.0,
        digits=(5, 2)
    )
    # parent_id = fields.Many2one(
    #     comodel_name='sale.project.line',
    #     string='Quote',
    #     compute='_compute_quote',
    #     store=True
    # )
    # child_ids = fields.One2many(
    #     comodel_name='sale.project.line',
    #     inverse_name='parent_id',
    #     string='Estimates',
    #     readonly=True,
    #     copy=False
    # )

    # @api.depends('sequence')
    # def _compute_quote(self):
    #     self = self.sale_order_id.sale_estimates_line_ids
    #     for r in self:
    #         if r.type == 'estimate':
    #             nearest_quote = self.sale_order_id.sale_estimates_line_ids.filtered(
    #                 lambda sol: sol.type == 'quote' and
    #                             sol.sequence < r.sequence
    #             )
    #             nearest_quote = nearest_quote.sorted('sequence', True)[:1]
    #             if not nearest_quote:
    #                 r.parent_id = False
    #             else:
    #                 r.parent_id = nearest_quote.id
    #         else:
    #             r.parent_id = False

    @api.depends(
        'materials_price_unit',
        'worker_price_unit',
        'other_price_unit',
        'markup_materials',
        'markup_worker',
        'markup_other',
        'qty',
        # 'sequence',
        'type',
        # 'child_ids',
        # 'child_ids.materials_price_unit',
        # 'child_ids.worker_price_unit',
        # 'child_ids.other_price_unit',
        # 'child_ids.markup_materials',
        # 'child_ids.markup_worker',
        # 'child_ids.markup_other',
        # 'child_ids.qty',
        # 'child_ids.sequence',
        # 'child_ids.type',
    )
    @api.onchange('materials_price_unit', 'worker_price_unit', 'other_price_unit',
                  'markup_materials', 'markup_worker', 'markup_other', 'qty', 'type',
                  'timeline', 'sale_order_project_type')
    def _compute_price(self):
        for r in self:
            # if r.type == 'estimate' or r.sale_order_project_type == 'service':
            if any([r.materials_price_unit, r.worker_price_unit, r.other_price_unit,
                r.markup_materials, r.markup_worker, r.markup_other
            ]):
                r.total_price_unit = r._compute_total_price_unit()
                r.predicted_price = r._compute_predicted_price()
                r.retail_price_unit = r._compute_retail_price_unit()
            else:
                r.total_price_unit = 0
                # r.predicted_price = sum(r.child_ids.mapped('predicted_price'))
                # r.retail_price_unit = sum(r.child_ids.mapped('retail_price_unit'))
                # r.order_line_id.price_unit = r.retail_price_unit

    def _compute_total_price_unit(self):
        if len(self) != 1:
            return 0
        return self.materials_price_unit + self.worker_price_unit + self.other_price_unit

    def _compute_predicted_price(self):
        if len(self) != 1:
            return 0
        qty = 1 if (self.sale_order_project_type == 'service' and self.type == 'quote') else self.qty
        return qty * (
                self.materials_price_unit +
                self.worker_price_unit +
                self.other_price_unit
            ) * self.timeline / 100

    def _compute_retail_price_unit(self):
        if len(self) != 1:
            return 0
        qty = 1 if (self.sale_order_project_type == 'service' and self.type == 'quote') else self.qty
        return qty * (
                self.markup_materials * self.materials_price_unit / 100 +
                self.markup_worker * self.worker_price_unit / 100 +
                self.markup_other * self.other_price_unit / 100
            ) * self.timeline / 100

    @api.depends('product_id')
    @api.onchange('product_id')
    def onchange_product_id(self):
        plist_obj = self.env['product.pricelist.item'].sudo()
        for r in self:
            if not r.product_id:
                r.update({
                    'materials_price_unit': 0,
                    'worker_price_unit': 0,
                    'other_price_unit': 0,
                    'total_price_unit': 0,
                })
                continue
            plist_item_id = plist_obj.search([
                ('product_tmpl_id', '=', r.product_id.product_tmpl_id.id),
                ('pricelist_id.date_start', '<=', r.sale_order_id.date_order),
                ('pricelist_id.date_end', '>=', r.sale_order_id.date_order),
                ('active', '=', True),
            ])
            if not plist_item_id:
                continue
            r.update({
                'materials_price_unit': plist_item_id.material_price,
                'worker_price_unit': plist_item_id.worker_price,
                'other_price_unit': plist_item_id.other_price,
                'total_price_unit': plist_item_id.fixed_price,
            })

    @api.model
    def default_get(self, fields_list):
        res = super(SaleProjectLine, self).default_get(fields_list)
        res['sequence'] = self._context.get('x_count_project_line', 1)
        return res

    def _update_pseudo_record(self, predicted_price, retail_price_unit):
        self.update({
            'predicted_price': predicted_price,
            'retail_price_unit': retail_price_unit
        })
        if self.order_line_id:
            self.order_line_id.price_unit = retail_price_unit
            self.order_line_id.product_uom_qty = self.qty


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_tax_included_unit_price(self, company, currency, document_date, document_type,
                                     is_refund_document=False, product_uom=None, product_currency=None,
                                     product_price_unit=None, product_taxes=None, fiscal_position=None
                                     ):
        if document_type == 'sale':
            return 0
        return super()._get_tax_included_unit_price(company, currency, document_date, document_type,
                                                    is_refund_document, product_uom, product_currency,
                                                    product_price_unit, product_taxes, fiscal_position
                                                    )
