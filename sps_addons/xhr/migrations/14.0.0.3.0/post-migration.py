# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Gộp phụ cấp ăn trưa + nhà ở thành KPI định mức (kpi_norm).

    Từ 01/07/2026 bảng lương mới dùng 1 trường "KPI định mức" thay cho 2 phụ cấp
    x_allowance_lunch (ăn trưa) và x_allowance_home (nhà ở). Cột kpi_norm đã được
    ORM tạo trước khi post-migration chạy; ở đây chỉ nạp giá trị = tổng 2 cột cũ.

    GIỮ NGUYÊN 2 cột cũ trong DB (chỉ ẩn khỏi view) để an toàn dữ liệu và phục vụ
    đối chiếu/lịch sử thuế. Chỉ nạp cho các bản ghi kpi_norm còn trống để idempotent
    (chạy lại không đè giá trị đã nhập tay).
    """
    cr.execute("""
        UPDATE hr_contract
           SET kpi_norm = COALESCE(x_allowance_lunch, 0) + COALESCE(x_allowance_home, 0)
         WHERE COALESCE(kpi_norm, 0) = 0
           AND (COALESCE(x_allowance_lunch, 0) + COALESCE(x_allowance_home, 0)) <> 0
    """)
    _logger.info('[xhr] Đã gộp ăn trưa + nhà ở -> kpi_norm cho %s hợp đồng.', cr.rowcount)
