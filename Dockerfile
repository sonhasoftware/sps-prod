FROM cuongntt/odoo-sps:14.1
COPY --chown=odoo:odoo requirements.txt /
RUN pip install --break-system-packages -r /requirements.txt
COPY --chown=odoo:odoo addons_e/ /mnt/extra-addons/enterprise
COPY --chown=odoo:odoo sps_addons/ /mnt/extra-addons/sps_addons
USER odoo
CMD ["odoo"]