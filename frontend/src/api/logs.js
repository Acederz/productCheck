import request from './request'

export function listOperationLogsApi(params) {
  return request.get('/logs/operations', { params })
}

export function listFieldChangeLogsApi(params) {
  return request.get('/logs/changes', { params })
}
