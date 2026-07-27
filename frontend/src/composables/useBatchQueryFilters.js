/**
 * 管理员列表：导入批次号多选筛选。
 * 选项来自导入批次列表，查询参数为 batch_id=1,2,3
 */
import { ref } from 'vue'
import { listImportsApi } from '@/api/imports'

export function useBatchQueryFilters() {
  const batchOptions = ref([]) // [{ id, batch_no }]
  const selectedBatchIds = ref([])
  const batchLoading = ref(false)

  async function loadBatchOptions() {
    batchLoading.value = true
    try {
      const res = await listImportsApi({ page: 1, page_size: 500 })
      const items = res.data?.items || []
      batchOptions.value = items.map((b) => ({
        id: b.id,
        batch_no: b.batch_no,
        label: b.batch_no,
      }))
    } finally {
      batchLoading.value = false
    }
  }

  function resetBatchFilters() {
    selectedBatchIds.value = []
  }

  /** 并入列表查询参数 */
  function withBatchParams(params = {}) {
    if (!selectedBatchIds.value.length) return { ...params }
    return {
      ...params,
      batch_id: selectedBatchIds.value.join(','),
    }
  }

  return {
    batchOptions,
    selectedBatchIds,
    batchLoading,
    loadBatchOptions,
    resetBatchFilters,
    withBatchParams,
  }
}
