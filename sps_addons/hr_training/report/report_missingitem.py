from odoo import api, fields, models, tools


class ReportMissingItem(models.Model):
    _name = 'report.missing.item'
    _auto = False

    name = fields.Char()
    x_code = fields.Char()
    job_title = fields.Char()
    basic_item = fields.Integer()
    item_done = fields.Integer()
    missing_item = fields.Integer()

    @api.model
    def init(self):
        """ Event main report """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute(""" CREATE VIEW {table} AS (
            with detail_data as 
        (select 
            he.x_code as ma_nhan_vien,
            he.name as ten_nhan_vien,
            hd.name as phong_ban,
            hj.name as chuc_danh, 
            hti.name as hang_muc_dao_tao,
            htc.name as phan_loai,
            htir.result_require as yeu_cau_ket_qua,
            htr1.training_date as ngay_dao_tao,
            he2.name as nguoi_dao_tao,
            htr1.document_name as ten_va_nguon_giao_trinh,
            htr1.result1 as ket_qua_dao_tao
        from hr_employee he
        left join hr_training_item_require htir on htir.job_id = he.job_id
        left join hr_job hj on hj.id = he.job_id
        left join hr_department hd on hd.id = he.department_id
        left join hr_training_item hti on hti.id = htir.item_id
        left join hr_training_categ htc on htc.id = hti.categ_id
        left join 
                (select 
                    htr.trainee_id,
                    htrl.training_item_id,
                    max(htrl.trainer_id) trainer_id,
                    max(htrl.document_name) document_name,
                    max(htr.date) as training_date,
                    max(htrl.result) as result1
                from hr_training_result htr
                left join hr_training_result_line htrl on htrl.master_id = htr.id
                where htrl.result is not null and htrl.result != '0'
                group by 	htr.trainee_id,htrl.training_item_id
                ) htr1 
            on htr1.trainee_id = he.id and htr1.training_item_id = hti.id
        left join hr_employee he2 on he2.id = htr1.trainer_id
        where he.active = true)
        
        select 
        	row_number() OVER () AS id,
            ddx.ten_nhan_vien as name,
            ddx.ma_nhan_vien x_code,
            ddx.chuc_danh job_title,
            (	select count(distinct dd3.hang_muc_dao_tao) 
                from detail_data dd3
                where dd3.ten_nhan_vien = ddx.ten_nhan_vien and dd3.ma_nhan_vien = ddx.ma_nhan_vien and dd3.chuc_danh = ddx.chuc_danh
            ) as basic_item,
            (	select count(distinct dd1.hang_muc_dao_tao) 
                from detail_data dd1 
                where dd1.ngay_dao_tao is not null 
                    and dd1.ten_nhan_vien = ddx.ten_nhan_vien and dd1.ma_nhan_vien = ddx.ma_nhan_vien and dd1.chuc_danh = ddx.chuc_danh
            ) as item_done,
            (	select count(distinct dd2.hang_muc_dao_tao) 
                from detail_data dd2
                where dd2.ngay_dao_tao is null 
                    and dd2.ten_nhan_vien = ddx.ten_nhan_vien and dd2.ma_nhan_vien = ddx.ma_nhan_vien and dd2.chuc_danh = ddx.chuc_danh
            ) as missing_item
        from 
            (select distinct dd.ten_nhan_vien,dd.ma_nhan_vien,dd.chuc_danh from detail_data dd) ddx
        )""".format(table=self._table))



