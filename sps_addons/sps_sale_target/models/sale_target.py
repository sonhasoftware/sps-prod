# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SaleTarget(models.Model):
    _name = 'sale.target'
    _description = 'Sale Target'

    target_month = fields.Selection(
        selection=[
            ("1", "Janunary"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December")
        ],
        string="Month",
        required=True,
        copy=False,
    )
    target_year = fields.Integer(
        string="Year",
        required=True,
        copy=False,
    )
    sale_target = fields.Float(
        string="Sale Target",
        required=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "month_year_uniq",
            "UNIQUE(target_month, target_year)",
            "Month and Year should be unique combination!"
        ),
        # (
        #     "year_positive",
        #     "CHECK(target_year > 0)",
        #     "Year should be positive!"
        # ),
        # (
        #     "sale_target_positive",
        #     "CHECK(sale_target > 0)",
        #     "Sale Target should be positive!"
        # )
    ]


class SaleFrequency(models.Model):
    _name = 'sale.frequency'
    _description = 'khoảng thời gian giữa các lần thực hiện'

    name = fields.Char(string='Tên tần suất')
    code = fields.Char(string='Mã tần suất', required='True')
    timeline = fields.Integer(required='True')
    type = fields.Selection([('D', 'Ngày'), ('W', 'Tuần'), ('M', 'Tháng'), ('Y', 'Năm'), ], required='True')



