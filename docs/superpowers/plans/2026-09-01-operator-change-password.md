# 操作员自助修改密码 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 操作员可在顶栏弹窗用原密码 + 新密码 + 确认修改自己的密码。

**Architecture:** 校验与改密集中在 `POST /api/auth/change-password`（`login_required` + 角色校验）；可选抽出纯函数 `_password_strength_ok` / 服务方法便于单测。前端仅改操作员 `Layout.vue` 弹窗与 `auth.js` API。

**Tech Stack:** Flask、Flask-JWT-Extended、bcrypt、Vue 3、Element Plus、unittest

## Global Constraints

- 规格：`docs/superpowers/specs/2026-09-01-operator-change-password-design.md`
- 仅操作员可调用；管理员 → 403「请使用用户管理重置密码」
- 请求体字段：`old_password`、`new_password`、`confirm_password`
- 新密码：≥8 位且同时含字母与数字；不可与原密码相同
- 成功后保持登录（不失效 JWT）
- 写操作日志 `change_password`
- 中文注释；SOLID / DRY / KISS
- **不自动 git commit**（除非用户明确要求）

## Files

- Modify: `backend/app/api/auth.py` — 新增 `change_password` 路由
- Create: `backend/tests/test_change_password.py` — API / 校验用例
- Modify: `frontend/src/api/auth.js` — `changePasswordApi`
- Modify: `frontend/src/views/operator/Layout.vue` — 改密入口与弹窗
- Modify: `README.md` — 进度与 API 表

---

### Task 1: 改密 API（TDD）

**Files:**
- Create: `backend/tests/test_change_password.py`
- Modify: `backend/app/api/auth.py`

**Interfaces:**
- Consumes: `login_required`、`User.check_password` / `set_password`、`write_operation_log`、`ROLE_OPERATOR` / `ROLE_ADMIN`
- Produces: `POST /api/auth/change-password`；成功 `message` 含成功语义；错误 400/403/401

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_change_password.py`（从 `backend` 目录跑；用户名前缀 `UT_CPWD_`，`tearDown` 清理）：

```python
"""操作员自助修改密码 API 单测。"""
import json
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from flask_jwt_extended import create_access_token

from app import create_app
from app.constants import ROLE_ADMIN, ROLE_OPERATOR
from app.extensions import db
from app.models.log import OperationLog
from app.models.user import User


class ChangePasswordTests(unittest.TestCase):
    _UT_OP = "UT_CPWD_operator"
    _OLD = "OldPass12"
    _NEW = "NewPass34"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        op = User.query.filter_by(username=cls._UT_OP).first()
        if op:
            db.session.delete(op)
            db.session.commit()
        cls.ctx.pop()

    def setUp(self):
        op = User.query.filter_by(username=self._UT_OP).first()
        if op:
            db.session.delete(op)
            db.session.commit()
        op = User(username=self._UT_OP, role=ROLE_OPERATOR, is_active=True)
        op.set_password(self._OLD)
        db.session.add(op)
        db.session.commit()
        self.op_id = op.id

    def _op_headers(self):
        token = create_access_token(identity=str(self.op_id))
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _admin_headers(self):
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin)
        token = create_access_token(identity=str(admin.id))
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _post(self, headers, body):
        return self.client.post(
            "/api/auth/change-password",
            headers=headers,
            data=json.dumps(body),
        )

    def test_operator_success(self):
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": self._NEW,
                "confirm_password": self._NEW,
            },
        )
        self.assertEqual(resp.status_code, 200)
        op = User.query.get(self.op_id)
        self.assertTrue(op.check_password(self._NEW))
        self.assertFalse(op.check_password(self._OLD))
        log = (
            OperationLog.query.filter_by(action="change_password", target_id=self.op_id)
            .order_by(OperationLog.id.desc())
            .first()
        )
        self.assertIsNotNone(log)

    def test_wrong_old_password(self):
        resp = self._post(
            self._op_headers(),
            {
                "old_password": "WrongPass1",
                "new_password": self._NEW,
                "confirm_password": self._NEW,
            },
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("原密码", body["message"])
        op = User.query.get(self.op_id)
        self.assertTrue(op.check_password(self._OLD))

    def test_confirm_mismatch(self):
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": self._NEW,
                "confirm_password": "NewPass99",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("不一致", json.loads(resp.data)["message"])

    def test_weak_password(self):
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": "short1",
                "confirm_password": "short1",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("8", json.loads(resp.data)["message"])

    def test_same_as_old(self):
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": self._OLD,
                "confirm_password": self._OLD,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("不能与原密码相同", json.loads(resp.data)["message"])

    def test_admin_forbidden(self):
        resp = self._post(
            self._admin_headers(),
            {
                "old_password": "x",
                "new_password": self._NEW,
                "confirm_password": self._NEW,
            },
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("用户管理", json.loads(resp.data)["message"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_change_password -v
```

Expected: 路由不存在 → 404 或类似失败（非全部绿）

- [ ] **Step 3: 实现 API**

在 `backend/app/api/auth.py` 增加（补全 import：`g`、`db`、`login_required`、`ROLE_OPERATOR`、`write_operation_log`、`re`）：

```python
def _password_strength_ok(password: str) -> bool:
    """新密码至少 8 位且同时含字母与数字。"""
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


@auth_bp.post("/change-password")
@login_required
def change_password():
    """操作员自助修改密码。"""
    from app.constants import ROLE_OPERATOR
    from app.extensions import db
    from app.services.operation_log_service import write_operation_log

    if g.current_user.role != ROLE_OPERATOR:
        return fail("请使用用户管理重置密码", 403)

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not old_password or not new_password or not confirm_password:
        return fail("请填写原密码、新密码和确认密码")
    if new_password != confirm_password:
        return fail("两次输入的新密码不一致")
    if not _password_strength_ok(new_password):
        return fail("新密码至少 8 位，且需同时包含字母和数字")
    if not g.current_user.check_password(old_password):
        return fail("原密码错误")
    if g.current_user.check_password(new_password):
        return fail("新密码不能与原密码相同")

    g.current_user.set_password(new_password)
    write_operation_log(
        g.current_user.id,
        "change_password",
        "user",
        g.current_user.id,
        {},
    )
    db.session.commit()
    return success(message="密码修改成功")
```

注意：`auth.py` 顶部需 `from flask import Blueprint, g, request`，并用 `login_required` 替代仅 `jwt_required` 的模式（与项目装饰器一致）。

- [ ] **Step 4: 再跑测试确认全部通过**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_change_password -v
```

Expected: 全部 `ok`

---

### Task 2: 前端顶栏弹窗

**Files:**
- Modify: `frontend/src/api/auth.js`
- Modify: `frontend/src/views/operator/Layout.vue`

**Interfaces:**
- Consumes: `POST /api/auth/change-password`
- Produces: `changePasswordApi({ old_password, new_password, confirm_password })`

- [ ] **Step 1: API 封装**

```js
export function changePasswordApi(data) {
  return request.post('/auth/change-password', data)
}
```

- [ ] **Step 2: Layout 增加入口与弹窗**

在 `operator/Layout.vue`：

- 用户名与「退出」之间增加：`<el-button link type="primary" @click="openChangePwd">修改密码</el-button>`
- `el-dialog` 标题「修改密码」，表单三项：`old_password` / `new_password` / `confirm_password`，均为 `type="password"` + `show-password`
- 提交逻辑：
  1. 本地：非空、两次一致、`length>=8` 且含字母数字
  2. 调 `changePasswordApi`
  3. 成功：`ElMessage.success`、关弹窗、清空表单；**不**调用 logout
- 引入 `ref`、`ElMessage`、`changePasswordApi`

本地强度校验可内联：

```js
function passwordStrengthOk(pwd) {
  if (!pwd || pwd.length < 8) return false
  return /[A-Za-z]/.test(pwd) && /\d/.test(pwd)
}
```

- [ ] **Step 3: 浏览器冒烟（或报告注明交 Task 3）**

操作员登录 → 改密 → 仍保持在任务页 → 退出后用新密码可登录。

---

### Task 3: README 与验收

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** 「登录/用户」行补充「操作员可自助修改密码」
- [ ] **Step 2:** API 表增加 `POST /api/auth/change-password`
- [ ] **Step 3:** 复跑单测

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_change_password -v
```

- [ ] **Step 4:** 对照规格验收清单（自动化 vs 需浏览器）写入实现报告或本计划勾选说明

| 项 | 期望 |
|----|------|
| 操作员合法改密 | 单测 |
| 原密码错误等拒绝 | 单测 |
| 管理员 403 | 单测 |
| 顶栏弹窗 / 保持登录 | 浏览器 |

---

## Spec coverage（自检）

| 规格项 | 任务 |
|--------|------|
| 仅操作员 + 403 文案 | Task 1 |
| 三字段校验顺序与提示 | Task 1 |
| 强度规则 / 不可同原密码 | Task 1 |
| 操作日志 | Task 1 |
| 保持登录 | Task 1（不失效 token）+ Task 2（不 logout） |
| 顶栏弹窗 | Task 2 |
| README | Task 3 |
| 管理员无入口 | Task 2（不改 admin Layout） |

## 执行说明

Plan 已保存。实现时按 Task 顺序；默认不 commit。
