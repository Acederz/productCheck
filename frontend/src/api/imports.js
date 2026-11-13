import request from './request'

export function listImportsApi(params) {
  return request.get('/imports', { params })
}

/**
 * 上传导入：结果（含失败）由页面结果框展示，不走拦截器弹错。
 * 超时与服务器 Nginx/uWSGI 的 300 秒保持一致。
 */
export function uploadImportApi(file) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/imports', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    silent: true,
    timeout: 300 * 1000,
  })
}

export function getImportBatchApi(id) {
  return request.get(`/imports/${id}`)
}

export function downloadImportErrorsApi(id) {
  return `/api/imports/${id}/errors`
}

/** 删除导入批次及其关联任务、正式库数据 */
export function deleteImportApi(id) {
  return request.delete(`/imports/${id}`)
}
