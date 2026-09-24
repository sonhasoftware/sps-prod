# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CategoryList(models.Model):
    _name = 'category.supplier'
    _description = 'Phân loại nhà cung cấp'

    name = fields.Char(string='Phân loại NCC', required=1)
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Phân loại NCC không được trùng lặp')
    ]


class ProductGroup(models.Model):
    _name = 'product.group'
    _description = 'Nhóm mặt hàng'

    name = fields.Char(string='Nhóm mặt hàng', required=1)
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Nhóm mặt hàng không được trùng lặp')
    ]


class BuyingFrequency(models.Model):
    _name = 'buying.frequency'
    _description = 'Tần suất mua'

    name = fields.Char(string='Tần suất mua', required=1)
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Tần suất mua không được trùng lặp')
    ]


class PurchaseForm(models.Model):
    _name = 'purchase.form'
    _description = 'Hình thức mua'

    name = fields.Char(string='Hình thức mua', required=1)
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Hình thức mua không được trùng lặp')
    ]


class DeliveryForm(models.Model):
    _name = 'delivery.form'
    _description = 'Hình thức giao hàng'

    name = fields.Char(string='Hình thức giao hàng', required=1)
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Hình thức giao hàng không được trùng lặp')
    ]
