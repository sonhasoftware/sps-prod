# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.models import NewId
from odoo.exceptions import ValidationError


class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    date_start = fields.Datetime(
        string='Start',
        required=True,
        default=fields.Datetime.now(),
        copy=False
    )
    date_end = fields.Datetime(
        string='End',
        copy=False,
        required=True
    )

    _sql_constraints = [
        (
            "start_comes_before_end",
            "CHECK(date_start < date_end)",
            "Start date must come before End date!"
        )
    ]

    @api.constrains(
        'date_start',
        'date_end'
    )
    def _check_date(self):
        for r in self:
            r._check_in_range()

    def _check_in_range(self):
        if isinstance(self.id, NewId):
            all_other_pricelists = self.search([])
        else:
            all_other_pricelists = self.search([('id', '!=', self.id)])
        for pricelist in all_other_pricelists:
            if (
                pricelist.date_start < self.date_start < pricelist.date_end or
                pricelist.date_start < self.date_end < pricelist.date_end
            ):
                raise ValidationError(_("Pricelist duration overlap detected!"))

class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    date_start = fields.Datetime(
        related='pricelist_id.date_start',
        store=True,
        readonly=True
    )
    date_end = fields.Datetime(
        related='pricelist_id.date_end',
        store=True,
        readonly=True
    )
    min_quantity = fields.Float(
        default=1.0
    )
    compute_price = fields.Selection(
        readonly=True
    )
    material_price = fields.Float(
        string='Material Price',
        required=True,
        default=0.0
    )
    worker_price = fields.Float(
        string='Worker Price',
        required=True,
        default=0.0
    )
    other_price = fields.Float(
        string='Other Price',
        required=True,
        default=0.0
    )
    fixed_price = fields.Float(
        compute='_compute_fixed_price',
        readonly=True,
        store=True,
    )

    _sql_constraints = [
        (
            "material_price_pos",
            "CHECK(material_price >= 0)",
            "Price must be greater and equal 0!"
        ),
        (
            "worker_price_pos",
            "CHECK(worker_price >= 0)",
            "Price must be greater and equal 0!"
        ),
        (
            "other_price_pos",
            "CHECK(other_price >= 0)",
            "Price must be greater and equal 0!"
        )
    ]

    @api.depends(
        'material_price',
        'worker_price',
        'other_price'
    )
    def _compute_fixed_price(self):
        for r in self:
            r.fixed_price = r.material_price + r.worker_price + r.other_price

# Restrict end users for selecting advance pricelist
class Settings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_pricelist_setting = fields.Selection(
        readonly=True
    )
