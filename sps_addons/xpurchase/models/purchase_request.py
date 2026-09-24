# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class RequestPurchase(models.Model):
    _inherit = 'purchase.requisition'

    x_state = fields.Selection([('draft', 'Nháp'),
                                ('pending', 'Chờ duyệt'),
                                ('official', 'Đã phê duyệt'),
                                ('going', 'Đang thực hiện'),
                                ('done', 'Hoàn thành'),
                                ('cancel', 'Huỷ'),
                                ('pause', 'Tạm hoãn')], default="draft", string="Trạng thái", copy=False)
    x_check_user = fields.Boolean(string="check", compute="action_check")
    x_purpose = fields.Selection([
        ('project', 'Dự án'),
        ('other', 'Mục đích khác'),
        ('replenish_inventory', 'Bổ sung tồn kho')], string="Mục đích", required="1", default="project")
    x_code_project_id = fields.Many2one('project.project', string="Mã dự án", required=1)
    x_name_project = fields.Char("Tên dự án", compute='_compute_x_name_project', store=1)
    x_estimator = fields.Many2one('res.users',
        string='Người lập dự toán',
        compute = 'compute_estimator',
        store =True
    )
    x_cost_source = fields.Selection([('estimating_item', 'Hạng mục trong dự toán'),
                                      ('out_of_budget', 'Hạng mục phát sinh ngoài dự toán với lý do dưới đây'),
                                      ('approved', 'Hạng mục trong ngân sách cần phê duyệt'),
                                      ('offer', 'Hạng mục không có ngân sách nhưng đã đề xuất dưới đây')],
                                     'Nguồn chi phí', store=True)
    x_cost_project = fields.Selection([
        ('estimating_item', 'Hạng mục trong dự toán'),
        ('out_of_budget', 'Hạng mục phát sinh ngoài tự toán với lý do dưới đây')],
        string="Nguồn chi phí", store=True)
    x_cost_other = fields.Selection([
        ('approved', 'Hạng mục trong ngân sách cần phê duyệt'),
        ('offer', 'Hạng mục không có ngân sách nhưng đã đề xuất dưới đây')],
        string="Nguồn chi phí", store=True)
    x_reason = fields.Char('Lý do')
    x_request_address = fields.Selection([
        ('sps', 'Chuyển về kho SPS'),
        ('other', 'Giao tới địa chỉ khác')],
        string="Yêu cầu về địa điểm nhận hàng")
    x_address_ship = fields.Char(string='Địa chỉ giao hàng')
    x_info_receiver = fields.Many2one('hr.employee', string='Thông tin người nhận hàng (Nếu có)',
                                      domain=[('active', '=', 't')])
    ordering_date = fields.Date(default=fields.Date.today)
    schedule_date = fields.Date(default=fields.Date.today)
    x_puchase_requisiton_ids = fields.One2many('purchase.requisition.line', 'x_purchase_requisition_id', 'Lines')

    def _get_picking_in(self):
        pick_in = self.env.ref('stock.picking_type_in', raise_if_not_found=False)
        company = self.env.company
        if not pick_in or not pick_in.sudo().active or pick_in.sudo().warehouse_id.company_id.id != company.id:
            pick_in = self.env['stock.picking.type'].search([('x_type', '=', 'type_1')],
                                                            limit=1,
                                                            )
        return pick_in

    @api.depends('x_code_project_id', 'x_code_project_id.label_tasks')
    def _compute_x_name_project(self):
        for rec in self:
            rec.x_name_project = rec.x_code_project_id.label_tasks
    @api.onchange('x_cost_project')
    def onchange_project2(self):
        for rec in self:
            if rec.x_cost_project == 'estimating_item':
                rec.x_cost_source = 'estimating_item'
            elif rec.x_cost_project == 'out_of_budget':
                rec.x_cost_source = 'out_of_budget'

    @api.onchange('x_cost_other')
    def onchange_project1(self):
        for rec in self:
            if rec.x_cost_other == 'approved':
                rec.x_cost_source = 'approved'
            elif rec.x_cost_other == 'offer':
                rec.x_cost_source = 'offer'

    @api.onchange('x_code_project_id')
    def onchange_project3(self):
        for r in self:
            if r.x_code_project_id:
                r.x_name_project = r.x_code_project_id.label_tasks
                # if r.x_code_project_id.x_order_id and r.x_code_project_id.sudo().x_order_id.solution_maker:
                #     r.x_estimator = r.x_code_project_id.sudo().x_order_id.solution_maker
                # else: r.x_estimator = False
            else:
                r.x_name_project = False
        lines = [(5, 0)]
        for r in self.x_code_project_id.x_material_estimate_ids:
            lines.append((0, 0, {
                'product_id': r.product_id,
                'product_uom_id': r.uom_id,
                'product_qty': r.amount,
                'price_unit': r.unit_price,
                'x_default_code': r.product_id.x_code_brand,
                'x_brand': r.product_id.x_product_company
            }))
        self.line_ids = lines

    def action_check(self):
        x = self.env.user.has_group('purchase.group_purchase_manager')
        for r in self:
            r.x_check_user = r.x_state == 'pending' and x

    @api.depends('x_code_project_id')
    def compute_estimator(self):
        for r in self:
            if r.x_code_project_id.x_order_id and r.x_code_project_id.sudo().x_order_id.solution_maker:
                r.x_estimator = r.x_code_project_id.sudo().x_order_id.solution_maker
            else:
                r.x_estimator = False

    @api.onchange('x_purpose')
    def onchange_purpose(self):
        for r in self:
            r.x_cost_project = False
            r.x_cost_other = False
            r.x_cost_source = False

    @api.onchange('x_request_address')
    def request_address(self):
        for r in self:
            if r.x_request_address == 'sps':
                r.x_address_ship = 'Tầng 1, Tòa VG, ngõ 235 Nguyễn Trãi, Phường Khương Đình, Hà Nội'
            else:
                r.x_address_ship = False

    def action_send_browsing(self):
        for r in self:
            if r.x_state == 'draft':
                r.x_state = 'pending'
            else:
                continue

    def action_approve(self):
        for r in self:
            if r.x_state == 'pending':
                r.x_state = 'official'
            else:
                continue

    def check_x_state_1(self, pa_ids):
        self._cr.execute('''update purchase_requisition pr 
                         set x_state = 'going'
                           from (
                               SELECT pr.id, count(pol.id) FROM purchase_requisition pr 
                                    LEFT JOIN purchase_requisition_line prl ON pr.id = prl.requisition_id
                                    LEFT JOIN pa_line_po_line_ref rel ON prl.id = rel.pa_line_id
                                    LEFT JOIN purchase_order_line pol ON pol.id = rel.po_line_id
                                    LEFT JOIN purchase_order po ON pol.order_id = po.id
                                    WHERE pr.id in %s 
                                    group by pr.id
                            ) pr1 (pr_id, count)
                            where count > 0
                                    and pr.id = pr1.pr_id''', [tuple(pa_ids + [0, 0])])

    def check_x_state(self):
        self._cr.execute(''' update purchase_requisition 
                             set x_state = 'done' , state = 'done'
                             where id in (
                                select distinct A.requisition_id from 
                                    (
                                     select 
                                      prl.requisition_id , pr.x_state  , sum(case when prl.product_qty > coalesce(prl.qty_done,0) then 1 else 0 end) as count1
                                     from purchase_requisition_line prl
                                     left join purchase_requisition pr on pr.id = prl.requisition_id 
                                     group by prl.requisition_id , pr.x_state
                                    ) A
                                where A.count1 = 0
                                )''')

    def check_x_state2(self):
        self._cr.execute(''' update purchase_requisition 
                             set x_state = 'going' , state = 'ongoing'
                             where id in (
                                Select DISTINCT(pr.id) 
                                FROM purchase_requisition pr 
                                    INNER JOIN purchase_requisition_line prl ON pr.id = prl.requisition_id 
                                    WHERE coalesce(prl.qty_done,0) < prl.product_qty 
                                           AND (pr.x_state = 'done' or pr.state='done')
                                )''')

    def action_refuse(self):
        for r in self:
            if r.x_state == 'pending':
                r.x_state = 'cancel'
            else:
                continue

    def action_back_draft(self):
        for r in self:
            if r.x_state != 'done':
                r.x_state = 'draft'
            else:
                continue

    def action_pause(self):
        for r in self:
            if r.x_state != 'done':
                r.x_state = 'pause'
            else:
                continue

    def action_continue(self):
        for rec in self:
            sql = f'''select count(po.id) from purchase_requisition pr
                        left join purchase_requisition_line prl on pr.id=prl.requisition_id
                        left join pa_line_po_line_ref rel on prl.id=rel.pa_line_id
                        left join purchase_order_line pol on rel.po_line_id=pol.id
                        left join purchase_order po on po.id=pol.order_id
                        where true and pr.id={rec.id}'''
            self._cr.execute(sql)
            bod_partners = self._cr.dictfetchall()
            if bod_partners[0]['count'] == 0:
                rec.x_state = "official"
            else:
                rec.x_state = 'going'

    def cancel_action(self):
        for r in self:
            if r.x_state != 'done':
                r.x_state = 'cancel'
            else:
                continue

    def action_reset_draft(self):
        self.ensure_one()
        if self.x_state in ('pending', 'official'):
            self.write({'x_state': 'draft'})
        else:
            raise UserError('Không thể chuyển về nháp')

    def unlink(self):
        for r in self:
            if r.x_state in ['cancel', 'pending', 'official', 'going', 'pause', 'done']:
                raise UserError("Không được xoá bản ghi này.")
        return super(RequestPurchase, self).unlink()

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition')
        return super(RequestPurchase, self).create(vals)

    @api.model
    def fields_get(self, fields=None):
        hide = ['state']
        res = super(RequestPurchase, self).fields_get()
        for field in hide:
            res[field]['searchable'] = False
        return res

    def _update_name_project(self):
        pr_ids = self.search([])
        for pr_id in pr_ids:
            pr_id._compute_x_name_project()


class RequestPurchaseLine(models.Model):
    _inherit = 'purchase.requisition.line'

    x_cost_classification_id = fields.Many2one('cost.type', string="Phân loại chi phí")
    x_default_code = fields.Char('Mã hiệu')
    x_brand = fields.Char('Thương hiệu')
    x_origin = fields.Char('Xuất xứ')
    x_source = fields.Char('Nguồn cấp tham khảo')
    qty_done = fields.Float('Số lượng hoàn thành', readonly="1", copy=False)
    x_po_lines = fields.Many2many('purchase.order.line', 'pa_line_po_line_ref', 'pa_line_id', 'po_line_id',
                                  'Dòng đơn mua', copy=False)
    x_po_ids = fields.Many2many('purchase.order', 'pa_line_po_ref', 'pa_line_id', 'po_id', string='Đơn đặt hàng', compute='compute_po' )
    qty_ordered = fields.Float(store=True)
    x_note = fields.Char('Ghi chú')
    x_purchase_requisition_id = fields.Many2one('purchase.requisition', 'Yêu cầu báo giá')

    @api.onchange('product_id')
    def onchange_product(self):
        for r in self:
            if r.product_id:
                r.x_default_code = r.product_id.product_tmpl_id.x_code_brand
                r.x_brand = r.product_id.product_tmpl_id.x_product_company
            else:
                r.x_default_code = False
                r.x_brand = False

    @api.model
    def update_qty_done(self, list):
        for r in self.browse(list):
            return

    @api.depends('x_po_lines')
    def compute_po(self):
        for r in self:
            po_list =[]
            for line in r.x_po_lines:
                if line.order_id.x_state not in ('draft','cancel'):
                   po_list.append(line.order_id.id)
            r.x_po_ids =[(6, 0, po_list)]

    @api.depends('x_po_lines', 'x_po_lines.product_qty', 'x_po_lines.order_id.x_state')
    def _compute_ordered_qty(self):
        for r in self:
            r.qty_ordered = sum(
                line.product_qty for line in r.x_po_lines if line.order_id.x_state not in ('draft', 'cancel')
            )

    def update_qty(self):
        for r in self:
            r.qty_ordered = sum(
                line.product_qty for line in r.x_po_lines
                if line.order_id.x_state not in ('draft', 'cancel')
            )

    def _get_committed_qty(self):
        """Số lượng đã mua thực tế: tổng số lượng trên các dòng đơn mua đã xác nhận,
        loại trừ đơn ở trạng thái nháp và huỷ."""
        self.ensure_one()
        return sum(
            pol.product_qty for pol in self.x_po_lines
            if pol.order_id.x_state not in ('draft', 'cancel')
        )

    def action_open_change_qty_wizard(self):
        self.ensure_one()
        return {
            'name': 'Thay đổi số lượng cần mua',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition.line.qty.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_current_qty': self.product_qty,
                'default_new_qty': self.product_qty,
                'default_qty_ordered': self._get_committed_qty(),
                'default_qty_done': self.qty_done,
            },
        }