# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


FORMULA_VARIABLES = {
    'au': 'amount_untaxed',
    'oc': 'overhead_cost',
    'xae': 'x_amount_estimate',
    'cr': 'cr',
    'tp': 'tp',
}


class ProfitFormulaConfig(models.Model):
    _name = 'profit.formula.config'
    _description = 'Cấu hình công thức tính lợi nhuận sau thuế'
    _order = 'sequence, id'

    name = fields.Char('Tên', required=True)
    sequence = fields.Integer('Thứ tự', default=10)
    formula = fields.Char('Công thức', required=True)

    @api.constrains('formula')
    def _check_formula(self):
        test_vars = {k: 1.0 for k in FORMULA_VARIABLES}
        for rec in self:
            try:
                safe_eval(rec.formula, test_vars, nocopy=True)
            except Exception as e:
                raise ValidationError(
                    'Công thức không hợp lệ: %s\nLỗi: %s' % (rec.formula, str(e))
                )

    def compute_profit(self, sale_order):
        self.ensure_one()
        variables = {
            'au': sale_order.amount_untaxed,
            'oc': sale_order.overhead_cost_amount,
            'xae': sale_order.x_amount_estimate,
            'cr': sale_order.cr_amount,
            'tp': sale_order.tp_amount,
        }
        return safe_eval(self.formula, variables, nocopy=True)
