import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

/** 带 Token 下载文件 */
export async function downloadFile(url, filename) {
  const userStore = useUserStore()
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${userStore.token}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    ElMessage.error(err.message || '下载失败')
    return
  }
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

/** 构建查询字符串 */
export function buildQuery(params) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.append(k, v)
  })
  const s = qs.toString()
  return s ? `?${s}` : ''
}
