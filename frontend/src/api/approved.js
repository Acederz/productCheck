import request from './request'

export function listApprovedApi(params) {
  return request.get('/approved-products', { params })
}
