# -*- coding: utf-8 -*-


from odoo import api, fields, models,tools


class PurchaseTrackingSupplier(models.Model):
    _name = 'purchase.tracking.supplier'
    _description = 'Báo cáo theo dõi nhà cung cấp'

    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)
    index = fields.Integer('STT')
    supplier = fields.Char('Nhà cung cấp')
    amount = fields.Integer('Giá trị đã mua')
