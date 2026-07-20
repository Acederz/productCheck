import request from './request'

export function listTasksApi(params) {
  return request.get('/tasks', { params })
}

export function myTasksApi(params) {
  return request.get('/tasks/my', { params })
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
