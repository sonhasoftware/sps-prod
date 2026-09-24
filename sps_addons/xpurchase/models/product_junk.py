# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .junk_scanner import scan_referenced_ids, PRODUCT_EXCLUDED_PREFIXES

JUNK_HELP = ('Sản phẩm chưa được dùng ở đâu: chưa mua, chưa bán, chưa nhập/xuất kho, '
             'không có bút toán, không nằm trong tồn kho/định giá... (bỏ qua các tham '
             'chiếu kỹ thuật và cấu hình nội bộ của sản phẩm).')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Không lưu (store=False): lọc động qua `search`, luôn cập nhật real-time.
    x_is_junk = fields.Boolean(
        string='Sản phẩm rác', store=False,
        compute='_compute_x_is_junk', search='_search_x_is_junk', help=JUNK_HELP)

    @api.model
    def _junk_template_ids(self):
        """Set id product.template rác: bản thân template không bị tham chiếu VÀ không
        biến thể (product.product) nào của nó được tham chiếu trong hệ thống."""
        ref_tmpl = scan_referenced_ids(self.env, ['product.template'],
                                       PRODUCT_EXCLUDED_PREFIXES)
        ref_variant = scan_referenced_ids(self.env, ['product.product'],
                                          PRODUCT_EXCLUDED_PREFIXES)
        cr = self.env.cr
        not_junk = set(ref_tmpl)
        if ref_variant:
            cr.execute("SELECT product_tmpl_id FROM product_product WHERE id IN %s",
                       (tuple(ref_variant),))
            not_junk.update(r[0] for r in cr.fetchall())
        cr.execute("SELECT id FROM product_template")
        all_ids = {r[0] for r in cr.fetchall()}
        return all_ids - not_junk

    def _compute_x_is_junk(self):
        if not self:
            return
        junk = self.env['product.template']._junk_template_ids()
        for tmpl in self:
            tmpl.x_is_junk = tmpl.id in junk

    def _search_x_is_junk(self, operator, value):
        if operator not in ('=', '!='):
            raise ValidationError('Toán tử không hỗ trợ cho trường Sản phẩm rác.')
        junk_ids = list(self._junk_template_ids())
        want_junk = (operator == '=') == bool(value)
        return [('id', 'in' if want_junk else 'not in', junk_ids)]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    x_is_junk = fields.Boolean(
        string='Sản phẩm rác', store=False,
        compute='_compute_x_is_junk', search='_search_x_is_junk', help=JUNK_HELP)

    @api.model
    def _junk_variant_ids(self):
        """Set id product.product (biến thể) rác: không bị tham chiếu ở đâu."""
        ref_variant = scan_referenced_ids(self.env, ['product.product'],
                                          PRODUCT_EXCLUDED_PREFIXES)
        cr = self.env.cr
        cr.execute("SELECT id FROM product_product")
        all_ids = {r[0] for r in cr.fetchall()}
        return all_ids - ref_variant

    def _compute_x_is_junk(self):
        if not self:
            return
        junk = self.env['product.product']._junk_variant_ids()
        for product in self:
            product.x_is_junk = product.id in junk

    def _search_x_is_junk(self, operator, value):
        if operator not in ('=', '!='):
            raise ValidationError('Toán tử không hỗ trợ cho trường Sản phẩm rác.')
        junk_ids = list(self._junk_variant_ids())
        want_junk = (operator == '=') == bool(value)
        return [('id', 'in' if want_junk else 'not in', junk_ids)]
