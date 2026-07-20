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
