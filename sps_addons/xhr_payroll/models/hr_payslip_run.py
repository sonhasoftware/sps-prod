import base64
from odoo import models, fields, api, _

class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def create_wage_cost_actual(self):
        for record in self:
            for payslip in record.slip_ids:
                payslip.create_wage_cost_actual()
            # Đơn giá nhân công/ăn ca đổi -> chi phí nhân công theo giờ công
            # (project.member.hour_cost, dùng cho x_cost_real) cũng cần tính lại cho
            # các dự án có chấm công trong kỳ đợt lương này (bình thường chỉ tự tính
            # lại khi chấm công được validate lại, không tự theo đơn giá mới).
            dates = record.slip_ids.mapped('date_from') + record.slip_ids.mapped('date_to')
            if dates:
                entries = self.env['hr.work.entry'].sudo().search([
                    ('x_date', '>=', min(dates)), ('x_date', '<=', max(dates)),
                    ('state', '=', 'validated'),
                ])
                projects = entries.x_line_ids.mapped('project_id') | entries.x_allowance_ids.mapped('project_id')
                projects._load_member_info()

    def action_send_payslip(self):
        report_id = self.env.ref('hr_payroll.action_report_payslip')
        channel_obj = self.env['mail.channel'].sudo()
        for record in self:
            for payslip in record.slip_ids.filtered(lambda x: x.state == 'done'):
                if not payslip.employee_id.user_id:
                    continue
                partner_id = payslip.employee_id.user_id.partner_id
                channel_info = channel_obj.channel_get(partner_id.ids)

                # Kiểm tra attachment đã tồn tại chưa
                existing_attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', 'hr.payslip'),
                    ('res_id', '=', payslip.id),
                    ('mimetype', '=', 'application/x-pdf'),
                ], limit=1)

                if existing_attachment:
                    attachment_id = existing_attachment
                else:
                    report = report_id._render_qweb_pdf(payslip.id)
                    filename = 'Phiếu lương %s %s.pdf' % (payslip.employee_id.name, payslip.date_from.strftime('%m/%Y'))
                    attachment_id = self.env['ir.attachment'].create({
                        'name': filename,
                        'type': 'binary',
                        'datas': base64.b64encode(report[0]),
                        'store_fname': filename,
                        'res_model': 'hr.payslip',
                        'res_id': payslip.id,
                        'mimetype': 'application/x-pdf'
                    })

                channel_obj.browse(channel_info['id']).message_post(
                    body=_('Phiếu lương %s') % payslip.date_from.strftime('%m/%Y'),
                    message_type='comment',
                    subtype_id=self.env.ref('mail.mt_comment').id,
                    attachment_ids=[attachment_id.id]
                )
