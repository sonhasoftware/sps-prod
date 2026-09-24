def migrate(cr, version):
    cr.execute(
        """
ALTER TABLE sale_project_line DROP CONSTRAINT IF EXISTS sale_project_line_total_markup_100;
        """
    )
