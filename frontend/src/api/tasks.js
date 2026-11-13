import request from './request'

export function listTasksApi(params) {
  return request.get('/tasks', { params })
}

export function myTasksApi(params) {
  return request.get('/tasks/my', { params })
}

/** 操作员：分给自己任务的批次（新到旧），用于统计切换 */
export function myTaskBatchesApi() {
  return request.get('/tasks/my/batches')
}

/** 操作员：指定批次的填写统计；不传 batchId 取自己最近被分配的批次 */
export function myTaskStatsApi(batchId) {
  const params = batchId ? { batch_id: batchId } : {}
  return request.get('/tasks/my/stats', { params })
}

export function getTaskApi(id) {
  return request.get(`/tasks/${id}`)
}

export function assignTasksApi(taskIds, assigneeId) {
  return request.post('/tasks/assign', { task_ids: taskIds, assignee_id: assigneeId })
}

export function withdrawTasksApi(taskIds) {
  return request.post('/tasks/withdraw', { task_ids: taskIds })
}

export function updateTaskApi(id, data) {
  return request.put(`/tasks/${id}`, data)
}

export function saveDraftApi(id, draft) {
  return request.post(`/tasks/${id}/draft`, { draft })
}

export function submitTasksApi(taskIds) {
  return request.post('/tasks/submit', { task_ids: taskIds })
}
