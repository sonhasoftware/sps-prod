# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

_Project_type = [
    ('maintainance', 'Maintenance'),
    ('service', 'Services'),
    ('operation', 'Facility Management'),
    ('trouble', 'Trouble shooting'),
    ('warranty', 'Warranty'),
    ('support', 'Support'),
    ('survey', 'Survey'),
]

# Nhãn phân loại dùng cho sheet Estimation (cột H) — khớp cách hiển thị của
# báo cáo Productivity (manpower.efficiency PROJECT_TYPE_LABEL).
ESTIMATION_CLASSIFY_LABEL = {
    'maintainance': 'Maintenance',
    'service': 'Services',
    'operation': 'FM',
}


class Project(models.Model):
    _inherit = 'project.project'

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Mã dự án đã tồn tại')
    ]
    label_tasks = fields.Char(tracking=True)
    x_to_invoice = fields.Boolean('Đã hoàn thành, cần xuất hóa đơn')
    personal_employee_id = fields.Many2one(
        'hr.employee', 'Nhân viên (dự án cá nhân)', index=True,
        help='Chọn nhân viên sở hữu nếu đây là mã dự án cá nhân (vd hanh.ttn). '
             'Có giá trị = dự án cá nhân: MỌI CCDC mượn vào đây được quy chi phí '
             'khấu hao cho đúng nhân viên này (bỏ qua người nhận trên phiếu), tính '
             'đơn giá theo số giờ dự kiến/năm (x_hours_per_year) của từng CCDC.')
    x_depreciation_line_ids = fields.One2many(
        'project.depreciation.line', 'project_id', 'Khấu hao CCDC')
    total_depreciation_cost = fields.Float(
        'Tổng chi phí khấu hao CCDC',
        compute='_compute_total_depreciation_cost',
        help='Tổng giá trị khấu hao CCDC ghi nhận vào dự án (bao gồm dòng đang mượn — tính động tới hiện tại).')
    x_damage_cost_total = fields.Float(
        'Tổng chi phí hỏng/mất CCDC',
        compute='_compute_damage_cost',
        help='Tổng giá vốn CCDC báo hỏng/mất quy về dự án này (dự án làm mất '
             'hoặc cá nhân làm mất ghi vào dự án cá nhân). Tính trực tiếp bằng '
             'SQL từ lịch sử phiếu Báo hỏng, mất CCDC (sequence_code=\'HM\') — '
             'giống cách actual_costs/material_usage_display tính, không qua '
             'bảng trung gian nào.')
    x_damage_line_display = fields.Html(
        'Chi tiết chi phí hỏng/mất CCDC', compute='_compute_damage_cost')

    @api.depends('x_depreciation_line_ids.depreciation_value')
    def _compute_total_depreciation_cost(self):
        for r in self:
            r.total_depreciation_cost = sum(r.x_depreciation_line_ids.mapped('depreciation_value'))

    def _compute_damage_cost(self):
        """Tính chi phí hỏng/mất CCDC quy về dự án — trực tiếp từ lịch sử
        stock_move_line/stock_picking, KHÔNG qua bảng trung gian (giống
        _compute_actual_costs/_compute_material_usage_display).

        Điều kiện lọc 1 dòng phiếu là hỏng/mất THẬT quy cho dự án này:
          - CCDC (x_type='product', x_product_type='tools') — không lấy vật tư;
          - đã done, qty_done > 0, đích đến ĐÚNG kho "Kho hàng hỏng, hủy";
          - phiếu Báo hỏng, mất CCDC (sequence_code='HM') — loại phiếu DUY
            NHẤT có "Từ dự án" trên form nên chỉ phiếu này quy trách nhiệm
            được cho dự án cụ thể;
          - KHÔNG phải chính nó là dòng trả lại, và sau đó KHÔNG bị move nào
            khác trả lại (coi như hết hỏng/mất khi dùng nút Return chính thức
            — origin_returned_move_id);
          - payer KHÁC "HM - Hao mòn" (hao mòn tự nhiên, không quy cho dự án
            nào — đã có chỉ tiêu riêng ở báo cáo hiệu suất nhân viên).
        Giá trị = qty_done × stock_valuation_layer.unit_cost (giá vốn TẠI THỜI
        ĐIỂM phát sinh, không đổi theo standard_price hiện tại).
        """
        sql = """
            SELECT sp.name AS picking_name, sp.date_done AS date,
                   pp.default_code AS product_code, pt.name AS product_name,
                   lot.name AS lot_name, rp.name AS payer_name,
                   sml.qty_done AS quantity, svl.unit_cost AS cost_unit,
                   sml.qty_done * svl.unit_cost AS damage_value
            FROM stock_move sm
                JOIN stock_move_line sml ON sml.move_id = sm.id
                JOIN stock_picking sp ON sp.id = sml.picking_id
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                JOIN product_product pp ON pp.id = sml.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN stock_production_lot lot ON lot.id = sml.lot_id
                LEFT JOIN stock_location sl ON sl.id = sml.location_dest_id
                LEFT JOIN res_users ru ON ru.id = sp.x_payer_id
                LEFT JOIN res_partner rp ON rp.id = ru.partner_id
                LEFT JOIN stock_valuation_layer svl ON svl.stock_move_id = sm.id
            WHERE spt.sequence_code = 'HM'
                AND sml.state = 'done'
                AND sml.qty_done > 0
                AND pt.x_type = 'product'
                AND pt.x_product_type = 'tools'
                AND sl.x_name = 'Kho hàng hỏng, hủy'
                AND sm.origin_returned_move_id IS NULL
                AND sm.id NOT IN (SELECT origin_returned_move_id FROM stock_move
                                  WHERE origin_returned_move_id IS NOT NULL)
                AND (ru.login IS NULL OR ru.login != 'HM')
                AND sml.x_from_the_project_id = %(project_id)s
            ORDER BY sp.date_done DESC, sml.id DESC
        """
        for rec in self:
            self._cr.execute(sql, {'project_id': rec.id})
            rows = self._cr.dictfetchall()
            rec.x_damage_cost_total = sum(r['damage_value'] or 0.0 for r in rows)
            if not rows:
                rec.x_damage_line_display = '<p>Không có dữ liệu hỏng/mất CCDC</p>'
                continue

            html = '''
            <div class="table-responsive">
                <table class="table table-sm table-bordered">
                    <thead class="thead-light">
                        <tr>
                            <th>Mã CCDC</th>
                            <th>Tên CCDC</th>
                            <th>Số Lô/Sê-ri</th>
                            <th>Người trả</th>
                            <th>Phiếu</th>
                            <th>Ngày</th>
                            <th>SL</th>
                            <th>Giá vốn</th>
                            <th>Giá trị hỏng/mất</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            total = 0.0
            for r in rows:
                total += r['damage_value'] or 0.0
                date_str = r['date'].strftime('%d/%m/%Y') if r['date'] else ''
                html += '''
                    <tr>
                        <td>{product_code}</td>
                        <td>{product_name}</td>
                        <td>{lot_name}</td>
                        <td>{payer_name}</td>
                        <td>{picking_name}</td>
                        <td>{date}</td>
                        <td class="text-right">{qty:.2f}</td>
                        <td class="text-right">{cost_unit:,.0f}</td>
                        <td class="text-right"><strong>{damage_value:,.0f}</strong></td>
                    </tr>
                '''.format(
                    product_code=r['product_code'] or '',
                    product_name=r['product_name'] or '',
                    lot_name=r['lot_name'] or '',
                    payer_name=r['payer_name'] or '',
                    picking_name=r['picking_name'] or '',
                    date=date_str,
                    qty=r['quantity'] or 0.0,
                    cost_unit=r['cost_unit'] or 0.0,
                    damage_value=r['damage_value'] or 0.0,
                )
            html += '''
                    </tbody>
                    <tfoot>
                        <tr class="table-info">
                            <th colspan="8" class="text-right">Tổng cộng:</th>
                            <th class="text-right">{total:,.0f}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>
            '''.format(total=total)
            rec.x_damage_line_display = html

    def action_recompute_depreciation_lines(self):
        """Quét lại lịch sử picking CCDC type_4/type_6 của dự án này
        và rebuild bảng project.depreciation.line.
        """
        DL = self.env['project.depreciation.line']
        for project in self:
            DL._rebuild_for_project(project)
        return True
    x_merge_project_id = fields.Many2one('project.project','Mã dự án gộp')
    is_merge_project = fields.Boolean('Là dự án gộp', default=False)
    x_sub_project_ids = fields.One2many('sub.project.project','merge_project_id', string='Mã dự án chi tiết')
    user_id = fields.Many2one('res.users', string='Project Manager', default=False, tracking=True)
    x_scope = fields.Char('Phạm vi công việc')
    state = fields.Selection([
        ('planning', 'Kế hoạch'),
        ('ongoing', 'Đang thực hiện'),
        ('pending', 'Tạm hoãn'),
        ('completed', 'Hoàn thành'),
        ('canceled', 'Đã huỷ'),
    ], 'Trạng thái', default='planning', copy=0)
    # Tab General
    x_phone = fields.Char('Điện thoại')
    x_email = fields.Char('Email')
    x_address = fields.Many2one('res.partner', 'Địa điểm', related='x_order_id.location_partner_id')
    x_investor_id = fields.Many2one('res.partner', 'Chủ đầu tư', related='x_order_id.x_investor_id')
    x_project_type = fields.Selection([
        ('maintainance', 'Maintenance'),
        ('service', 'Services'),
        ('operation', 'Facility Management'),
    ], 'Loại hình dự án', default='maintainance')
    x_expertise_ids = fields.Many2many('expertise.type', 'project_expertise_ref', 'project_id', 'expertise_id',
                                       string='Chuyên môn')
    x_model = fields.Selection([
        ('b', 'Building'),
        ('f', 'Factory'),
    ], 'Mô hình', default='b')
    x_self_register = fields.Boolean('Đăng ký nguyện vọng', default=1)
    x_cost_object = fields.Selection([
        ('company', 'Công ty'),
        ('pm', 'Quản lý dự án'),
    ], 'Đối tượng tính chi phí', default='pm')
    x_date_plan_start = fields.Date('Ngày bắt đầu kế hoạch')
    x_date_plan_end = fields.Date('Ngày kết thúc kế hoạch')
    # Tuỳ chọn phân bổ giờ công dự toán — đặt trực tiếp trên dự án (tab Dự toán).
    plan_work_saturday = fields.Boolean('KH làm việc thứ 7', default=False)
    plan_work_sunday = fields.Boolean('KH làm việc chủ nhật', default=False)
    plan_work_holiday = fields.Boolean('KH làm việc ngày lễ/tết', default=False)
    x_date_start = fields.Date('Ngày bắt đầu thực tế')
    x_date_end = fields.Date('Ngày kết thúc thực tế')
    x_date_warranty_expire = fields.Date('Ngày hết hạn bảo hành')
    x_warranty_period = fields.Float('Thời hạn bảo hành')
    x_warranty_period_unit = fields.Selection(
        [
            ('day', 'Ngày'),
            ('month', 'Tháng'),
            ('year', 'Năm')
        ],
        required=True,
        default='month',
        string='warranty Time Unit'
    )
    x_order_id = fields.Many2one('sale.order', 'Báo giá')
    r_maintenace = fields.Boolean(string='R-Maintenace', related='x_order_id.r_maintenace',store = True)
    e_fm = fields.Boolean(string='E-FM', related='x_order_id.e_fm',store = True)
    x_order_line_id = fields.Many2one('sale.order.line', 'Dòng trên báo giá')
    x_category = fields.Char('Hạng mục tổng')
    x_cost_ok = fields.Boolean('Tính phí')
    # Tab Estimate
    x_estimate_ids = fields.One2many('project.estimate', 'project_id', 'Dự toán nhân công')
    x_cost_estimate = fields.Float('Tổng chi phí nhân công dự toán', compute='onchange_estimate_ids')
    # Tab Members
    x_member_ids = fields.One2many('project.member', 'project_id', 'Thành viên')
    x_member_employee_ids = fields.Many2many('hr.employee', 'project_employee_rel', 'project_id', 'employee_id',
                                             'Các nhân viên', readonly=1)
    x_member_user_ids = fields.Many2many('res.users', 'project_member_rel', 'project_id', 'user_id', 'Các thành viên',
                                         readonly=1)
    x_cost_real = fields.Float('Tổng chi phí nhân công thực tế', compute='onchange_member_ids')
    # Tab Customer satisfaction
    x_report_date = fields.Date('Ngày xem xét báo cáo')
    x_general_status = fields.Text('Tình trạng chung')
    x_rate = fields.Selection([
        ('E', 'Rất hài lòng'),
        ('S', 'Hài lòng'),
        ('A', 'Chấp nhận'),
        ('D', 'Không hài lòng'),
    ], 'Mức độ hài lòng')
    x_rate_id = fields.Many2one('customer.rate', 'Mức độ hài lòng')
    x_feedback = fields.Text('Ý kiến của khách hàng')
    x_action = fields.Text('Hành động khắc phục')
    x_feedback_note = fields.Text('Ghi chú')
    x_total_plan_day = fields.Integer(string='Số ngày thực hiện dự kiến', default=1)
    x_material_estimate_ids = fields.One2many('material.estimate', 'material_id', 'Dự toán vật tư')
    x_material_estimate_total = fields.Float('Tổng cộng', compute='_compute_x_material_estimate_ids')
    wage_cost_ids = fields.One2many('project.wage.cost', 'project_id', 'Chi phí nhân công của dự án')
    wage_cost_total = fields.Float('Tổng chi phí', compute='_compute_wage_cost_total', store=True, help='Tổng cộng chi phí theo giờ công')
    travel_expenses_total = fields.Float('Chi phí đi lại',compute='_compute_travel_expenses_total')
    labor_repay_line_ids = fields.Many2many('account.repay.line', compute='_compute_travel_expenses_total')
    labor_costs_total = fields.Float('Chi phí thuê chuyên gia/thầu phụ')
    accommodation_costs_total = fields.Float('Chi phí lưu trú')
    other_costs_total =  fields.Float()
    actual_costs = fields.Float('Chi phí vật tư và chi phí khác',compute='_compute_actual_costs')
    actual_costs_store = fields.Float('Chi phí vật tư và chi phí khác')
    # purchase_line_costs_ids = fields.Many2many('purchase.order.line', compute='_compute_actual_costs')
    material_repay_line_ids = fields.Many2many('account.repay.line', compute='_compute_travel_expenses_total')
    iv_repay_line_ids = fields.Many2many('account.repay.line', compute='_compute_travel_expenses_total')
    iv_costs_total = fields.Float('Chi phí IV', compute='_compute_iv_costs_total')
    service_purchase_line_ids = fields.Many2many('purchase.order.line', compute='_compute_service_purchase_lines')
    # Thuế TNDN: lợi ích xử lý hóa đơn + chi phí thuế phát sinh khi mua hàng không HĐ.
    iv_value_total = fields.Float('Giá trị xử lý hóa đơn', compute='_compute_tndn_amounts',
                                  help='Tổng giá trị (trước thuế) các hóa đơn được xử lý/mua cho dự án.')
    iv_value_repay_line_ids = fields.Many2many('account.repay.line', compute='_compute_tndn_amounts',
                                               help='Các dòng hoàn ứng IV (license xử lý hóa đơn) cấu thành Doanh thu IV.')
    invoice_processing_profit = fields.Float('Doanh thu IV', compute='_compute_tndn_amounts')
    no_invoice_extra_cost = fields.Float('Phí mua hàng không hóa đơn',
                                         compute='_compute_tndn_amounts',
                                         help='Chi phí thuế TNDN phải gánh thêm với phần mua hàng không có hóa đơn '
                                              '(vật tư/nhân công/đi lại/lưu trú/dịch vụ chứng từ nội bộ) = giá trị '
                                              '(trước thuế) x thuế suất TNDN.')
    input_invoice_value_total = fields.Float('Tổng giá trị hóa đơn đầu vào',
                                              compute='_compute_tndn_amounts',
                                              help='Phần chi phí CÓ hóa đơn (license = thuế) - đối lập với phần '
                                                   'không hóa đơn (no_invoice_extra_cost) - cộng giá trị hóa đơn IV '
                                                   'đã xử lý (iv_value_total). Loại CR/TP (tính TNCN riêng). '
                                                   'Đều TRƯỚC THUẾ, dùng làm cơ sở tính Thuế TNDN.')
    cr_tp_cost_total = fields.Float('Chi phí CR + TP', compute='_compute_tndn_amounts',
                                    help='Tổng chi phí (trước thuế) các dòng hoàn ứng cost_type CR/TP của dự án - '
                                         'dùng làm cơ sở tính TNCN khấu trừ khi chi trả cho cá nhân.')
    riv_project_detail_ids = fields.Many2many('project.detail', compute='_compute_riv_project_details')
    riv_payment_line_ids = fields.Many2many('payment.line', compute='_compute_riv_project_details')
    material_usage_display = fields.Html('Chi tiết vật tư sử dụng', compute='_compute_material_usage_display')
    budget_cost = fields.Float('Chênh lệch dự toán và giá vốn',compute='_compute_budget_cost',store=False)
    # estimate_wage_cost_total = fields.Float('Tổng chi phí tạm tính', compute='_compute_estimate_wage_cost_total', store=True,
    #                                         help='Tổng cộng chi phí theo giờ công tạm tính')
    satisfaction_ids = fields.One2many('customer.satisfaction', 'project_id', 'Khách hàng đánh giá')

    main_project = fields.Boolean('Là dự án chính?', default=False)
    cr_amount = fields.Float('CR', related='x_order_id.cr_amount')
    tp_amount = fields.Float('TP', related='x_order_id.tp_amount')
    overhead_cost_amount = fields.Float('Overhead Cost', related='x_order_id.overhead_cost_amount')
    export_satisfaction_report = fields.Boolean('Xuất báo cáo chỉ số hài lòng')
    project_supporter_id = fields.Many2one('hr.employee',string='Người hỗ trợ')
    is_export_project_efficiency_detail = fields.Boolean('Xuất báo cáo dự án hoàn thành và xem xét hiệu quả',default= True)
    update_cost = fields.Boolean()
    actual_completion_date = fields.Date(compute='_compute_actual_completion_date')

    @api.model
    def _project_completion_dates(self, project_ids=None):
        """{project_id: ngày hoàn thành} cho các dự án `active=False & state='completed'`.

        NGUỒN DUY NHẤT xét ngày đóng dự án cho MỌI báo cáo (hiệu quả dự án chung,
        thưởng ký, hiệu suất NV 11.x, reward.line, tổng giá trị nhân lực...).

        LOẠI các dự án đã GỘP (x_merge_project_id set) — coi như đã đóng và tính
        gộp ở dự án gộp, không tính riêng ở báo cáo.

        Một dự án đã archive + completed được coi là HOÀN THÀNH kể cả không phát
        sinh chi phí. Ngày hoàn thành lấy theo thứ tự ưu tiên:
          1. Ngày muộn nhất từ nguồn (customer_satisfaction / hr_work_entry /
             tạm ứng / hoàn ứng / NGÀY XUẤT VẬT TƯ cuối / NGÀY TRẢ CCDC cuối);
          2. Nếu không có -> x_date_end (ngày kết thúc thực tế);
          3. Nếu không có nữa -> x_date_plan_end (ngày kết thúc kế hoạch);
          4. Không có cả 3 -> None (caller tự bỏ qua khi lọc theo năm).

        `project_ids=None` -> quét toàn bộ dự án completed+archived.
        Trả về GỒM cả dự án có ngày = None (để phép xét 'mọi dự án con hoàn thành'
        theo SO vẫn đếm được).
        """
        params = {}
        id_filter = ''
        if project_ids is not None:
            if not project_ids:
                return {}
            id_filter = 'AND pp.id IN %(ids)s'
            params['ids'] = tuple(project_ids)
        sql = """
            WITH completion_dates AS (
                SELECT cs.project_id, MAX(cs.report_date) AS d
                FROM customer_satisfaction cs
                WHERE cs.report_date IS NOT NULL GROUP BY cs.project_id
                UNION ALL
                SELECT wel.project_id, MAX(we.x_date)
                FROM hr_work_entry_line wel JOIN hr_work_entry we ON we.id = wel.entry_id
                WHERE we.x_date IS NOT NULL GROUP BY wel.project_id
                UNION ALL
                SELECT aal.project_id, MAX(am.date)
                FROM account_advance_line aal
                    JOIN account_advance aa ON aa.id = aal.advance_id
                    JOIN account_payment ap ON ap.id = aa.payment_id
                    JOIN account_move am ON am.id = ap.move_id
                WHERE am.state = 'posted' AND am.date IS NOT NULL GROUP BY aal.project_id
                UNION ALL
                SELECT arl.project_id, MAX(am.date)
                FROM account_repay_line arl
                    JOIN account_advance_repay aar ON aar.id = arl.account_repay_id
                    JOIN account_payment ap ON ap.id = aar.payment_id
                    JOIN account_move am ON am.id = ap.move_id
                    LEFT JOIN cost_type ct ON ct.id = arl.cost_type_id
                WHERE am.state = 'posted' AND am.date IS NOT NULL
                  AND ct.cost_type IS NOT NULL AND ct.cost_type != 'vat'
                GROUP BY arl.project_id
                UNION ALL
                -- Ngày xuất vật tư cuối cùng (xuất kho cho dự án) — khớp
                -- _compute_material_usage_display (picking_type_id=2, x_to_the_project_id).
                SELECT sml.x_to_the_project_id, MAX(sp.date_done)::date
                FROM stock_move_line sml JOIN stock_picking sp ON sp.id = sml.picking_id
                WHERE sml.state = 'done' AND sp.picking_type_id = 2
                  AND sml.x_to_the_project_id IS NOT NULL AND sp.date_done IS NOT NULL
                GROUP BY sml.x_to_the_project_id
                UNION ALL
                -- Ngày trả CCDC cuối cùng (project.depreciation.line.date_return).
                SELECT pdl.project_id, MAX(pdl.date_return)::date
                FROM project_depreciation_line pdl
                WHERE pdl.date_return IS NOT NULL
                GROUP BY pdl.project_id
            )
            SELECT pp.id,
                   COALESCE(MAX(cd.d), pp.x_date_end, pp.x_date_plan_end) AS completion_date
            FROM project_project pp
            LEFT JOIN completion_dates cd ON cd.project_id = pp.id
            WHERE pp.active = FALSE AND pp.state = 'completed'
              AND pp.x_merge_project_id IS NULL %s
            GROUP BY pp.id, pp.x_date_end, pp.x_date_plan_end
        """ % id_filter
        self._cr.execute(sql, params)
        return {r[0]: r[1] for r in self._cr.fetchall()}

    def _compute_actual_completion_date(self):
        rec_map = self._project_completion_dates(self.ids)
        for rec in self:
            rec.actual_completion_date = rec_map.get(rec.id) or False

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # TDE FIXME: strange
        args = list(args)
        report_date_terms = [
            (idx, term) for idx, term in enumerate(args)
            if isinstance(term, (list, tuple))
            and len(term) >= 3
            and term[0] == 'x_report_date'
        ]
        if report_date_terms:
            report_date_domain = [
                ('report_date', term[1], term[2])
                for _, term in report_date_terms
            ]
            extra_project_id = self.env['customer.satisfaction'].sudo().search(report_date_domain)
            extra_project_ids = extra_project_id.project_id.ids
            if extra_project_ids:
                extra_condition = ('id', 'in', extra_project_ids)
                delta = 0
                for idx, term in report_date_terms:
                    insert_pos = idx + delta
                    args.pop(insert_pos)
                    args[insert_pos:insert_pos] = ['|', term, extra_condition]
                    delta += 2

        return super(Project, self)._search(args, offset=offset, limit=limit, order=order, count=count,
                                                   access_rights_uid=access_rights_uid)

    def toggle_active(self):
        for rec in self:
            if not rec.active and not self.user_has_groups('xproject.group_unarchive_project'):
                raise ValidationError('Bạn không có quyền bỏ lưu trữ dự án!')
        return super().toggle_active()

    def _compute_budget_cost(self):
        # Chênh lệch dự toán và giá vốn = Dự toán - (Nhân công + Vật tư & khác +
        # Chi phí CCDC) - Chi phí IV + Doanh thu IV - Phí mua hàng không HĐ.
        # (Điều chỉnh TNDN giống công thức "Hiệu quả dự án" - project_efficiency_detail.diff.)
        for rec in self:
            rec.budget_cost = (rec.x_cost_estimate + rec.x_material_estimate_total
                               - rec.wage_cost_total - rec.actual_costs - rec.total_depreciation_cost
                               - rec.iv_costs_total
                               + rec.invoice_processing_profit - rec.no_invoice_extra_cost)

    def _compute_actual_costs(self):
        for rec in self:
            rec.actual_costs = 0
            actual_costs = 0

            # Add account repay line costs (excluding code_money = 38 and records without account_repay_id)
            repay_sql = """
                SELECT sum(arl.amount_untaxed) 
                FROM account_repay_line arl
                JOIN cost_type ct ON ct.id = arl.cost_type_id
                JOIN account_advance_repay aar ON aar.id = arl.account_repay_id
                LEFT JOIN code_money cm ON cm.id = aar.code_money
                WHERE arl.project_id = %s 
                  AND arl.account_repay_id IS NOT NULL
                  AND ct.cost_category NOT ILIKE '%%đi lại%%' 
                  AND ct.cost_category NOT ILIKE '%%Nhân công%%' 
                  AND ct.cost_category NOT ILIKE '%%Lưu trú%%'
                  AND (aar.code_money IS NULL OR aar.code_money != 38)
            """
            
            self._cr.execute(repay_sql, (rec.id,))
            repay_result = self._cr.fetchone()
            if repay_result and repay_result[0]:
                actual_costs += repay_result[0]

            # Add material costs - Tính giống như _compute_material_usage_display
            # Lấy từng bản ghi xuất kho riêng biệt
            outbound_sql = """
                SELECT 
                    sml.product_id,
                    sml.qty_done,
                    COALESCE(
                        (SELECT pol.price_unit 
                         FROM purchase_order_line pol
                         JOIN purchase_order po ON po.id = pol.order_id
                         WHERE pol.product_id = sml.product_id and po.x_state in ('done', 'wait_license', 'to_late')
                           AND po.date_order <= sp.date_done
                           AND pol.x_project_id = %s
                         ORDER BY po.date_order DESC
                         LIMIT 1),
                        (SELECT pol.price_unit 
                         FROM purchase_order_line pol
                         JOIN purchase_order po ON po.id = pol.order_id
                         WHERE pol.product_id = sml.product_id and po.x_state in ('done', 'wait_license', 'to_late')
                           AND po.date_order <= sp.date_done
                         ORDER BY po.date_order DESC
                         LIMIT 1),
                        pt.standard_price
                    ) as price_unit
                FROM stock_move_line sml
                LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
                LEFT JOIN product_product pp ON pp.id = sml.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE sml.state = 'done' 
                  AND sp.picking_type_id = 2 
                  AND sml.x_to_the_project_id = %s
                ORDER BY sp.date_done, sml.product_id, sml.id
            """
            
            # Lấy tất cả vật tư nhập lại với thông tin chi tiết
            inbound_sql = """
                SELECT 
                    sml.product_id,
                    sml.qty_done
                FROM stock_move_line sml
                LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
                WHERE sml.state = 'done' 
                  AND sp.picking_type_id = 9 
                  AND sml.x_from_the_project_id = %s
                ORDER BY sp.date_done, sml.product_id, sml.id
            """
            
            self._cr.execute(outbound_sql, (rec.id, rec.id))
            outbound_records = self._cr.dictfetchall()
            
            self._cr.execute(inbound_sql, (rec.id,))
            inbound_records = self._cr.dictfetchall()
            
            material_used_cost = 0
            if outbound_records:
                # Tạo queue cho vật tư nhập lại theo sản phẩm (FIFO)
                inbound_queues = {}
                for inbound in inbound_records:
                    product_id = inbound['product_id']
                    if product_id not in inbound_queues:
                        inbound_queues[product_id] = []
                    inbound_queues[product_id].append(inbound['qty_done'])
                
                # Xử lý từng bản ghi xuất kho và trừ dần từ queue nhập lại
                for out_record in outbound_records:
                    product_id = out_record['product_id']
                    qty_out = out_record['qty_done']
                    price_unit = out_record['price_unit']
                    remaining_to_return = qty_out
                    
                    # Trừ dần từ queue nhập lại
                    if product_id in inbound_queues:
                        queue = inbound_queues[product_id]
                        i = 0
                        while i < len(queue) and remaining_to_return > 0:
                            if queue[i] > 0:
                                returned_from_this = min(remaining_to_return, queue[i])
                                queue[i] -= returned_from_this
                                remaining_to_return -= returned_from_this
                            i += 1
                    
                    qty_used = remaining_to_return
                    material_used_cost += qty_used * price_unit
                    
            actual_costs += material_used_cost

            # Add service purchase line costs
            # Lấy theo GIÁ TRỊ HÓA ĐƠN thực tế (dòng hóa đơn NCC in_invoice đã
            # posted) thay vì giá đặt hàng (pol.price_subtotal) - vì giá hóa đơn
            # mới là chi phí thực (có thể lệch so với đơn mua). Nhất quán với
            # nhánh TNDN (no_invoice_extra_cost / input_invoice_value_total) và
            # cột 'Giá trị theo hóa đơn' (x_invoice_subtotal) - cả ba đều CHỈ tính
            # dòng đã có hóa đơn. Đều là giá TRƯỚC THUẾ (price_subtotal, chưa VAT).
            # Dòng PO chưa có hóa đơn posted không tính vào (INNER JOIN).
            service_sql = """
                SELECT COALESCE(SUM(aml.price_subtotal), 0)
                FROM purchase_order_line pol
                JOIN purchase_order po ON po.id = pol.order_id
                JOIN product_product pp ON pp.id = pol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN account_move_line aml ON aml.purchase_line_id = pol.id
                JOIN account_move am ON am.id = aml.move_id
                WHERE pol.x_project_id = %s
                  AND pt.x_type = 'service'
                  AND po.x_state in ('done', 'wait_license', 'to_late')
                  AND am.move_type = 'in_invoice'
                  AND am.state = 'posted'
            """
            
            self._cr.execute(service_sql, (rec.id,))
            service_result = self._cr.fetchone()
            if service_result and service_result[0]:
                actual_costs += service_result[0]

            rec.actual_costs = actual_costs

    def _compute_material_usage_display(self):
        """Tính toán và hiển thị chi tiết vật tư sử dụng trong dự án dưới dạng HTML table"""
        for rec in self:
            # Lấy từng bản ghi xuất kho riêng biệt
            outbound_sql = """
                SELECT 
                    sml.product_id,
                    pp.default_code as product_code,
                    pt.name as product_name,
                    uu.name as uom_name,
                    sp.name as picking_name,
                    sp.date_done,
                    sml.qty_done,
                    COALESCE(
                        (SELECT pol.price_unit 
                         FROM purchase_order_line pol
                         JOIN purchase_order po ON po.id = pol.order_id
                         WHERE pol.product_id = sml.product_id and po.x_state in ('done', 'wait_license', 'to_late')
                           AND po.date_order <= sp.date_done
                           AND pol.x_project_id = %s
                         ORDER BY po.date_order DESC
                         LIMIT 1),
                        (SELECT pol.price_unit 
                         FROM purchase_order_line pol
                         JOIN purchase_order po ON po.id = pol.order_id
                         WHERE pol.product_id = sml.product_id and po.x_state in ('done', 'wait_license', 'to_late')
                           AND po.date_order <= sp.date_done
                         ORDER BY po.date_order DESC
                         LIMIT 1),
                        pt.standard_price
                    ) as price_unit
                FROM stock_move_line sml
                LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
                LEFT JOIN product_product pp ON pp.id = sml.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN uom_uom uu ON uu.id = pt.uom_id
                WHERE sml.state = 'done' 
                  AND sp.picking_type_id = 2 
                  AND sml.x_to_the_project_id = %s
                ORDER BY sp.date_done, sml.product_id, sml.id
            """
            
            # Lấy tất cả vật tư nhập lại với thông tin chi tiết
            inbound_sql = """
                SELECT 
                    sml.product_id,
                    sml.qty_done,
                    sp.name as picking_name,
                    sp.date_done
                FROM stock_move_line sml
                LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
                WHERE sml.state = 'done' 
                  AND sp.picking_type_id = 9 
                  AND sml.x_from_the_project_id = %s
                ORDER BY sp.date_done, sml.product_id, sml.id
            """
            
            self._cr.execute(outbound_sql, (rec.id, rec.id))
            outbound_records = self._cr.dictfetchall()
            
            self._cr.execute(inbound_sql, (rec.id,))
            inbound_records = self._cr.dictfetchall()
            
            if not outbound_records:
                rec.material_usage_display = '<p>Không có dữ liệu vật tư sử dụng</p>'
                continue
            
            # Tạo queue cho vật tư nhập lại theo sản phẩm (FIFO)
            inbound_queues = {}
            for inbound in inbound_records:
                product_id = inbound['product_id']
                if product_id not in inbound_queues:
                    inbound_queues[product_id] = []
                inbound_queues[product_id].append({
                    'qty': inbound['qty_done'],
                    'picking_name': inbound['picking_name'],
                    'date_done': inbound['date_done']
                })
            
            # Xử lý từng bản ghi xuất kho và trừ dần từ queue nhập lại
            processed_records = []
            
            for out_record in outbound_records:
                product_id = out_record['product_id']
                qty_out = out_record['qty_done']
                remaining_to_return = qty_out
                
                inbound_info = []
                
                # Trừ dần từ queue nhập lại
                if product_id in inbound_queues:
                    queue = inbound_queues[product_id]
                    i = 0
                    while i < len(queue) and remaining_to_return > 0:
                        inbound_item = queue[i]
                        if inbound_item['qty'] > 0:
                            returned_from_this = min(remaining_to_return, inbound_item['qty'])
                            inbound_info.append({
                                'qty': returned_from_this,
                                'picking': inbound_item['picking_name'],
                                'date': inbound_item['date_done']
                            })
                            inbound_item['qty'] -= returned_from_this
                            remaining_to_return -= returned_from_this
                        i += 1
                
                qty_returned_total = qty_out - remaining_to_return
                qty_used = remaining_to_return
                
                # Format thông tin phiếu nhập
                inbound_info_str = ""
                inbound_date_str = ""
                if inbound_info:
                    inbound_pickings = []
                    inbound_dates = []
                    for info in inbound_info:
                        inbound_pickings.append(info['picking'])
                        if info['date']:
                            inbound_dates.append(info['date'].strftime('%d/%m/%Y'))
                    inbound_info_str = ", ".join(inbound_pickings)
                    inbound_date_str = ", ".join(inbound_dates)
                
                processed_records.append({
                    'product_code': out_record['product_code'] or '',
                    'product_name': out_record['product_name'],
                    'uom_name': out_record['uom_name'],
                    'picking_out_name': out_record['picking_name'],
                    'picking_in_info': inbound_info_str,
                    'date_out': out_record['date_done'],
                    'date_in': inbound_date_str,
                    'price_unit': out_record['price_unit'],
                    'qty_out': qty_out,
                    'qty_in': qty_returned_total,
                    'qty_used': qty_used,
                    'amount_total': qty_used * out_record['price_unit']
                })
            
            # Xử lý số lượng nhập lại dư (tạo bản ghi âm)
            for product_id, queue in inbound_queues.items():
                for inbound_item in queue:
                    if inbound_item['qty'] > 0:
                        # Lấy thông tin sản phẩm
                        product_info_sql = """
                            SELECT pp.default_code, pt.name, uu.name
                            FROM product_product pp
                            JOIN product_template pt ON pt.id = pp.product_tmpl_id
                            LEFT JOIN uom_uom uu ON uu.id = pt.uom_id
                            WHERE pp.id = %s
                        """
                        self._cr.execute(product_info_sql, (product_id,))
                        product_info = self._cr.fetchone()
                        
                        if product_info:
                            date_str = inbound_item['date_done'].strftime('%d/%m/%Y') if inbound_item['date_done'] else ''
                            processed_records.append({
                                'product_code': product_info[0] or '',
                                'product_name': product_info[1],
                                'uom_name': product_info[2],
                                'picking_out_name': '',
                                'picking_in_info': inbound_item['picking_name'],
                                'date_out': None,
                                'date_in': date_str,
                                'price_unit': 0,
                                'qty_out': 0,
                                'qty_in': inbound_item['qty'],
                                'qty_used': -inbound_item['qty'],
                                'amount_total': 0
                            })
            
            # Tạo HTML table
            html_content = '''
            <div class="table-responsive">
                <table class="table table-sm table-bordered">
                    <thead class="thead-light">
                        <tr>
                            <th>Mã SP</th>
                            <th>Tên sản phẩm</th>
                            <th>ĐVT</th>
                            <th>Phiếu xuất</th>
                            <th>Ngày xuất</th>
                            <th>Phiếu nhập</th>
                            <th>Ngày nhập</th>
                            <th>Đơn giá</th>
                            <th>SL Xuất</th>
                            <th>SL Nhập lại</th>
                            <th>SL Sử dụng</th>
                            <th>Tổng tiền</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            
            total_amount = 0
            for record in processed_records:
                amount_total = record['amount_total']
                total_amount += amount_total
                
                # Format số tiền và ngày
                price_formatted = f"{record['price_unit']:,.0f}"
                amount_formatted = f"{amount_total:,.0f}"
                date_out_str = record['date_out'].strftime('%d/%m/%Y') if record['date_out'] else ''
                
                # Style cho số âm
                qty_used_style = 'color: red;' if record['qty_used'] < 0 else ''
                
                html_content += f'''
                    <tr>
                        <td>{record['product_code']}</td>
                        <td>{record['product_name']}</td>
                        <td>{record['uom_name']}</td>
                        <td>{record['picking_out_name']}</td>
                        <td>{date_out_str}</td>
                        <td>{record['picking_in_info']}</td>
                        <td>{record['date_in']}</td>
                        <td class="text-right">{price_formatted}</td>
                        <td class="text-right">{record['qty_out']:.2f}</td>
                        <td class="text-right">{record['qty_in']:.2f}</td>
                        <td class="text-right" style="{qty_used_style}"><strong>{record['qty_used']:.2f}</strong></td>
                        <td class="text-right"><strong>{amount_formatted}</strong></td>
                    </tr>
                '''
            
            # Thêm tổng cộng
            total_formatted = f"{total_amount:,.0f}"
            html_content += f'''
                    </tbody>
                    <tfoot>
                        <tr class="table-info">
                            <th colspan="11" class="text-right">Tổng cộng:</th>
                            <th class="text-right">{total_formatted}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>
            '''
            
            rec.material_usage_display = html_content

    def _compute_travel_expenses_total(self):
        for rec in self:
            account_repay_line = self.env['account.repay.line'].with_context(active_test=False)
            rec.travel_expenses_total = sum(account_repay_line.search([('account_repay_id.code_money.code_money', '!=', 'IV'),('project_id', '=', rec.id),
                                                                       ('cost_type_id.cost_type', '=', 'move')]).mapped('amount_untaxed'))
            rec.labor_costs_total = sum(account_repay_line.search([('account_repay_id.code_money.code_money', '!=', 'IV'),('project_id', '=', rec.id),
                                                                   ('cost_type_id.cost_type', '=', 'labor')]).mapped('amount_untaxed'))
            rec.accommodation_costs_total = sum(account_repay_line.search([('account_repay_id.code_money.code_money', '!=', 'IV'),('project_id', '=', rec.id),
                                                                           ('cost_type_id.cost_type', '=', 'stay')]).mapped('amount_untaxed'))
            rec.other_costs_total = rec.travel_expenses_total + rec.labor_costs_total + rec.accommodation_costs_total
            rec.wage_cost_total = sum(rec.wage_cost_ids.mapped('cost')) + rec.other_costs_total
            labor_repay_line_ids = account_repay_line.search([('account_repay_id.code_money.code_money', '!=', 'IV'), ('project_id', '=', rec.id), ('account_repay_id', '!=', False), '|', '|', ('cost_type_id.cost_type', '=', 'move'), ('cost_type_id.cost_type', '=', 'labor'), ('cost_type_id.cost_type', '=', 'stay')])
            
            # IV repay line ids: account_repay_line có account_repay_id.code_money = 38
            iv_repay_line_ids = account_repay_line.search([('project_id', '=', rec.id), ('account_repay_id', '!=', False), ('account_repay_id.code_money.code_money', '=', 'IV'), ('account_repay_id.license_type', '=', 'internal'), ('cost_type_id.cost_type', '=', 'iv')])
            
            # Material repay line ids: tất cả records có account_repay_id trừ labor và IV
            material_repay_line_ids = account_repay_line.search(
                [('account_repay_id.code_money.code_money', '!=', 'IV'),
                 ('project_id', '=', rec.id), ('account_repay_id', '!=', False),
                 ('cost_type_id.cost_type', '!=', 'move'),
                 ('cost_type_id.cost_type', '!=', 'labor'),
                 ('cost_type_id.cost_type', '!=', 'stay')])
            
            rec.labor_repay_line_ids = labor_repay_line_ids
            rec.material_repay_line_ids = material_repay_line_ids
            rec.iv_repay_line_ids = iv_repay_line_ids

    def _compute_iv_costs_total(self):
        for rec in self:
            rec.iv_costs_total = sum(rec.iv_repay_line_ids.mapped('amount_untaxed'))

    def _get_tndn_rate(self, date=None):
        """Thuế suất TNDN (%) áp dụng cho 'date' theo bảng tndn.tax.rate
        (Kế toán > Cấu hình > Thuế suất TNDN). Dự án tra theo ngày bắt đầu
        thực tế (x_date_start)."""
        return self.env['tndn.tax.rate'].get_rate_for_date(date)

    def _compute_tndn_amounts(self):
        """- Giá trị xử lý hóa đơn = các dòng hoàn ứng IV mang giá trị hóa đơn
             (code_money='IV', license='tax', cost_type != 'iv').
           - Lợi nhuận xử lý hóa đơn = giá trị xử lý x TNDN% - chi phí xử lý (IV).
           - Chi phí thêm khi mua hàng không hóa đơn = (vật tư/nhân công/đi
             lại/lưu trú hoàn ứng nội bộ + dịch vụ mua hàng công nợ nội bộ) x
             TNDN%. (đều TRƯỚC THUẾ)
           - Tổng giá trị hóa đơn đầu vào = phần ĐỐI LẬP (license = thuế thay vì
             nội bộ) của "mua hàng không hóa đơn" ở trên + giá trị hóa đơn IV.
           - Chi phí CR + TP = tổng dòng hoàn ứng cost_type CR/TP của dự án.
           Thuế suất TNDN lấy theo ngày bắt đầu thực tế của dự án (x_date_start)."""
        repay_line = self.env['account.repay.line'].with_context(active_test=False)
        for rec in self:
            rate = rec._get_tndn_rate(rec.x_date_start) / 100.0
            iv_value_lines = repay_line.search([
                ('project_id', '=', rec.id),
                ('account_repay_id', '!=', False),
                ('account_repay_id.code_money.code_money', '=', 'IV'),
                ('account_repay_id.license_type', '=', 'tax'),
                ('cost_type_id.cost_type', '!=', 'iv'),
            ])
            rec.iv_value_repay_line_ids = iv_value_lines
            iv_value = sum(iv_value_lines.mapped('amount_untaxed'))
            rec.iv_value_total = iv_value
            # Lãi thuế từ xử lý hóa đơn = giá trị xử lý x TNDN%. KHÔNG trừ phí IV
            # ở đây vì phí IV (iv_costs_total) đã nằm trong tổng chi phí của báo cáo.
            rec.invoice_processing_profit = iv_value * rate

            # Mua hàng không hóa đơn = chứng từ nội bộ (license = internal), xét
            # CẢ vật tư LẪN nhân công/đi lại/lưu trú hoàn ứng (không chỉ vật tư).
            # LOẠI dòng hoàn ứng cost_type 'cr'/'tp'; LOẠI dòng mà phiếu thanh toán
            # có mã khoản tiền (payment.x_code_money) = 'BA'.
            all_repay_lines = rec.material_repay_line_ids | rec.labor_repay_line_ids
            all_internal = sum(all_repay_lines.filtered(
                lambda l: l.account_repay_id.license_type == 'internal'
                and l.cost_type_id.cost_type not in ('cr', 'tp')
                and l.account_repay_id.payment_id.x_code_money.code_money != 'BA'
            ).mapped('amount_untaxed'))
            # Đối lập: các dòng hoàn ứng (mọi loại chi phí, kể cả nhân công/đi
            # lại/lưu trú) CÓ hóa đơn thật (license = thuế).
            all_tax = sum(all_repay_lines.filtered(
                lambda l: l.account_repay_id.license_type == 'tax'
                and l.cost_type_id.cost_type not in ('cr', 'tp')
                and l.account_repay_id.payment_id.x_code_money.code_money != 'BA'
            ).mapped('amount_untaxed'))
            service_internal = 0.0
            service_tax = 0.0
            if rec.service_purchase_line_ids:
                svc_amls = self.env['account.move.line'].search([
                    ('purchase_line_id', 'in', rec.service_purchase_line_ids.ids),
                    ('move_id.move_type', '=', 'in_invoice'),
                    ('move_id.state', '=', 'posted'),
                    ('move_id.x_license_type', 'in', ('internal', 'tax')),
                ])
                # LOẠI hóa đơn có PHIẾU CHI gắn với hóa đơn (payment.x_origin_move_id
                # = hóa đơn) mang mã khoản tiền (x_code_money) = 'BA'.
                ba_move_ids = set(self.env['account.payment'].sudo().search([
                    ('x_origin_move_id', 'in', svc_amls.mapped('move_id').ids),
                    ('state', '=', 'posted'),
                    ('x_code_money.code_money', '=', 'BA'),
                ]).mapped('x_origin_move_id').ids)
                svc_amls = svc_amls.filtered(lambda a: a.move_id.id not in ba_move_ids)
                service_internal = sum(a.price_subtotal for a in svc_amls
                                       if a.move_id.x_license_type == 'internal')
                # price_subtotal đã là giá trị TRƯỚC THUẾ (không gồm VAT).
                service_tax = sum(a.price_subtotal for a in svc_amls
                                  if a.move_id.x_license_type == 'tax')
            rec.no_invoice_extra_cost = (all_internal + service_internal) * rate
            rec.input_invoice_value_total = all_tax + service_tax + iv_value

            cr_tp_lines = rec.material_repay_line_ids.filtered(
                lambda l: l.cost_type_id.cost_type in ('cr', 'tp')
                and l.account_repay_id.payment_id.x_code_money.code_money != 'BA'
            )
            rec.cr_tp_cost_total = sum(cr_tp_lines.mapped('amount_untaxed'))

    def _compute_service_purchase_lines(self):
        for rec in self:
            # Tìm các purchase_order_line có:
            # - product_id.x_type = 'service'  
            # - order_id.state = 'done'
            # - x_project_id = project_id
            purchase_lines = self.env['purchase.order.line'].search([
                ('x_project_id', '=', rec.id),
                ('product_id.x_type', '=', 'service'),
                ('order_id.x_state', 'in', ['done', 'wait_license', 'to_late'])
            ])
            rec.service_purchase_line_ids = purchase_lines

    def _compute_riv_project_details(self):
        for rec in self:
            # Tìm các project_detail có:
            # - project_id = project_id
            # - payment_id.move_id.state = 'posted' 
            # - payment_id.x_code_money = 42
            project_details = self.env['project.detail'].search([
                ('project_id', '=', rec.id),
                ('payment_id.move_id.state', '=', 'posted'),
                ('payment_id.x_code_money', '=', 42),
                ('amount_total', '!=', 0)
            ])
            rec.riv_project_detail_ids = project_details
            payment_line = self.env['payment.line'].search([
                ('project_id', '=', rec.id),
                ('payment_id.move_id.state', '=', 'posted'),
                ('payment_id.x_code_money', '=', 42),
                ('amount', '!=', 0)
            ])
            rec.riv_payment_line_ids = payment_line


    @api.depends('wage_cost_ids', 'wage_cost_ids.cost')
    def _compute_wage_cost_total(self):
        for rec in self:
            rec.wage_cost_total = sum(rec.wage_cost_ids.mapped('cost')) + rec.other_costs_total

    @api.depends('x_material_estimate_ids')
    def _compute_x_material_estimate_ids(self):
        for rec in self:
            rec.x_material_estimate_total = sum(rec.x_material_estimate_ids.mapped('amount_total'))

    # ------------------------------------------------------------------
    # Phân bổ giờ công dự toán ra từng ngày -> sheet Estimation (Productivity)
    # ------------------------------------------------------------------
    @api.model
    def _get_global_holiday_dates(self, start, end):
        """Tập các ngày lễ/tết (date) trong [start, end] theo hr.global.off active."""
        result = set()
        if not start or not end or start > end:
            return result
        offs = self.env['hr.global.off'].search([
            ('active', '=', True),
            ('date_start', '<=', end),
            ('date_end', '>=', start),
        ])
        for off in offs:
            d = max(off.date_start, start)
            last = min(off.date_end, end)
            while d <= last:
                result.add(d)
                d += timedelta(days=1)
        return result

    def _estimation_working_days(self, holiday_dates=None):
        """List ngày làm việc trong [x_date_plan_start, x_date_plan_end] theo 3
        tuỳ chọn T7/CN/Lễ của báo giá. Ngày bị bỏ khi rơi vào T7/CN/lễ mà
        tuỳ chọn tương ứng không bật."""
        self.ensure_one()
        start, end = self.x_date_plan_start, self.x_date_plan_end
        if not start or not end or start > end:
            return []
        if holiday_dates is None:
            holiday_dates = self._get_global_holiday_dates(start, end)
        days = []
        d = start
        while d <= end:
            wd = d.weekday()  # Mon=0 ... Sat=5, Sun=6
            skip = (wd == 5 and not self.plan_work_saturday) \
                or (wd == 6 and not self.plan_work_sunday) \
                or (d in holiday_dates and not self.plan_work_holiday)
            if not skip:
                days.append(d)
            d += timedelta(days=1)
        return days

    @api.model
    def _build_estimation_rows(self, year, block_id=None):
        """Sinh các dòng cho sheet Estimation: mỗi ngày làm việc của mỗi dự án
        (trong năm báo cáo) được phân bổ giờ công dự toán theo loại nguồn lực.

        Lọc dự án: có ngày KH bắt đầu/kết thúc, có dự toán, chưa huỷ, và cửa sổ
        KH giao với `year`. Khối phòng ban -> loại dự án (giống manpower_weekly):
        2 = Bảo trì & Dịch vụ, 3 = FM, 1 = không có, không chọn = tất cả.
        """
        year = int(year)
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        if block_id == 1:
            return []
        domain = [
            ('x_date_plan_start', '!=', False),
            ('x_date_plan_end', '!=', False),
            ('x_estimate_ids', '!=', False),
            ('state', '!=', 'canceled'),
            ('x_date_plan_start', '<=', year_end),
            ('x_date_plan_end', '>=', year_start),
        ]
        if block_id == 2:
            domain.append(('x_project_type', 'in', ['maintainance', 'service']))
        elif block_id == 3:
            domain.append(('x_project_type', '=', 'operation'))
        projects = self.with_context(active_test=False).search(domain)
        if not projects:
            return []
        # Gom ngày lễ 1 lần cho toàn bộ khoảng của tập dự án.
        all_start = min(projects.mapped('x_date_plan_start'))
        all_end = max(projects.mapped('x_date_plan_end'))
        holiday_dates = self._get_global_holiday_dates(all_start, all_end)
        rows = []
        for p in projects:
            totals = {}
            for est in p.x_estimate_ids:
                rt = est.product_id.x_resource_type
                if not rt:
                    continue
                totals[rt] = totals.get(rt, 0.0) + est.quantity
            if not totals:
                continue
            days = p._estimation_working_days(holiday_dates)
            if not days:
                continue
            per_day = {rt: (val / len(days)) for rt, val in totals.items()}
            client = p.partner_id.name or ''
            project_name = p.label_tasks or p.x_scope or ''
            fre = ''
            line = p.x_order_line_id
            if line and line.product_id and line.product_id.product_tmpl_id.x_frequency_id:
                fre = line.product_id.product_tmpl_id.x_frequency_id.code or ''
            classify = ESTIMATION_CLASSIFY_LABEL.get(p.x_project_type, '')
            for d in days:
                if d < year_start or d > year_end:
                    continue
                rows.append({
                    'date': d,
                    'client': client,
                    'project_no': p.name or '',
                    'project_name': project_name,
                    'fre': fre,
                    'classify': classify,
                    'hours': dict(per_day),
                })
        rows.sort(key=lambda r: (r['date'], r['project_no']))
        return rows

    @api.onchange('x_date_end', 'x_warranty_period', 'x_warranty_period_unit')
    def onchange_x_date_end(self):
        if self.x_date_end and self.x_warranty_period > 0:
            if self.x_warranty_period_unit == 'day':
                date_warranty_expire = self.x_date_end + relativedelta(days=self.x_warranty_period)
            elif self.x_warranty_period_unit == 'month':
                date_warranty_expire = self.x_date_end + relativedelta(months=self.x_warranty_period)
            else:
                date_warranty_expire = self.x_date_end + relativedelta(years=self.x_warranty_period)
            self.x_date_warranty_expire = date_warranty_expire
        else:
            self.x_date_warranty_expire = False

    def _load_member_info(self):
        sql = '''
        select d.employee_id, d.project_id, sum(d.h) hours
        from (
            select we.employee_id, wel.project_id, sum(wel.hour) h
            from hr_work_entry_line wel
                inner join hr_work_entry we on wel.entry_id=we.id
            where 1=1
                and wel.project_id in (%s)
                and we.state = 'validated'
            group by wel.project_id, we.employee_id
            
            union
            
            select we.employee_id, wea.project_id, sum(wea.hour) h
            from hr_work_entry_allowance wea
                inner join hr_work_entry we on wea.entry_id=we.id
            where 1=1
                and wea.project_id in (%s)
                and we.state = 'validated'
            group by wea.project_id, we.employee_id
        ) d
        group by d.employee_id, d.project_id
        '''

        sql2 = '''
            with all_day_year as
                (
                    SELECT
                        cast(generate_series as date) as ngay_trong_nam,
                        extract (dow from generate_series) as ngay_trong_tuan
                    FROM
                        GENERATE_SERIES
                            (
                                cast(concat(cast(extract(year from '{day}'::date) as varchar),'-01-01') as date),
                                cast(concat(cast(extract(year from '{day}'::date) as varchar),'-12-31') as date),
                                interval '1 day'
                            )
                ),
            company_other_expenses as
                (
                    select 
                        oex.hr_job_id,
                        oex.expense_type,
                        oex.gender,
                        sum(coalesce(oex.expense_price,0)) as price
                    from 
                        (
                            select 
                                hj.id as hr_job_id,
                                oe."type" as expense_type,
                                oe.price as expense_price,
                                oe.gender 
                            from hr_job hj 
                            left join hr_job_other_expenses_rel hjoer on hjoer.hr_job_id = hj.id 
                            left join other_expenses oe on oe.id = hjoer.other_expenses_id
                            where extract(year from '{day}'::date) between oe.start_year and oe.end_year and oe.gender is not null 
                            
                            union all 
                            
                            select
                                hj2.id as hr_job_id,
                                oe2."type" as expense_type,
                                oe2.price as expense_price,
                                oe2.gender 
                            from hr_job hj2 
                            left join other_expenses oe2 on (select count(*) from hr_job_other_expenses_rel hjoer2 where hjoer2.other_expenses_id = oe2.id) = 0
                            where extract(year from '{day}'::date) between oe2.start_year and oe2.end_year and oe2.gender is not null
                            
                            union all 
                            
                            select 
                                hj.id as hr_job_id,
                                oe."type" as expense_type,
                                oe.price as expense_price,
                                'male' as gender 
                            from hr_job hj 
                            left join hr_job_other_expenses_rel hjoer on hjoer.hr_job_id = hj.id 
                            left join other_expenses oe on oe.id = hjoer.other_expenses_id
                            where extract(year from '{day}'::date) between oe.start_year and oe.end_year and oe.gender is null 
                            
                            union all 
                            
                            select
                                hj2.id as hr_job_id,
                                oe2."type" as expense_type,
                                oe2.price as expense_price,
                                'male' as gender 
                            from hr_job hj2 
                            left join other_expenses oe2 on (select count(*) from hr_job_other_expenses_rel hjoer2 where hjoer2.other_expenses_id = oe2.id) = 0
                            where extract(year from '{day}'::date) between oe2.start_year and oe2.end_year and oe2.gender is null
                            
                            union all 
                            
                            select 
                                hj.id as hr_job_id,
                                oe."type" as expense_type,
                                oe.price as expense_price,
                                'female' as gender 
                            from hr_job hj 
                            left join hr_job_other_expenses_rel hjoer on hjoer.hr_job_id = hj.id 
                            left join other_expenses oe on oe.id = hjoer.other_expenses_id
                            where extract(year from '{day}'::date) between oe.start_year and oe.end_year and oe.gender is null 
                            
                            union all 
                            
                            select
                                hj2.id as hr_job_id,
                                oe2."type" as expense_type,
                                oe2.price as expense_price,
                                'female' as gender 
                            from hr_job hj2 
                            left join other_expenses oe2 on (select count(*) from hr_job_other_expenses_rel hjoer2 where hjoer2.other_expenses_id = oe2.id) = 0
                            where extract(year from '{day}'::date) between oe2.start_year and oe2.end_year and oe2.gender is null
                            
                            union all 
                            
                            select 
                                hj.id as hr_job_id,
                                oe."type" as expense_type,
                                oe.price as expense_price,
                                'other' as gender 
                            from hr_job hj 
                            left join hr_job_other_expenses_rel hjoer on hjoer.hr_job_id = hj.id 
                            left join other_expenses oe on oe.id = hjoer.other_expenses_id
                            where extract(year from '{day}'::date) between oe.start_year and oe.end_year and oe.gender is null 
                            
                            union all 
                            
                            select
                                hj2.id as hr_job_id,
                                oe2."type" as expense_type,
                                oe2.price as expense_price,
                                'other' as gender 
                            from hr_job hj2 
                            left join other_expenses oe2 on (select count(*) from hr_job_other_expenses_rel hjoer2 where hjoer2.other_expenses_id = oe2.id) = 0
                            where extract(year from '{day}'::date) between oe2.start_year and oe2.end_year and oe2.gender is null
                        ) oex
                    group by oex.hr_job_id, oex.expense_type, oex.gender
                ),
            detail_data as
                (
                    select 
                        he.id as id_nhan_vien,
                        case 
                            when hpst2.wage_type = 'monthly' then coalesce (hc2.x_insurance_wage,0)
                            when hc2.id is null and hpst.wage_type = 'monthly' then coalesce (hcx.x_insurance_wage,0)
                            else 0 
                        end as luong_chinh,
                        case
                            when hpst2.wage_type = 'monthly' then coalesce (hc2.kpi_norm,0)
                            when hc2.id is null and hpst.wage_type = 'monthly' then coalesce (hcx.kpi_norm,0)
                            else 0
                        end as luong_an_trua,
                        0::numeric as luong_nha_o,
                        0::numeric as du_kien_tang_luong,
                        case 
                            when hpst2.wage_type = 'monthly' then coalesce (hc2.wage,0)
                            when hc2.id is null and hpst.wage_type = 'monthly' then coalesce (hcx.wage,0)
                            when hpst2.wage_type = 'hourly' then coalesce(hc2.hourly_wage)*208
                            when hc2.id is null and hpst.wage_type = 'hourly' then coalesce(hcx.hourly_wage)*208
                            else 0 
                        end as luong_tong,
                        case 
                            when hpst2.wage_type = 'monthly' then coalesce (hc2.x_insurance_wage,0)
                            when hc2.id is null and hpst.wage_type = 'monthly' then coalesce (hcx.x_insurance_wage,0)
                            else 0 
                        end as bao_hiem,
                        case 
                            when hc2.id is not null then coalesce (hc2.x_allowance_phone,0)
                            when hc2.id is null and hcx.id is not null then coalesce (hcx.x_allowance_phone,0)
                            else 0 
                        end as dien_thoai,
                        case 
                            when hc2.id is not null then coalesce (hc2.x_gasoline_standard,0) * coalesce(hpop.price,0)
                            when hc2.id is null and hcx.id is not null then coalesce (hcx.x_gasoline_standard,0) * coalesce(hpop.price,0)
                            else 0 
                        end as xang_xe,
                        case 
                            when hpst2.wage_type = 'monthly' then coalesce (hc2.wage,0) / 12
                            when hc2.id is null and hpst.wage_type = 'monthly' then coalesce (hcx.wage,0) / 12
                            when hpst2.wage_type = 'hourly' then coalesce(hc2.hourly_wage)*208/12
                            when hc2.id is null and hpst.wage_type = 'hourly' then coalesce(hcx.hourly_wage)*208/12
                            else 0 
                        end as thuong_13,
                        coalesce (coe.price,0)/12 as dong_phuc,
                        coalesce (coe2.price,0)/12 as kham_sk,
                        coalesce (coe3.price,0)/12 as thuong_le,
                        coalesce (coe4.price,0)/12 as du_lich,
                        case 
                            when hpst2.wage_type = 'monthly' then coalesce (hc2.x_insurance_wage,0) * 2 / 100
                            when hc2.id is null and hpst.wage_type = 'monthly' then coalesce (hcx.x_insurance_wage,0) * 2 / 100
                            else 0 
                        end as cong_doan,
                        case 
                            when hc2.id is not null then 
                                (
                                    (select count(ady.ngay_trong_nam) from all_day_year ady) * 8 - (12+11) * 8 --so ngay trong nam tru so ngay nghi phep tru so ngay nghi le
                                    - (case 
                                        when rc2.full_time_required_hours = 44 then (select count(ady2.ngay_trong_nam) from all_day_year ady2 where ady2.ngay_trong_tuan = 6) * 4 + (select count(ady3.ngay_trong_nam) from all_day_year ady3 where ady3.ngay_trong_tuan = 0) * 8
                                        when rc2.full_time_required_hours = 48 then (select count(ady4.ngay_trong_nam) from all_day_year ady4 where ady4.ngay_trong_tuan = 0) * 8
                                        else (select count(ady2.ngay_trong_nam) from all_day_year ady2 where ady2.ngay_trong_tuan = 6) * 4 + (select count(ady3.ngay_trong_nam) from all_day_year ady3 where ady3.ngay_trong_tuan = 0) * 8
                                    end) -- tru so ngay thu 7 chu nhat
                                ) / 12 
                            when hc2.id is null and hcx.id is not null then 
                                (
                                    (select count(ady.ngay_trong_nam) from all_day_year ady) * 8 - (12+11) * 8 --so ngay trong nam tru so ngay nghi phep tru so ngay nghi le
                                    - (case 
                                        when rc.full_time_required_hours = 44 then (select count(ady2.ngay_trong_nam) from all_day_year ady2 where ady2.ngay_trong_tuan = 6) * 4 + (select count(ady3.ngay_trong_nam) from all_day_year ady3 where ady3.ngay_trong_tuan = 0) * 8
                                        when rc.full_time_required_hours = 48 then (select count(ady4.ngay_trong_nam) from all_day_year ady4 where ady4.ngay_trong_tuan = 0) * 8
                                        else (select count(ady2.ngay_trong_nam) from all_day_year ady2 where ady2.ngay_trong_tuan = 6) * 4 + (select count(ady3.ngay_trong_nam) from all_day_year ady3 where ady3.ngay_trong_tuan = 0) * 8
                                    end) -- tru so ngay thu 7 chu nhat
                                ) / 12 
                            else 0
                        end as gio_lv_thang,
                        case when hdb.id = 2 then coalesce(hj.x_labor_efficiency::numeric,0)::numeric else 100::numeric end as hs_lao_dong,
                        case when coalesce(hc2.x_type_employee, hcx.x_type_employee) in ('1','3') then 1 else 0 end as is_meal_eligible
                    from hr_employee he
                    left join hr_contract hc2 on hc2.state not in ('draft','cancel') and '{day}'::date between hc2.date_start and hc2.date_end and hc2.employee_id = he.id 
                    left join 
                        (
                            select 
                                row_number () over (order by hc.date_start asc) as stt,
                                * 
                            from hr_contract hc 
                            where hc.state not in ('draft','cancel') and hc.date_start > '{day}'::date and hc.employee_id = {employee_id}
                        ) as hcx on hcx.stt = 1 
                    left join hr_department hd on hd.id = he.department_id
                    left join hr_department_block hdb on hdb.id = hd.x_block_id 
                    left join hr_job hj on hj.id = he.job_id 
                    left join hr_payroll_structure_type hpst on hpst.id = hcx.structure_type_id  
                    left join hr_payroll_structure_type hpst2 on hpst2.id = hc2.structure_type_id 
                    left join hr_payroll_oil_price hpop on hpop."year"::int = extract(year from '{day}'::date) and hpop."month"::int = extract(month from '{day}'::date)
                    left join resource_calendar rc on rc.id = hcx.resource_calendar_id 
                    left join resource_calendar rc2 on rc2.id = hc2.resource_calendar_id 
                    left join company_other_expenses coe on coe.hr_job_id = hj.id and coe.gender = he.gender and coe.expense_type = 'uniform'
                    left join company_other_expenses coe2 on coe2.hr_job_id = hj.id and coe2.gender = he.gender  and coe2.expense_type = 'health'
                    left join company_other_expenses coe3 on coe3.hr_job_id = hj.id and coe3.gender = he.gender  and coe3.expense_type = 'holiday'
                    left join company_other_expenses coe4 on coe4.hr_job_id = hj.id and coe4.gender = he.gender  and coe4.expense_type = 'travel'
                    where 1=1
                        and (hcx.id is not null or hc2.id is not null)
                        and he.active is true
                        and he.id = {employee_id}
                )
            select
                case 
                    when coalesce(dd.gio_lv_thang,0) = 0 or coalesce(dd.hs_lao_dong,0) = 0 then 0
                    else (dd.bao_hiem+dd.dien_thoai+dd.xang_xe+dd.thuong_13+dd.dong_phuc+dd.kham_sk+dd.thuong_le+dd.du_lich+dd.cong_doan+dd.luong_tong
                          + (case when dd.is_meal_eligible = 1 then dd.gio_lv_thang/8*40000 else 0 end)) / (dd.gio_lv_thang*dd.hs_lao_dong) * 100
                end as don_gia_tb
            from detail_data dd
        '''
        for r in self:
            self._cr.execute(sql, [r.id, r.id])
            recs = self._cr.dictfetchall()
            members = [(5, 0)]
            for rec in recs:
                cost = [0]
                if r.x_date_start:
                    self._cr.execute(sql2.format(employee_id=rec['employee_id'], day=r.x_date_start))
                    cost = self._cr.fetchone()
                members.append((0, 0, {
                    'employee_id': rec['employee_id'],
                    'project_id': rec['project_id'],
                    'hour': rec['hours'],
                    'hour_cost': (cost[0] if cost else 0) * rec['hours'],
                }))
            r.sudo().x_member_ids = members

    @api.constrains('x_member_ids')
    def contrain_members(self):
        for r in self:
            r.x_member_user_ids = [(6, 0, [x.employee_id.user_id.id for x in r.x_member_ids if x.employee_id.user_id])]
            r.x_member_employee_ids = [(6, 0, [x.employee_id.id for x in r.x_member_ids])]

    @api.constrains('x_to_invoice')
    def contrain_x_to_invoice(self):
        for r in self:
            if r.x_to_invoice:
                if r.is_merge_project and len(r.x_sub_project_ids) > 0:
                    for project in r.x_sub_project_ids:
                        if not project.sub_project_id.x_to_invoice:
                            project.sub_project_id.sudo().write({'x_to_invoice': True})
                        else:
                            continue
            else:
                if r.is_merge_project and len(r.x_sub_project_ids) > 0:
                    for project in r.x_sub_project_ids:
                        if project.sub_project_id.x_to_invoice:
                            project.sub_project_id.sudo().write({'x_to_invoice': False})
                        else:
                            continue

    def cron_warning_project_process(self):
        today = date.today()
        channel_obj = self.env['mail.channel'].sudo()
        bod_partners = self.env.ref('project.group_project_manager').users.mapped('partner_id')
        pending_projects = self.sudo().search([
            ('state', '=', 'planning'),
            ('x_date_plan_start', '<=', today),
        ])
        if pending_projects:
            names = ', '.join(["<a href=#id=%s&view_type=form&model=project.project>%s</a>" % (x.id, x.name)
                               for x in pending_projects])
            channel_info = channel_obj.channel_get(bod_partners.ids)
            channel_obj.browse(channel_info['id']).message_post(
                body="Hiện có các dự án sau đã tới ngày bắt đầu mà chưa thực hiện: %s" % names,
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )
            pm_partner2projects = {}
            for p in pending_projects:
                pm_partner_id = p.user_id.partner_id
                if pm_partner_id in bod_partners:
                    continue
                if pm_partner_id not in pm_partner2projects:
                    pm_partner2projects[pm_partner_id] = self.env['project.project'].browse()
                pm_partner2projects[pm_partner_id] |= p
            for pm_partner_id in pm_partner2projects:
                names = ', '.join(["<a href=#id=%s&view_type=form&model=project.project>%s</a>" % (x.id, x.name)
                                   for x in pm_partner2projects[pm_partner_id]])
                channel_info = channel_obj.channel_get(pm_partner_id.ids)
                channel_obj.browse(channel_info['id']).message_post(
                    body="Hiện có các dự án sau đã tới ngày bắt đầu mà chưa thực hiện: %s" % names,
                    message_type='comment',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )

        late_projects = self.sudo().search([
            ('state', 'not in', ['completed', 'cancel']),
            ('x_date_plan_end', '<=', today),
        ])
        if late_projects:
            names = ', '.join(
                ["<a href=#id=%s&view_type=form&model=project.project>%s</a>" % (x.id, x.name) for x in late_projects])
            channel_info = channel_obj.channel_get(bod_partners.ids)
            channel_obj.browse(channel_info['id']).message_post(
                body="Hiện có các dự án sau đã tới ngày kết thúc mà chưa hoàn thành: %s" % names,
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )
            pm_partner2projects = {}
            for p in late_projects:
                pm_partner_id = p.user_id.partner_id
                if pm_partner_id in bod_partners:
                    continue
                if pm_partner_id not in pm_partner2projects:
                    pm_partner2projects[pm_partner_id] = self.env['project.project'].browse()
                pm_partner2projects[pm_partner_id] |= p
            for pm_partner_id in pm_partner2projects:
                names = ', '.join(["<a href=#id=%s&view_type=form&model=project.project>%s</a>" % (x.id, x.name)
                                   for x in pm_partner2projects[pm_partner_id]])
                channel_info = channel_obj.channel_get(pm_partner_id.ids)
                channel_obj.browse(channel_info['id']).message_post(
                    body="Hiện có các dự án sau đã tới ngày kết thúc mà chưa hoàn thành: %s" % names,
                    message_type='comment',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )

    def cron_done_to_invoice_project_process(self):
        channel_obj = self.env['mail.channel'].sudo()
        bod1_partners = self.env.ref('project.group_project_manager').users.mapped('partner_id')
        bod2_partners = self.env.ref('account.group_account_user').users.mapped('partner_id')
        bod_partners = bod1_partners & bod2_partners
        sql = '''SELECT pp.id
                    FROM
                        account_move am
                        LEFT JOIN project_invoice_ref pir on am.id = pir.invoice_id
                        LEFT JOIN project_project pp on  pir.project_id = pp.id
                    WHERE
                        am.STATE = 'posted' and pir.project_id is not null and am.move_type ='out_invoice' '''
        self._cr.execute(sql)
        res = self._cr.fetchall()
        check_project =[]
        for r in res :
            check_project.append(r[0])
        done_to_invoice_projects = self.sudo().search([
            ('x_to_invoice', '=', True),
            ('is_merge_project', '=', False),
            ('id', 'not in', check_project),
        ])
        if done_to_invoice_projects:
            names = ', '.join(["<a href=#id=%s&view_type=form&model=project.project>%s</a>" % (x.id, x.name)
                               for x in done_to_invoice_projects])
            channel_info = channel_obj.channel_get(bod_partners.ids)
            channel_obj.browse(channel_info['id']).message_post(
                body="Hiện có các dự án đã hoàn thành và cần xuất hóa đơn như sau: %s" % names,
                message_type='comment',
                subtype_id=self.env.ref('mail.mt_comment').id,
            )
            pm_partner2projects = {}
            for p in done_to_invoice_projects:
                pm_partner_id = p.user_id.partner_id
                if pm_partner_id in bod_partners:
                    continue
                if pm_partner_id not in pm_partner2projects:
                    pm_partner2projects[pm_partner_id] = self.env['project.project'].browse()
                pm_partner2projects[pm_partner_id] |= p
            for pm_partner_id in pm_partner2projects:
                names = ', '.join(["<a href=#id=%s&view_type=form&model=project.project>%s</a>" % (x.id, x.name)
                                   for x in pm_partner2projects[pm_partner_id]])
                channel_info = channel_obj.channel_get(pm_partner_id.ids)
                channel_obj.browse(channel_info['id']).message_post(
                    body="Hiện có các dự án đã hoàn thành và cần xuất hóa đơn như sau: %s" % names,
                    message_type='comment',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                )

    @api.onchange('x_estimate_ids')
    def onchange_estimate_ids(self):
        self.x_cost_estimate = sum(x.amount for x in self.x_estimate_ids)

    @api.onchange('x_order_line_id')
    def onchange_order(self):
        if self.x_order_line_id:
            for l in self.x_order_id.sale_estimates_line_ids:
                if l.order_line_id.id == self.x_order_line_id.id and l.category is not None:
                    self.x_category = l.category.name

    def compute_estimates(self):
        self.ensure_one()
        if self.is_merge_project and self.x_order_id:
            if len(self.x_sub_project_ids) == 0:
                raise UserError('Bạn chưa chọn mã dự án chi tiết')
            sub_ids = self.x_sub_project_ids.mapped('sub_project_id').ids
            merge_lines_quant = [(5, 0)]
            merge_lines_price = [(5, 0)]
            cost_total = 0
            sql_1 = ''' SELECT product_id, SUM ( quantity ) as quantity, price_unit, percent,SUM ( amount ) as amount 
                        FROM project_estimate
                        WHERE project_id in %s
                        GROUP BY product_id,price_unit,percent '''
            self.env.cr.execute(sql_1 , tuple([tuple(sub_ids + [0, 0])]))
            quant_rec = self._cr.dictfetchall()
            sql_2 = ''' SELECT product_id, uom_id, sum(amount) as qty,  unit_price  ,sum(amount) *  unit_price  as amount_total ,time_line
                                    FROM   material_estimate
                                    WHERE material_id in %s 
                                    GROUP BY product_id,unit_price,uom_id,time_line '''
            self.env.cr.execute(sql_2, tuple([tuple(sub_ids + [0, 0])]))
            price_rec = self._cr.dictfetchall()
            for rec in quant_rec:
                merge_lines_quant.append((0, 0, {
                    'product_id': rec['product_id'],
                    'quantity': rec['quantity'],
                    'price_unit': rec['price_unit'],
                    'percent' : rec['percent'],
                    'amount': rec['amount'],
                }))
                cost_total += rec['amount']
            for res in price_rec :
                merge_lines_price.append((0, 0, {
                    'product_id': res['product_id'] or False,
                    'amount': res['qty'],
                    'unit_price': res['unit_price'],
                    'time_line': res['time_line'] if res['time_line'] and res['time_line'] > 0 else 100,
                    'amount_total': res['amount_total'],
                }))
            self.x_estimate_ids = merge_lines_quant
            self.x_material_estimate_ids=merge_lines_price
            self.x_cost_estimate =cost_total
            return
        if not self.x_order_id and not self.x_order_line_id and self.is_merge_project == False:
            raise UserError(_('Dự án đang không liên kết tới báo giá nào'))
        # dự toán nhân công
        lines = [(5, 0)]
        cost_total = 0
        current_order_line_id = False
        total_qty = {}
        product2quant = {}
        product2price = {}
        product_template_ids = self.x_order_id.sale_estimates_line_ids.sorted(key='sequence')
        x = 0
        for r in self.x_order_id.sale_estimates_line_ids.sorted(key='sequence'):
            if r.order_line_id:
                current_order_line_id = r.order_line_id
            x += 1
            if r.type == 'quote' and len(product_template_ids) > x and product_template_ids[x]['type'] == 'estimate':
                continue
            # if r.type == 'quote' and x < len(product_template_ids) and product_template_ids[x]['type'] == 'estimate':
            #     continue
            product_id = r.product_id
            if product_id.categ_id.x_labor_cost is False:
                continue
            if self.x_order_line_id and current_order_line_id != self.x_order_line_id:
                continue
            if self.x_order_id and not self.x_order_line_id:
                if self.x_project_type == 'service':
                    if not current_order_line_id:
                        raise UserError('Không xác định được chi tiết đơn hàng khi tính toán bảng dự toán')

                    if r.type == 'quote' and r.order_line_id.id == current_order_line_id.id:
                        qty = current_order_line_id.product_uom_qty
                    else:
                        qty = r.qty * current_order_line_id.product_uom_qty
                elif self.x_project_type == 'maintainance':
                    if not current_order_line_id:
                        raise UserError('Không xác định được chi tiết đơn hàng khi tính toán bảng dự toán')

                    qty = r.qty * current_order_line_id.product_uom_qty
                else:
                    qty = r.qty
            else:
                qty = r.qty

            if product_id not in product2quant:
                product2quant[product_id] = 0
            product2quant[product_id] += qty
            if product_id not in product2price:
                product2price[product_id] = r.total_price_unit
                total_qty[product_id] = qty * r.total_price_unit
            else:
                total_qty[product_id] = total_qty[product_id] + qty * r.total_price_unit
                product2price[product_id] = total_qty[product_id] / product2quant[product_id]

        for product_id in product2quant:
            price_unit = product2price[product_id]
            quantity = product2quant[product_id]
            amount = price_unit * quantity
            time_line = next(
                (line.timeline for line in self.x_order_id.sale_estimates_line_ids.sorted(key='sequence') if
                 line.product_id == product_id),
                100
            )
            lines.append((0, 0, {
                'product_id': product_id.id,
                'quantity': quantity,
                'price_unit': price_unit,
                'percent': time_line,
                'amount': amount,
            }))
            cost_total += amount
        self.x_cost_estimate = cost_total
        self.x_estimate_ids = lines
        self.x_estimate_ids.compute_amount()
        # dự toán vật tư
        lines1 = [(5, 0)]
        cost_total = {}
        current_order_line_id = False
        product2quant1 = {}
        product2price1 = {}
        y = 0
        for r in self.x_order_id.sale_estimates_line_ids.sorted(key='sequence'):
            if r.order_line_id:
                current_order_line_id = r.order_line_id
            y += 1
            if r.type == 'quote' and len(product_template_ids) > y and product_template_ids[y]['type'] == 'estimate':
                continue
            # if r.type == 'quote' and y < len(product_template_ids) and product_template_ids[y]['type'] == 'estimate':
            #     continue
            product_id = r.product_id

            if product_id.categ_id.x_labor_cost is True:
                continue
            if product_id.x_type == 'service':
                continue
            if self.x_order_line_id and current_order_line_id != self.x_order_line_id:
                continue
            if self.x_order_id and not self.x_order_line_id:
                if r.product_id.x_type == 'product':
                    if self.x_project_type == 'service':
                        if not current_order_line_id:
                            raise UserError('Không xác định được chi tiết đơn hàng khi tính toán bảng dự toán')

                        if r.type == 'quote' and r.order_line_id.id == current_order_line_id.id:
                            qty = current_order_line_id.product_uom_qty
                        else:
                            qty = r.qty * current_order_line_id.product_uom_qty
                    elif self.x_project_type == 'maintainance':
                        if not current_order_line_id:
                            raise UserError('Không xác định được chi tiết đơn hàng khi tính toán bảng dự toán')

                        qty = r.qty * current_order_line_id.product_uom_qty
                    else:
                        qty = r.qty
                else:
                    continue
            else:
                qty = r.qty
            if product_id not in product2quant1:
                product2quant1[product_id] = 0
            product2quant1[product_id] += qty
            if product_id not in product2price1:
                product2price1[product_id] = r.total_price_unit
                cost_total[product_id] = qty * r.total_price_unit
            else:
                cost_total[product_id] = cost_total[product_id] + qty * r.total_price_unit
                product2price1[product_id] = cost_total[product_id] / product2quant1[product_id]
        for product_id in product2quant1:
            price_unit = product2price1[product_id]
            quantity = product2quant1[product_id]
            amount = price_unit * quantity
            time_line = next(
                (line.timeline for line in self.x_order_id.sale_estimates_line_ids.sorted(key='sequence') if line.product_id == product_id),
                100)
            lines1.append((0, 0, {
                'product_id': product_id.id,
                'amount': quantity,
                'unit_price': price_unit,
                'amount_total': amount,
                'time_line': time_line,
            }))

        # dự toán chi phí khác
        cost_total1 = {}
        current_order_line_id = False
        product2quant2 = {}
        product2price2 = {}
        z = 0
        for r in self.x_order_id.sale_estimates_line_ids.sorted(key='sequence'):
            if r.order_line_id:
                current_order_line_id = r.order_line_id
            z += 1
            if r.type == 'quote' and len(product_template_ids) > z and product_template_ids[z]['type'] == 'estimate':
                continue
            # if r.type == 'quote' and z < len(product_template_ids) and product_template_ids[z]['type'] == 'estimate':
            #     continue
            product_id = r.product_id

            if product_id.categ_id.x_labor_cost is True or product_id.x_type == 'product':
                continue
            if self.x_order_line_id and current_order_line_id != self.x_order_line_id:
                continue
            if self.x_order_id and not self.x_order_line_id:
                if r.product_id.x_type == 'service':
                    if self.x_project_type == 'service':
                        if not current_order_line_id:
                            raise UserError('Không xác định được chi tiết đơn hàng khi tính toán bảng dự toán')

                        if r.type == 'quote' and r.order_line_id.id == current_order_line_id.id:
                            qty = current_order_line_id.product_uom_qty
                        else:
                            qty = r.qty * current_order_line_id.product_uom_qty
                    elif self.x_project_type == 'maintainance':
                        if not current_order_line_id:
                            raise UserError('Không xác định được chi tiết đơn hàng khi tính toán bảng dự toán')

                        qty = r.qty * current_order_line_id.product_uom_qty
                    else:
                        qty = r.qty
                else:
                    continue
            else:
                qty = r.qty
            if product_id not in product2quant2:
                product2quant2[product_id] = 0
            product2quant2[product_id] += qty
            if product_id not in product2price2:
                product2price2[product_id] = r.total_price_unit
                cost_total1[product_id] = qty * r.total_price_unit
            else:
                cost_total1[product_id] = cost_total1[product_id] + qty * r.total_price_unit
                product2price2[product_id] = cost_total1[product_id] / product2quant2[product_id]

        for product_id in product2quant2:
            price_unit = product2price2[product_id]
            quantity = product2quant2[product_id]
            amount = price_unit * quantity
            time_line = next(
                (line.timeline for line in self.x_order_id.sale_estimates_line_ids.sorted(key='sequence') if
                 line.product_id == product_id),
                100)
            lines1.append((0, 0, {
                'product_id': product_id.id,
                'amount': quantity,
                'unit_price': price_unit,
                'amount_total': amount,
                'time_line': time_line,
            }))

        self.x_material_estimate_ids = lines1
        self.x_material_estimate_ids._compute_total()

    def compute_wage_cost_all(self):
        project_ids = self.with_context(active_test=False).search([('update_cost', '=', False)], limit=500, order='id')
        i = 1
        for project_id in project_ids:
            i += 1
            project_id.compute_wage_cost()
            project_id.update_cost = True

    # Cập nhật chi phí nhân công
    def compute_wage_cost(self):
        self.ensure_one()
        data = {}
        if self.wage_cost_ids:
            self.wage_cost_ids = [(5, 0, 0)]

        # tim chi tiet cham cong
        sql = """
        select sum(hwel.costing_hours) as costing_hours, sum(hwel.hour_converted) as hour_converted, entry.employee_id, entry.x_date,
            (select coalesce(sum(hwea.hour), 0) as hour
            from hr_work_entry_allowance hwea 
            where hwea.entry_id = entry.id and hwea.project_id = project.id)
        from hr_work_entry_line hwel 
        left join hr_work_entry entry on entry.id = hwel.entry_id
        left join project_project project on hwel.project_id = project.id
        where project.id = {project_id} and entry.state = 'validated'
	    group by entry.employee_id, entry.x_date, entry.id, project.id 
	    order by x_date asc
        """.format(project_id = self.id)
        self._cr.execute(sql)
        lines = self._cr.dictfetchall()
        for line in lines:
            day_entry = line.get('x_date').replace(day=1)
            year = int(line.get('x_date').year)
            month = str(line.get('x_date').month)
            employee_id = line.get('employee_id')
            # wage_cost = self.wage_cost_ids.search(
            #     [('employee_id', '=', employee_id), ('year', '=', year), ('month', '=', month)])
            wage_cost = self.wage_cost_ids.filtered(
                lambda wc: wc.employee_id.id == employee_id and wc.year == year and wc.month == month
            )
            # nếu chưa có chi phí nhân công cho tháng đó thì tạo mới, có rồi thì update
            if not wage_cost:
                wage_cost_values = {
                    'project_id': self.id,
                    'employee_id': employee_id,
                    'year': year,
                    'month': month,
                    # 'wage_cost_id': 0, đơn giá nhân công sẽ đc update sau khi wage.cost.actual được tạo
                    'hour_converted': line.get('hour_converted'),
                    'costing_hours': line.get('costing_hours'),
                    'hour': line.get('hour'),
                }

                # tìm kiếm xem có đơn giá nhân công của tháng đó chưa
                wage_cost_actual = self.env['wage.cost.actual'].search(
                    [('date_from', '<=', day_entry), ('date_to', '>=', day_entry),
                     ('employee_id', '=', line.get('employee_id'))], limit=1)
                # nếu có đơn giá nhân công của tháng đó thì tạo dữ liệu vào bảng project.wage.cost
                if wage_cost_actual:
                    wage_cost_values['wage_cost_id'] = wage_cost_actual.id
                else:
                    payslip = self.env['hr.payslip'].search(
                        [('employee_id', '=', line.get('employee_id')), ('state', '=', 'done'),
                         ('date_from', '<=', day_entry), ('date_to', '>=', day_entry)], limit=1)
                    if payslip:
                        payslip.create_wage_cost_actual()
                        wage_cost_actual = self.env['wage.cost.actual'].search(
                            [('date_from', '<=', day_entry), ('date_to', '>=', day_entry),
                             ('employee_id', '=', line.get('employee_id'))], limit=1)
                        if wage_cost_actual:
                            wage_cost_values['wage_cost_id'] = wage_cost_actual.id

                self.env['project.wage.cost'].create(wage_cost_values)
            else:
                # update
                hour_converted = wage_cost.hour_converted + line.get('hour_converted')
                costing_hours = wage_cost.costing_hours + line.get('costing_hours')
                hour = wage_cost.hour + line.get('hour')
                wage_cost.update({
                    'hour_converted': hour_converted,
                    'hour': hour,
                    'costing_hours':costing_hours
                })


    @api.onchange('x_order_id')
    def x_onchange_order_id(self):
        if self.x_order_line_id.order_id != self.x_order_id:
            self.x_order_line_id = False

    @api.onchange('partner_id')
    def x_onchange_partner_id(self):
        self.x_phone = self.partner_id.phone
        self.x_email = self.partner_id.email

    @api.depends('x_estimate_ids')
    @api.onchange('x_estimate_ids')
    def onchange_estimate_ids(self):
        for r in self:
            r.x_cost_estimate = sum(x.amount for x in r.x_estimate_ids)

    @api.depends('x_member_ids')
    @api.onchange('x_member_ids')
    def onchange_member_ids(self):
        for r in self:
            r.x_cost_real = sum(x.hour_cost for x in r.x_member_ids)

    @api.constrains('state')
    def inactive_project(self):
        if self.state in ['completed', 'cancel']:
            self.active = False
            if self.x_order_id.name == self.name:
                project_ids = self.env['project.project'].search([('x_order_id', '=', self.x_order_id.id)])
                for project_id in project_ids:
                    project_id.active = self.active

    @api.depends('x_rate')
    def compute_rate(self):
        for r in self:
            if r.x_rate :
                r.x_rate_id = self.env['customer.rate'].search([('code', '=', r.x_rate)]).id
            else:
                r.x_rate_id = False


                
    def find_lowest_rating(self):
        self.ensure_one()
        lowest_rate = 100
        find_lowest_id = 0
        for satisfaction in self.satisfaction_ids:
            if satisfaction.rate_id:
                # set lowest_rate
                if lowest_rate == 100:
                   lowest_rate = satisfaction.rate_id.rate 
                   find_lowest_id = satisfaction.id
                if satisfaction.rate_id.rate < lowest_rate:
                    find_lowest_id = satisfaction.id
                    
        for satisfaction in self.satisfaction_ids:
            if satisfaction.id == find_lowest_id:
                satisfaction.is_valuatation = True
            else:
                satisfaction.is_valuatation = False

    def write(self, vals):
        if vals.get('x_sub_project_ids'):
            sub_project_update = vals.get('x_sub_project_ids')
            for project in list(filter(lambda s: s[0] == 2,sub_project_update)):
                project_update = self.env['sub.project.project'].browse(project[1]).sub_project_id
                if project_update.x_merge_project_id.id == False:
                    continue
                else:
                    project_update.write({'x_merge_project_id': False})
            for project in list(filter(lambda s: s[0] == 1,sub_project_update)):
                project_id = project[2]['sub_project_id']
                project_update = self.env['project.project'].browse(project_id)
                project_update.write({'x_merge_project_id': self.id})
            for project in list(filter(lambda s: s[0] == 0, sub_project_update)):
                project_id = project[2]['sub_project_id']
                project_update = self.env['project.project'].browse(project_id)
                project_update.write({'x_merge_project_id': self.id})
        # sua du an chinh
        if 'main_project' in vals and vals['main_project']:
            projects = self.env['project.project'].search([('x_order_id', '=', self.x_order_id.id),
                                                         ('id', '!=', self.id),('active','in',(True,False))])
            for project in projects:
                project.main_project = False
        
        if 'state' in vals and vals['state'] == 'completed':
            self.find_lowest_rating()

        res = super().write(vals)
        if len(self.satisfaction_ids.filtered(lambda cs: cs.is_valuatation)) > 1:
            raise ValidationError('Chỉ được chọn một ĐGHQ!')
        return res

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        if vals_list.get('x_sub_project_ids'):
            sub_project_update = vals_list.get('x_sub_project_ids')
            for project in sub_project_update:
                project_id = project[2]['sub_project_id']
                project_update = self.env['project.project'].browse(project_id)
                project_update.write({'x_merge_project_id' : res.id})
        return res


class ProjectMember(models.Model):
    _name = 'project.member'
    _description = 'Thành viên'

    project_id = fields.Many2one('project.project', 'Dự án')
    employee_id = fields.Many2one('hr.employee', 'Tên nhân viên', required=1)
    job_id = fields.Many2one('hr.job', 'Chức danh', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', 'Phòng ban', related='employee_id.department_id')
    hour = fields.Float('Giờ công thực tế')
    hour_cost = fields.Float('Chi phí theo giờ công')


class ProjectEstimate(models.Model):
    _name = 'project.estimate'
    _description = 'Dự toán nhân công'

    project_id = fields.Many2one('project.project', 'Dự án')
    product_id = fields.Many2one('product.product', 'Phân loại', domain=[('categ_id.x_labor_cost', '=', True)], ondelete='restrict')
    uom_id = fields.Many2one('uom.uom', 'Đơn vị', related='product_id.uom_id')
    quantity = fields.Float('Số lượng')
    price_unit = fields.Float('Đơn giá')
    percent = fields.Float('Timeline (%)', default=100)
    amount = fields.Float('Thành tiền')
    note = fields.Char('Ghi chú')

    @api.depends('quantity', 'price_unit', 'percent')
    @api.onchange('quantity', 'price_unit', 'percent')
    def compute_amount(self):
        for r in self:
            r.amount = r.price_unit * r.quantity * r.percent * 0.01

    @api.depends('quantity', 'amount', 'percent')
    @api.onchange('quantity', 'amount', 'percent')
    def compute_price_unit(self):
        for r in self:
            if r.percent and r.amount and r.quantity and r.price_unit:
                r.price_unit = r.amount / r.quantity / r.percent / 0.01
            else:
                continue


class MaterialEstimate(models.Model):
    _name = 'material.estimate'
    _description = 'Dự toán vật tư'

    product_id = fields.Many2one('product.product', string='Sản phẩm', ondelete='restrict')
    uom_id = fields.Many2one('uom.uom', string='Đơn vị', readonly=True)
    amount = fields.Float('Số lượng')
    unit_price = fields.Float('Đơn giá')
    time_line = fields.Float('Timeline(%)', default=100)
    amount_total = fields.Float('Thành tiền', compute='_compute_total')
    material_id = fields.Many2one('project.project', 'Dự án')

    def _compute_total(self):
        for r in self:
            r.amount_total = r.amount * r.unit_price * r.time_line * 0.01

    @api.constrains('product_id')
    @api.depends('product_id')
    def compute_uom(self):
        for r in self:
            r.uom_id = r.product_id.uom_id


class ProjectWish(models.Model):
    _name = 'project.wish'
    _description = 'Đăng ký nguyện vọng'
    _inherit = ['mail.thread']

    name = fields.Char('Tên', compute='compute_rec_name', store=1)
    employee_id = fields.Many2one('hr.employee', 'Nhân viên', required=1, tracking=True)
    user_id = fields.Many2one('res.users', 'Người dùng', related='employee_id.user_id', store=1)
    date = fields.Date('Ngày đăng ký', required=1, tracking=True)
    project_id = fields.Many2one('project.project', 'Dự án đăng ký', required=1, tracking=True,
                                 domain=[('x_self_register', '=', True),
                                         ('state', 'not in', ['completed', 'canceled', 'pending'])])
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approval', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('cancel', 'Bị từ chối'),
    ], 'Trạng thái', default='draft', copy=0, readonly=1, tracking=True)
    is_approvable = fields.Boolean('Là QLDA', compute='compute_nonstore_data')

    @api.constrains('employee_id', 'project_id', 'date')
    def compute_rec_name(self):
        for r in self:
            if r.employee_id and r.project_id and r.date:
                r.name = '%s - %s (%s)' % (r.employee_id.name, r.project_id.name, r.date.strftime('%d/%m/%Y'))
            else:
                r.name = '/'

    @api.model
    def default_get(self, fields_list):
        res = super(ProjectWish, self).default_get(fields_list)
        employee_id = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        if employee_id:
            res['employee_id'] = employee_id[0].id
        res['date'] = date.today()
        return res

    def button_send_approval(self):
        self.filtered(lambda s: s.state == 'draft').write({'state': 'approval'})

    def button_approve(self):
        channel_obj = self.env['mail.channel'].sudo()
        for r in self:
            if r.state != 'approval':
                continue
            if r.is_approvable:
                r.write({'state': 'approved'})
                if r.employee_id not in r.project_id.x_member_ids.mapped('employee_id'):
                    r.project_id.x_member_ids = [(0, 0, {
                        'employee_id': r.employee_id.id,
                    })]
                if r.employee_id.user_id:
                    channel_info = channel_obj.channel_get(r.employee_id.user_id.partner_id.ids)
                    channel_obj.browse(channel_info['id']).message_post(
                        body="Đăng ký nguyện vọng của bạn cho dự án <a href=#id=%s&view_type=form&model=project.project>%s</a> đã được duyệt" % (
                            r.project_id.id, r.project_id.name),
                        message_type='comment',
                        subtype_id=self.env.ref('mail.mt_comment').id,
                    )
                    # self.message_subscribe(partner_ids=r.employee_id.user_id.partner_id.ids)
            else:
                raise UserError(_('Anh/chị không được phân quyền thực hiện hành động này'))

    def button_reject(self):
        channel_obj = self.env['mail.channel'].sudo()
        for r in self:
            if r.is_approvable:
                r.write({'state': 'cancel'})
                if r.employee_id.user_id:
                    channel_info = channel_obj.channel_get(r.employee_id.user_id.partner_id.ids)
                    channel_obj.browse(channel_info['id']).message_post(
                        body="Đăng ký nguyện vọng của bạn cho dự án <a href=#id=%s&view_type=form&model=project.project>%s</a> đã bị từ chối" % (
                            r.project_id.id, r.project_id.name),
                        message_type='comment',
                        subtype_id=self.env.ref('mail.mt_comment').id,
                    )
            else:
                raise UserError(_('Anh/chị không được phân quyền thực hiện hành động này'))

    def compute_nonstore_data(self):
        is_project_manager = self.user_has_groups('project.group_project_manager')
        for r in self:
            r.is_approvable = is_project_manager or (self._uid == r.project_id.user_id.id)

    def unlink(self):
        if any(x for x in self):
            raise UserError(_('Anh/chị không được xoá phiếu đã duyệt hoặc đã huỷ'))
        return super(ProjectWish, self).unlink()


class SubProject(models.Model):
    _name = "sub.project.project"
    _description = "Các dự án chi tiết "

    merge_project_id = fields.Many2one('project.project', 'Dự án gộp')
    sub_project_id = fields.Many2one('project.project', 'Dự án con', required=1)
    user_id = fields.Many2one('res.users', 'Quản lý dự án')
    x_date_plan_start = fields.Date('Ngày bắt đầu kế hoạch')
    x_date_plan_end = fields.Date('Ngày kết thúc kế hoạch')
    x_date_start = fields.Date('Ngày bắt đầu thực tế')
    x_date_end = fields.Date('Ngày kết thúc thực tế')
    x_rate = fields.Selection([
        ('E', 'Rất hài lòng'),
        ('S', 'Hài lòng'),
        ('A', 'Chấp nhận'),
        ('D', 'Không hài lòng'),
    ], 'Mức độ hài lòng')
    x_rate_id = fields.Many2one('customer.rate', 'Mức độ hài lòng')
    state = fields.Selection([
        ('planning', 'Kế hoạch'),
        ('ongoing', 'Đang thực hiện'),
        ('pending', 'Tạm hoãn'),
        ('completed', 'Hoàn thành'),
        ('canceled', 'Đã huỷ'),
    ], 'Trạng thái', default='planning', copy=0)

    @api.depends('sub_project_id')
    @api.onchange('sub_project_id')
    def onchange_sub_project(self):
        for r in self:
            sub_project = r.sub_project_id
            if sub_project:
                r.state = sub_project.state
                r.x_rate = sub_project.x_rate or False
                r.x_rate_id = sub_project.x_rate_id.id or False
                r.x_date_end = sub_project.x_date_end or False
                r.x_date_start = sub_project.x_date_start or False
                r.x_date_plan_end = sub_project.x_date_plan_end or False
                r.x_date_plan_start = sub_project.x_date_plan_start or False
                r.user_id = sub_project.user_id.id or False


class CustomerRate(models.Model):
    _name = 'customer.rate'
    _description = 'Mức độ hài lòng của khách hàng'

    code = fields.Char('Mã')
    name = fields.Char('Tên')
    rate = fields.Float('Giá trị (%)')


class CustomerSatisfaction(models.Model):
    _name = 'customer.satisfaction'
    _description = 'Chi phí nhân công của dự án'

    def default_start_date(self):
        project_id = self.env.context.get('default_project_id')
        sql = """
            select min(entry.x_date) as start_date from hr_work_entry_line hwel
            left join hr_work_entry entry on entry.id = hwel.entry_id
            where hwel.project_id = %s
        """
        self._cr.execute(sql, (project_id,))
        start_date = self._cr.fetchone()[0]
        return start_date

    def default_end_date(self):
        project_id = self.env.context.get('default_project_id')
        sql = """
            select max(entry.x_date) as end_date from hr_work_entry_line hwel
            left join hr_work_entry entry on entry.id = hwel.entry_id
            where hwel.project_id = %s
        """
        self._cr.execute(sql, (project_id,))
        end_date = self._cr.fetchone()[0]
        return end_date

    project_id = fields.Many2one('project.project', 'Dự án')
    work_employee_ids = fields.Many2many('hr.employee', string='Tên nhân viên', compute='compute_work_employee_ids')
    employee_ids = fields.Many2many('hr.employee', 'satisfaction_employee_ref', 'satisfaction_id', 'employee_id','Tên nhân viên', required=0)
    start_date = fields.Date('Ngày bắt đầu', default=default_start_date, required=False)
    end_date = fields.Date('Ngày kết thúc', default=default_end_date, required=False)
    report_date = fields.Date('Ngày xem xét báo cáo', required=False)
    rate_id = fields.Many2one('customer.rate', 'Mức độ hài lòng', required=0)
    general_status = fields.Text('Tình trạng chung')
    feedback = fields.Text('Ý kiến của khách hàng')
    action = fields.Text('Hành động khắc phục')
    feedback_note = fields.Text('Ghi chú')
    is_valuatation = fields.Boolean('ĐGHQ', default=False)

    @api.model
    def official_rate_code_map(self, project_ids):
        """{project_id: rate code ĐGHQ chính thức} cho tập dự án.

        Chọn XÁC ĐỊNH khi 1 dự án có nhiều đánh giá: ưu tiên bản is_valuatation=True
        (ĐGHQ, ràng buộc tối đa 1/dự án); nếu chưa gắn cờ thì lấy rate THẤP NHẤT
        (khớp find_lowest_rating), tie-break theo id. Tránh non-deterministic khiến
        báo cáo thưởng (reward.line) lệch với báo cáo hiệu suất (11.1/11.2).
        """
        sats = self.search([('project_id', 'in', project_ids),
                            ('rate_id', '!=', False)])
        by_proj = {}
        for s in sats:
            by_proj.setdefault(s.project_id.id, []).append(s)
        out = {}
        for pid, lst in by_proj.items():
            chosen = (next((s for s in lst if s.is_valuatation), None)
                      or min(lst, key=lambda s: (s.rate_id.rate, s.id)))
            out[pid] = chosen.rate_id.code
        return out

    @api.onchange('start_date', 'end_date', 'project_id')
    def onchange_employee(self):
        project_id = self.env.context.get('default_project_id')
        domain = [
            ('entry_id.x_date', '>=', self.start_date),
            ('entry_id.x_date', '<=', self.end_date),
            ('entry_id.state', '=', 'validated')
        ]
        if project_id:
            domain += [('project_id', '=', project_id)]

        work_entries = self.env['hr.work.entry.line'].sudo().search(domain)
        employee_ids = [entry.entry_id.employee_id.id for entry in work_entries if entry.entry_id.employee_id]
        self.employee_ids = [(6, 0, employee_ids)]

    @api.depends('start_date', 'end_date', 'project_id')
    def compute_work_employee_ids(self):
        for rec in self:
            # Thử lấy project_id từ context nếu có
            project_id = self.env.context.get('default_project_id')
            if rec.start_date and rec.end_date:
                domain = [
                    ('entry_id.x_date', '>=', rec.start_date),
                    ('entry_id.x_date', '<=', rec.end_date), ('entry_id.state', '=', 'validated')
                ]
                if project_id:
                    domain += [('project_id', '=', project_id)]

                work_entries = self.env['hr.work.entry.line'].sudo().search(domain)
                employee_ids = [entry.entry_id.employee_id.id for entry in work_entries if entry.entry_id.employee_id]
                rec.work_employee_ids = [(6, 0, employee_ids)]
            else:
                rec.work_employee_ids = [(5, 0, 0)]

    def _get_default_project_type(self):
        project_id = self.env.context.get('default_project_id')
        project = self.env['project.project'].browse(project_id)
        if project.x_order_id:
            return project.x_order_id.project_type
        return None
    
    project_type = fields.Selection(_Project_type, 'Loại hình công việc', default=_get_default_project_type)
    @api.model
    def create(self, vals):
        current_project_id = self.env['project.project'].browse(vals.get('project_id'))
        if not current_project_id.satisfaction_ids:
            vals['is_valuatation'] = True
        return super(CustomerSatisfaction, self).create(vals)


