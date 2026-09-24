# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- Odoo 14 Enterprise
- Python 3.8
- PostgreSQL 12

The `odoo/` and `addons/` directories are vendored Odoo 14 core/community source; `addons_e/` is the Odoo 14 Enterprise source. Treat all three as read-only references — production changes go in `sps_addons/`.

## Custom code lives in `sps_addons/`

All project-owned modules are under `sps_addons/`. Custom modules are authored by "THG" and many use Vietnamese for user-facing strings, field labels, menus, and commit messages — match this convention when adding code.

Naming convention:
- `x*` modules (`xbase`, `xaccount`, `xhr`, `xhr_payroll`, `xhr_recruitment`, `xstock`, `xpurchase`, `xproject`) are project-specific customizations layered on top of stock Odoo modules with the corresponding name.
- `xbase` has `'auto_install': True` — it loads whenever `web`, `mail`, `base` are present, so changes there affect every database.
- Non-`x*` modules (`account_advanced`, `account_saving`, `effective_management`, `hr_training`, `sps_sale_target`, `num2currency`, `report_xlsx`, `auto_backup`, `backup_upload_google_drive`) are standalone features.

Dependency graph hot spots: `xaccount` depends on `account_advanced`, `sps_sale_target`, `xproject`, plus enterprise `account_accountant` and `account_reports`. `xstock` depends on `xproject` and `sps_sale_target`. When editing a base module, check downstream `x*` modules for overrides before changing field semantics.

## Build & deploy (GitLab CI)

CI is driven entirely by `.gitlab-ci.yml`. There is no local lint/test harness configured.

- Branch `production_hot_fix` → builds `cuongntt/odoo-sps:14-<sha>` and updates the prod k8s manifest in `git.bms-group/app-odoo/odoo-manifest`. **This is the current branch — pushes here ship to production.** Main branch for PRs is `production`.
- Branch `stage` → builds `cuongntt/odoo-sps-stage:14-<sha>` and updates the stage manifest in `bms-stage-env/k8s-stage`.
- Pipelines only run when triggered via the GitLab web UI (`$CI_PIPELINE_SOURCE == "web"`).

The Dockerfile starts from `cuongntt/odoo-sps:14.1` (a prebuilt base containing odoo core), then copies `addons_e/` to `/mnt/extra-addons/enterprise` and `sps_addons/` to `/mnt/extra-addons/sps_addons`. The vendored `addons/` and `odoo/` directories are **not** copied — they're for local inspection only; the deployed Odoo core comes from the base image.

## Running locally

`odoo-bin` is the standard Odoo entrypoint (`python3 odoo-bin -c <config> -d <db> -u <module>`). There is no project-provided config or seed data; databases must be supplied externally. `psql *` is pre-allowed in `.claude/settings.local.json` for direct DB inspection.

To update a single module after editing it, restart Odoo with `-u <module_name>` (e.g. `-u xaccount`). Module installs/upgrades require the database to be unused by other workers.
