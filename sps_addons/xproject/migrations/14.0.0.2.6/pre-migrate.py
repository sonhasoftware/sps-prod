# -*- coding: utf-8 -*-
"""Gỡ bỏ hoàn toàn model project.damage.line (thay bằng tính LIVE trực tiếp
từ stock_move_line trên project.x_damage_cost_total/x_damage_line_display,
không còn bảng riêng).

Chạy TRƯỚC khi module nạp lại registry — cần dọn sạch ir.model.fields.selection/
ir.model.fields/ir.model.access/ir.model.data của model này trước, nếu không
bước tự phản chiếu (reflect) field Selection của Odoo sẽ crash với
KeyError('project.damage.line') vì cố tra cứu 1 model không còn được đăng ký
trong Python nhưng vẫn còn dữ liệu tham chiếu tới nó trong DB.
"""


def migrate(cr, version):
    cr.execute("""
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT id FROM ir_model_fields WHERE model = 'project.damage.line'
        )
    """)
    cr.execute("DELETE FROM ir_model_fields WHERE model = 'project.damage.line'")
    cr.execute("""
        DELETE FROM ir_model_access
        WHERE model_id IN (SELECT id FROM ir_model WHERE model = 'project.damage.line')
    """)
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE (model = 'ir.model.fields' AND res_id IN (
                   SELECT id FROM ir_model_fields WHERE model = 'project.damage.line'))
           OR (model = 'ir.model.access' AND res_id IN (
                   SELECT id FROM ir_model_access WHERE model_id IN (
                       SELECT id FROM ir_model WHERE model = 'project.damage.line')))
           OR (model = 'ir.model' AND res_id IN (
                   SELECT id FROM ir_model WHERE model = 'project.damage.line'))
    """)
    cr.execute("DELETE FROM ir_model WHERE model = 'project.damage.line'")
    cr.execute("DROP TABLE IF EXISTS project_damage_line")
