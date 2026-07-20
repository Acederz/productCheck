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
