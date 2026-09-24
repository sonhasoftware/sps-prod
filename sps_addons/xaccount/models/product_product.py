from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_penalty_fee = fields.Boolean()
