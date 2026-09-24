# -*- coding: utf-8 -*-

from openpyxl.writer.excel import save_virtual_workbook
from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    advance_ids = fields.One2many('account.advance', 'po_id')
    remaining_amount = fields.Monetary(compute='_compute_remaining_amount', search='_search_remaining_amount', string="Còn lại")

    def _compute_remaining_amount(self):
        for rec in self:
            reconcile_ids = self.env['account.partial.reconcile'].search(
                [('credit_move_id', 'in', rec.invoice_ids.filtered(lambda p: p.state != 'cancel').line_ids.ids)])
            move_advance_ids = rec.advance_ids.payment_id.move_id
            total_move = sum(reconcile_ids.filtered(lambda r: r.debit_move_id.move_id not in move_advance_ids).mapped('amount'))
            total_advance = sum(rec.advance_ids.filtered(lambda a: a.state in ['payment', 'completed']).payment_id.mapped('amount'))
            rec.remaining_amount = rec.amount_total - total_move - total_advance

    def _search_remaining_amount(self, operator, value):
        """Search method for remaining_amount computed field"""
        purchase_orders = self.search([])
        filtered_ids = []

        for order in purchase_orders:
            reconcile_ids = self.env['account.partial.reconcile'].search(
                [('credit_move_id', 'in', order.invoice_ids.filtered(lambda p: p.state != 'cancel').line_ids.ids)])
            move_advance_ids = order.advance_ids.payment_id.move_id
            total_move = sum(reconcile_ids.filtered(lambda r: r.debit_move_id.move_id not in move_advance_ids).mapped('amount'))
            total_advance = sum(order.advance_ids.filtered(lambda a: a.state in ['payment', 'completed']).payment_id.mapped('amount'))
            total = order.amount_total - total_move - total_advance

            if operator == '=':
                if total == value:
                    filtered_ids.append(order.id)
            elif operator == '!=':
                if total != value:
                    filtered_ids.append(order.id)
            elif operator == '>':
                if total > value:
                    filtered_ids.append(order.id)
            elif operator == '>=':
                if total >= value:
                    filtered_ids.append(order.id)
            elif operator == '<':
                if total < value:
                    filtered_ids.append(order.id)
            elif operator == '<=':
                if total <= value:
                    filtered_ids.append(order.id)
            elif operator in ('in', 'not in'):
                if operator == 'in' and total in value:
                    filtered_ids.append(order.id)
                elif operator == 'not in' and total not in value:
                    filtered_ids.append(order.id)

        return [('id', 'in', filtered_ids)]