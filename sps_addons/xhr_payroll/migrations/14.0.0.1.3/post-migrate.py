# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Khởi tạo cờ count_in_unit_price cho các phân loại thu nhập (bonus)
    đang được tính vào đơn giá nhân công TRƯỚC khi chuyển sang cơ chế checkbox.

    Trước đây đơn giá nhân công chỉ cộng 2 khoản, lọc cứng theo name/code:
      - 'Thưởng nhân viên xuất sắc' / code 'TNVXS'
      - 'Phụ cấp kiêm nhiệm'        / code 'PCKN'
    Set count_in_unit_price = true cho đúng 2 nhóm này để số liệu đơn giá +
    cột "Thưởng NVXS" trên báo cáo lương giữ nguyên sau khi nâng cấp.
    """
    cr.execute("""
        UPDATE hr_payroll_other_category
        SET count_in_unit_price = true
        WHERE type = 'bonus'
          AND (
              code = 'TNVXS'
              OR code = 'PCKN'
              OR name = 'Thưởng nhân viên xuất sắc'
              OR name = 'Phụ cấp kiêm nhiệm'
          )
    """)
    _logger.info(
        "xhr_payroll: set count_in_unit_price=true cho %s phân loại bonus",
        cr.rowcount,
    )
