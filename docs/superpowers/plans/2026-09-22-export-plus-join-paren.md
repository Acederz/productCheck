# Plan: 导出多值 `+` + 区隔去括号

把导出分类多值连接符改为 `+`，并让区隔走与类别相同的括号/`-` 清洗。

## Scope

- In: `export_clean.py`、`export_service.py`、单测、README 导出说明
- Out: 库表、前端展示、大类字段

## Action items

[x] 新增 `backend/tests/test_export_clean.py`：多值 `+`、去括号、白名单、区隔 list
[x] 改 `clean_export_classification_value` / `upper_classification_text` 连接符为 `+`
[x] `export_service` 区隔改走清洗函数；更新模块注释与 `EXPORT_CLEAN_FIELDS`
[x] 跑相关 pytest（16 passed）
[x] 更新 README 导出一行说明
