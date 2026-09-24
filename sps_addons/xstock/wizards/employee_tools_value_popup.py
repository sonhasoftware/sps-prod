# -*- coding: utf-8 -*-
import datetime as dt

from odoo import api, fields, models, _
from odoo.http import request


class EmployeeToolsValuePopup(models.Model):

    _name = 'employee.tools.value.popup'
    master_key = fields.Integer('Master Key', default=lambda self: self.env.uid)

    year = fields.Selection(
        selection='years_selection',
        string="Năm",
        default=str(dt.datetime.now().year), required=True)

    def years_selection(self):
        y = dt.datetime.now().year
        year_list = []
        while y != 1939:
            year_list.append((str(y), str(y)))
            y -= 1
        return year_list

    def action_report_stock(self):
        # Hybrid approach:
        #   - Tổng giá trị hiện tại: lấy từ stock_borrow_tools (nguồn chính xác)
        #   - Biến động hàng tháng (t1..t12): tính từ stock_move_line
        #   - amount_before = tổng hiện tại - tổng biến động từ đầu năm trở đi
        # Công thức biến động đồng bộ với stock_picking.button_validate:
        #   type_4 (Mượn)       : +qty cho người nhận (x_receiver_id)
        #   type_5 (Chuyển giao) : +qty cho người nhận, -qty cho người bàn giao (x_payer_id)
        #   type_6 (Thu hồi)    : -qty cho người trả khi đúng chiều, +qty khi đảo chiều
        current_year = int(self.year)
        next_year = current_year + 1
        self._cr.execute(
            "DELETE FROM employee_damage_value_report WHERE master_key = %s",
            (self.master_key,))

        sql = f'''
            WITH current_total AS (
                SELECT
                    sbt.receiver_id AS user_id,
                    SUM(sbt.amount * COALESCE(ip.value_float, 0)) AS total_value
                FROM stock_borrow_tools sbt
                LEFT JOIN ir_property ip
                    ON ip.name = 'standard_price'
                   AND ip.res_id = concat('product.product,', sbt.product_id)
                GROUP BY sbt.receiver_id
            ),
            signed_moves AS (
                -- type_4 / type_5 : cộng cho người nhận
                SELECT sp.x_receiver_id AS user_id,
                       sp.date_done::date AS move_date,
                       sml.qty_done * COALESCE(ip.value_float, 0) AS signed_value
                FROM stock_move sm
                JOIN stock_move_line sml ON sm.id = sml.move_id
                JOIN stock_picking sp ON sml.picking_id = sp.id
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN ir_property ip
                    ON ip.name = 'standard_price'
                   AND ip.res_id = concat('product.product,', sml.product_id)
                WHERE sp.state = 'done'
                  AND spt.x_type IN ('type_4', 'type_5')
                  AND sp.x_receiver_id IS NOT NULL
                  AND sp.date_done::date >= '{current_year}-01-01'

                UNION ALL
                -- type_5 / type_6 (đúng chiều mặc định): trừ người bàn giao / người trả
                SELECT sp.x_payer_id,
                       sp.date_done::date,
                       -sml.qty_done * COALESCE(ip.value_float, 0)
                FROM stock_move sm
                JOIN stock_move_line sml ON sm.id = sml.move_id
                JOIN stock_picking sp ON sml.picking_id = sp.id
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN ir_property ip
                    ON ip.name = 'standard_price'
                   AND ip.res_id = concat('product.product,', sml.product_id)
                WHERE sp.state = 'done'
                  AND sp.x_payer_id IS NOT NULL
                  AND sp.date_done::date >= '{current_year}-01-01'
                  AND (spt.x_type = 'type_5'
                       OR (spt.x_type = 'type_6'
                           AND spt.default_location_src_id  = sp.location_id
                           AND spt.default_location_dest_id = sp.location_dest_id))

                UNION ALL
                -- type_6 (đảo chiều src/dest): cộng cho người trả
                SELECT sp.x_payer_id,
                       sp.date_done::date,
                       sml.qty_done * COALESCE(ip.value_float, 0)
                FROM stock_move sm
                JOIN stock_move_line sml ON sm.id = sml.move_id
                JOIN stock_picking sp ON sml.picking_id = sp.id
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN ir_property ip
                    ON ip.name = 'standard_price'
                   AND ip.res_id = concat('product.product,', sml.product_id)
                WHERE sp.state = 'done'
                  AND sp.x_payer_id IS NOT NULL
                  AND sp.date_done::date >= '{current_year}-01-01'
                  AND spt.x_type = 'type_6'
                  AND spt.default_location_src_id  = sp.location_dest_id
                  AND spt.default_location_dest_id = sp.location_id
            ),
            monthly AS (
                SELECT user_id,
                    SUM(signed_value) AS delta_from_year,
                    SUM(CASE WHEN move_date >= '{current_year}-01-01' AND move_date < '{current_year}-02-01' THEN signed_value ELSE 0 END) AS jan,
                    SUM(CASE WHEN move_date >= '{current_year}-02-01' AND move_date < '{current_year}-03-01' THEN signed_value ELSE 0 END) AS feb,
                    SUM(CASE WHEN move_date >= '{current_year}-03-01' AND move_date < '{current_year}-04-01' THEN signed_value ELSE 0 END) AS mar,
                    SUM(CASE WHEN move_date >= '{current_year}-04-01' AND move_date < '{current_year}-05-01' THEN signed_value ELSE 0 END) AS apr,
                    SUM(CASE WHEN move_date >= '{current_year}-05-01' AND move_date < '{current_year}-06-01' THEN signed_value ELSE 0 END) AS may,
                    SUM(CASE WHEN move_date >= '{current_year}-06-01' AND move_date < '{current_year}-07-01' THEN signed_value ELSE 0 END) AS jun,
                    SUM(CASE WHEN move_date >= '{current_year}-07-01' AND move_date < '{current_year}-08-01' THEN signed_value ELSE 0 END) AS jul,
                    SUM(CASE WHEN move_date >= '{current_year}-08-01' AND move_date < '{current_year}-09-01' THEN signed_value ELSE 0 END) AS aug,
                    SUM(CASE WHEN move_date >= '{current_year}-09-01' AND move_date < '{current_year}-10-01' THEN signed_value ELSE 0 END) AS sep,
                    SUM(CASE WHEN move_date >= '{current_year}-10-01' AND move_date < '{current_year}-11-01' THEN signed_value ELSE 0 END) AS oct,
                    SUM(CASE WHEN move_date >= '{current_year}-11-01' AND move_date < '{current_year}-12-01' THEN signed_value ELSE 0 END) AS nov,
                    SUM(CASE WHEN move_date >= '{current_year}-12-01' AND move_date < '{next_year}-01-01'    THEN signed_value ELSE 0 END) AS dec
                FROM signed_moves
                GROUP BY user_id
            )
            SELECT
                ru.login,
                rp.name,
                COALESCE(ct.total_value, 0) - COALESCE(m.delta_from_year, 0) AS amount_before,
                COALESCE(m.jan, 0) AS jan,
                COALESCE(m.feb, 0) AS feb,
                COALESCE(m.mar, 0) AS mar,
                COALESCE(m.apr, 0) AS apr,
                COALESCE(m.may, 0) AS may,
                COALESCE(m.jun, 0) AS jun,
                COALESCE(m.jul, 0) AS jul,
                COALESCE(m.aug, 0) AS aug,
                COALESCE(m.sep, 0) AS sep,
                COALESCE(m.oct, 0) AS oct,
                COALESCE(m.nov, 0) AS nov,
                COALESCE(m.dec, 0) AS dec,
                CASE WHEN ru.active THEN ' ' ELSE 'Nghỉ việc' END AS user_state
            FROM current_total ct
            FULL OUTER JOIN monthly m ON ct.user_id = m.user_id
            JOIN res_users ru ON COALESCE(ct.user_id, m.user_id) = ru.id
            JOIN res_partner rp ON ru.partner_id = rp.id
        '''
        self._cr.execute(sql)
        recs = self._cr.dictfetchall()

        x = 1
        for r in recs:
            self._cr.execute(
                """INSERT INTO employee_damage_value_report
                   (master_key, index, login, name, amount_bf,
                    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, remark)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (self.master_key, x, r['login'], r['name'],
                 r['amount_before'] or 0.0,
                 r['jan'] or 0.0, r['feb'] or 0.0, r['mar'] or 0.0,
                 r['apr'] or 0.0, r['may'] or 0.0, r['jun'] or 0.0,
                 r['jul'] or 0.0, r['aug'] or 0.0, r['sep'] or 0.0,
                 r['oct'] or 0.0, r['nov'] or 0.0, r['dec'] or 0.0,
                 r['user_state'] or 'Null'))
            x += 1

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo giá trị vật tư nhân viên đang quản lý',
            'view_mode': 'tree',
            'res_model': 'employee.damage.value.report',
            'view_id': self.env.ref('xstock.employee_tools_value_report_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'current',
        }
