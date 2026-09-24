from odoo import tools
from odoo import api, fields, models


class CashFlowReport(models.Model):
    _name = "cash.flow.view_report"
    _description = "Cash Flow Report"
    _rec_name = 'nguoi_nhan'
    _auto = False
    _order = 'ngay desc'

    ngay = fields.Date('Ngày')
    thang = fields.Integer('Tháng')
    nam = fields.Integer('Năm')
    thang_nam = fields.Char('Tháng năm')
    nguoi_nhan = fields.Char('Người nhận/nộp tiền')
    ten_khach_hang = fields.Char('Tổ chức nhận/nộp tiền')
    dien_giai = fields.Char('Diễn giải')
    ma_du_an = fields.Char('Mã dự án')
    chung_tu = fields.Selection([('tax', 'Thuế'), ('internal', 'Nội bộ')], 'Phân loại chứng từ')
    ma_khoan_tien = fields.Char('Mã khoản tiền')
    kieu_thanh_toan = fields.Char('Hình thức thu/chi')
    chi = fields.Monetary('Chi')
    thu = fields.Monetary('Thu')
    kq_1 = fields.Monetary('Hiệu 1',compute='_compute_kq_1')
    ghi_chu = fields.Text('Ghi chú')
    so_chung_tu = fields.Char('Số chứng từ')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('thu', 'chi')
    def _compute_kq_1(self):
        for rec in self:
            rec.kq_1 = (rec.thu or 0.0) - (rec.chi or 0.0)

    def _query(self):

        select_ = """
        select
                row_number() OVER (ORDER BY X.move_id, X.pd_id NULLS FIRST, X.pl_id NULLS FIRST, X.aar_id NULLS FIRST) AS id,
                ngay,
                EXTRACT(MONTH FROM ngay)::integer as thang,
                EXTRACT(YEAR FROM ngay)::integer as nam,
                TO_CHAR(ngay, 'MM/YYYY') as thang_nam,
                nguoi_nhan,
                ten_khach_hang,
                dien_giai,
                so3.name as ma_du_an,
                chung_tu,
                ma_khoan_tien,
                kieu_thanh_toan,
                chi,
                thu,
                ghi_chu,
                so_chung_tu,
                23 as currency_id
            from
                (select
                    amx.id as move_id,
                    pd.id as pd_id,
                    pl.id as pl_id,
                    aar.id as aar_id,
                    amx.date as ngay,
                    case when ru.id is not null then coalesce(rp.name,'') else coalesce(ap.x_receiver,'') end as nguoi_nhan,
                    case when ru.id is not null then coalesce(rc.name,'') else coalesce(rp.name,rc.name) end as ten_khach_hang,
                    coalesce(amx.ref,'') as dien_giai,
                    case
                        when aa.id is not null and pd.id is not null then pd.code_project
                        when aa.id is not null and pd.id is null and aa."type" = 'supplier' then po_rate.so_id
                        when aar.id is not null then prd.main_project
                        when am.id is not null and pd.id is not null then pd.code_project
                        when am.id is not null and pd.id is null then am.x_order_id
                        when so.id is not null then so.id
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is not null and ap.is_internal_transfer is false and ap.x_pay_cost is false then pd.code_project
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and ap.is_internal_transfer is false and ap.x_pay_cost is true then pl.x_sale_project_id
                        else null
                    end as ma_du_an,
                    coalesce(ap.x_license_type,'') as chung_tu,
                    coalesce(cm.code_money,'') as ma_khoan_tien,
                    coalesce(aj.name,'') as kieu_thanh_toan,
                    case
                        when aa.id is not null and pd.id is not null then (case when pdc.pd_count = 1 and ap.amount > pd.amount_total then ap.amount else pd.amount_total end)
                        when aa.id is not null and pd.id is null and aa."type" = 'supplier' then po_rate.pol_so_rate*ap.amount
                        when aa.id is not null and pd.id is null and aa."type" = 'internal' then ap.amount
                        when aar.id is not null and ap.payment_type = 'outbound' then prd.amount_repay
                        when am.id is not null and pd.id is not null and ap.payment_type = 'outbound' then (case when pdc.pd_count = 1 and ap.amount > pd.amount_total then ap.amount else pd.amount_total end)
                        when am.id is not null and pd.id is null and ap.payment_type = 'outbound' then ap.amount
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is not null and ap.x_pay_cost is false and ap.payment_type = 'outbound' then (case when pdc.pd_count = 1 and ap.amount > pd.amount_total then ap.amount else pd.amount_total end)
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is null and ap.x_pay_cost is false and ap.payment_type = 'outbound' then ap.amount
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and ap.x_pay_cost is true and ap.payment_type = 'outbound' then pl.amount
                        else 0
                    end as chi,
                    case
                        when aar.id is not null and ap.payment_type = 'inbound' then prd.amount_repay
                        when am.id is not null and pd.id is not null and ap.payment_type = 'inbound' then (case when pdc.pd_count = 1 and ap.amount > pd.amount_total then ap.amount else pd.amount_total end)
                        when am.id is not null and pd.id is null and ap.payment_type = 'inbound' then ap.amount
                        when so.id is not null then ap.amount
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is not null and ap.x_pay_cost is false and ap.payment_type = 'inbound' then (case when pdc.pd_count = 1 and ap.amount > pd.amount_total then ap.amount else pd.amount_total end)
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and pd.id is null and ap.x_pay_cost is false and ap.payment_type = 'inbound' then ap.amount
                        when aa.id is null and aar.id is null and am.id is null and so.id is null and ap.x_pay_cost is true and ap.payment_type = 'inbound' then pl.amount
                        else 0
                    end as thu,
                    coalesce(ap.x_note,'') as ghi_chu,
                    coalesce(amx.name,'') as so_chung_tu
                from account_payment ap
                left join account_move amx on amx.payment_id = ap.id
                left join account_journal aj on aj.id = amx.journal_id
                left join res_partner rp on ap.partner_id = rp.id
                left join res_users ru on ap.partner_id = ru.partner_id
                left join res_company rc on 1 = 1 and rc.id=1
                left join code_money cm on cm.id = ap.x_code_money
                left join project_detail pd on pd.payment_id = ap.id and ap.is_internal_transfer is false and ap.x_pay_cost is false
                left join (
                    select payment_id, count(*) as pd_count
                    from project_detail
                    where payment_id is not null
                    group by payment_id
                ) as pdc on pdc.payment_id = ap.id
                left join account_advance aa on aa.id = ap.x_origin_advance_id
                left join
                    (
                        select
                            po.id as po_id,
                            so2.id as so_id,
                            case when po.amount_total = 0 then 0 else sum(pol.price_total)/po.amount_total end as pol_so_rate
                        from purchase_order po
                        left join purchase_order_line pol on pol.order_id = po.id
                        left join project_project pp on pp.id = pol.x_project_id
                        left join sale_order so2 on so2.id = pp.x_order_id
                        group by po.id,so2.id,po.amount_total
                    ) as po_rate on ap.x_origin_advance_id is not null and pd.id is null and aa.type = 'supplier' and aa.po_id = po_rate.po_id
                left join account_advance_repay aar on aar.id = ap.x_origin_repay_id
                left join project_repay_detail prd on prd.payment_id = ap.id and ap.x_origin_repay_id is not null
                left join account_move am on am.id = ap.x_origin_move_id
                left join sale_order so on so.id = ap.x_origin_so_id
                left join payment_line pl on pl.payment_id = ap.id and ap.x_pay_cost is true and aa.id is null and aar.id is null and am.id is null and so.id is null
                where amx.state = 'posted'
                )X
            left join sale_order so3 on so3.id = X.ma_du_an
            order by X.ngay,X.so_chung_tu"""
        return select_

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    def preview_with_year(self,year):
        try:
            DetailModel = self.env['cash.flow.report.detail']
            DetailModel.sudo().search([]).unlink()

            cash_flow_code_mappings = self.env['cash.flow.code.mapping'].search([], order='sequence')
            if not cash_flow_code_mappings:
                return self._return_notification('Cảnh báo', 'Không tìm thấy mã khoản tiền nào', 'warning')

            income_codes = ['RMS', 'RFM', 'RIN', 'RIV', 'RRM', 'CCL']
            expense_codes = ['MS', 'FM', 'SS', 'CS', 'PG', 'LC', 'CR', 'GC', 'AT', 'OH', 'TA', 'DP', 'IV', 'BA']

            sql_regular_data = """
                SELECT 
                    nam as year,
                    ma_khoan_tien as code,
                    thang as month,
                    COALESCE(SUM(thu), 0) as total_thu,
                    COALESCE(SUM(chi), 0) as total_chi
                FROM cash_flow_view_report 
                WHERE nam IS NOT NULL 
                AND ma_khoan_tien IS NOT NULL 
                AND ma_khoan_tien != ''
                AND nam='{year}'
                GROUP BY nam, ma_khoan_tien, thang
                ORDER BY nam DESC, ma_khoan_tien, thang
            """.format(year=year)

            sql_payment_type_data = """
                WITH year_range AS (
                    SELECT {year}::integer as year
                ),
                month_ends AS (
                    SELECT 
                        yr.year as nam,
                        generate_series(1, 12) as thang,
                        (date (yr.year || '-01-01') + (generate_series(1, 12) - 1) * interval '1 month' + interval '1 month' - interval '1 day')::date as end_date
                    FROM year_range yr
                ),
                cash_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'Cash' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('Cash')
                    GROUP BY me.nam, me.thang, me.end_date
                ),
                itcb_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'I-TCB' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('I-TCB')
                    GROUP BY me.nam, me.thang, me.end_date
                ),
                bidv_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'BIDV' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('BIDV')
                    GROUP BY me.nam, me.thang, me.end_date
                ),
                tcb_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'TCB' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('TCB')
                    GROUP BY me.nam, me.thang, me.end_date
                ),
                bidv2_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'BIDV2' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('BIDV2')
                    GROUP BY me.nam, me.thang, me.end_date
                ),
                vcb_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'VCB' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('VCB')
                    GROUP BY me.nam, me.thang, me.end_date
                ),
                vpb_totals AS (
                    SELECT
                        me.nam,
                        me.thang,
                        'VPBank' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('VPBank')
                    GROUP BY me.nam, me.thang, me.end_date
                )
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM cash_totals
                UNION ALL
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM itcb_totals
                UNION ALL
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM bidv_totals
                UNION ALL
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM tcb_totals
                UNION ALL
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM bidv2_totals
                UNION ALL
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM vcb_totals
                UNION ALL
                SELECT
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM vpb_totals
                ORDER BY year, code, month
            """.format(year=year)

            # Query for "Số chưa đến hạn" calculation
            sql_pending_amount = """
                WITH year_range AS (
                    SELECT {year}::integer as year
                ),
                month_ends AS (
                    SELECT 
                        yr.year as nam,
                        generate_series(1, 12) as thang,
                        (date (yr.year || '-' || LPAD(generate_series(1, 12)::text, 2, '0') || '-01'))::date as start_date,
                        (date (yr.year || '-' || LPAD(generate_series(1, 12)::text, 2, '0') || '-01') + interval '1 month' - interval '1 day')::date as end_date
                    FROM year_range yr
                ),
                pending_calculations AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        '-' as code,
                        COALESCE(
                            (SELECT SUM(av.value_deposits)
                             FROM account_saving av
                             LEFT JOIN res_bank rb ON av.bank_id = rb.id
                             WHERE av.state != 'draft'
                               AND av.date_sent <= me.end_date 
                               AND av.date_settlement > me.end_date), 0
                        ) +
                        COALESCE(
                            (SELECT SUM(av.value_deposits)
                             FROM account_saving av
                             LEFT JOIN res_bank rb ON av.bank_id = rb.id
                             WHERE av.state != 'draft'
                               AND av.date_settlement >= me.start_date
                               AND av.date_settlement <= me.end_date
                               AND av.date_settlement > CURRENT_DATE), 0
                        ) as pending_amount
                    FROM month_ends me
                )
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    pending_amount as total_amount
                FROM pending_calculations
                ORDER BY year, month
            """.format(year=year)
            print('hshshshshhshshshshshshs')
            # Execute all queries and combine results
            self.env.cr.execute(sql_regular_data)
            regular_data = self.env.cr.fetchall()

            self.env.cr.execute(sql_payment_type_data)
            payment_type_data = self.env.cr.fetchall()

            self.env.cr.execute(sql_pending_amount)
            pending_data = self.env.cr.fetchall()

            sql_matured_amount = """
                WITH year_range AS (
                    SELECT {year}::integer as year
                ),
                month_range AS (
                    SELECT 
                        yr.year as nam,
                        generate_series(1, 12) as thang,
                        (date (yr.year || '-' || LPAD(generate_series(1, 12)::text, 2, '0') || '-01'))::date as start_date,
                        (date (yr.year || '-' || LPAD(generate_series(1, 12)::text, 2, '0') || '-01') + interval '1 month' - interval '1 day')::date as end_date
                    FROM year_range yr
                ),
                matured_calculations AS (
                    SELECT 
                        mr.nam,
                        mr.thang,
                        '-' as code,
                        COALESCE(
                            (SELECT SUM(av.amount_settlement)
                             FROM account_saving av
                             LEFT JOIN res_bank rb ON av.bank_id = rb.id
                             WHERE av.state != 'draft'
                               AND av.date_settlement >= mr.start_date
                               AND av.date_settlement <= mr.end_date
                               AND av.date_settlement <= CURRENT_DATE), 0
                        ) as matured_amount
                    FROM month_range mr
                )
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    matured_amount as total_amount
                FROM matured_calculations
                ORDER BY year, month
            """.format(year=year)

            self.env.cr.execute(sql_matured_amount)
            matured_data = self.env.cr.fetchall()

            # Query for SC codes (Thu lại tiền đầu tư tài chính và Chi tiền gửi tiết kiệm)
            sql_sc_data = """
                SELECT 
                    nam as year,
                    'SC' as code,
                    thang as month,
                    COALESCE(SUM(thu), 0) as total_thu,
                    COALESCE(SUM(chi), 0) as total_chi
                FROM cash_flow_view_report 
                WHERE nam IS NOT NULL 
                AND ma_khoan_tien = 'SC'
                GROUP BY nam, thang
                ORDER BY nam DESC, thang
            """

            self.env.cr.execute(sql_sc_data)
            sc_data = self.env.cr.fetchall()

            # Query for TCBS and TKDT codes
            sql_tcbs_tkdt_data = """
                WITH year_range AS (
                    SELECT {year}::integer as year
                ),
                month_ends AS (
                    SELECT 
                        yr.year as nam,
                        generate_series(1, 12) as thang,
                        (date (yr.year || '-01-01') + (generate_series(1, 12) - 1) * interval '1 month' + interval '1 month' - interval '1 day')::date as end_date
                    FROM year_range yr
                ),
                tcbs_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'TCBS' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('TCBS')
                    GROUP BY me.nam, me.thang, me.end_date
                ),
                tkdt_totals AS (
                    SELECT 
                        me.nam,
                        me.thang,
                        'TKDT' as code,
                        COALESCE(SUM(cfv.thu) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_thu,
                        COALESCE(SUM(cfv.chi) FILTER (WHERE cfv.ngay <= me.end_date), 0) as total_chi
                    FROM month_ends me
                    LEFT JOIN cash_flow_view_report cfv ON cfv.kieu_thanh_toan in ('TKDT')
                    GROUP BY me.nam, me.thang, me.end_date
                )
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM tcbs_totals
                UNION ALL
                SELECT 
                    nam as year,
                    code,
                    thang as month,
                    total_thu,
                    total_chi
                FROM tkdt_totals
                ORDER BY year, code, month
            """.format(year=year)

            self.env.cr.execute(sql_tcbs_tkdt_data)
            tcbs_tkdt_data = self.env.cr.fetchall()

            # Combine all data
            all_data = regular_data + payment_type_data + tcbs_tkdt_data

            if not all_data:
                return self._return_notification('Cảnh báo', 'Không tìm thấy dữ liệu báo cáo', 'warning')

            # Process pending amount data
            pending_dict = {}
            for year, code, month, total_amount in pending_data:
                year = int(year)
                month = int(month)

                if year not in pending_dict:
                    pending_dict[year] = {}

                pending_dict[year][f't{month}'] = total_amount

            # Process matured amount data
            matured_dict = {}
            for year, code, month, total_amount in matured_data:
                year = int(year)
                month = int(month)

                if year not in matured_dict:
                    matured_dict[year] = {}

                matured_dict[year][f't{month}'] = total_amount

            sc_thu_dict = {}
            sc_chi_dict = {}

            for year, code, month, total_thu, total_chi in sc_data:
                year = int(year)
                month = int(month)

                if year not in sc_thu_dict:
                    sc_thu_dict[year] = {}
                if year not in sc_chi_dict:
                    sc_chi_dict[year] = {}

                sc_thu_dict[year][f't{month}'] = total_thu
                sc_chi_dict[year][f't{month}'] = total_chi

            # Process TCBS and TKDT data separately
            tcbs_tkdt_dict = {}
            for year, code, month, thu, chi in tcbs_tkdt_data:
                year = int(year)
                month = int(month)

                if year not in tcbs_tkdt_dict:
                    tcbs_tkdt_dict[year] = {}
                if code not in tcbs_tkdt_dict[year]:
                    tcbs_tkdt_dict[year][code] = {}

                # For TCBS and TKDT, use thu - chi as amount
                amount = thu - chi
                tcbs_tkdt_dict[year][code][f't{month}'] = amount

            data_dict = {}
            processed_rows = 0
            for year, code, month, thu, chi in all_data:
                year = int(year)  # Convert to int
                month = int(month)  # Convert to int

                # Skip TCBS and TKDT as they are processed separately
                if code in ['TCBS', 'TKDT']:
                    continue

                if year not in data_dict:
                    data_dict[year] = {}
                if code not in data_dict[year]:
                    data_dict[year][code] = {}

                if code in income_codes:
                    amount = thu
                elif code in expense_codes:
                    amount = chi
                else:
                    amount = thu - chi

                data_dict[year][code][f't{month}'] = amount
                processed_rows += 1

            all_codes_in_data = set()
            for year in data_dict:
                all_codes_in_data.update(data_dict[year].keys())
            bulk_data = []

            # Process all codes in sequence order
            for year in sorted(data_dict.keys(), reverse=True):
                for mapping in cash_flow_code_mappings:
                    code = mapping.code

                    if mapping.parent_2 == 'thu':
                        parent_2_order = 1
                    elif mapping.parent_2 == 'chi':
                        parent_2_order = 2
                    elif mapping.parent_2 == 'ton_cuoi_ky':
                        parent_2_order = 3
                    else:
                        parent_2_order = 999

                    if code == '-':
                        if mapping.name == 'Số chưa đến hạn' and year in pending_dict:
                            monthly_pending = pending_dict[year]
                            total_pending = sum(monthly_pending.values())

                            record_data = {
                                'year': year,
                                'sequence': mapping.sequence,
                                'name': mapping.name,
                                'code': mapping.code,
                                'parent': mapping.parent,
                                'parent_2': mapping.parent_2,
                                'parent_2_order': parent_2_order,
                                't1': monthly_pending.get('t1', 0),
                                't2': monthly_pending.get('t2', 0),
                                't3': monthly_pending.get('t3', 0),
                                't4': monthly_pending.get('t4', 0),
                                't5': monthly_pending.get('t5', 0),
                                't6': monthly_pending.get('t6', 0),
                                't7': monthly_pending.get('t7', 0),
                                't8': monthly_pending.get('t8', 0),
                                't9': monthly_pending.get('t9', 0),
                                't10': monthly_pending.get('t10', 0),
                                't11': monthly_pending.get('t11', 0),
                                't12': monthly_pending.get('t12', 0),
                            }
                        elif mapping.name == 'Số tất toán trong tháng' and year in matured_dict:
                            monthly_matured = matured_dict[year]
                            total_matured = sum(monthly_matured.values())

                            record_data = {
                                'year': year,
                                'sequence': mapping.sequence,
                                'name': mapping.name,
                                'code': mapping.code,
                                'parent': mapping.parent,
                                'parent_2': mapping.parent_2,
                                'parent_2_order': parent_2_order,
                                't1': monthly_matured.get('t1', 0),
                                't2': monthly_matured.get('t2', 0),
                                't3': monthly_matured.get('t3', 0),
                                't4': monthly_matured.get('t4', 0),
                                't5': monthly_matured.get('t5', 0),
                                't6': monthly_matured.get('t6', 0),
                                't7': monthly_matured.get('t7', 0),
                                't8': monthly_matured.get('t8', 0),
                                't9': monthly_matured.get('t9', 0),
                                't10': monthly_matured.get('t10', 0),
                                't11': monthly_matured.get('t11', 0),
                                't12': monthly_matured.get('t12', 0),
                            }
                        else:
                            # Header rows have all months as 0
                            record_data = {
                                'year': year,
                                'sequence': mapping.sequence,
                                'name': mapping.name,
                                'code': mapping.code,
                                'parent': mapping.parent,
                                'parent_2': mapping.parent_2,
                                'parent_2_order': parent_2_order,
                                't1': 0, 't2': 0, 't3': 0, 't4': 0, 't5': 0, 't6': 0,
                                't7': 0, 't8': 0, 't9': 0, 't10': 0, 't11': 0, 't12': 0,
                            }
                        bulk_data.append(record_data)
                    elif code == 'SC':
                        # Handle SC codes specially
                        if mapping.name == 'Thu lại tiền đầu tư tài chính, tất toán tiết kiệm' and year in sc_thu_dict:
                            monthly_data = sc_thu_dict[year]
                        elif mapping.name == 'Chi tiền gửi tiết kiệm, đầu tư tài chính' and year in sc_chi_dict:
                            monthly_data = sc_chi_dict[year]
                        else:
                            # Default to empty data if no match
                            monthly_data = {}

                        # Ensure all months have values
                        for month in range(1, 13):
                            month_key = f't{month}'
                            if month_key not in monthly_data:
                                monthly_data[month_key] = 0

                        record_data = {
                            'year': year,
                            'sequence': mapping.sequence,
                            'name': mapping.name,
                            'code': mapping.code,
                            'parent':'4. Thu, chi Sc',
                            'parent_2': mapping.parent_2,
                            'parent_2_order': parent_2_order,
                            't1': monthly_data.get('t1', 0),
                            't2': monthly_data.get('t2', 0),
                            't3': monthly_data.get('t3', 0),
                            't4': monthly_data.get('t4', 0),
                            't5': monthly_data.get('t5', 0),
                            't6': monthly_data.get('t6', 0),
                            't7': monthly_data.get('t7', 0),
                            't8': monthly_data.get('t8', 0),
                            't9': monthly_data.get('t9', 0),
                            't10': monthly_data.get('t10', 0),
                            't11': monthly_data.get('t11', 0),
                            't12': monthly_data.get('t12', 0),
                        }

                        bulk_data.append(record_data)
                    elif code in ['TCBS', 'TKDT']:
                        # Handle TCBS and TKDT codes
                        monthly_data = {}
                        if year in tcbs_tkdt_dict and code in tcbs_tkdt_dict[year]:
                            monthly_data = tcbs_tkdt_dict[year][code]

                        for month in range(1, 13):
                            month_key = f't{month}'
                            if month_key not in monthly_data:
                                monthly_data[month_key] = 0

                        record_data = {
                            'year': year,
                            'sequence': mapping.sequence,
                            'name': mapping.name,
                            'code': mapping.code,
                            'parent': mapping.parent,
                            'parent_2': mapping.parent_2,
                            'parent_2_order': parent_2_order,
                            't1': monthly_data.get('t1', 0),
                            't2': monthly_data.get('t2', 0),
                            't3': monthly_data.get('t3', 0),
                            't4': monthly_data.get('t4', 0),
                            't5': monthly_data.get('t5', 0),
                            't6': monthly_data.get('t6', 0),
                            't7': monthly_data.get('t7', 0),
                            't8': monthly_data.get('t8', 0),
                            't9': monthly_data.get('t9', 0),
                            't10': monthly_data.get('t10', 0),
                            't11': monthly_data.get('t11', 0),
                            't12': monthly_data.get('t12', 0),
                        }

                        bulk_data.append(record_data)
                    elif code in data_dict[year]:
                        monthly_data = data_dict[year][code]

                        for month in range(1, 13):
                            month_key = f't{month}'
                            if month_key not in monthly_data:
                                monthly_data[month_key] = 0

                        # Calculate total and ratio
                        total = sum(monthly_data.values())

                        record_data = {
                            'year': year,
                            'sequence': mapping.sequence,
                            'name': mapping.name,
                            'code': mapping.code,
                            'parent': mapping.parent,
                            'parent_2': mapping.parent_2,
                            'parent_2_order': parent_2_order,
                            't1': monthly_data.get('t1', 0),
                            't2': monthly_data.get('t2', 0),
                            't3': monthly_data.get('t3', 0),
                            't4': monthly_data.get('t4', 0),
                            't5': monthly_data.get('t5', 0),
                            't6': monthly_data.get('t6', 0),
                            't7': monthly_data.get('t7', 0),
                            't8': monthly_data.get('t8', 0),
                            't9': monthly_data.get('t9', 0),
                            't10': monthly_data.get('t10', 0),
                            't11': monthly_data.get('t11', 0),
                            't12': monthly_data.get('t12', 0),
                        }

                        bulk_data.append(record_data)

            if bulk_data:
                # Debug: Print sequence information for TCBS and TKDT
                for record in bulk_data:
                    if record['code'] in ['TCBS', 'TKDT', 'SC']:
                        print(f"Code: {record['code']}, Sequence: {record['sequence']}, Name: {record['name']}")
                
                DetailModel.create(bulk_data)
            else:
                return self._return_notification('Cảnh báo', 'Không có dữ liệu để tạo báo cáo', 'warning')

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base_url}/web#action=account_saving.action_cash_flow_report_detail&model=cash.flow.report.detail&view_type=list"

            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Error in preview method: %s", str(e))
            return self._return_notification('Lỗi', f'Lỗi trong preview: {str(e)}', 'danger')

    def _return_notification(self, title, message, msg_type):
        """Helper method to return notification"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': msg_type,
            }
        }

    @api.model
    def get_custom_aggregate_values(self, model_name, domain, group_by, fields, group_value=None):
        """
        Tính toán aggregate values cho cash flow report
        """
        try:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info("get_custom_aggregate_values called with: model_name=%s, group_by=%s, fields=%s, group_value=%s",
                        model_name, group_by, fields, group_value)
            cash_flow_report_detail = self.env['cash.flow.report.detail']
            for field in fields:
                total = sum(cash_flow_report_detail.search([('parent_2','=','ton_cuoi_ky'),
                                                                        ('name','not in',['Số tất toán trong tháng','Thu lại tiền đầu tư tài chính, tất toán tiết kiệm','Chi tiền gửi tiết kiệm, đầu tư tài chính','TCBS','Tài khoản đầu tư TCBS'])]).mapped(f'{field}'))
                return total


        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Error in get_custom_aggregate_values: %s", str(e))
            return {}