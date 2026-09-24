# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrMealRate(models.Model):
    _name = 'hr.meal.rate'
    _description = 'Đơn giá hỗ trợ ăn ca theo thời gian'
    _order = 'date_from desc'

    name = fields.Char('Diễn giải')
    date_from = fields.Date('Từ ngày', required=True)
    date_to = fields.Date('Đến ngày', help='Để trống = áp dụng vô thời hạn.')
    amount = fields.Monetary('Đơn giá / suất', required=True, currency_field='currency_id',
                             help='Số tiền hỗ trợ ăn ca cho 1 suất (1 ngày làm việc đủ điều kiện).')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Công ty',
                                 default=lambda self: self.env.company)
    active = fields.Boolean('Hiệu lực', default=True)

    @api.model
    def get_rate(self, date, company=None):
        """Đơn giá ăn ca áp dụng cho ngày 'date' (bản ghi date_from<=date<=date_to, mới nhất).

        Không có bản ghi phù hợp -> fallback system param 'hr_payroll.meal_rate' (mặc định
        40.000đ) để tương thích dữ liệu cũ.
        """
        default = float(self.env['ir.config_parameter'].sudo().get_param(
            'hr_payroll.meal_rate', 40000))
        if not date:
            return default
        cid = (company or self.env.company).id
        rec = self.sudo().search([
            ('date_from', '<=', date),
            '|', ('date_to', '=', False), ('date_to', '>=', date),
            '|', ('company_id', '=', cid), ('company_id', '=', False),
        ], order='date_from desc', limit=1)
        return rec.amount if rec else default
