# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Set project_state='Done' cho phiếu tạm ứng/đặt cọc đã posted.

    Chỉ áp dụng cho payment gắn đơn bán (x_origin_so_id IS NOT NULL) — đúng phạm vi
    báo cáo turn over dùng project_state. payment.state là related tới move_id.state,
    nên 'posted' = move tương ứng đã posted. Dùng raw SQL để chạy 1 phát.
    """
    if not version:
        # Lần đầu cài module (chưa có dữ liệu cũ) -> không cần migrate
        return

    cr.execute("""
        UPDATE account_payment p
        SET project_state = 'Done'
        FROM account_move m
        WHERE m.id = p.move_id
          AND m.state = 'posted'
          AND p.x_origin_so_id IS NOT NULL
          AND p.project_state IS DISTINCT FROM 'Done'
    """)
    _logger.info(
        "Migration xaccount 14.0.0.2: set project_state='Done' cho %s payment posted",
        cr.rowcount,
    )
