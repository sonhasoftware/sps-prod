# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Category(models.Model):
    _inherit = 'product.category'

    x_labor_cost = fields.Boolean('Chi phí nhân công?', default=0)


class Template(models.Model):
    _inherit = 'product.template'

    x_labor_cost1 = fields.Boolean('Chi phí nhân công?', related='categ_id.x_labor_cost', track_visibility="always")
    x_resource_type = fields.Selection([
        ('seniorengsub', 'Kỹ sư / Giám sát cao cấp'),
        ('engsub', 'Kỹ sư / Giám sát'),
        ('teamleader', 'Trưởng nhóm'),
        ('technician', 'Kỹ thuật viên'),
        ('internship', 'Thực tập sinh'),
    ], string='Loại nguồn lực', track_visibility="always")
    name = fields.Char('Name', index=True, required=True, translate=True, track_visibility="always")
    default_code = fields.Char(
        'Internal Reference', compute='_compute_default_code',
        inverse='_set_default_code', store=True, track_visibility="always")
    sale_ok = fields.Boolean('Can be Sold', default=True, track_visibility="always")
    purchase_ok = fields.Boolean('Can be Purchased', default=True, track_visibility="always")
    x_hours_per_year = fields.Float(
        'Số giờ dự kiến trong năm',
        help='Dùng để tính đơn giá khấu hao cho CCDC cấp dự án (FM/MS). '
             'Ví dụ: máy phân tích điện ước tính 500h/năm. '
             'Đơn giá = giá vốn / (số năm khấu hao × số giờ này).', tracking=True)
    x_depreciation_years = fields.Float(
        'Số năm khấu hao dự kiến',
        help='Số năm khấu hao theo quy định doanh nghiệp (vd 5 năm cho máy tính).', tracking=True)
    x_hourly_depreciation_rate = fields.Float(
        'Đơn giá khấu hao/giờ',
        compute='_compute_x_hourly_depreciation_rate',
        help='= Giá vốn / (số giờ dự kiến trong năm × số năm khấu hao). '
             'Áp dụng cho CCDC cấp dự án (FM/MS). CCDC cấp cá nhân tính theo giờ làm việc/năm của công ty.')

    @api.depends('standard_price', 'x_hours_per_year', 'x_depreciation_years')
    def _compute_x_hourly_depreciation_rate(self):
        for r in self:
            denom = (r.x_hours_per_year or 0.0) * (r.x_depreciation_years or 0.0)
            r.x_hourly_depreciation_rate = (r.standard_price / denom) if denom > 0 else 0.0


