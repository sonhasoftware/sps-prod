# -*- coding: utf-8 -*-

from odoo import api, fields, models


class GroupProjectEfficiencyDetail(models.Model):
    _name = 'group.project.efficiency.detail'
    _description = 'Bảng thống kê các dự án chung đã hoàn thành và xem xét hiệu quả'
    # Sắp theo tháng kết thúc mới -> cũ (dùng completion_date để đúng thứ tự thời gian).
    _order = 'completion_date desc'

    master_key = fields.Integer('Master Key', index=True)
    order_id = fields.Many2one('sale.order', 'Mã báo giá', ondelete='set null')
    so_name = fields.Char('Mã dự án chung')
    partner_name = fields.Char('Khách hàng')
    project_name = fields.Char('Tên dự án')
    key_account = fields.Char('Key Account')
    solution_maker = fields.Char('Solution Maker')
    project_type = fields.Char('Phân loại')
    end_month = fields.Char('Tháng kết thúc')
    completion_date = fields.Date('Ngày hoàn thành')

    # --- Doanh thu (trước thuế) ---
    revenue_received = fields.Float('Doanh thu (không VAT)')
    payment_no_invoice = fields.Float('Thanh toán (không HĐ)')

    # --- Chi phí thực tế ---
    actual_labor = fields.Float('Chi phí nhân công')
    actual_materials_and_other_costs = fields.Float('Chi phí vật tư và chi phí khác')
    total_depreciation_cost = fields.Float('Chi phí CCDC')
    iv_fee = fields.Float('Chi phí IV')
    overhead_cost_amount = fields.Float('Overhead Cost')
    total_cost = fields.Float('Tổng chi phí', compute='_compute_total_cost')

    # --- Điều chỉnh thuế TNDN ---
    invoice_processing_profit = fields.Float('Doanh thu IV')
    no_invoice_extra_cost = fields.Float('Phí mua hàng không HĐ')

    # --- Hiệu quả ---
    efficiency = fields.Float('Hiệu quả dự án (trước thuế)', compute='_compute_efficiency')

    # --- Thuế & hiệu quả sau thuế ---
    input_invoice_total = fields.Float('Tổng giá trị HĐ đầu vào (Không VAT)')
    cit_tax_total = fields.Float('Thuế phải nộp (TNDN+TNCN)')
    after_tax_efficiency = fields.Float(
        'Hiệu quả dự án sau thuế', compute='_compute_after_tax_efficiency')

    def _compute_total_cost(self):
        # Tổng chi phí = Nhân công + Vật tư & khác + Chi phí CCDC (khấu hao +
        # hỏng/mất) + IV + Overhead.
        # Overhead = tỉ lệ overhead_cost (SO) x doanh thu (tính ở wizard).
        for rec in self:
            rec.total_cost = (rec.actual_labor + rec.actual_materials_and_other_costs
                              + rec.total_depreciation_cost + rec.iv_fee
                              + rec.overhead_cost_amount)

    def _compute_efficiency(self):
        # Hiệu quả (trước thuế) = Doanh thu + Thanh toán không HĐ - Tổng chi
        # phí + Lợi nhuận IV - Phí mua hàng không HĐ.
        for rec in self:
            rec.efficiency = (rec.revenue_received + rec.payment_no_invoice - rec.total_cost
                              + rec.invoice_processing_profit - rec.no_invoice_extra_cost)

    def _compute_after_tax_efficiency(self):
        # Hiệu quả dự án sau thuế = Hiệu quả (trước thuế) - Thuế phải nộp (TNDN+TNCN).
        for rec in self:
            rec.after_tax_efficiency = rec.efficiency - rec.cit_tax_total
