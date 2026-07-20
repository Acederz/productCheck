import request from './request'

export function getConfigApi() {
  return request.get('/config')
}

export function updateConfigApi(key, value) {
  return request.put(`/config/${key}`, { value })
}
