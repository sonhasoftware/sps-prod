odoo.define('xaccount.widgets', function (require) {
"use strict";

var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');
var FieldMany2ManyTags = relational_fields.FieldMany2ManyTags;

var FormFieldMany2ManyTag = FieldMany2ManyTags.extend({
    _addTag: function (data) {
        if (!_.contains(this.value.res_ids, data.id)) {
            return this._setValue({
                operation: 'REPLACE_WITH',
                ids: [data.id]
            });
        }
        return Promise.resolve();
    },
});

field_registry.add('many2many_tag_once', FormFieldMany2ManyTag);
});
