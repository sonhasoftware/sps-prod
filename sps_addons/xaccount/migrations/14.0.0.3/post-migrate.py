# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Backfill project.detail.project_id cho phiếu thanh toán PO (vendor bill).

    Trước đây khi tạo/đối soát thanh toán từ vendor bill, project.detail chỉ được set
    code_project (sale.order) mà bỏ trống project_id (project.project). Invoice line của
    vendor bill nhiều khi thiếu x_project_id, nhưng dòng PO gốc (purchase_order_line) luôn
    có x_project_id — nên lấy project từ đó.

    Quy tắc BẢO THỦ:
      - CHỈ xử lý phiếu thanh toán PO: nguồn project bắt buộc là dòng có purchase_line_id.
      - Bỏ qua tạm ứng / hoàn ứng (đã có luồng riêng điền project_id).
      - Bỏ qua phiếu thu / SO (1 SO nhiều dự án nên không suy được).
      - Chỉ điền khi 1:1 (một code_project ứng đúng một project) + guard nhất quán
        (project.x_order_id = code_project). Trường hợp mơ hồ để trống, KHÔNG đoán.

    Hai nguồn suy: (1) payment tạo trực tiếp từ vendor bill (x_origin_move_id),
    (2) payment gắn qua đối soát (reconcile).
    """
    if not version:
        # Lần đầu cài module -> không có dữ liệu cũ để migrate
        return

    cr.execute("""
        WITH po_lines AS (
            -- Nhánh reconcile: chỉ dòng có purchase_line_id (dòng PO)
            SELECT
                COALESCE(ap.id, ap2.id) AS payment_id,
                COALESCE(aml3.x_sale_project_id, aml4.x_sale_project_id) AS sale_project_id,
                COALESCE(pol3.x_project_id, pol4.x_project_id) AS project_id
            FROM account_partial_reconcile apr
            LEFT JOIN account_move_line aml ON aml.id = apr.debit_move_id
            LEFT JOIN account_payment ap ON ap.id = aml.payment_id
            LEFT JOIN account_move am ON am.id = aml.move_id AND ap.id IS NULL
            LEFT JOIN account_move_line aml3 ON aml3.move_id = am.id
                 AND aml3.exclude_from_invoice_tab IS NOT TRUE AND aml3.credit > 0
            LEFT JOIN purchase_order_line pol3 ON pol3.id = aml3.purchase_line_id
            LEFT JOIN account_move_line aml2 ON aml2.id = apr.credit_move_id
            LEFT JOIN account_payment ap2 ON ap2.id = aml2.payment_id
            LEFT JOIN account_move am2 ON am2.id = aml2.move_id AND ap2.id IS NULL
            LEFT JOIN account_move_line aml4 ON aml4.move_id = am2.id
                 AND aml4.exclude_from_invoice_tab IS NOT TRUE AND aml4.debit > 0
            LEFT JOIN purchase_order_line pol4 ON pol4.id = aml4.purchase_line_id
            WHERE COALESCE(aml3.x_sale_project_id, aml4.x_sale_project_id) IS NOT NULL
              AND COALESCE(pol3.x_project_id, pol4.x_project_id) IS NOT NULL

            UNION ALL

            -- Nhánh origin move: chỉ dòng có purchase_line_id (dòng PO)
            SELECT ap.id, aml.x_sale_project_id, pol.x_project_id
            FROM account_payment ap
            JOIN account_move_line aml
              ON aml.move_id = ap.x_origin_move_id AND aml.exclude_from_invoice_tab IS NOT TRUE
            JOIN purchase_order_line pol ON pol.id = aml.purchase_line_id
            WHERE aml.x_sale_project_id IS NOT NULL AND pol.x_project_id IS NOT NULL
        ),
        resolved AS (
            SELECT payment_id, sale_project_id,
                   MAX(project_id) FILTER (WHERE project_id IS NOT NULL) AS project_id
            FROM po_lines
            GROUP BY payment_id, sale_project_id
            HAVING COUNT(DISTINCT project_id) FILTER (WHERE project_id IS NOT NULL) = 1
        )
        UPDATE project_detail pd
        SET project_id = r.project_id
        FROM resolved r
        JOIN project_project pp ON pp.id = r.project_id
        JOIN account_payment ap ON ap.id = r.payment_id
        WHERE pd.payment_id = r.payment_id
          AND pd.code_project = r.sale_project_id
          AND pd.project_id IS NULL
          AND r.project_id IS NOT NULL
          AND pp.x_order_id = pd.code_project
          AND ap.x_origin_advance_id IS NULL
          AND ap.x_origin_repay_id IS NULL
    """)
    _logger.info(
        "Migration xaccount 14.0.0.3: backfill project.detail.project_id cho %s phiếu thanh toán PO",
        cr.rowcount,
    )
