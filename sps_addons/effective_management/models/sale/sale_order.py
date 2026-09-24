# -*- coding: utf-8 -*-

from datetime import date

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_completed_orders_with_date(self, year=None):
        """Chọn các SO đã hoàn thành trong `year` kèm ngày hoàn thành.

        Dùng CHUNG cho báo cáo thưởng (sale.closed.incentive) và báo cáo hiệu
        quả dự án chung (group.project.efficiency.detail).

        Điều kiện:
          - SO có >= 1 dự án con và TẤT CẢ dự án con đều đã đóng, trong đó:
              * dự án THƯỜNG: active=False & state='completed' — coi là hoàn thành
                kể cả không phát sinh chi phí;
              * dự án GỐC (main_project=TRUE): NHÂN NHƯỢNG điều kiện state — chỉ cần
                đã LƯU TRỮ (active=False) là coi như đóng, KHÔNG bắt buộc
                state='completed' (gốc thường để nguyên ở 'planning'). Nhưng nếu
                còn active (chưa lưu trữ) thì vẫn coi là CHƯA đóng.
          - Không còn hóa đơn bán/hoàn nào chưa 'paid';
          - completion_date = GREATEST(ngày dự án muộn nhất, ngày thu hóa đơn) và
            nằm trong năm. Ngày dự án lấy từ nguồn CHUNG
            project.project._project_completion_dates (nguồn -> x_date_end ->
            x_date_plan_end); SO không có ngày nào -> bỏ qua.

        Trả về list [{'sale_order_id', 'sale_order_name', 'completion_date'}].
        """
        if not year:
            year = fields.Date.today().year
        year = int(year)
        start = date(year, 1, 1)
        end = date(year, 12, 31)

        # {project_id: ngày} các dự án active=False & completed (có thể None).
        comp = self.env['project.project']._project_completion_dates()

        # Dự án con -> SO. Loại dự án ĐÃ GỘP (x_merge_project_id set) — coi như
        # đóng, đã tính ở dự án gộp; không được chặn điều kiện hoàn thành của SO.
        #
        # Dự án GỐC (main_project=TRUE) VẪN được giữ để xét, nhưng nhân nhượng
        # điều kiện state: chỉ cần đã lưu trữ (active=False) là coi như đóng.
        # -> cần cờ main_project + active của từng dự án để xử lý riêng.
        self.env.cr.execute("""
            SELECT so.id, so.name, pp.id, pp.main_project, pp.active
            FROM sale_order so JOIN project_project pp ON pp.x_order_id = so.id
            WHERE pp.x_merge_project_id IS NULL
        """)
        so_pids, so_name = {}, {}
        pid_is_main, pid_active = {}, {}
        for so_id, name, pid, is_main, active in self.env.cr.fetchall():
            so_pids.setdefault(so_id, set()).add(pid)
            so_name[so_id] = name
            pid_is_main[pid] = bool(is_main)
            pid_active[pid] = bool(active)

        # Ngày thu hóa đơn muộn nhất / SO.
        self.env.cr.execute("""
            SELECT x_order_id, MAX(x_payment_latest_date)
            FROM account_move
            WHERE x_order_id IS NOT NULL AND move_type = 'out_invoice'
              AND state != 'cancel' AND x_payment_latest_date IS NOT NULL
            GROUP BY x_order_id
        """)
        pay_date = {r[0]: r[1] for r in self.env.cr.fetchall()}

        # SO còn hóa đơn bán/hoàn CHƯA 'paid' -> loại.
        self.env.cr.execute("""
            SELECT DISTINCT x_order_id FROM account_move
            WHERE x_order_id IS NOT NULL AND move_type IN ('out_invoice', 'out_refund')
              AND state != 'cancel' AND (payment_state IS NULL OR payment_state != 'paid')
        """)
        has_unpaid = {r[0] for r in self.env.cr.fetchall()}

        result = []
        for so_id, pids in so_pids.items():
            if so_id in has_unpaid:
                continue
            # TẤT CẢ dự án của SO phải đã đóng:
            #  - dự án thường: phải có mặt trong comp (active=False & completed);
            #  - dự án GỐC (main_project): chỉ cần đã lưu trữ (active=False),
            #    nhân nhượng state; còn active (chưa lưu trữ) -> chưa đóng.
            if not pids:
                continue
            closed = True
            for pid in pids:
                if pid_is_main.get(pid):
                    if pid_active.get(pid):
                        closed = False
                        break
                elif pid not in comp:
                    closed = False
                    break
            if not closed:
                continue
            # Ngày dự án chỉ lấy từ nguồn chung (comp = completed+archived); dự án
            # gốc lưu-trữ-nhưng-chưa-completed không có trong comp -> không góp ngày.
            dates = [comp[pid] for pid in pids if comp.get(pid)]
            max_proj = max(dates) if dates else None
            pd = pay_date.get(so_id)
            completion = (max(max_proj, pd) if max_proj and pd else (max_proj or pd))
            if not completion or not (start <= completion <= end):
                continue
            result.append({
                'sale_order_id': so_id,
                'sale_order_name': so_name[so_id],
                'completion_date': completion,
            })
        result.sort(key=lambda r: r['completion_date'], reverse=True)
        return result

    def _group_eff_posted_invoices(self):
        """Hóa đơn bán đã posted của SO: gồm cả hóa đơn gắn qua invoice_ids chuẩn
        LẪN hóa đơn gắn SO qua x_order_id (tránh sót thanh toán trên hóa đơn
        không gắn dòng SO)."""
        self.ensure_one()
        invoices = self.invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
        via_x_order = self.env['account.move'].search([
            ('x_order_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ])
        return invoices | via_x_order

    def _group_eff_cash_on_invoice(self, inv):
        """Tiền mặt thực thu trên 1 hóa đơn = tổng các khoản ĐỐI SOÁT (reconcile)
        trên dòng phải thu mà đối ứng là PHIẾU THU (account.payment inbound).
        Bao gồm cả tạm ứng/đặt cọc cấn trừ vào hóa đơn; LOẠI TRỪ phần tất toán
        bằng credit note / xóa nợ (không phải account.payment)."""
        cash = 0.0
        for line in inv.line_ids.filtered(
                lambda l: l.account_id.internal_type == 'receivable'):
            for part in line.matched_credit_ids:
                pay = part.credit_move_id.move_id.payment_id
                if pay and pay.payment_type == 'inbound':
                    cash += part.amount
        return cash

    def _group_eff_unreconciled_deposit_gross(self):
        """Tiền đặt cọc (phiếu thu có x_origin_so_id = SO) đã posted NHƯNG chưa
        cấn trừ hết vào hóa đơn -> tổng phần DƯ (còn VAT) trên dòng phải thu.

        Đặt cọc chưa xuất/cấn hóa đơn không lọt vào doanh thu (chỉ đếm tiền
        reconcile TRÊN hóa đơn) lẫn "Thanh toán không HĐ" (cột này loại đặt cọc),
        nên khoản thực thu này bị bỏ sót. Chỉ lấy phần DƯ (amount_residual): phần
        đã cấn vào hóa đơn đã được tính ở doanh thu qua _group_eff_cash_on_invoice,
        lấy cả số gốc sẽ đếm trùng."""
        self.ensure_one()
        deposits = self.env['account.payment'].search([
            ('x_origin_so_id', '=', self.id),
            ('state', '=', 'posted'),
            ('payment_type', '=', 'inbound'),
        ])
        total = 0.0
        for pay in deposits:
            for line in pay.move_id.line_ids.filtered(
                    lambda l: l.account_id.internal_type == 'receivable'):
                # Dòng phải thu của phiếu thu là bên CÓ -> residual âm; phần dư
                # chưa cấn trừ = -amount_residual (>0).
                total += -line.amount_residual
        return total

    # Khoản thu IV (code.money) phải loại khỏi "Thanh toán không HĐ".
    _GROUP_EFF_IV_RECEIPT_CODES = ('RIV', 'IV')

    def _group_eff_payment_no_invoice(self):
        """Thanh toán (không HĐ), TRƯỚC THUẾ = các phiếu thu (inbound, posted)
        được phân bổ cho SO NHƯNG loại trừ: đặt cọc (x_origin_so_id), hóa đơn gốc
        của SO (x_origin_move_id - gồm cả hóa đơn gắn qua x_order_id), và KHOẢN THU
        IV (code_money RIV/IV). Trừ thuế theo tax_percent từng dòng.

        NGUỒN phân bổ tuỳ cờ x_pay_cost của phiếu (khớp báo cáo chi phí:
        x_pay_cost ? payment.line : project.detail) — nếu chỉ đọc project.detail
        sẽ SÓT toàn bộ phiếu thu chi-phí (x_pay_cost=True) vốn khai ở payment.line:
          - x_pay_cost=False -> dòng 'Chi tiết dự án' (project.detail);
          - x_pay_cost=True  -> dòng 'Chi tiết' (payment.line).
        Mỗi nguồn gắn SO qua: mã dự án chính (code_project / x_sale_project_id) =
        SO; HOẶC field đó TRỐNG nhưng project_id là 1 dự án con của SO (có trường
        hợp chỉ khai dự án con)."""
        self.ensure_one()
        own_invoice_ids = set(self._group_eff_posted_invoices().ids)
        # Toàn bộ dự án con của SO (kể cả đã lưu trữ) để bắt các dòng chỉ khai
        # project_id.
        sub_project_ids = self.env['project.project'].sudo().with_context(
            active_test=False).search([('x_order_id', '=', self.id)]).ids

        def _keep(pay):
            if pay.x_origin_so_id.id == self.id:
                return False  # đặt cọc của chính SO
            if pay.x_origin_move_id and pay.x_origin_move_id.id in own_invoice_ids:
                return False  # thanh toán hóa đơn gốc của chính SO
            if pay.x_code_money and pay.x_code_money.code_money in self._GROUP_EFF_IV_RECEIPT_CODES:
                return False  # khoản thu IV
            return True

        total = 0.0
        # (a) Phiếu thu x_pay_cost=False -> project.detail.
        details = self.env['project.detail'].sudo().search([
            '|',
                ('code_project', '=', self.id),
                '&', ('code_project', '=', False),
                     ('project_id', 'in', sub_project_ids),
            ('payment_id.state', '=', 'posted'),
            ('payment_id.payment_type', '=', 'inbound'),
            ('payment_id.x_pay_cost', '!=', True),
            ('amount_total', '!=', 0),
        ])
        for d in details:
            if _keep(d.payment_id):
                total += d.amount_total / (1 + (d.tax_percent or 0) / 100.0)

        # (b) Phiếu thu x_pay_cost=True -> payment.line.
        plines = self.env['payment.line'].sudo().search([
            '|',
                ('x_sale_project_id', '=', self.id),
                '&', ('x_sale_project_id', '=', False),
                     ('project_id', 'in', sub_project_ids),
            ('payment_id.state', '=', 'posted'),
            ('payment_id.payment_type', '=', 'inbound'),
            ('payment_id.x_pay_cost', '=', True),
            ('amount', '!=', 0),
        ])
        for l in plines:
            if _keep(l.payment_id):
                total += l.amount / (1 + (l.tax_percent or 0) / 100.0)
        return total

    def get_group_efficiency(self):
        """Hiệu quả THỰC TẾ của SO.

        - Doanh thu = tiền mặt thực thu trên hóa đơn (qua reconcile, gồm cả tạm
          ứng/đặt cọc, loại credit note/xóa nợ), quy về TRƯỚC THUẾ theo tỉ lệ
          amount_untaxed/amount_total của từng hóa đơn; CỘNG THÊM phần đặt cọc đã
          thu nhưng chưa cấn trừ hết vào hóa đơn (quy trước thuế theo tỉ lệ VAT
          của SO) để không bỏ sót tiền thực thu chưa xuất hóa đơn.
        - Tổng chi phí = Nhân công + Vật tư & khác + Chi phí CCDC (khấu hao +
          hỏng/mất) + IV (cộng dồn TẤT CẢ dự án của SO, kể cả main_project)
          + Overhead (= tỉ lệ
          overhead_cost % của SO x doanh thu).
        - Hiệu quả (trước thuế) = Doanh thu + Thanh toán (không HĐ) - Tổng chi
          phí + Doanh thu IV - Phí mua hàng không HĐ.
        - Thuế phải nộp (TNDN+TNCN) =
            (Doanh thu - Nhân công - Chi phí CCDC - Overhead - Tổng giá trị HĐ
             đầu vào) x thuế suất TNDN
          + (Chi phí CR + Chi phí TP) x 5% / 95%.
          Tổng giá trị HĐ đầu vào (S) = phần chi phí CÓ hóa đơn thật (license
          'tax', đối lập với "Phí mua hàng không HĐ" vốn chỉ tính phần KHÔNG
          hóa đơn) + giá trị hóa đơn IV đã xử lý; loại CR/TP (đã tính TNCN
          riêng ở trên).
        - Hiệu quả dự án sau thuế = Hiệu quả (trước thuế) - Thuế phải nộp.

        Lưu ý: việc "bỏ qua main_project" chỉ áp ở ĐIỀU KIỆN hoàn thành (kệ main
        ở planning) tại khâu chọn SO; CHI PHÍ vẫn cộng đủ mọi dự án.

        Trả về dict các thành phần để các báo cáo dùng chung."""
        self.ensure_one()
        invoices = self._group_eff_posted_invoices()

        revenue = 0.0
        for inv in invoices:
            cash = self._group_eff_cash_on_invoice(inv)
            if inv.amount_total:
                revenue += cash * inv.amount_untaxed / inv.amount_total
            else:
                revenue += cash

        # Cộng đặt cọc đã thu nhưng chưa cấn trừ hết vào hóa đơn (phần dư), quy về
        # TRƯỚC THUẾ theo tỉ lệ VAT của báo giá (amount_untaxed/amount_total của SO).
        deposit_gross = self._group_eff_unreconciled_deposit_gross()
        if deposit_gross:
            if self.amount_total:
                revenue += deposit_gross * self.amount_untaxed / self.amount_total
            else:
                revenue += deposit_gross

        payment_no_invoice = self._group_eff_payment_no_invoice()

        projects = self.env['project.project'].with_context(active_test=False).search([
            ('x_order_id', '=', self.id),
        ])
        labor = sum(projects.mapped('wage_cost_total'))
        materials = sum(projects.mapped('actual_costs'))
        # Chi phí CCDC = khấu hao + giá trị CCDC báo hỏng/mất quy về dự án.
        depreciation = (sum(projects.mapped('total_depreciation_cost'))
                        + sum(projects.mapped('x_damage_cost_total')))
        iv = sum(projects.mapped('iv_costs_total'))
        overhead = (self.overhead_cost or 0) / 100.0 * revenue
        total_cost = labor + materials + depreciation + iv + overhead

        # Điều chỉnh thuế TNDN (cộng dồn theo dự án con):
        #  + lãi thuế xử lý hóa đơn IV; - chi phí thuế khi mua hàng không hóa đơn
        iv_profit = sum(projects.mapped('invoice_processing_profit'))
        no_invoice_extra_cost = sum(projects.mapped('no_invoice_extra_cost'))

        # Hiệu quả dự án (trước thuế) = Doanh thu + Thanh toán không HĐ - Tổng
        #   chi phí + Doanh thu IV - Phí mua hàng không HĐ. (Tổng chi phí đã
        #   gồm Chi phí IV.)
        efficiency = (revenue + payment_no_invoice - total_cost
                      + iv_profit - no_invoice_extra_cost)

        # Tổng giá trị hóa đơn đầu vào (S) + Chi phí CR/TP (cộng dồn theo dự án
        # con) — dùng làm cơ sở tính Thuế phải nộp (TNDN+TNCN).
        input_invoice_total = sum(projects.mapped('input_invoice_value_total'))
        cr_tp_cost = sum(projects.mapped('cr_tp_cost_total'))

        # Thuế suất TNDN tra theo ngày kết thúc (muộn nhất) của dự án.
        end_dates = [p.x_date_end for p in projects if p.x_date_end]
        tndn_rate = self.env['tndn.tax.rate'].get_rate_for_date(
            max(end_dates) if end_dates else False) / 100.0

        # Thuế TNDN = (Doanh thu - Nhân công - Chi phí CCDC - Overhead - Tổng
        #   giá trị HĐ đầu vào) x thuế suất TNDN. (Vật tư/IV đã thay bằng S vì S
        #   phản ánh đúng phần CÓ hóa đơn được khấu trừ thuế; CR/TP loại khỏi S,
        #   xử lý riêng ở TNCN bên dưới.)
        cit_tndn = (revenue - labor - depreciation - overhead - input_invoice_total) * tndn_rate
        # Thuế TNCN (gross-up) trên chi phí CR + TP chi trả cho cá nhân = giá
        #   trị NET x 5% / (100% - 5%).
        cit_tncn = cr_tp_cost * 0.05 / 0.95
        cit_tax = cit_tndn + cit_tncn

        # Hiệu quả dự án sau thuế = Hiệu quả (trước thuế) - Thuế phải nộp
        #   (TNDN+TNCN). Đây cũng là GIÁ TRỊ TÍNH THƯỞNG cho sale.closed.incentive.
        incentive_base = efficiency - cit_tax

        return {
            'invoices': invoices,
            'projects': projects,
            'revenue': revenue,
            'payment_no_invoice': payment_no_invoice,
            'actual_labor': labor,
            'actual_materials_and_other_costs': materials,
            'total_depreciation_cost': depreciation,
            'iv_fee': iv,
            'overhead_cost_amount': overhead,
            'total_cost': total_cost,
            'invoice_processing_profit': iv_profit,
            'no_invoice_extra_cost': no_invoice_extra_cost,
            'efficiency': efficiency,
            'input_invoice_total': input_invoice_total,
            'cit_tax': cit_tax,
            'incentive_base': incentive_base,
        }
