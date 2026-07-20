import { buildQuery, downloadFile } from '@/utils/download'

export function exportTasksUrl(params) {
  return `/api/export/tasks${buildQuery(params)}`
}

export function exportApprovedUrl(params) {
  return `/api/export/approved${buildQuery(params)}`
}

export async function downloadTasksExport(params) {
  await downloadFile(exportTasksUrl(params), 'tasks_export.xlsx')
}

export async function downloadApprovedExport(params) {
  await downloadFile(exportApprovedUrl(params), 'approved_export.xlsx')
}
