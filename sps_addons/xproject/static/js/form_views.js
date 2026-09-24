odoo.define('xproject/static/js/form_views.js', function (require) {
"use strict";

const FormRenderer = require('web.FormRenderer');
FormRenderer.include({
    async _render() {
        await this._super(...arguments);
        var count = 0;
        function x() {
            setTimeout(function(){
                if (count < 120) {
                    var ele = $('.o_ChatterTopbar_buttonAttachments');
                    var element = $('.o_Chatter_attachmentBox');
                    if (!ele.length) {
                        x();
                    }
                    else {
                        if (!element.length){
                            ele.click();
                        }
                    }
                }
            }, 250);
            count +=1;
        }
        x();
    },
});
});


