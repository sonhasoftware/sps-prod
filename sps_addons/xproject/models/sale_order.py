# -*- coding: utf-8 -*-
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_project_count = fields.Integer('Số dự án', compute='compute_project_count')
    device = fields.Char('Thiết bị')
    model = fields.Char('Tên, Mã hiệu')
    frequency = fields.Char('Tần suất')

    def action_view_projects(self):
        self.ensure_one()
        projects = self.env['project.project'].search([('x_order_id', '=', self.id),('active','in',(True,False))])
        return {
            'name': _('Các dự án'),
            'view_mode': 'tree,form',
            'domain': [('id', 'in', projects.ids),('active','in',(True,False))],
            'res_model': 'project.project',
            'type': 'ir.actions.act_window',
        }

    def compute_project_count(self):
        project_obj = self.env['project.project']
        for r in self:
            r.x_project_count = project_obj.search_count([('x_order_id', '=', r.id),('active','in',(True,False))])

    def create_project_service(self):
        project_id = self.env['project.project'].create({
            'name': f"{self.name}_SER",
            'label_tasks': self.work_content,
            'x_scope': self.work_content,
            'partner_id': self.partner_id.id,
            'x_address': self.get_order_address(),
            'x_project_type': self.project_type,
            'x_order_id': self.id,
            'x_date_warranty_expire': self.x_date_warranty_expire,
            'x_warranty_period': self.x_warranty_period,
            'x_warranty_period_unit': self.x_warranty_period_unit,
            'x_expertise_ids': self.x_expertise_ids
        })
        project_id.x_onchange_partner_id()
        project_id.compute_estimates()

    def create_project_maintainance(self):
        project_obj = self.env['project.project']
        current_section_id = False
        z = 1
        for line in self.order_line.sorted(key='sequence'):
            if line.display_type == 'line_section':
                current_section_id = line
            if line.display_type is None or line.display_type == 'line_section':
                continue
            if not current_section_id:
                raise UserError(_('Không xác định được hạng mục tổng'))
            frequence_id = line.product_id.product_tmpl_id.x_manage_frequency and line.product_id.product_tmpl_id.x_frequency_id
            if frequence_id and frequence_id.timeline > 0:
                today = date.today()
                date_start = date(today.year, today.month, 1) + relativedelta(months=1)
                date_end = date(today.year, today.month, 1) + relativedelta(months=2, days=-1)
            else:
                date_start, date_end = False, False
            for i in range(1, int(line.product_uom_qty) + 1):
                if date_start and i > 1:
                    number = frequence_id.timeline
                    if frequence_id.type in ['D', 'W']:
                        pass    # Leave this line of code here to remind only, not compute date for those cases
                    if frequence_id.type == 'M':
                        date_start = date(date_start.year, date_start.month, 1) + relativedelta(months=number)
                    if frequence_id.type == 'Y':
                        date_start = date(date_start.year, date_start.month, 1) + relativedelta(years=number)
                    date_end = date(date_start.year, date_start.month, 1) + relativedelta(months=1, days=-1)

                if date_start and date_start.weekday() == 6:
                    date_start += relativedelta(days=1)
                if date_end and date_end.weekday() == 6:
                    date_end -= relativedelta(days=1)
                x = line.product_id.x_frequency_id and line.product_id.x_frequency_id.code or ''
                if x:
                    x = '_' + x

                values = {
                    'name': '%s_%s%s_%s_%s' % (self.name, current_section_id.name, x, i,z),
                    'label_tasks': '%s_%s_%s thứ %s' % (
                        line.product_id.name, current_section_id.name,
                        line.product_id.uom_id.name, i
                    ),
                    'x_scope': self.work_content,
                    'partner_id': self.partner_id.id,
                    'x_address': self.get_order_address(),
                    'x_project_type': self.project_type,
                    'x_order_id': self.id,
                    'x_order_line_id': line.id,
                    'x_date_plan_start': date_start,
                    'x_date_plan_end': date_end,
                    'x_date_warranty_expire': self.x_date_warranty_expire,
                    'x_warranty_period': self.x_warranty_period,
                    'x_warranty_period_unit': self.x_warranty_period_unit,
                    'x_expertise_ids': self.x_expertise_ids
                }
                project_id = project_obj.create(values)
                z+=1
                project_id.x_onchange_partner_id()
                project_id.compute_estimates()

    def create_project_operation(self):
        if self.work_time <= 0:
            raise UserError(_('Chưa khai báo thời gian thực hiện'))

        project_obj = self.env['project.project']
        unit = dict(self._fields['work_time_unit'].selection)[self.work_time_unit].lower()

        today = date.today()
        date_start = date(today.year, today.month, 1) + relativedelta(months=1)
        date_end = date(today.year, today.month, 1) + relativedelta(months=2, days=-1)

        number = int(self.work_time)
        for i in range(1, number + 1):
            if date_start and i > 1:
                if self.work_time_unit == 'month':
                    date_start = date(date_start.year, date_start.month, 1) + relativedelta(months=1)
                elif self.work_time_unit == 'year':
                    date_start = date(date_start.year, date_start.month, 1) + relativedelta(years=1)
                date_end = date(date_start.year, date_start.month, 1) + relativedelta(months=1, days=-1)

            if date_start and date_start.weekday() == 6:
                date_start += relativedelta(days=1)
            if date_end and date_end.weekday() == 6:
                date_end -= relativedelta(days=1)
            values = {
                'name': '%s_%s' % (self.name, i),
                'label_tasks': '%s_%s thứ %s' % (
                    self.work_content,
                    unit,
                    i
                ),
                'x_scope': self.work_content,
                'partner_id': self.partner_id.id,
                'x_address': self.get_order_address(),
                'x_project_type': self.project_type,
                'x_order_id': self.id,
                'x_date_plan_start': date_start,
                'x_date_plan_end': date_end,
                'x_date_warranty_expire': self.x_date_warranty_expire,
                'x_warranty_period': self.x_warranty_period,
                'x_warranty_period_unit': self.x_warranty_period_unit,
                'x_expertise_ids': self.x_expertise_ids
            }
            project_id = project_obj.create(values)
            project_id.x_onchange_partner_id()
            project_id.compute_estimates()

    def create_project_other(self):
        values = {
            'partner_id': self.partner_id.id,
            'x_address': self.get_order_address(),
            'x_order_id': self.id,
            'name': self.name,
            'label_tasks': self.work_content,
            'x_project_type': self.project_type,
            'main_project': True
        }
        project_id = self.env['project.project'].create(values)
        project_id.x_onchange_partner_id()
        # project_id.compute_estimates()

    def get_order_address(self):
        address = []
        if self.location_partner_id.street:
            address.append(self.location_partner_id.street)
        if self.location_partner_id.city:
            address.append(self.location_partner_id.city)
        if self.location_partner_id.state_id:
            address.append(self.location_partner_id.state_id.name)
        if self.location_partner_id.country_id:
            address.append(self.location_partner_id.state_id.name)
        return ', '.join(address)

    def action_update_project_code(self):
        """Đổi tên (rename) các dự án của báo giá theo Số báo giá hiện tại.

        Dùng khi báo giá đổi từ mã tạm sang mã chính thức: các project.project
        sinh lúc xác nhận có tên ghép cứng từ mã báo giá CŨ (vd '{name}_SER',
        '{name}_{i}'…). Nút này thay tiền tố mã cũ bằng mã mới, GIỮ NGUYÊN hậu tố
        cấu trúc — KHÔNG tạo dự án mới. Mọi chứng từ trỏ project theo ID nên tự
        đúng. Idempotent (bấm lại khi mã đã khớp sẽ báo không có gì để cập nhật).
        """
        self.ensure_one()
        Project = self.env['project.project'].with_context(active_test=False)
        projects = Project.search([('x_order_id', '=', self.id)])
        if not projects:
            raise UserError('Báo giá này chưa có dự án nào để cập nhật.')
        main = projects.filtered('main_project')[:1]
        if not main:
            raise UserError('Không xác định được dự án chính (main_project) để lấy mã cũ. '
                            'Vui lòng kiểm tra dữ liệu dự án của báo giá.')
        old_prefix = main.name
        new_prefix = self.name
        if old_prefix == new_prefix:
            raise UserError('Số báo giá chưa thay đổi so với mã dự án hiện tại — không có gì để cập nhật.')
        # Tính tên mới (thay tiền tố), bỏ qua dự án không bắt đầu bằng mã cũ
        rename_map = {}
        for proj in projects:
            if proj.name and proj.name.startswith(old_prefix):
                rename_map[proj] = new_prefix + proj.name[len(old_prefix):]
        # Validate trùng mã với dự án NGOÀI báo giá này
        clash = Project.search([
            ('name', 'in', list(rename_map.values())),
            ('id', 'not in', projects.ids),
        ])
        if clash:
            raise UserError('Mã dự án mới bị trùng với dự án đã tồn tại: %s'
                            % ', '.join(clash.mapped('name')))
        # Đổi tên + refresh snapshot báo cáo hiệu quả (nếu có)
        Detail = self.env['project.efficiency.detail'].sudo()
        for proj, new_name in rename_map.items():
            old_name = proj.name
            proj.name = new_name
            Detail.search([('pp_name_report', '=', old_name)]).write({'pp_name_report': new_name})
        # Cập nhật lại dự toán (giống nút "Cập nhật dự toán" trên từng dự án).
        # Dự án chính (main_project) không tính dự toán — xem create_project_other.
        # Thứ tự BẮT BUỘC: tính dự án chi tiết TRƯỚC, flush xuống DB, RỒI mới tới
        # dự án gộp — compute_estimates() của dự án gộp đọc dự toán các dự án con
        # bằng raw SQL trên project_estimate/material_estimate, nên dự án con phải
        # được ghi xong trước (nếu không dự án gộp đọc trúng số liệu cũ). Vì project
        # _order = "sequence, name, id" nên duyệt thẳng `projects` có thể chạy dự án
        # gộp trước dự án con → sai số.
        to_recompute = projects.filtered(lambda p: not p.main_project)
        detail_projects = to_recompute.filtered(lambda p: not p.is_merge_project)
        merge_projects = to_recompute.filtered('is_merge_project')
        for proj in projects:
            proj.x_onchange_partner_id()
        for proj in detail_projects:
            proj.compute_estimates()
        to_recompute.flush()
        for proj in merge_projects:
            proj.compute_estimates()
        self.message_post(
            body='Đã cập nhật mã dự án cho %s dự án theo Số báo giá <b>%s</b> (từ <b>%s</b>).'
                 % (len(rename_map), new_prefix, old_prefix))
        return True

    def action_confirm(self):
        to_create_project = []
        for r in self:
            if r.state in ['draft', 'sent']:
                to_create_project.append(r.id)
        res = super(SaleOrder, self).action_confirm()
        for r in self:
            if r.id in to_create_project:
                if r.project_type == 'service':
                    r.create_project_service()
                elif r.project_type == 'maintainance':
                    r.create_project_maintainance()
                elif r.project_type == 'operation':
                    r.create_project_operation()

            #  nếu báo giá cho dự án maitainance hoặc facility management thì tạo thêm 1 dự án
            if r.project_type in ('maintainance', 'operation','service'):
                r.create_project_other()
                # Tự động lưu trữ dự án chính sau khi phê duyệt
                main_projects = self.env['project.project'].search([
                    ('x_order_id', '=', r.id),
                    ('main_project', '=', True),
                    ('active', '=', True),
                ])
                if main_projects:
                    main_projects.write({'active': False})

        return res
