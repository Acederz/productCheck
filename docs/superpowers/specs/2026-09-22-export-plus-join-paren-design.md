# 导出分类字段：多值用 `+` 拼接 + 区隔去括号

## 背景

导出时分类多值原先用中文逗号 `，` 拼成一格；区隔未走括号清洗。业务要求统一用 `+`，且区隔与类别等一致去括号。

## 范围

- **In**：任务导出、正式库导出；字段：区隔、类别、主材质、辅材质、包装方式、尺寸、卷数、总入数
- **Out**：库内存储不变；大类 / 是否经营不走本清洗；界面展示不改

## 行为

1. 多值连接符：`+`（不再用 `，`）
2. 区隔与类别等共用清洗：去中英文括号及内容；单独 `-` 置空；白名单词整词保留
3. 示例：`XXX(jjj)` → `XXX`；`["A(x)", "B"]` → `A+B`
4. 正式库：先清洗再英文字母大写

## 白名单

位置：`backend/app/utils/export_clean.py` 中 `_PAREN_KEEP_VALUES`。  
当前保留：`免刀撕（点断）`、`免刀撕（单张）` 及对应英文括号写法。需增减时只改该集合。

## 实现落点

- `export_clean.py`：连接符改为 `+`；注释与 `EXPORT_CLEAN_FIELDS`（可含 `category_segment`）同步
- `export_service.py`：区隔改走 `clean_export_classification_value` / `clean_and_upper_classification_value`
- 单测覆盖多值 `+`、区隔去括号、白名单、正式库大写
- `README.md` 导出说明同步
