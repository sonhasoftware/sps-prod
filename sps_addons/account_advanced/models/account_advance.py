# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.osv import expression
class AccountAdvance(models.Model):
    _name = 'account.advance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tạm ứng'
    _rec_name = "number"
    _order = 'create_date desc'

    type = fields.Selection([
        ('internal', 'Nội bộ'),
        ('supplier', 'Nhà cung cấp')
    ], string='Loại tạm ứng', required='True', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    employee_id = fields.Many2one('res.users', string='Nhân Viên', default=lambda self: self.env.user)
    approver_id = fields.Many2one('res.users', string="Người quản lý")
    supplier_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    po_id = fields.Many2one('purchase.order', string='Số PO')
    advance_amount = fields.Monetary(string='Tiền tạm ứng')
    amount_total = fields.Monetary(string='Tổng số tiền', compute='compute_amount_total', store=True)
    reason = fields.Char(string='Lý do tạm ứng', required='True')
    number = fields.Char("Số phiếu", readonly='True')
    date_suggest = fields.Date(string='Ngày đề nghị', default=fields.Date.context_today)
    date_advance = fields.Date(string='Ngày tạm ứng', readonly='True')
    date_repay = fields.Date(string='Ngày hoàn ứng', readonly='True')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('wait_manager', 'Chờ quản lý duyệt'),
        ('pending', 'Chờ kế toán duyệt'),
        ('approved', 'Chờ thanh toán'),
        ('wait_bod', 'Chờ BOD duyệt thanh toán '),
        ('bod_approved', 'Đã duyệt thanh toán'),
        ('payment', 'Đã thanh toán'),
        ('completed', 'Đã hoàn ứng'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='draft',track_visibility="always")
    x_state = fields.Selection([
        ('0', 'Nháp'),
        ('1', 'Chờ quản lý duyệt'),
        ('2', 'Chờ kế toán duyệt'),
        ('3', 'Chờ thanh toán'),
        ('4', 'Chờ BOD duyệt thanh toán '),
        ('5', 'Đã duyệt thanh toán'),
        ('6', 'Đã thanh toán'),
        ('7', 'Đã hoàn ứng'),
        ('8', 'Hủy'),
    ], string='Trạng thái', default='0', track_visibility="always", compute='_compute_update_x_state', store=True)

    account_id = fields.Many2one('account.account', string='Tài khoản hạch toán', required='True')

    partner_bank_id = fields.Many2one('res.partner.bank', string='Tài khoản ngân hàng')
    diary_id = fields.Many2one('account.journal', string='Sổ nhật ký',
                               default=lambda self: self.env['account.journal'].search(
                                   [('name', '=', 'TCB')], limit=1))
    license_type = fields.Selection([
        ('tax', 'Thuế'),
        ('internal', 'Nội bộ')
    ], string='Phân loại chứng từ', default='tax')
    is_allowed_license_type = fields.Boolean(compute='_compute_allowed_license_type')
    code_money_id = fields.Many2one('code.money', string='Mã khoản tiền')
    payment_id = fields.Many2one('account.payment', 'Phiếu thanh toán', copy=False)
    advance_line_ids = fields.One2many('account.advance.line', 'advance_id', string='line' , copy=True)

    def _compute_allowed_license_type(self):
        for r in self:
            if self.user_has_groups('account_advanced.group_allow_change_license_type'):
                r.is_allowed_license_type = True
            else:
                r.is_allowed_license_type = False

    @api.model
    def create(self, vals):
        if vals['type'] == 'internal':
            vals['number'] = self.env['ir.sequence'].next_by_code('account_advance')
        else:
            vals['number'] = self.env['ir.sequence'].next_by_code('account_advance_supplies')
        return super(AccountAdvance, self).create(vals)

    def write(self, values):
        res = super(AccountAdvance, self).write(values)
        if 'license_type' in values and self.payment_id:
            self.payment_id.x_license_type = self.license_type
        return res

    @api.depends('state')
    def _compute_update_x_state(self):
        state_mapping = {
            'draft': '0',
            'wait_manager': '1',
            'pending': '2',
            'approved': '3',
            'wait_bod': '4',
            'bod_approved': '5',
            'payment': '6',
            'completed': '7',
            'cancel': '8',
        }
        for record in self:
            record.x_state = state_mapping.get(record.state, '0')

    @api.onchange('type', 'supplier_id', 'employee_id')
    def onchange_account(self):
        for r in self:
            if r.type == 'internal':
                account_id = self.env['account.account'].search(
                    [('code', '=', '141')], limit=1)
                if not account_id:
                    raise UserError('Bạn chưa thiết lập tài khoản tạm ứng 141')
                else:
                    r.account_id = account_id.id
                r.partner_bank_id = self.env['res.partner.bank'].search([('partner_id', '=', r.employee_id.partner_id.id)],
                                                                        limit=1).id
            elif r.supplier_id:
                r.account_id = r.supplier_id.property_account_payable_id.id
                r.partner_bank_id = self.env['res.partner.bank'].search([('partner_id', '=', r.supplier_id.id)],
                                                                        limit=1).id

    @api.onchange('employee_id', 'supplier_id')
    def onc_employee_id(self):
        for r in self:
            if r.type == 'internal':
                    r.approver_id = r.employee_id.employee_id.parent_id.user_id.id
            else:
                    r.approver_id = self.env.user.employee_id.parent_id.user_id.id

    def default_get(self, fields_list):
        res = super(AccountAdvance, self).default_get(fields_list)
        res['type'] = 'internal'
        return res

    @api.depends('advance_line_ids','advance_line_ids.amount','type')
    @api.onchange('advance_line_ids','advance_line_ids.amount','type')
    def compute_amount_total(self):
        for r in self:
            if r.advance_line_ids and r.type =='internal':
                r.amount_total = sum(line.amount for line in r.advance_line_ids)
            else:
                r.amount_total = r.advance_amount

    def unlink(self):
        for r in self:
            if r.state == "draft":
                rtn = super(AccountAdvance, self).unlink()
                return rtn
            else:
                raise UserError("Chỉ có thể xoá bản ghi ở trạng thái nháp")

    def action_cancel(self):
        for r in self:
            if r.state == 'wait_manager':
                if self._uid == r.approver_id.id or self.env.user.has_group('base.group_erp_manager'):
                    r.state = 'cancel'
                else:
                    raise UserError('Bạn không đủ quyền hạn để từ chối tạm ứng này !')
            elif r.state == 'pending':
                if self.env.user.has_group('account.group_account_manager'):
                    r.state = 'cancel'
                else:
                    raise UserError(
                        'Bạn không đủ quyền hạn để từ chối phiếu tạm ứng này. Hãy liên hệ với kế toán để được xử lý !')
            elif r.state == 'wait_bod':
                if self.env.user.has_group('base.group_erp_manager'):
                    r.state = 'cancel'
                else:
                    raise UserError('Bạn không đủ quyền hạn để từ chối phiếu tạm ứng này !')
            elif r.state in ('bod_approved', 'payment'):
                if self.env.user.has_group('base.group_erp_manager') or self.env.user.has_group('account.group_account_manager'):
                    r.state = 'cancel'
                    if r.payment_id:
                        # Xóa các đơn thanh toán
                        r.payment_id.action_cancel()
                        r.payment_id.action_draft()
                        r.payment_id.move_id.with_context(force_delete=True).unlink()
                        r.payment_id.unlink()
            else:
                continue

    def action_to_draft(self):
        for r in self:
            if r.state in ['pending','wait_manager', 'cancel']:
                r.state = 'draft'
            else:
                continue

    def action_sent_approve(self):
        for r in self:
            if r.state == 'draft':
                r.state = 'wait_manager'
            else:
                continue

    def action_manager_approve(self):
        for rec in self:
            if rec.state == 'wait_manager':
                if self._uid == rec.approver_id.id or self.env.user.has_group('base.group_erp_manager'):
                    rec.state ='pending'
                else:
                    raise UserError('Bạn không đủ quyền hạn để từ chối tạm ứng này !')
            else:
                continue

    def action_approve(self):
        for r in self:
            if r.state == 'pending':
                if not self.env.user.has_group('account.group_account_manager'):
                    raise UserError('Bạn không đủ quyền hạn để duyệt phiếu tạm ứng này. Hãy liên hệ với kế toán để được xử lý !')
                else:
                    r.state = 'approved'
            else:
                continue

    def action_payment(self):
        for r in self:
            if r.state == 'approved':
                if not self.env.user.has_group('account.group_account_manager'):
                    raise UserError('Bạn không đủ quyền hạn để duyệt phiếu tạm ứng này !')
                else:
                    r.state = 'wait_bod'
            else:
                continue

    def action_bod_approve(self):
        for r in self:
            # amount_advanced = 0
            # project_totals = {}
            # # Tổng hợp dữ liệu theo x_project_id
            # for ol in self.po_id.order_line:
            #     project_id = ol.x_project_id.id
            #     if project_id not in project_totals:
            #         project_totals[project_id] = ol.price_total
            #     else:
            #         project_totals[project_id] += ol.price_total
            #     amount_advanced += ol.price_total
            #
            # # Chuyển dữ liệu thành danh sách các dictionary cho One2many
            # for project_id, advance_detail in project_totals.items():
            #     line_ids.append((0, 0, {
            #         'project_id': project_id,
            #         'amount_total': advance_detail,
            #     }))

            if not r.code_money_id or not r.license_type:
                raise UserError('Bạn chưa điền thông tin mã khoản tiền hoặc phân loại chứng từ')
            r.date_advance = date.today()
            line_ids = []
            for line in self.advance_line_ids:
                line_ids.append((0, 0, {
                    'project_id': line.project_id.id,
                    'code_project': line.project_id.x_order_id.id,
                    'amount_total': line.amount,
                }))

            payment_id = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'payment_method_id': self.env['account.payment.method'].search(
                    [('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1).id,
                'partner_type': 'supplier' if r.type == 'supplier' else 'customer',
                'partner_id': r.supplier_id.id if r.type == 'supplier' else r.employee_id.partner_id.id,
                'destination_account_id': r.account_id.id,
                'is_internal_transfer':  False,
                'amount': r.amount_total,
                'ref': r.reason,
                'x_approved_state': 'approved',
                'x_license_type': r.license_type,
                'x_code_money': r.code_money_id.id,
                'journal_id': r.diary_id.id,
                'partner_bank_id': r.partner_bank_id.id,
                'x_origin_advance_id': r.id,
                'x_address': r.supplier_id.name if r.supplier_id else '',
                'x_amount_override': r.amount_total,
                # 'advance_line_ids': line_ids
                'x_project_detail_ids': line_ids
            })
            r.state = 'bod_approved'
            r.payment_id = payment_id.id

    def copy(self, default=None):
        self.ensure_one()
        if self.type == 'internal':
             rec = super(AccountAdvance, self).copy(default=default)
             rec.compute_amount_total()
             return rec
        else:
            default = dict(default or {})
            default['advance_line_ids'] = False
            res = super(AccountAdvance, self).copy(default=default)
            return res

class AccountAdvanceLine(models.Model):
    _name = 'account.advance.line'

    project_id = fields.Many2one('project.project', string='Mã dự án', required='True')
    project_name = fields.Char(string='Tên dự án', compute="_compute_project_name", store=1)
    amount = fields.Monetary(string='Số tiền')
    advance_id = fields.Many2one('account.advance', string='Mã phiếu')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    description = fields.Char(string="Mô tả")
    total_cost = fields.Float('Chi phí đơn hàng')
    percentage = fields.Float('Tỷ lệ (%)', default=0)


    @api.depends('project_id', 'project_id.label_tasks')
    def _compute_project_name(self):
        for rec in self:
            rec.project_name = rec.project_id.label_tasks

    # @api.onchange('project_id')
    # def onc_project(self):
    #     for r in self:
    #         r.project_name = self.project_id.label_tasks


class AdvancedRegister(models.TransientModel):
    _name = 'account.advance.register'
    _description = 'Register advanced from PO'

    supplier_id = fields.Many2one('res.partner', 'Nhà cung cấp')
    po_id = fields.Many2one('purchase.order', 'Số PO')
    ref = fields.Char(string='Lí do')
    amount_advanced = fields.Float(string='Số tiền')
    amount_purchase = fields.Float('Tổng tiền đơn mua')
    account_id = fields.Many2one('account.account', 'Tài khoản ')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    line_ids = fields.One2many('account.advance.register.line', 'register_id', 'Chi tiết tạm ứng')

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        if not self._context.get('po_id'):
            raise UserError('Lỗi')
        else:
            order_id = self.env['purchase.order'].browse(self._context.get('po_id'))
            res['supplier_id'] = order_id.partner_id.id
            res['po_id'] = order_id.id
            res['amount_purchase'] = order_id.amount_total
            res['account_id'] = order_id.partner_id.property_account_payable_id.id
        return res

    def action_create_advanced(self):
        total_advanced = self.amount_advanced
        account_advance_ids = self.env['account.advance'].search([('po_id', '=', self.po_id.id), ('state', '!=', 'cancel')])
        # Tính tổng tất cả các phiếu tạm ứng
        if account_advance_ids:
            total_advanced += sum(advance.amount_total for advance in account_advance_ids)
        if total_advanced > self.amount_purchase:
            raise UserError('Bạn không thể tạm ứng số tiền lớn hơn số tiền trên đơn mua')
        else:
            advance_line_ids = []
            for line in self.line_ids:
                advance_line_ids.append((0, 0, {
                    'project_id': line.project_id.id,
                    'total_cost': line.total_cost,
                    'percentage': line.percentage,
                    'amount': self.amount_advanced * line.percentage / 100
                }))

            advanced_val = {
                'type': 'supplier',
                'supplier_id': self.supplier_id.id,
                'po_id': self.po_id.id,
                'advance_amount': self.amount_advanced,
                'reason': self.ref,
                'account_id': self.account_id.id,
                'partner_bank_id':self.po_id.x_partner_bank.id or False,
                'approver_id':self.env.user.employee_id.parent_id.user_id.id,
                'advance_line_ids': advance_line_ids
            }
            advanced_id = self.env['account.advance'].create(advanced_val)
            advanced_id.action_sent_approve()


class AdvancedRegisterLine(models.TransientModel):
    _name = 'account.advance.register.line'
    _description = 'Chi tiết tạm ứng'

    register_id = fields.Many2one('account.advance.register', 'Tạm ứng')
    project_id = fields.Many2one('project.project', 'Dự án')
    total_cost = fields.Float('Chi phí đơn hàng')
    percentage = fields.Float('Tỷ lệ (%)', default=0)
    advance_detail = fields.Float('Số tiền tạm ứng', compute='compute_advance_detail', readonly=False)

    @api.depends('percentage', 'register_id.amount_advanced')
    def compute_advance_detail(self):
        for rec in self:
            rec.advance_detail = rec.register_id.amount_advanced * rec.percentage / 100


class PartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):

        if self._context.get('advance_type', False) or self._context.get('repay_type', False):
            args = args or []
            if self._context.get('advance_type') == 'internal' or self._context.get('repay_type') == 'employee' :
                employee_id = self._context.get('employee_id')
                if not employee_id:
                    raise UserError(_('Chưa chọn nhân viên'))
                partner_id = self.env['res.users'].browse(employee_id).partner_id.id
            else:
                supplier_id = self._context.get('supplier_id')
                if not supplier_id:
                    raise UserError(_('Chưa chọn nhà cung cấp'))
                partner_id = supplier_id

            domain = [('partner_id', '=', partner_id)]

            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return super()._name_search(name, args, operator, limit, name_get_uid)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self._context.get('advance_type', False) or self._context.get('repay_type', False):
            if self._context.get('advance_type') == 'internal' or self._context.get('repay_type') == 'employee':
                employee_id = self._context.get('employee_id')
                if not employee_id:
                    raise UserError(_('Chưa chọn nhân viên'))
                partner_id = self.env['res_users'].browse(employee_id).partner_id.id
            else:
                supplier_id = self._context.get('supplier_id')
                if not supplier_id:
                    raise UserError(_('Chưa chọn nhà cung cấp'))
                partner_id = supplier_id
            domain.append(('partner_id', '=', partner_id))
        return super(PartnerBank, self).search_read(domain, fields, offset, limit, order)


