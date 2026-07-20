import request from './request'

export function listImportsApi(params) {
  return request.get('/imports', { params })
}

export function uploadImportApi(file) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/imports', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getImportBatchApi(id) {
  return request.get(`/imports/${id}`)
}

export function downloadImportErrorsApi(id) {
  return `/api/imports/${id}/errors`
}
