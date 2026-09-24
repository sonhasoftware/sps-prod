# -*- coding: utf-8 -*-
import datetime as dt
from odoo import fields, models


class ProjectRewardDetailWizards(models.TransientModel):
    _name = "project.reward.detail.wizards"
    _description = "Nhập tham số bảng thống kê chi tiết thưởng"

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
        # Tái dùng đúng logic sinh dữ liệu của báo cáo hiệu quả dự án:
        # tạo project.efficiency.detail + project.efficiency.reward.line cho năm
        # (cùng master_key = uid), sau đó mở danh sách reward line dạng phẳng.
        gen = self.env['project.efficiency.detail.wizards'].create({'year': self.year})
        gen.action_report()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bảng thống kê chi tiết thưởng',
            'view_mode': 'tree',
            'res_model': 'project.efficiency.reward.line',
            'view_id': self.env.ref('effective_management.project_reward_detail_tree').id,
            'domain': [('master_key', '=', self.master_key)],
            'context': {'year': self.year},
            'target': 'main',
        }
