# -*- coding: utf-8 -*-
import logging
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .junk_scanner import scan_referenced_ids, PARTNER_EXCLUDED_PREFIXES

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_type_ncc = fields.Many2one('category.supplier', string='Phân loại NCC')
    x_group_item = fields.Many2many('product.group', string='Nhóm mặt hàng')
    x_product_typical = fields.Char(string='Sản phẩm điển hình')
    x_buying_frequency = fields.Many2one('buying.frequency', string='Tần suất mua')
    x_purchase_form = fields.Many2one('purchase.form', string='Hình thức mua')
    x_delivery_form = fields.Many2many('delivery.form', string='Hình thức giao hàng')
    type = fields.Selection(readonly=True)
    is_expense = fields.Boolean('Chi phí cọc',default=False)

    # Partner rác = không phát sinh BẤT KỲ dữ liệu nghiệp vụ nào trong hệ thống,
    # không phải user đăng nhập, không phải nhân viên, không có liên hệ con/cha.
    # Field KHÔNG lưu (store=False): dùng `search` để lọc động ngay lúc bấm filter,
    # nên luôn cập nhật real-time, không cần cron hay tính lại thủ công.
    x_is_junk = fields.Boolean(
        string='Partner rác', store=False,
        compute='_compute_x_is_junk', search='_search_x_is_junk',
        help='Không phải nhân viên, không phải user đăng nhập, không có liên hệ '
             'con/cha và không phát sinh dữ liệu nghiệp vụ nào (đơn bán, mua hàng, '
             'hoá đơn, thanh toán, phiếu kho, tạm ứng, tiết kiệm...) trong hệ thống.')

    @api.model
    def _junk_referenced_partner_ids(self):
        """Set id partner đang được tham chiếu ở bất kỳ cột Many2one / bảng Many2many
        nào trong toàn DB, trừ các model nhiễu kỹ thuật (mail, ir, bus, calendar...)."""
        return scan_referenced_ids(self.env, ['res.partner'],
                                   PARTNER_EXCLUDED_PREFIXES)

    def _compute_x_is_junk(self):
        """Hiển thị giá trị cho từng record (form/list). Lọc dùng _search_x_is_junk."""
        if not self:
            return
        referenced = self._junk_referenced_partner_ids()
        for partner in self:
            partner.x_is_junk = bool(
                partner.id
                and partner.id not in referenced
                and not partner.user_ids
                and not partner.parent_id
                and not partner.child_ids
            )

    @api.model
    def _junk_partner_ids(self):
        """Tập id partner rác tính động: không tham chiếu, không user, không cha/con."""
        referenced = self._junk_referenced_partner_ids()
        # Liên hệ cha-con: child có parent_id, hoặc partner đang là cha của ai đó
        self._cr.execute("""
            SELECT id, parent_id FROM res_partner
        """)
        all_ids, not_junk = set(), set(referenced)
        for pid, parent in self._cr.fetchall():
            all_ids.add(pid)
            if parent:
                not_junk.add(pid)      # bản thân là liên hệ con
                not_junk.add(parent)   # đối tượng cha (đang có liên hệ con)
        # User đăng nhập (đã nằm trong referenced qua res.users.partner_id, thêm cho chắc)
        self._cr.execute("SELECT partner_id FROM res_users WHERE partner_id IS NOT NULL")
        not_junk.update(r[0] for r in self._cr.fetchall())
        return all_ids - not_junk

    def _search_x_is_junk(self, operator, value):
        if operator not in ('=', '!='):
            raise ValidationError('Toán tử không hỗ trợ cho trường Partner rác.')
        junk_ids = list(self._junk_partner_ids())
        # (= True) hoặc (!= False) => là rác ; ngược lại => không rác
        want_junk = (operator == '=') == bool(value)
        return [('id', 'in' if want_junk else 'not in', junk_ids)]

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['vat'] = "%s (sao chép)" % (self.vat)
        res = super(ResPartner, self).copy(default=default)
        return res

    @api.depends('purchase_line_ids')
    def _compute_on_time_rate(self):
        sql = f'''select
                    case when (select count(*) as count_state from purchase_order po where po.partner_id = {self.id} and po.x_state not in ('draft','cancel')) = 0 then 0 else 100 
                    - coalesce((select count(*) as count_state from purchase_order po where po.partner_id = {self.id} and po.x_state in ('out_date','to_late')),0)::double precision
                    / coalesce((select count(*) as count_state from purchase_order po where po.partner_id = {self.id} and po.x_state not in ('draft','cancel')),1)::double precision * 100
                    end as on_time_rate'''
        self._cr.execute(sql)
        res = self._cr.fetchone()
        self.on_time_rate = res[0]