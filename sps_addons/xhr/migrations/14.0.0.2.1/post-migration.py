# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Gỡ hẳn model work.hours.year (không còn dùng cho khấu hao CCDC).

    Khấu hao CCDC đã quy hết về nền 24h và dùng x_hours_per_year trên product
    làm số giờ dự kiến/năm cho mọi loại cấp phát, nên bảng cấu hình giờ làm
    việc/năm này không còn cần.

    Xoá theo THAM CHIẾU MODEL (không dựa vào xmlid) để dọn sạch cả record mồ
    côi, không phụ thuộc thứ tự cơ chế dọn orphan của Odoo. Idempotent.
    """
    # 1. menu trỏ tới action của model → action → view
    cr.execute("""
        DELETE FROM ir_ui_menu
         WHERE action IN (
            SELECT 'ir.actions.act_window,' || id
              FROM ir_act_window WHERE res_model = 'work.hours.year')
    """)
    cr.execute("DELETE FROM ir_act_window WHERE res_model = 'work.hours.year'")
    cr.execute("DELETE FROM ir_ui_view WHERE model = 'work.hours.year'")

    # 2. bảng dữ liệu
    cr.execute("DROP TABLE IF EXISTS work_hours_year CASCADE")

    # 3. metadata: ir.model (+ ir.model.fields cascade) và mọi ir.model.data sót
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model'
           AND res_id IN (SELECT id FROM ir_model WHERE model = 'work.hours.year')
    """)
    cr.execute("DELETE FROM ir_model WHERE model = 'work.hours.year'")
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'xhr'
           AND name IN ('view_work_hours_year_tree', 'view_work_hours_year_form',
                        'action_work_hours_year', 'menu_work_hours_year',
                        'access_work_hours_year_user', 'access_work_hours_year_hr',
                        'access_work_hours_year_manager')
    """)
    _logger.info('[xhr] Đã gỡ sạch model work.hours.year (khấu hao CCDC quy về 24h).')
