import request from './request'

/** 获取当前无需填写字段规则版本 */
export function getSkipFieldRuleVersionApi() {
  return request.get('/skip-field-rules/version')
}

/** 导入无需填写字段规则 Excel（须上传 file） */
export function importSkipFieldRulesApi(file, remark = '') {
  const form = new FormData()
  if (file) form.append('file', file)
  if (remark) form.append('remark', remark)
  return request.post('/skip-field-rules/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 按大类查询禁用字段英文名列表 */
export function getDisabledFieldsApi(categoryLarge) {
  return request.get('/skip-field-rules/disabled-fields', {
    params: { category_large: categoryLarge || '' },
  })
}
