import request from './request'

export function listPendingReviewsApi(params) {
  return request.get('/reviews/pending', { params })
}

export function approveReviewsApi(taskIds) {
  return request.post('/reviews/approve', { task_ids: taskIds })
}

export function rejectReviewsApi(taskIds, reason = '') {
  return request.post('/reviews/reject', { task_ids: taskIds, reason })
}

/** 按范围统计待审核条数（scope=all 时忽略其它筛选参数） */
export function approveScopeCountApi(params) {
  return request.get('/reviews/approve-scope-count', { params })
}

/** 按范围批量审核通过（大批量可能较久，单独延长超时） */
export function approveScopeApi(payload) {
  return request.post('/reviews/approve-scope', payload, { timeout: 180000 })
}

/** 按范围统计待审核条数（驳回用，口径与通过一致） */
export function rejectScopeCountApi(params) {
  return request.get('/reviews/reject-scope-count', { params })
}

/** 按范围批量驳回（原因可空；大批量单独延长超时） */
export function rejectScopeApi(payload) {
  return request.post('/reviews/reject-scope', payload, { timeout: 180000 })
}
