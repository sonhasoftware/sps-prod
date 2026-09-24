# -*- coding: utf-8 -*-
from datetime import date, datetime
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Request(models.Model):
    _name = 'sale.request'
    _description = 'Yêu cầu từ khách hàng'
    _inherit = ['mail.thread']

    name = fields.Char('Số yêu cầu', default=lambda self: self.env['ir.sequence'].next_by_code('xproject.sale_request_name'))
    date = fields.Date('Ngày yêu cầu', required=1, tracking=1)
    partner_id = fields.Many2one('res.partner', 'Khách hàng', domain=[('type', '=', 'contact')], required=1, tracking=1)
    content = fields.Char('Nội dung yêu cầu', tracking=1)
    type = fields.Selection([
        ('maintainance', 'Maintenance'),
        ('service', 'Services'),
        ('operation', 'Facility Management'),
    ], 'Phân loại', default='maintainance', required=1, tracking=1)
    note = fields.Char('Ghi chú')
    state = fields.Selection([
        ('new', 'Mới'),
        ('quotation', 'Đã tạo báo giá'),
        ('cancel', 'Đã huỷ'),
    ], 'Trạng thái', default='new', copy=0, readonly=1, required=1, tracking=1)
    orders = fields.Many2many('sale.order', 'sale_order_request_rel', 'request_id', 'order_id', 'Các báo giá', copy=0)
    count_quotation = fields.Integer('Số lượng báo giá', compute='compute_nonstore_data')
    count_project = fields.Integer('Số lượng dự án', compute='compute_nonstore_data')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.env['ir.sequence'].next_by_code('xproject.sale_request_name')
        return super(Request, self).copy(default)

    def get_projects(self):
        return self.env['project.project'].search([
            ('x_order_id', 'in', self.orders.ids)
        ])

    def compute_nonstore_data(self):
        for r in self:
            r.count_quotation = len(r.orders)
            projects = r.get_projects()
            r.count_project = len(projects)

    def button_create_quotation(self):
        self.ensure_one()
        self.state = 'quotation'
        order_id = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.now(),
            'project_type': self.type,
            'work_note': self.note,
            'work_content': self.content,
            'origin': self.name,
        })
        self.orders = [(4, order_id.id)]
        return self.button_view_quotation()

    def button_cancel(self):
        self.ensure_one()
        if self.state == 'new':
            self.state = 'cancel'

    def button_view_quotation(self):
        return {
            'name': _('Các báo giá'),
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.orders.ids)],
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [[self.env.ref('sale.view_quotation_tree').id, "tree"], [False, "form"]],
        }

    def button_view_project(self):
        projects = self.get_projects()
        return {
            'name': _('Các báo giá'),
            'view_mode': 'tree,form',
            'domain': [('id', 'in', projects.ids)],
            'res_model': 'project.project',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def default_get(self, fields_list):
        res = super(Request, self).default_get(fields_list)
        res['date'] = date.today()
        return res

    def unlink(self):
        if any(x for x in self):
            raise UserError(_('Anh/chị không được xoá phiếu đã tạo báo giá hoặc đã huỷ'))
        return super(Request, self).unlink()
