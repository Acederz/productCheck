import request from './request'

export function loginApi(data) {
  return request.post('/auth/login', data)
}

export function getMeApi() {
  return request.get('/auth/me')
}

export function logoutApi() {
  return request.post('/auth/logout')
}

/** 操作员自助修改密码 */
export function changePasswordApi(data) {
  return request.post('/auth/change-password', data)
}
