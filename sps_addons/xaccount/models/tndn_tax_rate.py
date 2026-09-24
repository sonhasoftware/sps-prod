# -*- coding: utf-8 -*-

from odoo import api, fields, models


class TndnTaxRate(models.Model):
    _name = 'tndn.tax.rate'
    _description = 'Thuế suất thuế thu nhập doanh nghiệp (theo thời gian)'
    _order = 'date_start desc'

    rate = fields.Float('Thuế suất (%)', required=True, default=20.0)
    date_start = fields.Date('Ngày bắt đầu', required=True)
    date_end = fields.Date('Ngày kết thúc',
                           help='Để trống nếu mức thuế còn hiệu lực (mở).')
    note = fields.Char('Ghi chú')
    active = fields.Boolean('Hiệu lực', default=True)

    def name_get(self):
        result = []
        for r in self:
            label = '%g%%' % r.rate
            if r.date_start:
                label += ' (%s - %s)' % (r.date_start, r.date_end or '...')
            result.append((r.id, label))
        return result

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for r in self:
            if r.date_end and r.date_start and r.date_end < r.date_start:
                from odoo.exceptions import ValidationError
                raise ValidationError('Ngày kết thúc phải sau ngày bắt đầu.')

    @api.model
    def get_rate_for_date(self, date):
        """Trả về thuế suất TNDN (%) áp dụng cho 'date' (so khoảng hiệu lực).
        Nếu date rỗng / không có mức nào khớp -> lấy mức mới nhất, cuối cùng
        mặc định 20%."""
        if date:
            rec = self.search([
                ('date_start', '<=', date),
                '|', ('date_end', '=', False), ('date_end', '>=', date),
            ], order='date_start desc', limit=1)
            if rec:
                return rec.rate
        rec = self.search([], order='date_start desc', limit=1)
        return rec.rate if rec else 20.0
