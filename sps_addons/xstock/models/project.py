# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo.osv import expression


class Project(models.Model):
    _inherit = 'project.project'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):

        if self._context.get('x_project_by_payer', False) and self._context.get('type') in ('type_5','type_6'):
            args = args or []
            domain=[]
            payer_id = self._context.get('payer_id')
            product_id = self._context.get('product_id')
            lot_id = self._context.get('lot_id')
            if not payer_id:
                raise UserError(_('Chưa chọn người trả'))
            if not product_id:
                raise UserError(_('Chưa chọn sản phẩm'))
            records = self.env['stock.borrow.tools'].sudo().search([
                ('product_id', '=', product_id),
                ('lot_id', '=', lot_id),
                ('receiver_id', '=', payer_id),
                ('amount', '>', 0),
            ])
            domain = [('id', 'in', [x.project_id.id for x in records])]

            return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

        return super()._name_search(name, args, operator, limit, name_get_uid)

    def _get_unreturned_ccdc(self):
        """Trả về các dòng project.depreciation.line còn 'open' (đang mượn)
        của các dự án trong self. Đây là CCDC chưa được trả/thu hồi hết,
        khớp đúng với danh sách hiển thị ở tab Khấu hao CCDC."""
        if not self:
            return self.env['project.depreciation.line']
        return self.env['project.depreciation.line'].sudo().search([
            ('project_id', 'in', self.ids),
            ('state', '=', 'open'),
        ], order='project_id, date_borrow')

    def _check_ccdc_returned_before_archive(self):
        """Khi lưu trữ dự án: chặn nếu còn CCDC chưa trả, kèm danh sách."""
        open_lines = self._get_unreturned_ccdc()
        if not open_lines:
            return
        multi = len(self) > 1
        lines = []
        for r in open_lines:
            prefix = '[%s] ' % r.project_id.name if multi else ''
            lot = ' (Lô/SN: %s)' % r.lot_id.name if r.lot_id else ''
            receiver = r.receiver_id.name or '—'
            borrow = r.date_borrow and fields.Datetime.to_string(r.date_borrow)[:10] or ''
            lines.append('• %s%s%s — Người giữ: %s — SL: %s — Mượn từ: %s' % (
                prefix, r.product_id.display_name, lot, receiver,
                ('%g' % (r.quantity or 0.0)), borrow,
            ))
        raise UserError(_(
            'Không thể lưu trữ: dự án còn CCDC chưa được trả/thu hồi.\n'
            'Vui lòng trả/thu hồi hết trước khi đóng dự án:\n\n%s'
        ) % '\n'.join(lines))

    def write(self, vals):
        # Quét CCDC chưa trả khi dự án chuyển sang lưu trữ (active=False),
        # áp dụng cho cả lưu trữ thủ công (toggle_active) lẫn tự động
        # (inactive_project khi state = completed/cancel).
        if 'active' in vals and not vals.get('active'):
            self.filtered('active')._check_ccdc_returned_before_archive()
        return super(Project, self).write(vals)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self._context.get('x_project_by_payer', False) and self._context.get('type') in ('type_5','type_6'):
            payer_id = self._context.get('payer_id')
            product_id = self._context.get('product_id')
            lot_id = self._context.get('lot_id')
            if not payer_id:
                raise UserError(_('Chưa chọn người trả'))
            if not product_id:
                raise UserError(_('Chưa chọn sản phẩm'))
            records = self.env['stock.borrow.tools'].sudo().search([
                ('product_id', '=', product_id),
                ('lot_id', '=', lot_id),
                ('receiver_id', '=', payer_id),
                ('amount', '>', 0),
            ])
            domain.append(('id', 'in', [x.project_id.id for x in records]))
        return super(Project, self).search_read(domain, fields, offset, limit, order)
