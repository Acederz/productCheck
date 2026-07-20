import request from './request'

export function getRuleVersionApi() {
  return request.get('/rules/version')
}

export function importRulesApi(file, remark = '') {
  const form = new FormData()
  if (file) form.append('file', file)
  if (remark) form.append('remark', remark)
  return request.post('/rules/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getRuleOptionsApi(field, path) {
  return request.get('/rules/options', {
    params: { field, path: JSON.stringify(path) },
  })
}

export function getFieldMetaApi(field, path) {
  return request.get('/rules/field-meta', {
    params: { field, path: JSON.stringify(path) },
  })
}
