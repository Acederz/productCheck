"""操作员「我的任务」按批次统计：可选批次列表与指定批次的填写进度。"""

from __future__ import annotations

from app.constants import (
    TASK_STATUS_APPROVED,
    TASK_STATUS_PENDING,
    TASK_STATUS_REJECTED,
    TASK_STATUS_REVIEW,
)
from app.extensions import db
from app.models.task import ClassificationTask, ImportBatch

# 只统计导入成功的批次
_BATCH_STATUS_COMPLETED = "completed"


def empty_stats() -> dict:
    """无可统计批次时的返回结构。"""
    return {
        "batch_id": None,
        "batch_no": "",
        "total": 0,
        "pending": 0,
        "submitted": 0,
        "approved": 0,
    }


def _assigned_batches_query(user_id: int):
    """含该操作员任务的已完成批次查询，按批次 ID 倒序。"""
    own_batch_ids = (
        db.session.query(ClassificationTask.batch_id)
        .filter(
            ClassificationTask.assignee_id == user_id,
            ClassificationTask.batch_id.isnot(None),
        )
        .distinct()
    )
    return ImportBatch.query.filter(
        ImportBatch.id.in_(own_batch_ids),
        ImportBatch.status == _BATCH_STATUS_COMPLETED,
    ).order_by(ImportBatch.id.desc())


def list_assigned_batches(user_id: int) -> list[dict]:
    """返回分给该操作员任务的批次（新到旧）。

    :return: ``[{"id", "batch_no", "file_name"}]``
    """
    return [
        {"id": b.id, "batch_no": b.batch_no, "file_name": b.file_name}
        for b in _assigned_batches_query(user_id).all()
    ]


def get_batch_stats(user_id: int, batch_id: int | None = None) -> dict:
    """统计该操作员在指定批次的任务进度。

    - ``batch_id`` 为空：取该操作员最近被分配的批次
    - 指定批次中没有其任务（含他人批次、失败批次）：返回全 0
    - 口径：待处理 = 待处理 + 已驳回；已提交 = 待审核；已通过 = 已通过
    """
    query = _assigned_batches_query(user_id)
    if batch_id is not None:
        query = query.filter(ImportBatch.id == batch_id)
    batch = query.first()
    if not batch:
        return empty_stats()

    # 按状态一次分组，避免多次 count
    rows = (
        db.session.query(ClassificationTask.status, db.func.count(ClassificationTask.id))
        .filter(
            ClassificationTask.assignee_id == user_id,
            ClassificationTask.batch_id == batch.id,
        )
        .group_by(ClassificationTask.status)
        .all()
    )
    by_status = {status: int(cnt) for status, cnt in rows}
    return {
        "batch_id": batch.id,
        "batch_no": batch.batch_no,
        "total": sum(by_status.values()),
        "pending": by_status.get(TASK_STATUS_PENDING, 0) + by_status.get(TASK_STATUS_REJECTED, 0),
        "submitted": by_status.get(TASK_STATUS_REVIEW, 0),
        "approved": by_status.get(TASK_STATUS_APPROVED, 0),
    }
