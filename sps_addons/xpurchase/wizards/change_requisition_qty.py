# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class ChangeRequisitionQtyWizard(models.TransientModel):
    _name = 'purchase.requisition.line.qty.wizard'
    _description = 'Thay đổi số lượng cần mua'

    line_id = fields.Many2one('purchase.requisition.line', string='Dòng yêu cầu mua',
                              required=True, readonly=True, ondelete='cascade')
    requisition_id = fields.Many2one(related='line_id.requisition_id', string='Đề xuất mua', readonly=True)
    product_id = fields.Many2one(related='line_id.product_id', string='Sản phẩm', readonly=True)
    product_uom_id = fields.Many2one(related='line_id.product_uom_id', string='ĐVT', readonly=True)
    current_qty = fields.Float('Số lượng cần mua hiện tại', readonly=True)
    qty_ordered = fields.Float('Đã đặt mua (đơn đã xác nhận)', readonly=True)
    qty_done = fields.Float('Đã nhận', readonly=True)
    new_qty = fields.Float('Số lượng cần mua mới', required=True)
    reason = fields.Text('Lý do thay đổi', required=True)

    def action_change_qty(self):
        self.ensure_one()
        line = self.line_id
        if not line:
            raise UserError('Không tìm thấy dòng yêu cầu mua.')
        rounding = line.product_uom_id.rounding or 0.01
        new_qty = self.new_qty

        if float_compare(new_qty, 0.0, precision_rounding=rounding) < 0:
            raise UserError('Số lượng cần mua không được âm.')

        # Số lượng đã mua thực tế trên các đơn đã xác nhận (loại trừ nháp & huỷ)
        committed = line._get_committed_qty()
        if float_compare(new_qty, committed, precision_rounding=rounding) < 0:
            raise UserError(
                'Không thể giảm số lượng cần mua xuống %s vì đã đặt mua %s trên các đơn '
                'đã xác nhận. Số lượng mới phải lớn hơn hoặc bằng số đã đặt.'
                % (new_qty, committed)
            )

        old_qty = line.product_qty
        if float_compare(new_qty, old_qty, precision_rounding=rounding) == 0:
            return {'type': 'ir.actions.act_window_close'}

        line.product_qty = new_qty

        uom_name = line.product_uom_id.name or ''
        body = (
            'Thay đổi số lượng cần mua dòng <b>%s</b>: '
            '<span style="text-decoration: line-through;">%s</span> &rarr; <b>%s</b> %s'
            '<br/>Lý do: %s'
        ) % (line.product_id.display_name or '', old_qty, new_qty, uom_name, self.reason)
        line.requisition_id.message_post(body=body)

        return {'type': 'ir.actions.act_window_close'}
