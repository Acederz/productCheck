# 允许操作员修改密码开关 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 系统设置增加「允许操作员修改密码」开关；默认禁止；关闭时隐藏入口并拒绝改密 API。

**Architecture:** 复用 `SystemConfig`（键 `operator_change_password_enabled`，默认 `false`）。设置页读写与导出开关同模式；`change-password` 强制校验；`/me` 与登录 `user` 合并布尔字段供操作员 Layout `v-if` + `fetchMe`。

**Tech Stack:** Flask、Vue 3、Element Plus、unittest

## Global Constraints

- 规格：`docs/superpowers/specs/2026-09-04-operator-change-password-switch-design.md`
- 配置键：`operator_change_password_enabled`，值 `'true'` / `'false'`，缺省按禁止
- 403 文案：`管理员未开放修改密码`
- `/me` 与登录 `user` 字段：`operator_change_password_enabled: boolean`
- 管理员重置密码不受影响
- 中文注释；SOLID / DRY / KISS
- **不自动 git commit**（除非用户明确要求）
- 与分支 `feature/review-export-filters` 同分支改动，最终一起上传

## Files

- Modify: `backend/app/utils/init_db.py` — 默认插入配置
- Modify: `backend/app/utils/log_display.py` — 中文名
- Modify: `backend/app/api/auth.py` — `/me`、login、`change-password` 校验；读取配置辅助
- Modify: `backend/tests/test_change_password.py` — 默认关时成功用例需先开开关；新增关/开用例与 `/me` 字段
- Create: `backend/tests/test_change_password_switch.py`（可选：若改密测文件过大可拆；本计划优先扩写 `test_change_password.py`）
- Modify: `frontend/src/views/admin/SettingsPage.vue`
- Modify: `frontend/src/views/operator/Layout.vue`
- Modify: `README.md`

---

### Task 1: 后端配置 + 改密门禁 + /me 字段（TDD）

**Files:**
- Modify: `backend/tests/test_change_password.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/utils/init_db.py`
- Modify: `backend/app/utils/log_display.py`

**Interfaces:**
- Consumes: `SystemConfig`、`User.to_dict()`、`write_operation_log`
- Produces:
  - `is_operator_change_password_enabled() -> bool`（可放在 `auth.py` 模块级私有函数）
  - `enrich_user_dict(user) -> dict`：在 `to_dict()` 上附加 `operator_change_password_enabled`
  - `POST /api/auth/change-password` 在操作员校验后检查开关
  - `GET /api/auth/me`、`POST /api/auth/login` 返回带标志的 user

- [ ] **Step 1: 调整/扩展失败测试**

在 `backend/tests/test_change_password.py`：

1. 增加辅助方法：

```python
from app.models.user import SystemConfig

def _set_change_pwd_enabled(self, enabled: bool):
    key = "operator_change_password_enabled"
    row = SystemConfig.query.filter_by(config_key=key).first()
    if not row:
        row = SystemConfig(config_key=key, config_value="true" if enabled else "false")
        db.session.add(row)
    else:
        row.config_value = "true" if enabled else "false"
    db.session.commit()
```

2. `setUp` 末尾默认 `_set_change_pwd_enabled(False)`（对齐产品默认禁止）。
3. **现有** `test_operator_success` 及所有期望改密成功的用例，在 `_post` 前调用 `_set_change_pwd_enabled(True)`。
4. 新增：

```python
def test_disabled_returns_403(self):
    self._set_change_pwd_enabled(False)
    resp = self._post(
        self._op_headers(),
        {
            "old_password": self._OLD,
            "new_password": self._NEW,
            "confirm_password": self._NEW,
        },
    )
    self.assertEqual(resp.status_code, 403)
    body = json.loads(resp.data)
    self.assertIn("未开放", body.get("message", ""))
    op = User.query.get(self.op_id)
    self.assertTrue(op.check_password(self._OLD))

def test_me_includes_flag_false(self):
    self._set_change_pwd_enabled(False)
    resp = self.client.get("/api/auth/me", headers=self._op_headers())
    self.assertEqual(resp.status_code, 200)
    body = json.loads(resp.data)
    self.assertFalse(body["data"]["operator_change_password_enabled"])

def test_me_includes_flag_true(self):
    self._set_change_pwd_enabled(True)
    resp = self.client.get("/api/auth/me", headers=self._op_headers())
    self.assertEqual(resp.status_code, 200)
    body = json.loads(resp.data)
    self.assertTrue(body["data"]["operator_change_password_enabled"])
```

- [ ] **Step 2: 跑测确认失败**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_change_password -v
```

Expected: 新增用例 FAIL（缺字段或未拦截）；原成功用例在默认关时也会 FAIL，直到实现完成并在成功路径前开开关。

- [ ] **Step 3: 实现**

`auth.py` 增加（含中文注释）：

```python
def _is_operator_change_password_enabled() -> bool:
    """读取系统配置：仅当值为 'true' 时允许操作员自助改密。"""
    from app.models.user import SystemConfig
    row = SystemConfig.query.filter_by(
        config_key="operator_change_password_enabled"
    ).first()
    return bool(row and row.config_value == "true")


def _user_payload(user) -> dict:
    """用户字典 + 改密开关标志（供 login / me）。"""
    data = user.to_dict()
    data["operator_change_password_enabled"] = _is_operator_change_password_enabled()
    return data
```

- `login`：`"user": _user_payload(user)`
- `me`：`return success(_user_payload(user))`
- `change_password`：在 `role != operator` 之后立刻：

```python
if not _is_operator_change_password_enabled():
    return fail("管理员未开放修改密码", 403)
```

`init_db.py`：在两处默认配置块（init 与 reset）中，若不存在则插入：

```python
SystemConfig(
    config_key="operator_change_password_enabled",
    config_value="false",
)
```

`log_display.py` 配置键中文映射增加：

```python
"operator_change_password_enabled": "允许操作员修改密码",
```

- [ ] **Step 4: 跑测确认通过**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_change_password -v
```

Expected: OK（含原有用例 + 新用例）

- [ ] **Step 5: Commit** — **跳过**（用户未要求）

---

### Task 2: 设置页 + 操作员 Layout

**Files:**
- Modify: `frontend/src/views/admin/SettingsPage.vue`
- Modify: `frontend/src/views/operator/Layout.vue`

**Interfaces:**
- Consumes: `getConfigApi` / `updateConfigApi`；`userStore.fetchMe`；`user.operator_change_password_enabled`
- Produces: 设置可切换；仅开启时显示「修改密码」

- [ ] **Step 1: SettingsPage**

在导出开关下增加：

```vue
<el-form-item label="允许操作员修改密码">
  <el-switch
    v-model="operatorChangePassword"
    active-text="允许"
    inactive-text="禁止"
    @change="handleChangePasswordToggle"
  />
</el-form-item>
```

```js
const operatorChangePassword = ref(false)

// loadConfig 中：
operatorChangePassword.value =
  res.data?.operator_change_password_enabled === 'true'

async function handleChangePasswordToggle(val) {
  await updateConfigApi(
    'operator_change_password_enabled',
    val ? 'true' : 'false',
  )
  ElMessage.success('设置已保存')
}
```

说明文案可写：`默认禁止操作员自助修改密码，可按需开启。管理员重置密码不受影响。`

- [ ] **Step 2: operator Layout**

- 按钮：`v-if="userStore.user?.operator_change_password_enabled"`
- `onMounted`：

```js
import { onMounted } from 'vue'
onMounted(() => {
  userStore.fetchMe().catch(() => {})
})
```

- [ ] **Step 3: 手工验收清单（实现者自检）**

1. 设置页默认关；打开后刷新仍为开  
2. 操作员刷新：关无按钮；开有按钮且可改密  
3. 关时用接口直调改密 → 403  

- [ ] **Step 4: Commit** — **跳过**

---

### Task 3: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** 进度表「系统设置」改为同时写导出开关与改密开关；API 表 `change-password` 说明补充「受系统开关控制，默认关」

- [ ] **Step 2: Commit** — **跳过**

---

## Spec coverage（自检）

| 规格项 | 任务 |
|--------|------|
| 设置页开关 | Task 2 |
| 默认 false / 缺键禁止 | Task 1 |
| 关：藏按钮 + API 403 | Task 1+2 |
| `/me` + login 字段 | Task 1 |
| fetchMe 刷新 | Task 2 |
| 管理员重置不受影响 | 无改动（验收） |
| init-db / log_display | Task 1 |
| README | Task 3 |

无占位符；字段名全链路统一为 `operator_change_password_enabled`。
