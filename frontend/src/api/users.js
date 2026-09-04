import request from './request'

export function listUsersApi() {
  return request.get('/users')
}

export function createUserApi(data) {
  return request.post('/users', data)
}

export function updateUserApi(id, data) {
  return request.put(`/users/${id}`, data)
}

/** 删除操作员账号（后端校验未完成任务等） */
export function deleteUserApi(id) {
  return request.delete(`/users/${id}`)
}
