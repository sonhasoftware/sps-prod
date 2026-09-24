
import datetime as dt

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleclosedIncentiveWizards(models.TransientModel):
    _name = "sale.closed.incentive.wizards"
    _description = "Thống kê hợp đồng đã ký"

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

    def get_so_completion_with_budget(self, year=None):
        """
        Trả về list:
        [
            {
                'sale_order_id': 123,
                'sale_order_name': 'SO000123',
                'completion_date': datetime.date(...),
                'efficiency_total': 12345.0,
            },
            ...
        ]
        Chỉ bao gồm các SO mà TẤT CẢ project của nó đều đã hoàn thành.
        Việc chọn SO + tính ngày hoàn thành dùng CHUNG với báo cáo hiệu quả dự
        án chung qua sale.order._get_completed_orders_with_date().
        """
        if not year:
            year = fields.Date.today().year

        rows = self.env['sale.order']._get_completed_orders_with_date(year)
        if not rows:
            return []

        # Gắn GIÁ TRỊ TÍNH THƯỞNG = Hiệu quả dự án SAU THUẾ (TNDN+TNCN) cho
        # từng SO - dùng method chung get_group_efficiency()['incentive_base']
        # trên sale.order (đồng bộ với cột "Hiệu quả dự án sau thuế" của báo
        # cáo hiệu quả dự án chung).
        order_ids = [r['sale_order_id'] for r in rows]
        orders = self.env['sale.order'].sudo().browse(order_ids).exists()
        eff_by_order = {order.id: order.get_group_efficiency()['incentive_base'] for order in orders}

        for row in rows:
            row['efficiency_total'] = eff_by_order.get(row['sale_order_id'], 0.0)
        return rows

    def _get_employee_display_name(self, user):
        if not user:
            return "Không có dữ liệu"
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if employee:
            if employee.department_id and employee.department_id.id == 4:
                return "BOD"
            return employee.name
        return user.name or user.partner_id.name or "Không có dữ liệu"

    def action_report(self):
        from collections import defaultdict

        self.ensure_one()
        current_year = int(self.year or fields.Date.today().year)
        current_year_str = str(current_year)
        sale_order_data = self.get_so_completion_with_budget(year=current_year)
        if not sale_order_data:
            raise UserError(_("Hiện không có dữ liệu cho báo cáo"))

        sale_order_ids = {rec.get('sale_order_id') for rec in sale_order_data if rec.get('sale_order_id')}
        sale_orders = self.env['sale.order'].sudo().browse(list(sale_order_ids)).exists()
        order_map = {order.id: order for order in sale_orders}

        months = [f't{i}' for i in range(1, 13)]

        def empty_month_dict():
            return {m: 0.0 for m in months}

        # Tỉ lệ thưởng theo loại HĐ: (key_account, solution_maker).
        # FM (operation) tính CÙNG NHÓM Maintenance = 10%/5%; Services = 6%/4%.
        RATE = {
            'service': (0.06, 0.04),
            'maintainance': (0.10, 0.05),
            'operation': (0.10, 0.05),
        }
        type_labels = {
            'operation': 'Tổng lợi nhuận HĐ quản lý vận hành mới',
            'maintainance': 'Tổng lợi nhuận HĐ bảo trì mới',
            'service': 'Tổng lợi nhuận HĐ dịch vụ',
        }
        reward_suffix = 'Giá trị thưởng dự kiến'

        def init_profit():
            # Hiệu quả sau thuế CỘNG ĐẠI SỐ (gồm cả lỗ) theo loại HĐ, theo tháng.
            return {ptype: empty_month_dict() for ptype in RATE}

        key_profit = defaultdict(init_profit)       # key_profit[emp][ptype][tN]
        solution_profit = defaultdict(init_profit)  # solution_profit[emp][ptype][tN]

        for record in sale_order_data:
            so = order_map.get(record.get('sale_order_id'))
            completion_date = record.get('completion_date')
            if isinstance(completion_date, str):
                completion_date = fields.Date.from_string(completion_date)
            efficiency = float(record.get('efficiency_total') or 0.0)
            # KHÔNG loại dự án lỗ (efficiency < 0): cần cộng đại số lãi/lỗ.
            if not so or not completion_date or completion_date.year != current_year:
                continue
            if so.r_maintenace or so.e_fm:
                continue
            project_type = (so.project_type or '').lower()
            if project_type not in RATE:
                continue

            month_key = f"t{completion_date.month}"
            key_display = self._get_employee_display_name(so.user_id)
            solution_display = self._get_employee_display_name(so.solution_maker)
            if key_display and key_display != "BOD":
                key_profit[key_display][project_type][month_key] += efficiency
            if solution_display and solution_display != "BOD":
                solution_profit[solution_display][project_type][month_key] += efficiency

        # Tính thưởng từ hiệu quả CỘNG ĐẠI SỐ theo từng loại HĐ:
        #  - Cột từng tháng: net_tháng của loại, > 0 thì × tỉ lệ, ≤ 0 thì 0.
        #  - Cột Total: net CẢ NĂM của loại, > 0 thì × tỉ lệ, ≤ 0 thì 0.
        #    (Total KHÁC tổng 12 tháng vì các tháng lỗ đã bị chặn về 0.)
        def reward_from_profit(profit_by_type, role):
            reward = empty_month_dict()
            total = 0.0
            for ptype, vals in profit_by_type.items():
                rate = RATE[ptype][role]
                year_net = 0.0
                for m in months:
                    net = vals[m]
                    year_net += net
                    if net > 0:
                        reward[m] += net * rate
                if year_net > 0:
                    total += year_net * rate
            return reward, total

        key_reward = {emp: reward_from_profit(p, 0) for emp, p in key_profit.items()}
        solution_reward = {emp: reward_from_profit(p, 1) for emp, p in solution_profit.items()}

        def has_month_values(d):
            return any(d[m] for m in months)

        def profit_has_values(profit_by_type):
            return any(has_month_values(profit_by_type[p]) for p in profit_by_type)

        def profit_year_net(vals):
            # Total dòng "Tổng lợi nhuận" = net cả năm (cộng đại số, có thể âm).
            return sum(vals[m] for m in months)

        def sum_months(dicts):
            res = empty_month_dict()
            for d in dicts:
                for m in months:
                    res[m] += d[m]
            return res

        key_has = any(profit_has_values(key_profit[e]) for e in key_profit)
        sol_has = any(profit_has_values(solution_profit[e]) for e in solution_profit)
        if not key_has and not sol_has:
            raise UserError(_("Hiện không có dữ liệu cho báo cáo"))

        self._cr.execute("DELETE FROM sale_closed_incentive WHERE master_key = %s", (self.master_key,))

        def insert_line(classification, values, total):
            row = [round(values.get(m, 0.0) or 0.0, 0) for m in months]
            self._cr.execute(
                "INSERT INTO sale_closed_incentive (year, master_key, classification, "
                "t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12, total) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (self.year, self.master_key, classification, *row, round(total or 0.0, 0)),
            )

        def write_section(header, prefix, profit_map, reward_map):
            section_months = sum_months([reward_map[e][0] for e in reward_map]) if reward_map else empty_month_dict()
            section_total = sum(reward_map[e][1] for e in reward_map)
            insert_line(header, section_months, section_total)
            for emp in sorted(profit_map.keys()):
                profit_by_type = profit_map[emp]
                for ptype in ('operation', 'maintainance', 'service'):
                    vals = profit_by_type[ptype]
                    if has_month_values(vals):
                        insert_line('%s%s_%s' % (prefix, emp, type_labels[ptype]), vals, profit_year_net(vals))
                reward_months, reward_total = reward_map[emp]
                if has_month_values(reward_months) or reward_total:
                    insert_line('%s%s_%s' % (prefix, emp, reward_suffix), reward_months, reward_total)

        if key_has:
            write_section('A. KEY ACCOUNTS', '...', key_profit, key_reward)
        if sol_has:
            write_section('B. SOLUTION MAKER', '......', solution_profit, solution_reward)

        # C. ESTIMATED GROSS INCENTIVE = tổng thưởng (Key + Solution) theo người.
        people = set(key_reward) | set(solution_reward)
        gross_by_person = {}
        for p in people:
            km, kt = key_reward.get(p, (empty_month_dict(), 0.0))
            sm, st = solution_reward.get(p, (empty_month_dict(), 0.0))
            gm = empty_month_dict()
            for m in months:
                gm[m] = km[m] + sm[m]
            gross_by_person[p] = (gm, kt + st)
        if gross_by_person:
            gross_months = sum_months([gross_by_person[p][0] for p in gross_by_person])
            gross_total = sum(gross_by_person[p][1] for p in gross_by_person)
            if has_month_values(gross_months) or gross_total:
                insert_line('C. ESTIMATED GROSS INCENTIVE', gross_months, gross_total)
                for p in sorted(gross_by_person):
                    gm, gt = gross_by_person[p]
                    if has_month_values(gm) or gt:
                        insert_line('......' + p, gm, gt)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo thống kê các dự án đã hoàn thành',
            'view_mode': 'tree',
            'res_model': 'sale.closed.incentive',
            'context': {'year': current_year_str},
            'view_id': self.env.ref('effective_management.sale_closed_incentive_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',
        }
