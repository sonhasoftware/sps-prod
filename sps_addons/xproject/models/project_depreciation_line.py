# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProjectDepreciationLine(models.Model):
    _name = 'project.depreciation.line'
    _description = 'Chi phí khấu hao CCDC theo dự án'
    _order = 'date_borrow desc, id desc'

    project_id = fields.Many2one('project.project', 'Dự án',
                                 required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', 'CCDC', required=True, ondelete='restrict')
    lot_id = fields.Many2one('stock.production.lot', 'Số Lô/Sê-ri')
    quantity = fields.Float('Số lượng mượn', default=1.0,
                            help='Số lượng xuất kho của lần mượn này (giữ nguyên, không tách dòng).')
    returned_qty = fields.Float('Đã trả', default=0.0,
                                help='Tổng số lượng đã trả/thu hồi của lần mượn này (cộng dồn FIFO qua nhiều đợt).')
    remaining_qty = fields.Float('Còn lại', compute='_compute_live_values',
                                 help='= Số lượng mượn − Đã trả. Còn > 0 nghĩa là CCDC chưa trả hết.')
    receiver_id = fields.Many2one('res.users', 'Người nhận (trên phiếu)')

    picking_out_id = fields.Many2one('stock.picking', 'Phiếu xuất (mượn)', ondelete='set null')
    picking_in_ids = fields.Many2many(
        'stock.picking', 'project_depr_line_picking_in_rel', 'line_id', 'picking_id',
        'Phiếu nhập (trả/thu hồi)',
        help='Các phiếu trả/thu hồi đã khớp vào lần mượn này (có thể nhiều đợt).')
    has_picking_in = fields.Boolean('Có phiếu trả', compute='_compute_has_picking_in')

    @api.depends('picking_in_ids')
    def _compute_has_picking_in(self):
        for r in self:
            r.has_picking_in = bool(r.picking_in_ids)

    date_borrow = fields.Datetime('Thời điểm mượn', required=True)
    date_return = fields.Datetime('Thời điểm trả hết',
                                  help='Thời điểm đợt trả cuối hoàn tất (khi đã trả đủ số lượng).')

    allocation_type = fields.Selection([
        ('personal', 'Cấp cá nhân (mã dự án cá nhân)'),
        ('fm', 'Cấp dự án cố định - FM (Operation)'),
        ('ms', 'Cấp dự án linh hoạt - MS (Service/Maintenance)'),
    ], 'Loại cấp phát', required=True)

    state = fields.Selection([
        ('open', 'Đang mượn'),
        ('closed', 'Đã trả / Hỏng / Mất'),
    ], 'Trạng thái', default='open', required=True)

    cost_unit = fields.Float('Giá vốn đơn vị',
                             help='Giá vốn (standard_price) của CCDC tại thời điểm xuất kho.')
    hours_per_year_snapshot = fields.Float('Giờ dự kiến/năm (snapshot)',
                                           help='Số giờ dự kiến trong năm của CCDC tại thời điểm tạo dòng. Dùng cho FM/MS.')
    depreciation_years = fields.Float('Số năm khấu hao (snapshot)',
                                      help='Số năm khấu hao dự kiến của CCDC tại thời điểm tạo dòng.')

    hours_locked = fields.Float('Giờ đã chốt (phần đã trả)',
                                help='Tổng giờ đã chốt cho các đơn vị ĐÃ trả, cộng dồn theo từng đợt trả. '
                                     'Mỗi đợt trả tính giờ riêng từ lúc mượn đến đúng ngày trả đợt đó.')
    value_locked = fields.Float('Giá trị khấu hao đã chốt (phần đã trả)',
                                help='Tổng giá trị khấu hao đã chốt cho các đơn vị đã trả.')

    total_hours = fields.Float('Tổng số giờ', compute='_compute_live_values',
                               help='Giờ phần đã trả (chốt) + giờ phần còn đang mượn (tính tới hiện tại).')
    hourly_rate = fields.Float('Đơn giá khấu hao (đ/h)', compute='_compute_live_values')
    depreciation_value = fields.Float('Giá trị khấu hao', compute='_compute_live_values',
                                      help='Giá trị đã chốt (phần đã trả) + giá trị phần còn mượn tính động.')

    note = fields.Char('Ghi chú')

    @api.depends('state', 'date_borrow', 'allocation_type', 'cost_unit',
                 'quantity', 'returned_qty', 'hours_per_year_snapshot',
                 'depreciation_years', 'hours_locked', 'value_locked')
    def _compute_live_values(self):
        now = fields.Datetime.now()
        for r in self:
            remaining = (r.quantity or 0.0) - (r.returned_qty or 0.0)
            r.remaining_qty = remaining
            rate = r._calc_hourly_rate()
            r.hourly_rate = rate
            # Tính giờ-giữ-máy động cho MỌI loại cấp phát (personal/fm/ms):
            # khấu hao CCDC cấp cá nhân nay cũng ghi vào dự án như fm/ms.
            # LƯU Ý: với 'personal', khoản này được tính SONG SONG với phần đã
            # gộp trong đơn giá nhân công (get_personal_ccdc_rate + xhr_payroll)
            # — theo yêu cầu giữ cả hai, nên sẽ tính trùng trên báo cáo hiệu quả.
            # phần còn đang mượn: tính giờ động từ lúc mượn tới hiện tại
            open_unit_hours = r._hours_per_unit(end_dt=now) if remaining > 0 else 0.0
            open_hours = open_unit_hours * max(remaining, 0.0)
            r.total_hours = (r.hours_locked or 0.0) + open_hours
            r.depreciation_value = (r.value_locked or 0.0) + open_hours * rate

    def _hours_per_unit(self, end_dt=None):
        """Số giờ mượn của MỘT đơn vị, từ lúc mượn đến end_dt.

        Tính theo giờ THỰC trôi qua (24h/ngày, liên tục) cho MỌI loại cấp
        phát — đã quy hết về nền 24h, không còn phân biệt giờ làm việc 8h.
        """
        self.ensure_one()
        if not self.date_borrow:
            return 0.0
        end = end_dt or fields.Datetime.now()
        if isinstance(end, str):
            end = fields.Datetime.from_string(end)
        start = self.date_borrow
        if end < start:
            return 0.0
        delta = end - start
        return delta.total_seconds() / 3600.0

    def _calc_hourly_rate(self):
        """Đơn giá khấu hao = giá vốn / số năm / số giờ dự kiến trong năm.

        Áp dụng CHUNG cho mọi loại cấp phát (personal/fm/ms). Số giờ dự kiến
        trong năm lấy từ snapshot của product (x_hours_per_year) tại lúc tạo
        dòng — với CCDC cá nhân, SPS set số giờ này = số giờ sử dụng 1 năm.
        """
        self.ensure_one()
        years = self.depreciation_years or 0.0
        cost = self.cost_unit or 0.0
        hpy = self.hours_per_year_snapshot or 0.0
        if years <= 0 or cost <= 0 or hpy <= 0:
            return 0.0
        return cost / years / hpy

    @api.model
    def _resolve_allocation_type(self, project):
        if project.personal_employee_id:
            return 'personal'
        if project.x_project_type == 'operation':
            return 'fm'
        return 'ms'

    @api.model
    def get_personal_ccdc_rate(self, employee, year, month):
        """Đơn giá khấu hao CCDC cấp cá nhân (đ/giờ công) của 1 nhân viên/tháng.

        = Σ ( giá vốn × số lượng / số năm / số giờ dự kiến trong năm )
        cho các CCDC cá nhân (allocation_type='personal') thuộc dự án do nhân
        viên này sở hữu (project_id.personal_employee_id), CÒN ĐANG MƯỢN trong
        kỳ chấm công — khớp ngày mượn/trả với biên tháng (mượn trước cuối tháng
        VÀ chưa trả hoặc trả từ đầu tháng trở đi).

        LƯU Ý: tính chừng nào CCDC còn được mượn, KHÔNG dừng khi hết thời gian
        khấu hao (theo yêu cầu nghiệp vụ SPS). Do đó tổng khấu hao trích cho 1
        công cụ có thể vượt giá vốn nếu giữ quá số năm khấu hao.

        Đơn giá này được cộng vào đơn giá nhân công hàng tháng (xhr_payroll),
        rồi nhân với giờ công thực tế để ra chi phí khấu hao phân bổ.
        Ví dụ: máy tính 15tr / 5 năm / số giờ dự kiến/năm = đ/giờ.
        """
        if not employee:
            return 0.0
        from datetime import date
        try:
            month = int(month)
            year = int(year)
        except (TypeError, ValueError):
            return 0.0
        month_start = date(year, month, 1)
        month_end = date(year + (month == 12), (month % 12) + 1, 1)  # ngày 1 tháng sau

        # CCDC cá nhân của dự án do nhân viên này sở hữu, còn giữ trong tháng
        lines = self.search([
            ('allocation_type', '=', 'personal'),
            ('project_id.personal_employee_id', '=', employee.id),
            ('date_borrow', '<', fields.Datetime.to_datetime(month_end)),
            '|', ('date_return', '=', False),
                 ('date_return', '>=', fields.Datetime.to_datetime(month_start)),
        ])
        rate = 0.0
        for ln in lines:
            years = ln.depreciation_years or 0.0
            cost = ln.cost_unit or 0.0
            hours_year = ln.hours_per_year_snapshot or 0.0
            if years <= 0 or cost <= 0 or hours_year <= 0 or not ln.date_borrow:
                continue
            # Tính chừng nào CCDC còn được mượn trong kỳ (đã lọc qua ngày mượn/
            # trả ở search) — KHÔNG dừng khi hết thời gian khấu hao (theo yêu cầu
            # nghiệp vụ SPS).
            qty = ln.quantity or 1.0
            rate += cost * qty / years / hours_year
        return rate

    @api.model
    def _rebuild_for_project(self, project, preserve_snapshot=False):
        """Quét lịch sử stock.move.line đã done của 1 dự án và build lại bảng.

        Sự kiện MỞ (mượn): type_4 (xuất) / type_5 (chuyển giao đến) có
            x_to_the_project_id = dự án.
        Sự kiện ĐÓNG (trả/thu hồi): type_6 (thu hồi) / type_5 (chuyển giao đi)
            có x_from_the_project_id = dự án.
        Các sự kiện được sắp theo thời gian để khớp FIFO theo số lượng cho đúng
        (mở trước, đóng sau khi trùng thời điểm).

        Idempotent: xoá toàn bộ line của project rồi build lại.

        preserve_snapshot=True: giữ nguyên giá vốn/cấu hình (cost_unit,
        hours_per_year_snapshot, depreciation_years) của các dòng cũ, khớp theo
        (phiếu mượn, product, lot). Dùng khi chỉ ĐỒNG BỘ NGÀY (sửa date_done)
        — thay đổi ngày nhưng không làm mới giá vốn theo product hiện tại.
        """
        if not project:
            return self.browse()
        existing = self.search([('project_id', '=', project.id)])
        old_snap = {}
        if preserve_snapshot:
            for ln in existing:
                key = (ln.picking_out_id.id, ln.product_id.id, ln.lot_id.id or 0)
                old_snap[key] = {
                    'cost_unit': ln.cost_unit,
                    'hours_per_year_snapshot': ln.hours_per_year_snapshot,
                    'depreciation_years': ln.depreciation_years,
                }
        existing.unlink()

        ML = self.env['stock.move.line']
        tools_domain = [
            ('state', '=', 'done'),
            ('product_id.product_tmpl_id.x_type', '=', 'product'),
            ('product_id.product_tmpl_id.x_product_type', '=', 'tools'),
        ]
        open_mls = ML.search(tools_domain + [
            ('x_picking_type', 'in', ['type_4', 'type_5']),
            ('x_to_the_project_id', '=', project.id),
        ])
        close_mls = ML.search(tools_domain + [
            ('x_picking_type', 'in', ['type_5', 'type_6']),
            ('x_from_the_project_id', '=', project.id),
        ])

        def _dt(ml):
            return ml.picking_id.date_done or ml.date or fields.Datetime.now()

        events = [(_dt(ml), 0, ml) for ml in open_mls]          # 0 = mở
        events += [(_dt(ml), 1, ml) for ml in close_mls]        # 1 = đóng
        # cùng thời điểm: mở (0) xử lý trước đóng (1)
        events.sort(key=lambda e: (e[0], e[1]))

        # carry: lượng trả VƯỢT tại 1 thời điểm (data nhập lệch thứ tự) — bù vào
        # lần mượn kế tiếp để tổng open cuối cùng = net (mượn - trả), tránh kẹt open.
        carry = {}
        created = self.browse()
        eps = 1e-6
        for dt, kind, ml in events:
            picking = ml.picking_id
            key = (ml.product_id.id, ml.lot_id.id or 0)
            if kind == 0:
                qty = ml.qty_done or 0.0
                pending = carry.get(key, 0.0)
                if pending > eps:
                    applied = min(pending, qty)
                    carry[key] = pending - applied
                    qty -= applied
                if qty > eps:
                    snap = old_snap.get(
                        (picking.id if picking else False,
                         ml.product_id.id, ml.lot_id.id or 0)) if preserve_snapshot else None
                    created |= self.open_line(
                        project=project,
                        product=ml.product_id,
                        lot=ml.lot_id,
                        qty=qty,
                        receiver=picking.x_receiver_id,
                        picking=picking,
                        date_borrow=dt,
                        snapshot=snap,
                    )
            else:
                leftover = self.register_return(
                    project=project,
                    product=ml.product_id,
                    lot=ml.lot_id,
                    qty=ml.qty_done,
                    picking_in=picking,
                    date_return=dt,
                )
                if leftover and leftover > eps:
                    carry[key] = carry.get(key, 0.0) + leftover
        return created

    @api.model
    def open_line(self, project, product, lot, qty, receiver, picking, date_borrow,
                  snapshot=None):
        """Tạo 1 dòng khấu hao state='open' khi xuất CCDC (type_4).

        snapshot: khi rebuild để ĐỒNG BỘ NGÀY (preserve_snapshot=True), truyền
        vào giá vốn/cấu hình cũ để GIỮ NGUYÊN thay vì đọc lại từ product hiện
        tại. Khi mượn mới (không truyền), snapshot theo product tại lúc xuất kho.
        """
        if not project or not product:
            return self.browse()
        tmpl = product.product_tmpl_id
        if tmpl.x_type != 'product' or tmpl.x_product_type != 'tools':
            return self.browse()
        snapshot = snapshot or {}
        vals = {
            'project_id': project.id,
            'product_id': product.id,
            'lot_id': lot.id if lot else False,
            'quantity': qty or 1.0,
            'receiver_id': receiver.id if receiver else False,
            'picking_out_id': picking.id if picking else False,
            'date_borrow': date_borrow or fields.Datetime.now(),
            'allocation_type': self._resolve_allocation_type(project),
            'cost_unit': snapshot.get('cost_unit', product.standard_price),
            'hours_per_year_snapshot': snapshot.get(
                'hours_per_year_snapshot', tmpl.x_hours_per_year),
            'depreciation_years': snapshot.get(
                'depreciation_years', tmpl.x_depreciation_years),
            'state': 'open',
        }
        return self.create(vals)

    @api.model
    def register_return(self, project, product, lot, qty, picking_in, date_return):
        """Ghi nhận trả/thu hồi CCDC theo SỐ LƯỢNG (type_6/type_5 chuyển giao đi).

        KHÔNG tách dòng: trừ FIFO vào returned_qty của các dòng mượn open
        (cũ nhất trước). Mỗi đợt trả cộng dồn giờ/giá trị đã chốt cho đúng số
        đơn vị trả ở đợt đó (tính giờ từ lúc mượn đến đúng ngày trả đợt này).
        Khi returned_qty đạt quantity → dòng đóng (state='closed').

        Trả về phần trả VƯỢT (không còn dòng open để khớp) để caller bù carry.
        """
        if not project or not product:
            return 0.0
        remaining = qty or 0.0
        if remaining <= 0:
            return 0.0
        date_return = date_return or fields.Datetime.now()
        domain = [
            ('project_id', '=', project.id),
            ('product_id', '=', product.id),
            ('state', '=', 'open'),
        ]
        if lot:
            domain.append(('lot_id', '=', lot.id))
        else:
            domain.append(('lot_id', '=', False))
        candidates = self.search(domain, order='date_borrow asc, id asc')

        eps = 1e-6
        for line in candidates:
            if remaining <= eps:
                break
            avail = (line.quantity or 0.0) - (line.returned_qty or 0.0)
            if avail <= eps:
                continue
            take = min(avail, remaining)
            # chốt giờ + giá trị cho `take` đơn vị, tính tới đúng ngày trả đợt này
            unit_hours = line._hours_per_unit(end_dt=date_return)
            rate = line._calc_hourly_rate()
            vals = {
                'returned_qty': (line.returned_qty or 0.0) + take,
                'hours_locked': (line.hours_locked or 0.0) + unit_hours * take,
                'value_locked': (line.value_locked or 0.0) + unit_hours * rate * take,
            }
            if picking_in:
                vals['picking_in_ids'] = [(4, picking_in.id)]
            # đã trả đủ → đóng dòng, ghi thời điểm trả hết
            if vals['returned_qty'] >= (line.quantity or 0.0) - eps:
                vals['state'] = 'closed'
                vals['date_return'] = date_return
            line.write(vals)
            remaining -= take
        return remaining

    def action_open_picking_out(self):
        """Mở phiếu xuất (mượn) CCDC. Luôn 1 phiếu → form, target='new', readonly."""
        self.ensure_one()
        if not self.picking_out_id:
            raise UserError(_('Dòng này không gắn phiếu xuất (mượn).'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Phiếu mượn'),
            'res_model': 'stock.picking',
            'res_id': self.picking_out_id.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'readonly',
                'create': False, 'edit': False, 'delete': False,
            },
        }

    def action_open_picking_in(self):
        """Mở phiếu trả/thu hồi CCDC.

        - 1 phiếu → form, target='new' (popup), readonly không cho chỉnh sửa.
        - Nhiều phiếu → tree, target='current'.
        """
        self.ensure_one()
        pickings = self.picking_in_ids
        if not pickings:
            raise UserError(_('Dòng này chưa có phiếu trả / thu hồi.'))
        if len(pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Phiếu trả / thu hồi'),
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': pickings.id,
                'target': 'new',
                'context': {
                    'form_view_initial_mode': 'readonly',
                    'create': False, 'edit': False, 'delete': False,
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Phiếu trả / thu hồi'),
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', pickings.ids)],
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # One-shot: tính lại TOÀN BỘ dữ liệu khấu hao + đơn giá nhân công
    # ------------------------------------------------------------------
    @api.model
    def _ccdc_project_ids(self):
        """Các dự án từng phát sinh xuất/thu hồi CCDC (theo stock.move.line)."""
        self.env.cr.execute("""
            SELECT DISTINCT pid FROM (
                SELECT x_to_the_project_id   AS pid FROM stock_move_line
                    WHERE state = 'done' AND x_picking_type IN ('type_4', 'type_5')
                      AND x_to_the_project_id IS NOT NULL
                UNION
                SELECT x_from_the_project_id AS pid FROM stock_move_line
                    WHERE state = 'done' AND x_picking_type IN ('type_5', 'type_6')
                      AND x_from_the_project_id IS NOT NULL
            ) t
        """)
        return [r[0] for r in self.env.cr.fetchall() if r[0]]

    @api.model
    def _cleanup_legacy_cron(self):
        """Gỡ cron đồng bộ chi phí nhân công nặng (cũ) + cột flag không còn dùng.

        Record cron để noupdate nên KHÔNG tự xoá khi gỡ khỏi XML — phải xoá
        bằng code. Idempotent, gọi an toàn nhiều lần.
        """
        cron = self.env.ref(
            'xhr_payroll.cron_compute_related_projects_wage_cost',
            raise_if_not_found=False)
        if cron:
            cron.sudo().unlink()
        self.env.cr.execute(
            "ALTER TABLE hr_work_entry DROP COLUMN IF EXISTS project_cost_sync_pending")

    @api.model
    def recompute_all_ccdc(self, payslip_date_from=None, recompute_payslip=True,
                           batch_commit=True):
        """Tính lại toàn bộ khấu hao CCDC + đơn giá nhân công (chạy 1 lần).

        Dùng SAU khi đã điền cấu hình: số năm khấu hao & số giờ dự kiến/năm
        (x_hours_per_year) trên product CCDC. Gọi từ Odoo shell::

            env['project.depreciation.line'].recompute_all_ccdc()
            env.cr.commit()

        Trình tự:
          0. Dọn cron nặng cũ + cột flag (thay cho migration).
          1. Build lại bảng project.depreciation.line theo lịch sử phiếu
             (đọc lại cost_unit / số năm / số giờ mới nhất từ product).
          2. Tính lại đơn giá nhân công (unit_price) cho payslip đã 'done' của
             các nhân viên đang giữ CCDC cá nhân → cộng đơn giá khấu hao vào.
        ``depreciation_cost`` không lưu DB nên tự tươi, không cần build lại.
        """
        import logging
        _logger = logging.getLogger(__name__)

        # 0. dọn tàn dư cơ chế cũ
        self._cleanup_legacy_cron()

        # 1. build lại bảng khấu hao
        project_ids = self._ccdc_project_ids()
        Project = self.env['project.project'].with_context(active_test=False)
        projects = Project.browse(project_ids).exists()
        _logger.info('[KH-CCDC] Build lại khấu hao cho %s dự án.', len(projects))
        for i, project in enumerate(projects, 1):
            try:
                self._rebuild_for_project(project)
            except Exception as e:  # noqa: BLE001
                _logger.exception('[KH-CCDC] Lỗi build project %s: %s', project.id, e)
            if batch_commit and i % 50 == 0:
                self.env.cr.commit()
                _logger.info('[KH-CCDC] ... %s/%s dự án', i, len(projects))
        if batch_commit:
            self.env.cr.commit()

        if not recompute_payslip:
            return True

        # 2. tính lại đơn giá nhân công cho nhân viên có CCDC cá nhân
        personal = self.search([
            ('allocation_type', '=', 'personal'),
            ('project_id.personal_employee_id', '!=', False),
        ])
        if not personal:
            _logger.info('[KH-CCDC] Không có CCDC cá nhân (có chủ dự án) — bỏ qua tính lại đơn giá.')
            return True
        employees = personal.mapped('project_id.personal_employee_id')
        if not payslip_date_from:
            borrows = [d for d in personal.mapped('date_borrow') if d]
            payslip_date_from = min(borrows).date().replace(day=1) if borrows else None

        ps_domain = [('state', '=', 'done'), ('employee_id', 'in', employees.ids)]
        if payslip_date_from:
            ps_domain.append(('date_from', '>=', payslip_date_from))
        payslips = self.env['hr.payslip'].search(ps_domain, order='date_from')
        total = len(payslips)
        _logger.info('[KH-CCDC] Tính lại đơn giá nhân công cho %s phiếu lương '
                     '(%s nhân viên có CCDC cá nhân).', total, len(employees))
        for i, ps in enumerate(payslips, 1):
            try:
                ps.create_wage_cost_actual()
            except Exception as e:  # noqa: BLE001
                _logger.exception('[KH-CCDC] Lỗi payslip %s: %s', ps.id, e)
            if batch_commit and i % 100 == 0:
                self.env.cr.commit()
                _logger.info('[KH-CCDC] ... %s/%s phiếu lương', i, total)
        if batch_commit:
            self.env.cr.commit()
        _logger.info('[KH-CCDC] Hoàn tất recompute_all_ccdc.')
        return True

    @api.model
    def action_recompute_ccdc_now(self):
        """Nút bấm: lên lịch chạy recompute_all_ccdc NỀN ngay (qua cron one-shot).

        Chạy nền để tránh timeout web (recompute mất vài phút). Trả về thông báo.
        """
        cron = self.env.ref('xproject.cron_recompute_all_ccdc',
                             raise_if_not_found=False)
        if cron:
            cron.sudo().write({
                'active': True,
                'numbercall': 1,
                'nextcall': fields.Datetime.now(),
            })
            message = ('Đã lên lịch tính lại TOÀN BỘ khấu hao CCDC + đơn giá nhân '
                       'công, chạy nền ngay (vài phút). Theo dõi ở Cài đặt → Kỹ '
                       'thuật → Tác vụ định kỳ, hoặc log server.')
        else:
            # Không có cron (vd: chưa upgrade) → chạy đồng bộ luôn.
            self.recompute_all_ccdc()
            message = 'Đã tính lại xong khấu hao CCDC + đơn giá nhân công.'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Khấu hao CCDC'),
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }


class ProjectWageCostDepreciation(models.Model):
    _inherit = 'project.wage.cost'

    depreciation_cost = fields.Float(
        'Giá trị khấu hao CCDC',
        compute='_compute_depreciation_cost', store=False,
        help='Phần chi phí khấu hao CCDC cấp cá nhân đã gộp trong chi phí nhân công '
             '= giờ công tính chi phí × đơn giá khấu hao CCDC của nhân viên trong tháng. '
             'Cột chỉ để tiện đối chiếu (tính trực tiếp, không lưu DB).')

    @api.depends('work_hour', 'employee_id', 'year', 'month')
    def _compute_depreciation_cost(self):
        for rec in self:
            rate = 0.0
            if (rec.employee_id and rec.year and rec.month
                    and 'project.depreciation.line' in self.env):
                rate = self.env['project.depreciation.line'].get_personal_ccdc_rate(
                    rec.employee_id, rec.year, rec.month)
            rec.depreciation_cost = (rec.work_hour or 0.0) * rate
