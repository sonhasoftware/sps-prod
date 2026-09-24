# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.addons.account_invoice_extract.models.account_invoice import WARNING_DUPLICATE_VENDOR_REFERENCE
from odoo.exceptions import ValidationError
from odoo.tests.common import Form

TOLERANCE = 0.02  # tolerance applied to the total when searching for a matching purchase order


class AccountMove(models.Model):
    _inherit = ['account.move']

    def get_user_infos(self):
        def transform_numbers_to_regex(string):
            r"""Transforms each number of a string to their regex equivalent, i.e. P00042-12 -> P\d{5}-\d{2}"""
            digits_count = 0
            new_string = ''
            for c in string:
                if c.isdigit():
                    digits_count += 1
                else:
                    if digits_count:
                        new_string += r'\d{{{}}}'.format(digits_count) if digits_count > 1 else r'\d'
                    digits_count = 0
                    new_string += c
            if digits_count:
                new_string += r'\d{{{}}}'.format(digits_count) if digits_count > 1 else r'\d'
            return new_string

        user_infos = super(AccountMove, self).get_user_infos()
        po_sequence = self.env['ir.sequence'].search([('code', '=', 'purchase.order'), ('company_id', 'in', [self.company_id.id, False])], order='company_id', limit=1)
        if po_sequence:
            po_regex_prefix, po_regex_suffix = po_sequence._get_prefix_suffix()
            po_regex_prefix = transform_numbers_to_regex(po_regex_prefix)
            po_regex_suffix = transform_numbers_to_regex(po_regex_suffix)
            po_regex_sequence = r'\d{{{}}}'.format(po_sequence.padding)
            user_infos['purchase_order_regex'] = '^' + po_regex_prefix + po_regex_sequence + po_regex_suffix + '$'
        return user_infos

    @api.model
    def _save_form(self, ocr_results, no_ref=False):
        if self.move_type == 'in_invoice':
            purchase_orders_ocr = ocr_results['purchase_order']['selected_values'] if 'purchase_order' in ocr_results else []
            purchase_order_matched = False
            if purchase_orders_ocr:
                purchase_orders_found = [po['content'] for po in purchase_orders_ocr]
                purchase_id_domain = [('company_id', '=', self.company_id.id), ('state', '=', 'purchase'), ('name', 'in', purchase_orders_found)]
                matching_pos = self.env['purchase.order'].search(purchase_id_domain)
                for matching_po in matching_pos:
                    with Form(self) as move_form:
                        move_form.purchase_id = matching_po
                        purchase_order_matched = True

            if not purchase_order_matched:
                invoice_id_ocr = ocr_results['invoice_id']['selected_value']['content'] if 'invoice_id' in ocr_results else ""
                if invoice_id_ocr:
                    matching_po = self.env['purchase.order'].search([('company_id', '=', self.company_id.id), ('state', '=', 'purchase'), ('partner_ref', '=', invoice_id_ocr)])
                    if len(matching_po) == 1:
                        try:
                            with Form(self) as move_form:
                                move_form.purchase_id = matching_po
                        except ValidationError:
                            # in case of ValidationError due to a duplicated vendor reference, set it to False and display a warning message
                            with Form(self) as move_form:
                                move_form.purchase_id = matching_po
                                move_form.ref = False
                                move_form.extract_status_code = WARNING_DUPLICATE_VENDOR_REFERENCE
                                self.duplicated_vendor_ref = ocr_results['invoice_id']['selected_value']['content'] if 'invoice_id' in ocr_results else ""
                        purchase_order_matched = True

            if not purchase_order_matched:
                supplier_ocr = ocr_results['supplier']['selected_value']['content'] if 'supplier' in ocr_results else ""
                vat_number_ocr = ocr_results['VAT_Number']['selected_value']['content'] if 'VAT_Number' in ocr_results else ""
                total_ocr = ocr_results['total']['selected_value']['content'] if 'total' in ocr_results else 0.0

                partner_id = self.env["res.partner"].search([("vat", "=ilike", vat_number_ocr)], limit=1)
                if partner_id.exists():
                    partner_id = partner_id.id
                else:
                    partner_id = self.find_partner_id_with_name(supplier_ocr)
                if partner_id and total_ocr:
                    purchase_id_domain = [('company_id', '=', self.company_id.id), ('partner_id', 'child_of', [partner_id]),
                                          ('amount_total', '>=', total_ocr - TOLERANCE), ('amount_total', '<=', total_ocr + TOLERANCE), ('state', '=', 'purchase')]
                    matching_po = self.env['purchase.order'].search(purchase_id_domain)
                    if len(matching_po) == 1:
                        with Form(self) as move_form:
                            move_form.purchase_id = matching_po
        super(AccountMove, self)._save_form(ocr_results, no_ref=no_ref)
