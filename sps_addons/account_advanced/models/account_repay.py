# -*- coding: utf-8 -*-

import math
from odoo import models, fields, api
from odoo.exceptions import UserError



class AccountAdvanceRepay(models.Model):
    _name = 'account.advance.repay'
    _description = 'Hoàn ứng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'number_ballot'
    _order = 'create_date desc'

    repay_type = fields.Selection([('employee','Nhân viên'),('supplier','Nhà cung cấp')],string='Phân loại',default='employee',required=1)
    supplier_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    amount_total = fields.Monetary(string="Tổng số tiền(VNĐ)", compute='compute_amount', store=True)
    amount_advance = fields.Monetary(string="Số tiền tạm ứng", compute='com_amount_advance', store=True)
    still_pay = fields.Monetary(string="Còn phải thanh toán", compute='compute_amount', store=True)
    deposit_costs = fields.Monetary(string="Số tiền cọc", compute='compute_amount', store=True)

    state = fields.Selection([('draft', 'Nháp'),
                              ('pending', 'Chờ quản lý duyệt'),
                              ('pending_acc', 'Chờ kế toán duyệt'),
                              ('approved', 'Chờ thanh toán'),
                              ('paid_pending', 'Chờ BOD duyệt thanh toán'),
                              ('paid', 'Đã duyệt thanh toán'),
                              ('paid_done', 'Đã thanh toán'),
                              ('cancel', 'Hủy')], default="draft", string="Trạng thái",track_visibility="always")
    x_state = fields.Selection([('0', 'Nháp'),
                              ('1', 'Chờ quản lý duyệt'),
                              ('2', 'Chờ kế toán duyệt'),
                              ('3', 'Chờ thanh toán'),
                              ('4', 'Chờ BOD duyệt thanh toán'),
                              ('5', 'Đã duyệt thanh toán'),
                              ('6', 'Đã thanh toán'),
                              ('7', 'Hủy')], default="0", string="Trạng thái", track_visibility="always", compute="_compute_x_state", store=True)
    employee_id = fields.Many2one('res.users', string='Nhân viên', default=lambda self: self.env.uid, required=True,
                                  store=True)
    advance_account_id = fields.Many2one('account.account', string="Tài khoản tạm ứng", required=True, store=True)
    approver_id = fields.Many2one('res.users', string="Người phê duyệt")
    number_ballot = fields.Char(string="Số phiếu", readonly=True)
    date_suggest = fields.Date(string='Ngày đề nghị', default=fields.Date.today())
    date_repay = fields.Date(string='Ngày hoàn ứng')
    partner_bank_id = fields.Many2one('res.partner.bank', "Số tài khoản")
    beneficiary = fields.Char("Người thụ hưởng")
    bank_id = fields.Many2one('res.bank', 'Ngân hàng')
    diary_id = fields.Many2one('account.journal', string='Sổ nhật kí')
    license_type = fields.Selection([
        ('tax', 'Thuế'),
        ('internal', 'Nội bộ ')], string='Phân loại chứng từ', required=True)
    code_money = fields.Many2one('code.money', string="Mã khoản tiền")
    account_repay_line_ids = fields.One2many('account.repay.line', 'account_repay_id', 'Chi tiết hoàn ứng',copy =True, ondelete='cascade')
    account_account_line_ids = fields.One2many('account.accounting.line', 'repay_id', 'Chi tiết hạch toán',copy=True)
    account_advance_repay_line_ids = fields.One2many('account.advance.repay.line', 'repay_id',
                                                     string="Chi tiết tạm ứng")
    check_user = fields.Boolean('Kiểm tra user', compute="check_user_id")
    check_record = fields.Boolean('Kiểm tra bản ghi', compute="check_user_id")
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    check_accountant = fields.Boolean(compute="check_accountant_id")
    user_setting_id = fields.Boolean(compute="check_accountant_id")
    payment_id = fields.Many2one('account.payment' , string='Phiếu thanh toán', readonly=True,copy=False)
    is_allowed_license_type = fields.Boolean(compute='_compute_allowed_license_type')

    @api.depends('state')
    def _compute_x_state(self):
        state_mapping = {
            'draft': '0',
            'pending': '1',
            'pending_acc': '2',
            'approved': '3',
            'paid_pending': '4',
            'paid': '5',
            'paid_done': '6',
            'cancel': '7',
        }
        for record in self:
            record.x_state = state_mapping.get(record.state, '0')

    def write(self, values):
        res = super(AccountAdvanceRepay, self).write(values)
        payment_vals = {}
        if 'license_type' in values and self.payment_id:
            payment_vals['x_license_type'] = self.license_type
        if 'diary_id' in values and self.payment_id:
            payment_vals['journal_id'] = self.diary_id.id
        if 'code_money' in values and self.payment_id:
            payment_vals['x_code_money'] = self.code_money.id
            # self.payment_id.x_license_type = self.license_type
        self.payment_id.write(payment_vals)
        return res

    def _compute_allowed_license_type(self):
        for r in self:
            if self.user_has_groups('account_advanced.group_allow_change_license_type'):
                r.is_allowed_license_type = True
            else:
                r.is_allowed_license_type = False

    @api.onchange('supplier_id')
    def get_data_default(self):
        for rec in self:
            if rec.supplier_id.is_expense:
                account_repay_line_ids = self.env['account.repay.line'].search(
                    [('supplier_id', '=', rec.supplier_id.id), ('is_expense', '=', True),
                     ('is_the_first','=',True), ('account_repay_id', '!=', False)])

                expense_checked = self.env['account.repay.line'].search([('expense_line_id', 'in', account_repay_line_ids.ids), ('account_repay_id.state', '!=', 'cancel')])
                
                unique_records = []

                for line in account_repay_line_ids.filtered(lambda acc: acc not in expense_checked.expense_line_id):
                    new_record_vals = {
                        'project_id': line.project_id.id,
                        'project_name': line.project_name,
                        'amount_advance': line.amount_advance,
                        'supplier_id': line.supplier_id.id,
                        'date_suggest': line.date_suggest,
                        'date_payment': line.date_payment,
                        'invoice_number': line.invoice_number,
                        'date_invoice': line.date_invoice,
                        'content': line.content,
                        'cost_type_id': line.cost_type_id.id,
                        'account_id': line.account_id.id,
                        'uom_id': line.uom_id.id if line.uom_id else False,
                        'qty': line.qty,
                        'price_unit': - line.price_unit,
                        'vat_ids': line.vat_ids.id if line.vat_ids else False,
                        'note': line.note,
                        'is_expense': line.is_expense,
                        'is_the_first': False,
                        'account_repay_id': rec.id,
                        'expense_line_id': line.id,
                    }

                    new_record = self.env['account.repay.line'].create(new_record_vals)
                    unique_records.append(new_record.id)

                rec.account_repay_line_ids = [(6, 0, unique_records)]

            # else:
            #     rec.write({'account_repay_line_ids': [(6, 0, [])]})

    @api.model
    def check_accountant_id(self):
        for r in self:
            if self.user_has_groups('account.group_account_manager'):
                r.check_accountant = True
            else:
                r.check_accountant = False
            if self.user_has_groups('base.group_erp_manager'):
                r.user_setting_id = True
            else:
                r.user_setting_id = False

    @api.depends("employee_id", "advance_account_id")
    @api.onchange("employee_id", "advance_account_id")
    def onchange_tu(self):
        self.ensure_one()
        if not self.employee_id or not self.advance_account_id:
            self.account_advance_repay_line_ids = False
        else:
            self.account_advance_repay_line_ids = False
            sql = '''SELECT
                          av.id AS so_phieu,
                          av.reason AS li_do,
                          avl.project_id AS ma_du_an,
                          avl.amount AS so_tien,
                          av.date_suggest AS ngay_DN,
                          av.date_advance AS ngay_TU 
                        FROM
                          account_advance_line avl
                          LEFT JOIN account_advance av ON avl.advance_id = av.ID 
                        WHERE
                           av.STATE = 'payment'
                          and av.employee_id = {user_id}
                          and av.account_id = {account_id}'''.format(user_id=self.employee_id.id,
                                                                     account_id=self.advance_account_id.id)
            self._cr.execute(sql)
            recs = self._cr.dictfetchall()
            data = []
            if not recs:
                self.account_advance_repay_line_ids = False
            else:
                for r in recs:
                    data.append((0, 0, {
                        'advance_number': r['so_phieu'],
                        'advance_reason': r['li_do'] or None,
                        'project_id': r['ma_du_an'],
                        'advance_money': r['so_tien'],
                        'date_suggestions': r['ngay_dn'],
                        'date_payment': r['ngay_tu'],

                    }))
            self.account_advance_repay_line_ids = data

    @api.onchange('employee_id','supplier_id')
    def onc_employee_id(self):
        for r in self:
            if r.repay_type =='employee':
                if not r.employee_id.partner_id.property_account_receivable_id.id :
                    raise UserError('Bạn chưa thiết lập tài khoản phải thu cho nhân viên được chọn')
                else:
                    partner_bank_id = False
                    if len(r.employee_id.partner_id.bank_ids.ids) == 0:
                        employee_id = self.env['hr.employee'].search([('user_id', '=', r.employee_id.id)], limit=1)
                        if employee_id and employee_id.x_bank_account:
                            bank_id = self.env['res.bank'].search([('name', '=', employee_id.x_bank_name)], limit=1)
                            if not bank_id:
                                bank_id = self.env['res.bank'].create({'name': employee_id.x_bank_name})
                            partner_bank_id = self.env['res.partner.bank'].search([
                                ('acc_number', '=', employee_id.x_bank_account)
                            ], limit=1)
                            if partner_bank_id:
                                if partner_bank_id.partner_id and partner_bank_id.partner_id.id != r.employee_id.partner_id.id:
                                    raise UserError(f'Đã có nhân viên khác dùng tài khoản ngân hàng này rồi.\n'
                                                    f'Vui lòng kiểm tra lại tài khoản ngân hàng của nhân viên {employee_id.name}')
                                else:
                                    if not partner_bank_id.partner_id:
                                        partner_bank_id.partner_id = r.employee_id.partner_id.id
                            else:
                                partner_bank_id = self.env['res.partner.bank'].create(
                                    {'acc_number': employee_id.x_bank_account,
                                     'bank_id': bank_id.id,
                                     'acc_type': 'bank',
                                     'partner_id': r.employee_id.partner_id.id,
                                     'acc_holder_name': r.employee_id.partner_id.name}).id
                    else:
                        partner_bank_id = r.employee_id.partner_id.bank_ids.ids[0]
                    r.partner_bank_id = partner_bank_id
                    r.approver_id = r.employee_id.employee_id.parent_id.user_id.id
                    account_id = self.env['account.account'].search([('code', '=', '141')], limit =1)
                    if not account_id:
                        raise UserError('Bạn chưa thiết lập tài khoản tạm ứng 141')
                    else:
                        r.advance_account_id = account_id.id
            else:
                if not r.supplier_id.property_account_receivable_id.id:
                    raise UserError('Bạn chưa thiết lập tài khoản phải trả cho nhà cung cấp được chọn')
                else:
                    r.partner_bank_id = r.supplier_id.bank_ids.ids[0] if len(r.supplier_id.bank_ids.ids) >0 else False
                    r.advance_account_id = r.supplier_id.property_account_payable_id.id
                    r.approver_id = self.env.user.employee_id.parent_id.user_id.id

    @api.constrains('account_repay_line_ids', 'diary_id', 'advance_account_id')
    def check_user_id(self):
        for r in self:
            if r.approver_id.id == self.env.uid:
                r.check_user = True
            else:
                r.check_user = False
            if r.id:
                r.check_record = True
                r.account_account_line_ids = False
                sql = f'''
                        SELECT
                            account_id,
                            project_id,
                            CASE WHEN SUM(amount_untaxed) < 0 THEN ABS(SUM(amount_untaxed)) ELSE 0 END AS credit,
                            CASE WHEN SUM(amount_untaxed) > 0 THEN SUM(amount_untaxed) ELSE 0 END AS debit
                        FROM
                            account_repay_line arl
                            LEFT JOIN account_advance_repay arr ON arr.ID = arl.account_repay_id
                        WHERE
                            arr.ID = {r.id}
                        GROUP BY
                            account_id,
                            project_id
                        UNION ALL
                        SELECT
                            atrl.account_id,
                            NULL AS project_id,
                            CASE WHEN SUM(amount_tax - amount_untaxed) < 0 THEN ABS(SUM(amount_tax - amount_untaxed)) ELSE 0 END AS credit,
                            CASE WHEN SUM(amount_tax - amount_untaxed) > 0 THEN SUM(amount_tax - amount_untaxed) ELSE 0 END AS debit
                        FROM
                            account_repay_line arl
                            LEFT JOIN account_tax AT ON arl.vat_ids = AT.
                            ID LEFT JOIN account_advance_repay arr ON arr.ID = arl.account_repay_id
                            LEFT JOIN account_tax_repartition_line atrl ON atrl.invoice_tax_id = AT.ID
                            AND atrl.repartition_type = 'tax'
                        WHERE
                            arr.ID = {r.id}
                        GROUP BY
                            atrl.account_id 
                        UNION ALL
                        SELECT
                            aar.advance_account_id account_id,
                            NULL AS project_id,
                            aar.amount_advance credit,
                            0 AS debit
                        FROM
                            account_advance_repay aar
                        WHERE

                            aar.ID = {r.id}  
                        UNION ALL
                        SELECT
                            aa.ID,
                            NULL AS project_id,
                            ( CASE WHEN aar.still_pay < 0 THEN abs(aar.still_pay) ELSE 0 END ) AS credit,
                            0 AS debit
                        FROM
                            account_advance_repay aar
                            LEFT JOIN account_journal aj ON aar.diary_id = aj.
                            ID LEFT JOIN account_account aa ON aa.ID = aj.default_account_id
                        WHERE

                            aar.ID = {r.id}
                        '''
                self._cr.execute(sql)
                recs = self._cr.dictfetchall()
                order_line = []

                if r.still_pay > 0:
                    order_line.append((0, 0, {
                        'acc_id': r.diary_id.default_account_id.id,
                        'project_id': False,
                        'credit': 0,
                        'debit': r.still_pay,
                    }))
                if recs:
                    for rec in recs:
                        if not rec['account_id'] or rec['credit'] == 0 and rec['debit'] == 0:
                            continue
                        order_line.append((0, 0, {
                            'acc_id': rec['account_id'],
                            'project_id': rec['project_id'],
                            'credit': rec['credit'],
                            'debit': rec['debit'],
                        }))
                self.account_account_line_ids = order_line
            else:
                r.check_record = False

    @api.model
    def create(self, vals):
        vals['number_ballot'] = self.env['ir.sequence'].next_by_code('account_advance_repay')
        return super(AccountAdvanceRepay, self).create(vals)

    @api.onchange('partner_bank_id')
    def onchange_bank_id(self):
        for r in self:
            if r.partner_bank_id:
                r.beneficiary = r.partner_bank_id.acc_holder_name if r.partner_bank_id.acc_holder_name else r.partner_bank_id.partner_id.name
                r.bank_id = r.partner_bank_id.bank_id
            else:
                r.beneficiary = False
                r.bank_id = False

    def action_send(self):
        for r in self:
            if r.state == 'draft':
                r.state = 'pending'
            else:
                continue

    def prepare_project_repay(self,repay_id,arg):
        sql = f'''SELECT  du_an as project_id,sum (so_tien) as amount_repay 
                    from 
                        (SELECT
                         pp.x_order_id as du_an ,aar.advance_money as so_tien
                        FROM
                            account_advance_repay_line aar 
                            LEFT JOIN project_project pp on aar.project_id = pp.id 
                        WHERE
                            repay_id = {repay_id}
                        UNION all
                        SELECT
                             pp.x_order_id as du_an, -arl.amount_tax as so_tien
                        FROM
                            account_repay_line arl 
                            LEFT JOIN project_project pp on arl.project_id = pp.id 
                        WHERE
                            arl.account_repay_id = {repay_id}
                            )t1
                    GROUP BY du_an'''
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        project_repay = []
        if res:
            for r in res:
                project_repay.append((0, 0, {
                    'main_project': r['project_id'],
                    'amount_repay': r['amount_repay'] * arg
                }))
        return project_repay

    def action_approve(self):
        for rec in self:
            if rec.state == 'pending':
                if rec.check_user or rec.user_setting_id:
                    rec.state = 'pending_acc'
                else:
                    raise UserError('Bạn không đủ quyền hạn để duyệt phiếu hoàn ứng này !')
            elif rec.state == 'pending_acc':
                if rec.check_accountant:
                    rec.state = 'approved'
                else:
                    raise UserError('Bạn không đủ quyền hạn để duyệt phiếu hoàn ứng này. Hãy liên hệ với kế toán')
            elif rec.state == 'paid_pending':
                if not self.env.user.has_group('base.group_erp_manager'):
                    raise UserError('Bạn không đủ quyền hạn để duyệt phiếu hoàn ứng này !')
                line_ids = []
                self._cr.execute(f'''
                                    SELECT
                                            case when aar.repay_type = 'employee' then rp.id else aar.supplier_id end as id,
                                            atrl.account_id acc_id,
                                            'tax' AS cost_type,
                                            ABS ( SUM ( amount_untaxed - amount_tax ) ) so_tien 
                                        FROM
                                            account_repay_line arl
                                            INNER JOIN account_advance_repay aar ON arl.account_repay_id = aar.ID 
                                            LEFT JOIN res_users ru on ru.id = aar.employee_id 
                                            LEFT JOIN res_partner rp on rp.id = ru.partner_id
                                            LEFT JOIN account_tax AT ON arl.vat_ids = AT.ID 
                                            LEFT JOIN account_tax_repartition_line atrl ON atrl.invoice_tax_id = AT.ID 
                                            AND atrl.repartition_type = 'tax' 
                                        WHERE
                                            aar.ID = {rec.id}
                                        GROUP BY
                                            atrl.account_id,rp.id,aar.repay_type ,aar.supplier_id 
                                            
                                            UNION all
                                            
                                        SELECT
                                            case when aar.repay_type = 'employee' then rp.id else aar.supplier_id end as id,
                                            aa.ID,
                                            'expense' AS cost_type,
                                            SUM ( arl.amount_untaxed ) so_tien 
                                        FROM
                                            account_repay_line arl
                                            INNER JOIN account_advance_repay aar ON arl.account_repay_id = aar.ID  
                                            LEFT JOIN res_users ru on ru.id = aar.employee_id
                                            LEFT JOIN res_partner rp on rp.id = ru.partner_id
                                            LEFT JOIN account_account aa ON aa.code = 'TGCP' 
                                        WHERE
                                            aar.ID = {rec.id}
                                        GROUP BY
                                            aa.ID,  rp.id,aar.repay_type,aar.supplier_id
                                        ORDER BY acc_id DESC
                                        ''')

                recs = self._cr.dictfetchall()
                if not recs:
                    raise UserError('Kiểm tra lại chi tiết hoàn ứng !')
                move_amount = rec.amount_advance # giá trị bút toán
                pay_lines = []  # dòng hạch toán
                index = 0
                # dòng bút toán
                if min(rec.amount_total, rec.amount_advance) < 0:
                    line_ids.append((0, 0, {
                        'account_id': rec.advance_account_id.id,
                        'debit': abs(min(rec.amount_total, rec.amount_advance)),
                        'credit': 0,
                        'partner_id': recs[0]['id'] or None
                    }))
                    for r in recs:
                        index += 1
                        if not r['acc_id']:
                            continue
                        move_amount -= round(r['so_tien'])
                        if move_amount >= 0:
                            line_ids.append((0, 0, {
                                'account_id': r['acc_id'],
                                'debit': 0,
                                'credit': abs(round(r['so_tien'])),
                                'partner_id': r['id']
                            }))
                        if move_amount < 0:
                            line_ids.append((0, 0, {
                                'account_id': r['acc_id'],
                                'debit': 0,
                                'credit': abs(round(r['so_tien'] + move_amount)),
                                'partner_id': r['id']
                            }))
                            pay_lines = recs[index:]
                            pay_lines.append(({
                                'acc_id': r['acc_id'],
                                'so_tien': -move_amount,
                                'code_type': False,
                            }))
                            break
                else:
                    line_ids.append((0, 0, {
                        'account_id': rec.advance_account_id.id,
                        'debit': 0,
                        'credit': min(rec.amount_total, rec.amount_advance),
                        'partner_id': recs[0]['id'] or None
                    }))
                    for r in recs:
                        index += 1
                        if not r['acc_id']:
                            continue
                        move_amount -= round(r['so_tien'])
                        if move_amount >= 0:
                            line_ids.append((0, 0, {
                                'account_id': r['acc_id'],
                                'debit': abs(round(r['so_tien'])),
                                'credit': 0,
                                'partner_id': r['id']
                            }))
                        if move_amount < 0:
                            line_ids.append((0, 0, {
                                'account_id': r['acc_id'],
                                'debit': abs(round(r['so_tien'] + move_amount)),
                                'credit': 0,
                                'partner_id': r['id']
                            }))
                            pay_lines = recs[index:]
                            pay_lines.append(({
                                'acc_id': r['acc_id'],
                                'so_tien': -move_amount,
                                'code_type': False,
                            }))
                            break
                # biến bút toán
                move_values = {
                    'line_ids': line_ids,
                    'ref': rec.number_ballot,
                    'date': fields.date.today(),
                    'move_type': 'entry',
                    'journal_id': 3
                }
                move_id = self.env['account.move'].create(move_values)
                move_id.action_post()
                self._cr.execute(f'''
                                UPDATE account_advance aa
                                SET state = 'completed'
                                from(
                                SELECT
                                    distinct(aa.id)
                                FROM
                                    account_advance_repay adr 
                                    LEFT JOIN account_advance_repay_line aarl ON adr.id = aarl.repay_id 
                                    LEFT JOIN account_advance aa ON aa.id = aarl.advance_number
                                WHERE adr.id = {rec.id}
                                ) as table1 (id)
                                WHERE aa.id = table1.id
                                ''')
                payment_val = {}
                if rec.still_pay > 0:
                    # Kiểm tra destination_account_id
                    destination_account_id = False
                    if rec.account_advance_repay_line_ids and rec.account_advance_repay_line_ids[0].advance_number and rec.account_advance_repay_line_ids[0].advance_number.account_id:
                        destination_account_id = rec.account_advance_repay_line_ids[0].advance_number.account_id.id
                    elif rec.advance_account_id:
                        destination_account_id = rec.advance_account_id.id
                    
                    if not destination_account_id:
                        raise UserError('Không tìm thấy tài khoản đích cho payment. Vui lòng kiểm tra lại thông tin tạm ứng.')
                    
                    payment_val = {
                        'payment_type': 'inbound',
                        'partner_type': 'supplier' if any(al.is_expense for al in self.account_repay_line_ids) else 'customer',
                        'x_license_type':rec.license_type,
                        'x_code_money':rec.code_money.id,
                        'destination_account_id': destination_account_id,
                        'is_internal_transfer': False,
                        'x_pay_cost': False,
                        'partner_id': rec.employee_id.partner_id.id,
                        'x_origin_repay_id': rec.id,
                        'ref': 'Thu hồi tiền tạm ứng theo phiếu ' + rec.number_ballot,
                        'journal_id': rec.diary_id.id,
                        'x_project_repay_ids': self.prepare_project_repay(rec.id,1),
                        'partner_bank_id': False,
                        'amount': rec.still_pay,
                        'x_address': rec.supplier_id.name if rec.supplier_id else '',
                        'x_amount_override': rec.still_pay
                    }
                elif rec.still_pay < 0:
                    payment_lines = []
                    for r in pay_lines:
                        if not r['acc_id']: continue
                        payment_lines.append((0, 0, {
                            'account_id': r['acc_id'],
                            'partner_id': False,
                            'content': None,
                            'amount': r['so_tien']
                        }))
                    payment_val = {
                        'payment_type': 'outbound',
                        'partner_type': 'supplier',
                        'x_pay_cost': True,
                        'x_approved_state': 'approved',
                        'x_license_type': rec.license_type,
                        'x_code_money': rec.code_money.id,
                        'partner_id': rec.employee_id.partner_id.id if rec.repay_type == 'employee' else rec.supplier_id.id,
                        'x_origin_repay_id': rec.id,
                        'ref': 'Hoàn ứng số tiền còn phải thanh toán theo phiếu ' + rec.number_ballot,
                        'journal_id': rec.diary_id.id,
                        'partner_bank_id': rec.partner_bank_id.id,
                        'x_payment_line_ids': payment_lines,
                        'x_project_repay_ids': self.prepare_project_repay(rec.id, -1),
                        'amount': sum(r['so_tien'] for r in pay_lines),
                        'x_address': rec.supplier_id.name if rec.supplier_id else '',
                        'x_amount_override': sum(r['so_tien'] for r in pay_lines)
                    }
                else:
                    rec.state = 'paid'
                    continue
                payment = self.env['account.payment'].create(payment_val)
                rec.payment_id = payment.id
                rec.state = 'paid'
            else:
                continue

    def action_cancel(self):
        for r in self:
            if r.state in ['pending', 'pending_acc']:
                r.state = 'cancel'
            elif r.state == 'paid_pending':
                r.state = 'approved'
            else:
                continue

    def action_draft(self):
        for r in self:
            if r.state in ['pending', 'pending_acc', 'cancel']:
                r.state = 'draft'
            else:
                continue

    def action_payment(self):
        for rec in self:
            if rec.state == 'approved':
                if not rec.diary_id or not rec.code_money:
                    raise UserError('Bạn cần điền thông tin sổ nhật kí và mã khoản tiền ')
                else:
                    rec.state = 'paid_pending'
            else:
                continue

    def unlink(self):
        for r in self:
            if r.state not in ['draft']:
                raise UserError("Không thể xóa bản ghi này.")
            else:
                return super(AccountAdvanceRepay, self).unlink()

    @api.depends('account_repay_line_ids', 'amount_advance', 'amount_total')
    @api.onchange('account_repay_line_ids', 'amount_advance', 'amount_total')
    def compute_amount(self):
        for r in self:
            r.amount_total = sum(r.account_repay_line_ids.mapped('amount_tax'))
            r.deposit_costs = sum(r.account_repay_line_ids.filtered(lambda x: x.is_expense == True and x.is_the_first == False).mapped('amount_tax'))
            r.still_pay =  r.amount_advance - r.amount_total

    @api.depends('account_advance_repay_line_ids')
    @api.onchange('account_advance_repay_line_ids')
    def com_amount_advance(self):
        for r in self:
            r.amount_advance = sum(line.advance_money for line in r.account_advance_repay_line_ids)

    def _update_name_project(self):
        ar_ids = self.search([])
        for ar_id in ar_ids:
            ar_id.account_repay_line_ids._compute_project_name()
            ar_id.account_account_line_ids._compute_project_name()
            ar_id.account_advance_repay_line_ids._compute_project_name()


class AccountRepayLine(models.Model):
    _name = 'account.repay.line'
    _description = 'Chi tiết hoàn ứng'

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    account_repay_id = fields.Many2one('account.advance.repay', string="Phiếu hoàn ứng")
    project_id = fields.Many2one('project.project', string="Mã dự án", required=True)
    project_name = fields.Char(string='Tên dự án', compute="_compute_project_name", store=1)
    amount_advance = fields.Float(string='Số tiền tạm ứng')
    supplier_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    date_suggest = fields.Date(string='Ngày đề nghị')
    date_payment = fields.Date(string='Ngày chi tiền')
    invoice_number = fields.Char(string="Số hoá đơn")
    date_invoice = fields.Date(string="Ngày hoá đơn")
    content = fields.Char(string="Nội dung", required=True)
    cost_type_id = fields.Many2one('cost.type', string="Phân loại chi phí", required=True)
    account_id = fields.Many2one('account.account', string="TK hạch toán", readonly=True)
    uom_id = fields.Many2one('uom.uom', string="Đơn vị tính")
    qty = fields.Float(string="Số lượng")
    price_unit = fields.Float(string='Đơn giá')
    amount_untaxed = fields.Float(string="Thành tiền trước thuế", compute='com_amount_untaxed', store=True)
    vat_ids = fields.Many2one("account.tax", string="VAT", store=True)
    amount_tax = fields.Monetary(string="Thành tiền sau thuế", compute='com_amount_untaxed', store=True)
    note = fields.Char(string="Ghi chú")
    is_expense = fields.Boolean('Chi phí cọc',default=False, copy=False)
    is_the_first = fields.Boolean('Chi phí cọc mới',default=False, copy=False)
    expense_line_id = fields.Many2one('account.repay.line')

    @api.onchange('is_the_first')
    def onchange_is_the_first(self):
        for rec in self:
            if rec.is_the_first:
                rec.is_expense = True
            else:
                rec.is_expense = False

    @api.depends('project_id', 'project_id.label_tasks')
    def _compute_project_name(self):
        for rec in self:
            rec.project_name = rec.project_id.label_tasks
    @api.depends('qty', 'price_unit', 'vat_ids')
    @api.onchange('qty', 'price_unit', 'vat_ids')
    def com_amount_untaxed(self):
        for r in self:
            if r.qty and r.price_unit:
                r.amount_untaxed = r.qty * r.price_unit
                r.amount_tax = r.amount_untaxed * (1 + r.vat_ids.amount / 100)

    @api.onchange('project_id')
    def onchange_project_id(self):
        for r in self:
            if r.project_id:
                r.project_name = r.project_id.label_tasks
            else:
                continue

    @api.onchange('cost_type_id')
    def onc_cost_type_id(self):
        for r in self:
            r.account_id = self.cost_type_id.account_id


class AccountAdvanceRepayLine(models.Model):
    _name = 'account.advance.repay.line'
    _description = "Danh sách tạm ứng"

    advance_number = fields.Many2one('account.advance', string="Số yêu cầu tạm ứng")
    advance_reason = fields.Char(string="Lý do tạm ứng")
    project_id = fields.Many2one('project.project', string="Mã dự án")
    project_name = fields.Char(string="Tên dự án", compute='_compute_project_name', store=1)
    advance_money = fields.Float(string="Số tiền tạm ứng")
    date_suggestions = fields.Date("Ngày đề nghị")
    date_payment = fields.Date("Ngày chi tiền")
    repay_id = fields.Many2one('account.advance.repay', 'Phiếu hoàn ứng')

    @api.depends('project_id', 'project_id.label_tasks')
    def _compute_project_name(self):
        for rec in self:
            rec.project_name = rec.project_id.label_tasks

class AccountAccountingLine(models.Model):
    _name = "account.accounting.line"
    _description = "Hạch toán hoàn ứng"

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    acc_id = fields.Many2one('account.account', string="Tài khoản")
    debit = fields.Monetary(string="Nợ")
    credit = fields.Monetary(string="Có")
    project_id = fields.Many2one('project.project', string="Mã dự án")
    project_name = fields.Char(string="Tên dự án", compute='_compute_project_name', store=1)
    repay_id = fields.Many2one("account.advance.repay", string="Hoàn ứng")

    @api.depends('project_id', 'project_id.label_tasks')
    def _compute_project_name(self):
        for rec in self:
            rec.project_name = rec.project_id.label_tasks
    @api.onchange('project_id')
    def onchange_project_2(self):
        for rec in self:
            if rec.project_id:
                rec.project_name = rec.project_id.label_tasks
            else:
                continue
