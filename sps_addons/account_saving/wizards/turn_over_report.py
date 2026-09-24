# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date, datetime
import base64

import os
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Border, Side, Alignment
from openpyxl.writer.excel import save_virtual_workbook
from odoo import api, fields, models
from six import BytesIO


class TurnOverReport(models.TransientModel):
    _name = 'turn.over.report'
    _description = 'Báo cáo xuất data cho file Turn over report'

    def turn_over_report(self):
        sale_order_ids = self.with_context(active_test=False).env['sale.order'].search([('state', 'in', ['sale', 'done'])], order='date_order desc')
        records = []
        customer_list = []

        # --- OPTIMIZATION: Prefetch tất cả fields cần thiết cho sale.order ---
        sale_order_ids.read([
            'partner_id', 'x_investor_id', 'name', 'work_content', 'project_type',
            'date_order', 'work_time', 'work_time_unit', 'payment_term_id',
            'x_contract_status', 'x_invoice_frequency', 'x_payment_ids'
        ])
        # Prefetch related name fields (partner, investor, payment_term, invoice_frequency)
        sale_order_ids.mapped('partner_id').read(['name'])
        sale_order_ids.mapped('x_investor_id').read(['name'])
        sale_order_ids.mapped('payment_term_id').read(['name'])
        sale_order_ids.mapped('x_invoice_frequency').read(['name'])

        # --- OPTIMIZATION: Cache selection labels 1 lần duy nhất ---
        project_type_labels = dict(
            sale_order_ids._fields['project_type']._description_selection(self.env)
        )
        contract_status_labels = dict(
            sale_order_ids._fields['x_contract_status']._description_selection(self.env)
        )

        # --- OPTIMIZATION: Pre-fetch Invoice data ---
        all_invoice_ids = self.env['account.move'].search([('x_order_id', 'in', sale_order_ids.ids)])
        # Prefetch all invoice fields needed in the loop
        all_invoice_ids.read([
            'state', 'x_order_id', 'amount_total', 'amount_residual', 'payment_state',
            'invoice_date', 'date', 'x_payment_term', 'x_date_sent', 'x_number_invoice',
            'x_project_state', 'x_payment_ids'
        ])

        # 1. Gom nhóm Invoice theo Order ID để tránh filtered() trong vòng lặp
        invoice_map = {}
        for inv in all_invoice_ids:
            order_id_val = inv.x_order_id.id
            if order_id_val not in invoice_map:
                invoice_map[order_id_val] = self.env['account.move']
            invoice_map[order_id_val] |= inv

        # --- OPTIMIZATION: Prefetch tất cả payment liên quan ---
        # Payments từ sale orders (tạm ứng)
        all_order_payment_ids = sale_order_ids.mapped('x_payment_ids')
        all_order_payment_ids.read([
            'state', 'amount', 'expected_date', 'date', 'invoice_number',
            'advance_request_date', 'invoice_date', 'x_note', 'report_amount',
            'project_state', 'display_date'
        ])

        # Payments từ invoices (thanh toán thường)
        all_invoice_payment_ids = all_invoice_ids.mapped('x_payment_ids')
        all_invoice_payment_ids.read([
            'state', 'amount', 'date', 'report_amount'
        ])

        # 2. Lấy dữ liệu Phạt (Penalty) bằng Raw SQL — tránh load toàn bộ move lines
        penalty_map = {}  # {invoice_id: total_penalty_amount}
        valid_invoices = all_invoice_ids.filtered(lambda p: p.state != 'cancel')
        if valid_invoices:
            self.env.cr.execute("""
                SELECT aml.move_id, SUM(apr.amount)
                FROM account_partial_reconcile apr
                JOIN account_move_line credit_line ON credit_line.id = apr.credit_move_id
                JOIN account_move credit_move ON credit_move.id = credit_line.move_id
                JOIN account_move_line aml ON aml.id = apr.debit_move_id
                WHERE credit_move.is_penalty_move = TRUE
                  AND aml.move_id IN %s
                GROUP BY aml.move_id
            """, [tuple(valid_invoices.ids)])
            penalty_map = dict(self.env.cr.fetchall())
        # --- END OPTIMIZATION ---

        # Cache set cho trạng thái không hợp lệ của payment
        invalid_payment_states = {'cancel'}

        for order_id in sale_order_ids:
            customer_list.append(order_id.partner_id.name)
            
            # Lấy Invoice từ Map thay vì filtered
            invoice_ids = invoice_map.get(order_id.id, self.env['account.move'])
            
            payment_ids = order_id.x_payment_ids

            if order_id.work_time_unit == 'day':
                date_end = order_id.date_order + timedelta(days=order_id.work_time)
            elif order_id.work_time_unit == 'month':
                date_end = order_id.date_order + relativedelta(months=order_id.work_time)
            elif order_id.work_time_unit == 'year':
                date_end = order_id.date_order + relativedelta(years=order_id.work_time)
            else:
                date_end = order_id.date_order

            value = {
                'chu_dau_tu': order_id.x_investor_id.name,
                'khach_hang': order_id.partner_id.name,
                'so_du_an': order_id.name,
                'ten_du_an': order_id.work_content,
                'phan_loai': project_type_labels[order_id.project_type],
                'tu': order_id.date_order.strftime('%d/%m/%Y'),
                'den': date_end.strftime('%d/%m/%Y'),
                'dieu_khoan_thanh_toan': order_id.payment_term_id.name,
                'contract_status': contract_status_labels[order_id.x_contract_status],
                'tan_suat': 'Một lần' if order_id.project_type == 'service' else order_id.x_invoice_frequency.name,
            }

            # XUẤT RIÊNG PAYMENT TẠM ỨNG (từ order_id.x_payment_ids)
            # Payment tạm ứng luôn xuất riêng dòng, không gộp vào invoice
            advance_payments = payment_ids.filtered(lambda p: p.state not in invalid_payment_states)
            for payment_id in advance_payments:
                # posted = đã thu (Done); chưa posted = lấy theo project_state, chưa thu
                is_done = payment_id.state == 'posted'
                payment_value = value.copy()
                payment_value.update({
                    'gia_tri_hop_dong': payment_id.amount,
                    'thang_nam': payment_id.expected_date if payment_id.expected_date else payment_id.date,
                    'kl_da_suat_hd': payment_id.amount if payment_id.invoice_number else 0,
                    'phat': 0,
                    'da_thu': payment_id.amount if is_done else 0,
                    'ngay_thu': payment_id.display_date if payment_id.display_date else '',
                    'con_phai_thu': 0 if is_done else payment_id.amount,
                    'tinh_trang_du_an': 'Done' if is_done else payment_id.project_state,
                    'payment_submit': payment_id.advance_request_date if payment_id.advance_request_date else payment_id.date,
                    'ngay_hoa_don': payment_id.invoice_date if payment_id.invoice_date else '',
                    'ghi_chu': payment_id.x_note if payment_id.x_note else '',
                    'name': payment_id.invoice_number if payment_id.invoice_number else '',
                })
                records.append(payment_value)

            # PHÂN BỔ PAYMENT TẠM ỨNG VÀO INVOICE
            # Mỗi payment tạm ứng chỉ được phân bổ vào 1 invoice (để tính residual)
            # Dictionary tracking: {invoice_id: [payment_tam_ung1, payment_tam_ung2, ...]}
            allocated_advance_payments = {}

            # Sắp xếp invoice theo invoice_date (sớm nhất trước)
            sorted_invoices = invoice_ids.filtered(lambda inv: inv.state != 'cancel').sorted(
                key=lambda inv: inv.invoice_date or inv.date or date.min
            )

            # Phân bổ từng payment tạm ứng vào invoice phù hợp
            for payment in advance_payments:
                for invoice in sorted_invoices:
                    # Tính residual còn lại của invoice sau khi trừ payment đã phân bổ
                    current_residual = invoice.amount_total

                    # Trừ payment thường của invoice
                    invoice_payments = invoice.x_payment_ids.filtered(lambda p: p.state not in invalid_payment_states)
                    current_residual -= sum(invoice_payments.mapped('amount'))

                    # Trừ payment tạm ứng đã phân bổ vào invoice này
                    if invoice.id in allocated_advance_payments:
                        current_residual -= sum(allocated_advance_payments[invoice.id].mapped('amount'))

                    # Nếu invoice còn đủ giá trị để chứa payment tạm ứng này
                    if current_residual >= payment.amount:
                        if invoice.id not in allocated_advance_payments:
                            allocated_advance_payments[invoice.id] = self.env['account.payment'].browse()
                        allocated_advance_payments[invoice.id] |= payment
                        break

            for invoice_id in invoice_ids.filtered(lambda p: p.state != 'cancel'):
                # Lấy phí phạt từ dictionary
                penalty_fee = penalty_map.get(invoice_id.id, 0)

                if invoice_id.state == 'draft':
                    # Tính residual cho invoice draft, trừ payment tạm ứng đã phân bổ
                    allocated_advance = 0
                    if invoice_id.id in allocated_advance_payments:
                        allocated_advance = sum(allocated_advance_payments[invoice_id.id].mapped('amount'))

                    draft_residual = invoice_id.amount_residual - allocated_advance

                    invoice_draft_value = value.copy()
                    invoice_draft_value.update({
                        'gia_tri_hop_dong': draft_residual if draft_residual > 0 else 0,
                        'thang_nam': invoice_id.x_payment_term if invoice_id.x_payment_term else invoice_id.invoice_date,
                        'kl_da_suat_hd': 0,
                        'phat': 0,
                        'da_thu': 0,
                        'ngay_thu': '',
                        'con_phai_thu': draft_residual if draft_residual > 0 else 0,
                        'tinh_trang_du_an': invoice_id.x_project_state,
                        'payment_submit': invoice_id.invoice_date,
                        'ngay_hoa_don': invoice_id.x_date_sent if invoice_id.x_date_sent else invoice_id.invoice_date,
                        'ghi_chu': '',
                        'name': invoice_id.x_number_invoice if invoice_id.x_number_invoice else '',
                    })
                    # Chỉ xuất invoice draft nếu còn residual > 0
                    if draft_residual > 0:
                        records.append(invoice_draft_value)

                elif invoice_id.state == 'posted':
                    # Lấy payment thường từ invoice (CHỈ payment đã posted)
                    invoice_payments = invoice_id.x_payment_ids.filtered(lambda p: p.state not in invalid_payment_states)

                    # Tính toán trước tổng thanh toán và phân bổ
                    total_paid_invoice = sum(invoice_payments.mapped('amount'))
                    allocated_advance = 0
                    if invoice_id.id in allocated_advance_payments:
                        allocated_advance = sum(allocated_advance_payments[invoice_id.id].mapped('amount'))

                    # Tính residual thực tế theo sổ sách
                    real_residual = invoice_id.amount_total - total_paid_invoice - allocated_advance

                    # Nếu đã mark PAID nhưng vẫn còn dư (lệch nhỏ), cộng phần lệch vào giá trị hợp đồng của payment cuối
                    diff_to_add = 0
                    if invoice_id.payment_state == 'paid' and real_residual > 0:
                        diff_to_add = real_residual

                    # Xuất chi tiết từng payment thường của invoice
                    for index, payment_id in enumerate(invoice_payments):
                        contract_val = payment_id.amount
                        # Nếu là payment cuối cùng, cộng thêm phần chênh lệch
                        if index == len(invoice_payments) - 1:
                            contract_val += diff_to_add

                        invoice_payment_value = value.copy()
                        invoice_payment_value.update({
                            'gia_tri_hop_dong': contract_val,
                            'thang_nam': invoice_id.x_payment_term if invoice_id.x_payment_term else invoice_id.invoice_date,
                            'kl_da_suat_hd': payment_id.amount,
                            'phat': 0,
                            'da_thu': payment_id.amount if not payment_id.report_amount else payment_id.report_amount,
                            'ngay_thu': payment_id.date,
                            'con_phai_thu': 0,
                            'tinh_trang_du_an': 'Done',
                            'payment_submit': invoice_id.invoice_date,
                            'ngay_hoa_don': invoice_id.x_date_sent if invoice_id.x_date_sent else invoice_id.invoice_date,
                            'ghi_chu': '',
                            'name': invoice_id.x_number_invoice if invoice_id.x_number_invoice else '',
                        })
                        records.append(invoice_payment_value)

                    if invoice_id.payment_state == 'paid':
                        remaining_residual = 0
                    else:
                        remaining_residual = real_residual

                    # Nếu còn residual, xuất dòng residual
                    if remaining_residual > 0:
                        invoice_residual_value = value.copy()
                        invoice_residual_value.update({
                            'gia_tri_hop_dong': remaining_residual,
                            'thang_nam': invoice_id.x_payment_term if invoice_id.x_payment_term else invoice_id.invoice_date,
                            'kl_da_suat_hd': remaining_residual if invoice_id.x_number_invoice else 0,
                            'phat': 0,
                            'da_thu': 0,
                            'ngay_thu': '',
                            'con_phai_thu': remaining_residual,
                            'tinh_trang_du_an': invoice_id.x_project_state,
                            'payment_submit': invoice_id.invoice_date,
                            'ngay_hoa_don': invoice_id.x_date_sent if invoice_id.x_date_sent else invoice_id.invoice_date,
                            'ghi_chu': '',
                            'name': invoice_id.x_number_invoice if invoice_id.x_number_invoice else '',
                        })
                        records.append(invoice_residual_value)

                # Gán penalty fee vào record cuối cùng của invoice này (nếu có)
                if records:
                    records[-1]['phat'] = penalty_fee
        customer_list = list(dict.fromkeys(customer_list))
        # return
        dir_path = os.path.dirname(os.path.realpath(__file__))
        wb = openpyxl.load_workbook(dir_path + '%s..%stemplates%sturn_over_report.xlsx' % (os.sep, os.sep, os.sep))
        ws = wb['DATA']
        ws2 = wb['Annual']
        ws3 = wb['PlanActual']
        # --- OPTIMIZATION: gán trực tiếp font/border/alignment dùng chung thay cho
        # NamedStyle. Mỗi lần `cell.style = NamedStyleObject` openpyxl phải so sánh
        # tuyến tính với hàng trăm named-style rác trong template (vòng gán cell từ
        # ~38s xuống <1s). Style object được tái sử dụng nên openpyxl tự dedupe. ---
        bd1 = Side(style='thin', color="000000")
        _border = Border(left=bd1, top=bd1, right=bd1, bottom=bd1)
        _font = Font(name='Times New Roman', size=11)
        al_wrap = Alignment(wrap_text=True, vertical='center')                          # ~ highlight_0 / style_sum_1
        al_center = Alignment(wrap_text=True, vertical='center', horizontal='center')   # ~ highlight_1
        al_date = Alignment(horizontal='center', vertical='center', wrapText=True)      # ~ highlight_17 / highlight_18

        x = 1
        row = 7
        records.sort(key=lambda r: (0, 0) if not r.get('ngay_thu') else (1, -r['ngay_thu'].toordinal()))

        def _w(col, value, align, numfmt='General'):
            c = ws.cell(row, col)
            c.value = value
            c.font = _font
            c.border = _border
            c.alignment = align
            c.number_format = numfmt

        for r in records:
            _w(1, x, al_wrap)
            _w(2, r['chu_dau_tu'], al_wrap)
            _w(3, r['khach_hang'], al_wrap)
            _w(4, r['so_du_an'], al_center)
            _w(5, r['ten_du_an'], al_wrap)
            _w(6, r['phan_loai'], al_center)
            _w(7, r['tu'], al_date, 'DD/MM/YYYY')
            _w(8, r['den'], al_date, 'DD/MM/YYYY')
            _w(9, r['gia_tri_hop_dong'] if r['gia_tri_hop_dong'] and r['gia_tri_hop_dong'] > 0 else " ", al_wrap, '#,##0')
            _w(10, r['thang_nam'], al_date, 'MM/YYYY')
            _w(11, r['kl_da_suat_hd'] if r['kl_da_suat_hd'] and r['kl_da_suat_hd'] > 0 else " ", al_wrap, '#,##0')

            # Payment-related columns - không merge
            _w(12, r['phat'] if r['phat'] and r['phat'] > 0 else " ", al_wrap, '#,##0')
            _w(13, r['da_thu'] if r['da_thu'] and r['da_thu'] > 0 else " ", al_wrap, '#,##0')
            _w(14, r['ngay_thu'], al_date, 'DD/MM/YYYY')
            _w(15, r['con_phai_thu'] if r['con_phai_thu'] and r['con_phai_thu'] > 0 else " ", al_wrap, '#,##0')

            _w(16, r['tinh_trang_du_an'], al_center)
            _w(17, r['payment_submit'], al_date, 'DD/MM/YYYY')
            _w(18, r['name'], al_wrap)
            _w(19, r['dieu_khoan_thanh_toan'], al_wrap)
            _w(20, r['tan_suat'], al_center)
            _w(21, r['ngay_hoa_don'], al_date, 'DD/MM/YYYY')
            _w(22, r['contract_status'], al_center)
            _w(23, r['ghi_chu'], al_wrap)

            ws.row_dimensions[row].height = 55
            row += 1
            x += 1

        customer_list = list(dict.fromkeys(customer_list))
        row_annual = 6
        row_plan = 6
        for customer in customer_list:
            ws2.cell(row_annual, 2).value = customer
            ws3.cell(row_plan, 2).value = customer
            row_annual += 1
            row_plan += 2

        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)

        attachment_id = self.env['ir.attachment'].create({
            'name': 'turn_over_report.xlsx',
            'datas': base64.b64encode(stream.read()),
            'type': 'binary',
        })
        # download
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(attachment_id.id) + '?download=true',
            'target': 'new',
        }
