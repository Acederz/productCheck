# 管理员删除操作员账号 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理员可在用户管理页删除无未完成任务的操作员账号。

**Architecture:** `DELETE /api/users/<id>` 集中校验与外键清理；前端仅操作员行显示删除并确认。未完成定义：`assignee_id` 且状态 ∈ 待处理/待审核/已驳回。

**Tech Stack:** Flask、SQLAlchemy、Vue 3、Element Plus、unittest

## Global Constraints

- 规格：`docs/superpowers/specs/2026-09-01-delete-operator-user-design.md`
- 仅管理员可删；仅可删操作员；不能删自己
- 有待处理/待审核/已驳回任务则拒绝，提示条数
- 已通过任务可删：置空 `assignee_id` 等，保留业务数据
- 写 `delete_user` 操作日志（管理员为操作者）
- 中文注释；SOLID / DRY / KISS
- **不自动 git commit**（除非用户明确要求）

## Files

- Modify: `backend/app/api/users.py` — `DELETE` 路由与清理逻辑（或抽 `UserService.delete_operator`）
- Create: `backend/tests/test_delete_operator_user.py`
- Modify: `frontend/src/api/users.js` — `deleteUserApi`
- Modify: `frontend/src/views/admin/UserManage.vue`
- Modify: `README.md`

---

### Task 1: DELETE API（TDD）

**Files:**
- Create: `backend/tests/test_delete_operator_user.py`
- Modify: `backend/app/api/users.py`

**Interfaces:**
- Consumes: `admin_required`、任务状态常量、相关模型
- Produces: `DELETE /api/users/<int:user_id>`

- [ ] **Step 1: 写失败测试**

```python
"""管理员删除操作员账号单测。"""
import json
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from flask_jwt_extended import create_access_token

from app import create_app
from app.constants import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    TASK_STATUS_APPROVED,
    TASK_STATUS_PENDING,
)
from app.extensions import db
from app.models.task import ClassificationTask, TaskDraft
from app.models.user import User


class DeleteOperatorUserTests(unittest.TestCase):
    _UT_OP = "UT_DEL_USER_op"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_op()
        cls.ctx.pop()

    @classmethod
    def _cleanup_op(cls):
        op = User.query.filter_by(username=cls._UT_OP).first()
        if not op:
            return
        TaskDraft.query.filter_by(assignee_id=op.id).delete(synchronize_session=False)
        ClassificationTask.query.filter_by(assignee_id=op.id).update(
            {ClassificationTask.assignee_id: None}, synchronize_session=False
        )
        ClassificationTask.query.filter_by(reviewed_by=op.id).update(
            {ClassificationTask.reviewed_by: None}, synchronize_session=False
        )
        db.session.delete(op)
        db.session.commit()

    def setUp(self):
        self._cleanup_op()
        op = User(username=self._UT_OP, role=ROLE_OPERATOR, is_active=True)
        op.set_password("OpPass12")
        db.session.add(op)
        db.session.commit()
        self.op_id = op.id

    def _admin_headers(self):
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin)
        token = create_access_token(identity=str(admin.id))
        return {"Authorization": f"Bearer {token}"}

    def _make_task(self, status: str) -> ClassificationTask:
        t = ClassificationTask(
            product_id=f"P_{status}_{self.op_id}",
            product_name="n",
            platform="淘宝",
            status=status,
            assignee_id=self.op_id,
        )
        db.session.add(t)
        db.session.commit()
        return t

    def test_delete_operator_ok(self):
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(User.query.filter_by(username=self._UT_OP).first())

    def test_reject_when_pending_tasks(self):
        self._make_task(TASK_STATUS_PENDING)
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("未完成", body["message"])
        self.assertIsNotNone(User.query.get(self.op_id))

    def test_allow_when_only_approved(self):
        t = self._make_task(TASK_STATUS_APPROVED)
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(t)
        self.assertIsNone(t.assignee_id)
        self.assertEqual(t.status, TASK_STATUS_APPROVED)

    def test_reject_delete_admin(self):
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        resp = self.client.delete(
            f"/api/users/{admin.id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("管理员", json.loads(resp.data)["message"])

    def test_reject_delete_self(self):
        # 用临时管理员作为「自己」：创建 UT 管理员再删自己
        name = "UT_DEL_USER_admin_self"
        u = User.query.filter_by(username=name).first()
        if u:
            db.session.delete(u)
            db.session.commit()
        u = User(username=name, role=ROLE_ADMIN, is_active=True)
        u.set_password("AdPass12")
        db.session.add(u)
        db.session.commit()
        headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(u.id))}"
        }
        resp = self.client.delete(f"/api/users/{u.id}", headers=headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("当前登录", json.loads(resp.data)["message"])
        db.session.delete(u)
        db.session.commit()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败（路由 404）**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_delete_operator_user -v
```

- [ ] **Step 3: 实现 DELETE**

在 `users.py` 增加（补全 import）：

```python
@users_bp.delete("/<int:user_id>")
@admin_required
def delete_user(user_id: int):
    """删除操作员账号（有未完成任务则拒绝）。"""
    from app.constants import (
        TASK_STATUS_PENDING,
        TASK_STATUS_REJECTED,
        TASK_STATUS_REVIEW,
    )
    from app.models.approved import ApprovedProduct
    from app.models.log import AssignmentLog, FieldChangeLog, OperationLog, ReviewLog
    from app.models.rule import ClassificationRuleChangeLog, ClassificationRuleVersion
    from app.models.task import ClassificationTask, TaskDraft
    from app.models.user import SystemConfig
    from app.services.operation_log_service import write_operation_log

    user = User.query.get(user_id)
    if not user:
        return fail("用户不存在", 404)
    if user.role == ROLE_ADMIN:
        return fail("不能删除管理员账号", 403)
    if user.id == g.current_user.id:
        return fail("不能删除当前登录账号")

    unfinished = ClassificationTask.query.filter(
        ClassificationTask.assignee_id == user_id,
        ClassificationTask.status.in_(
            [TASK_STATUS_PENDING, TASK_STATUS_REVIEW, TASK_STATUS_REJECTED]
        ),
    ).count()
    if unfinished:
        return fail(f"该账号仍有 {unfinished} 条未完成任务，请先处理或改派后再删")

    username = user.username
    try:
        TaskDraft.query.filter_by(assignee_id=user_id).delete(synchronize_session=False)
        ClassificationTask.query.filter_by(assignee_id=user_id).update(
            {ClassificationTask.assignee_id: None}, synchronize_session=False
        )
        ClassificationTask.query.filter_by(reviewed_by=user_id).update(
            {ClassificationTask.reviewed_by: None}, synchronize_session=False
        )
        ApprovedProduct.query.filter_by(approved_by=user_id).update(
            {ApprovedProduct.approved_by: None}, synchronize_session=False
        )
        OperationLog.query.filter_by(user_id=user_id).update(
            {OperationLog.user_id: None}, synchronize_session=False
        )
        FieldChangeLog.query.filter_by(operator_id=user_id).update(
            {FieldChangeLog.operator_id: None}, synchronize_session=False
        )
        AssignmentLog.query.filter_by(operator_id=user_id).update(
            {AssignmentLog.operator_id: None}, synchronize_session=False
        )
        ReviewLog.query.filter_by(operator_id=user_id).update(
            {ReviewLog.operator_id: None}, synchronize_session=False
        )
        SystemConfig.query.filter_by(updated_by=user_id).update(
            {SystemConfig.updated_by: None}, synchronize_session=False
        )
        ClassificationRuleVersion.query.filter_by(created_by=user_id).update(
            {ClassificationRuleVersion.created_by: None}, synchronize_session=False
        )
        ClassificationRuleChangeLog.query.filter_by(operator_id=user_id).update(
            {ClassificationRuleChangeLog.operator_id: None}, synchronize_session=False
        )
        write_operation_log(
            g.current_user.id,
            "delete_user",
            "user",
            user_id,
            {"username": username},
        )
        db.session.delete(user)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return fail(f"删除失败：{exc}", 500)

    return success(message="删除成功")
```


- [ ] **Step 4: 测试全部通过**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_delete_operator_user -v
```

---

### Task 2: 前端删除按钮

**Files:**
- Modify: `frontend/src/api/users.js`
- Modify: `frontend/src/views/admin/UserManage.vue`

**Interfaces:**
- Produces: `deleteUserApi(id)` → `DELETE /users/{id}`

- [ ] **Step 1: API**

```js
export function deleteUserApi(id) {
  return request.delete(`/users/${id}`)
}
```

- [ ] **Step 2: UserManage**

- 操作列 `width` 调到约 `280`
- 在停用按钮后增加：

```vue
<el-button
  v-if="row.role === 'operator'"
  link
  type="danger"
  @click="handleDelete(row)"
>
  删除
</el-button>
```

- `handleDelete`：`ElMessageBox.confirm(\`确定删除账号 ${row.username}？删除后不可恢复。\`, '删除确认', { type: 'warning' })` → `deleteUserApi` → 成功刷新

- [ ] **Step 3: 浏览器冒烟可 defer Task 3**

---

### Task 3: README 与验收

**Files:**
- Modify: `README.md`

- [ ] 登录/用户行补充「可删除无未完成任务的操作员」
- [ ] API 表增加 `DELETE /api/users/{id}`
- [ ] 复跑 `tests.test_delete_operator_user`
- [ ] 报告中标注自动化 vs 浏览器项

---

## Spec coverage

| 规格项 | 任务 |
|--------|------|
| 操作列删除仅操作员 | Task 2 |
| 未完成拦截 | Task 1 |
| 已通过可删置空 | Task 1 |
| 禁删管理员/自己 | Task 1 |
| 确认弹窗 | Task 2 |
| README | Task 3 |

## 执行说明

Plan 已保存。默认不 commit。
