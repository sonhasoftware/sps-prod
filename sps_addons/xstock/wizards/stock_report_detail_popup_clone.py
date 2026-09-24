# -*- coding: utf-8 -*-
import datetime as dt

from odoo import api, fields, models, tools
from odoo.http import request


class StockReportDetailPopupClone(models.TransientModel):
    _name = 'stock.report.detail.popup.clone'
    _description = 'Báo cáo chi tiết hoạt đông kho'

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    picking_type = fields.Char(string='Kiểu hoạt động')
    move_date = fields.Date(string="Ngày phiếu")
    entry_name = fields.Char(string="Số phiếu")
    product_code = fields.Char(string="Mã sản phẩm")
    product_name = fields.Char(string="tên sản phẩm")
    product_type = fields.Char(string="Phân loại vật phẩm")
    uom_name = fields.Char(string="Đơn vị tính")
    serial = fields.Char(string="Serial")
    location_name = fields.Char(string="Kho xuất")
    location_dest_name = fields.Char(string="Kho nhập")
    from_project = fields.Char(string="Từ dự án")
    to_project = fields.Char(string="Tới dự án")
    create_user = fields.Char(string="Người tạo")
    payer_name = fields.Char(string="Người trả")
    receiver_name = fields.Char(string="Người nhận")
    quantity = fields.Float(string="Số lượng")
    price_unit = fields.Float(string="Đơn giá")
    value = fields.Float(string="Thành tiền")

