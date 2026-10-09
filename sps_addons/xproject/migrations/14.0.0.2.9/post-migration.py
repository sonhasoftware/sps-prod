# -*- coding: utf-8 -*-
"""Đồng bộ cờ 'Xuất báo cáo dự án' cho dữ liệu cũ.

Quy tắc mới: dự án THƯỜNG -> tích (True); dự án GỘP (is_merge_project) hoặc
dự án CHÍNH (main_project) -> KHÔNG tích (False). Trước đây trường mặc định
True cho MỌI dự án nên các dự án gộp/chính cũ có thể đang bị tích, gây xuất
trùng báo cáo. Migration này bỏ tích cho các dự án đó.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE project_project
        SET is_export_project_efficiency_detail = FALSE
        WHERE (is_merge_project IS TRUE OR main_project IS TRUE)
          AND is_export_project_efficiency_detail IS TRUE
    """)
    _logger.info(
        "xproject: đã bỏ tích 'Xuất báo cáo dự án' cho %s dự án gộp/chính.",
        cr.rowcount,
    )
