# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime


class CashFlowPreviewWizard(models.TransientModel):
    _name = 'cash.flow.preview.wizard'
    _description = 'Wizard để chọn năm cho báo cáo Cash Flow'

    year = fields.Integer(
        string='Năm', 
        default=lambda self: datetime.now().year,
        required=True,
        help='Chọn năm để tạo báo cáo'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(CashFlowPreviewWizard, self).default_get(fields_list)
        res['year'] = datetime.now().year
        return res

    def action_generate_report(self):
        """Gọi logic preview với năm được chọn"""
        cash_flow_report = self.env['cash.flow.view_report']
        return cash_flow_report.preview_with_year(self.year)

    def action_cancel(self):
        """Đóng wizard"""
        return {
            'type': 'ir.actions.act_window_close'
        } 