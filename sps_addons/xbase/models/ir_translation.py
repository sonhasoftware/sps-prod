# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.base.models.ir_actions import IrActions as BaseIrActions
from odoo.exceptions import MissingError, AccessError
from collections import defaultdict


class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    def cron_translation_update_src(self):
        sql1 = '''select id 
                    from ir_translation it2 
                    where it2.src <> it2.value and it2.lang = 'vi_VN' and it2.state = 'translated' 
                            and it2.res_id <> 0 and it2.name like '%,name' '''
        self._cr.execute(sql1)
        lists = self._cr.fetchall()
        ids = []
        for l in lists:
            id = l[0]
            ids.append(id)
            trans_obj = self.env['ir.translation'].sudo().browse(id)
            name = trans_obj.name
            if name.find('_') != -1 or name.find('ir') != -1 or name.find('res') != -1 :
                continue
            table_name = name.split(',')[0].replace('.','_')
            fields_name = name.split(',')[1]
            value = trans_obj.value.replace("'","")
            res_id = trans_obj.res_id
            sql2 = f'''update {table_name} set {fields_name} = '{value}' where id = {res_id}'''
            self._cr.execute(sql2)
            sql3 = f'''update ir_translation set src = '{value}' where res_id = {res_id} and lang <> 'vi_VN' and name = '{name}' '''
            self._cr.execute(sql3)
        sql4 = '''update ir_translation 
                    set src = value 
                    where id in %s'''
        self.env.cr.execute(sql4, tuple([tuple(ids + [0, 0])]))

