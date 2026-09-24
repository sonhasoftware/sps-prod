# -*- coding: utf-8 -*-
import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Loại dự án -> nhãn hiển thị.
PROJECT_TYPE_LABEL = {
    'service': 'Services',
    'maintainance': 'Maintenance',
    'operation': 'FM',
}


class GroupProjectEfficiencyDetailWizards(models.TransientModel):
    _name = "group.project.efficiency.detail.wizards"
    _description = "Tham số báo cáo hiệu quả dự án chung"

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

    def action_report(self):
        self.ensure_one()
        year = int(self.year)

        # Xóa dữ liệu cũ của phiên hiện tại.
        self.env['group.project.efficiency.detail'].search(
            [('master_key', '=', self.master_key)]).unlink()

        # Chọn SO hoàn thành + ngày hoàn thành theo LOGIC CHUNG với báo cáo
        # thưởng (sale.order._get_completed_orders_with_date) để 2 báo cáo luôn
        # đồng bộ về tập SO và tháng hoàn thành. SQL thô đã bỏ qua record rules.
        rows = self.env['sale.order']._get_completed_orders_with_date(year)
        if not rows:
            raise UserError(_("Hiện không có dự án chung nào đã đóng."))

        completion_by_order = {}
        for r in rows:
            cdate = r['completion_date']
            if isinstance(cdate, str):
                cdate = fields.Date.from_string(cdate)
            completion_by_order[r['sale_order_id']] = cdate

        # sudo: gom đủ dữ liệu (get_group_efficiency, invoice_ids... và các search
        # bên trong) không phụ thuộc quyền đọc của user đang chạy.
        orders = self.env['sale.order'].sudo().browse(list(completion_by_order)).exists()
        detail_vals = []
        for order in orders:
            completion_date = completion_by_order.get(order.id)
            if not completion_date:
                continue

            # Toàn bộ dự án sinh ra từ SO (kể cả đã lưu trữ).
            projects = self.env['project.project'].sudo().with_context(
                active_test=False).search([('x_order_id', '=', order.id)])
            if not projects:
                continue

            rep = projects.filtered(lambda p: not p.main_project)[:1] or projects[:1]

            # Hiệu quả thực tế (doanh thu thực thu, chi phí dự án con) - method dùng chung.
            eff = order.get_group_efficiency()

            # Phân loại: FM/Maintenance có cờ bổ trợ E-FM / R-Maintenace.
            # Chỉ áp cờ khi đúng loại dự án tương ứng.
            project_type = PROJECT_TYPE_LABEL.get(
                rep.x_project_type, rep.x_project_type or '')
            if rep.x_project_type == 'operation' and order.e_fm:
                project_type = 'E-FM'
            elif rep.x_project_type == 'maintainance' and order.r_maintenace:
                project_type = 'R-Maintenace'

            detail_vals.append({
                'master_key': self.master_key,
                'order_id': order.id,
                'so_name': order.name or '',
                'partner_name': order.partner_id.display_name or '',
                'project_name': order.work_content or order.partner_id.display_name or '',
                'key_account': order.user_id.name or '',
                'solution_maker': order.solution_maker.name or '',
                'project_type': project_type,
                'completion_date': completion_date,
                'end_month': '%s - %s' % (completion_date.month, completion_date.year),
                'actual_labor': eff['actual_labor'],
                'actual_materials_and_other_costs': eff['actual_materials_and_other_costs'],
                'total_depreciation_cost': eff['total_depreciation_cost'],
                'iv_fee': eff['iv_fee'],
                'overhead_cost_amount': eff['overhead_cost_amount'],
                'invoice_processing_profit': eff['invoice_processing_profit'],
                'no_invoice_extra_cost': eff['no_invoice_extra_cost'],
                'revenue_received': eff['revenue'],
                'payment_no_invoice': eff['payment_no_invoice'],
                'input_invoice_total': eff['input_invoice_total'],
                'cit_tax_total': eff['cit_tax'],
            })

        if not detail_vals:
            raise UserError(_("Hiện không có dữ liệu cho báo cáo năm %s") % self.year)

        self.env['group.project.efficiency.detail'].create(detail_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Báo cáo hiệu quả dự án chung'),
            'view_mode': 'tree',
            'res_model': 'group.project.efficiency.detail',
            'context': {'year': self.year},
            'view_id': self.env.ref(
                'effective_management.group_project_efficiency_detail_tree').id,
            'search_view_id': self.env.ref(
                'effective_management.group_project_efficiency_detail_search').id,
            'domain': [('master_key', '=', self.master_key)],
            'target': 'main',
        }
