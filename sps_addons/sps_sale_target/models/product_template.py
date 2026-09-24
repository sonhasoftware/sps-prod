# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_manage_frequency = fields.Boolean(string='Quản lý tần suất', default=False, track_visibility="always")
    x_frequency_id = fields.Many2one('sale.frequency', string='Tần suất', track_visibility="always")
    type = fields.Selection(
        default='service',
        selection_add=[('product', 'Lưu kho')],
        ondelete={'product': 'cascade'}, track_visibility="always"
    )
    x_type = fields.Selection([
        ('product', 'Lưu kho'),
        ('service', 'Dịch vụ'),
    ], string='Loại sản phẩm', default='service', track_visibility="always")
    x_product_type = fields.Selection([
        ('tools', 'Công cụ dụng cụ'),
        ('supplies', 'Vật tư'),
    ], string='Phân loại sản phẩm lưu kho', default='tools', track_visibility="always")
    x_supplies_type = fields.Selection([
        ('supplies', 'Vật tư tiêu chuẩn'),
        ('labor_protection', 'Bảo hộ lao động'),
        ('stationery', 'Văn phòng phẩm'),
        ('supplies_project', 'Vật tư xuất cho dự án'),
    ], string='Loại vật tư', default='supplies', track_visibility="always")
    min_inventory = fields.Float(string='Tồn kho tối thiểu', track_visibility="always")
    max_inventory = fields.Float(string='Tồn kho tối đa', track_visibility="always")
    x_location_stock = fields.Char(string='Vị trí trong kho SPS', track_visibility="always")
    x_product_company = fields.Char(string='Hãng sản xuất', track_visibility="always")
    x_code_brand = fields.Char(string='Mã hiệu', track_visibility="always")

    @api.onchange('x_type')
    @api.constrains('x_type')
    def _contrains_x_type(self):
        for r in self:
            r.type = r.x_type

    _sql_constraints = [
        (
            "default_code_uniq",
            "UNIQUE(default_code)",
            "Internal Reference should be unique!"
        )
    ]
