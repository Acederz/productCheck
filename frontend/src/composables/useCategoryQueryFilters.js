/**
 * 列表页「大类 / 区隔」查询筛选项。
 * 选项来自分类规则；选了大类后，区隔取所选大类下选项的并集。
 */
import { reactive, ref } from 'vue'
import { getRuleOptionsApi } from '@/api/rules'

/** 多选筛选项：未选或全选视为「全部」，不传查询参数 */
export function resolveFilterValues(selected, allOptions) {
  if (!selected?.length) return undefined
  if (
    selected.length >= allOptions.length
    && allOptions.every((item) => selected.includes(item))
  ) {
    return undefined
  }
  return selected.join(',')
}

export function useCategoryQueryFilters() {
  const categoryLargeOptions = ref([])
  const categorySegmentOptions = ref([])
  const categoryFilters = reactive({
    category_large: [],
    category_segment: [],
  })

  /** 加载全部大类选项 */
  async function loadCategoryLargeOptions() {
    try {
      const res = await getRuleOptionsApi('大类', {})
      categoryLargeOptions.value = res.data?.options || []
    } catch (e) {
      categoryLargeOptions.value = []
      console.error('加载大类筛选项失败', e)
    }
  }

  /** 按当前已选大类加载区隔（空则加载全量并集） */
  async function loadCategorySegmentOptions() {
    try {
      const path = {}
      if (categoryFilters.category_large?.length) {
        path['大类'] = [...categoryFilters.category_large]
      }
      const res = await getRuleOptionsApi('区隔', path)
      categorySegmentOptions.value = res.data?.options || []
      // 去掉已不在新选项中的区隔选择
      const allowed = new Set(categorySegmentOptions.value)
      categoryFilters.category_segment = categoryFilters.category_segment.filter((v) =>
        allowed.has(v),
      )
    } catch (e) {
      categorySegmentOptions.value = []
      console.error('加载区隔筛选项失败', e)
    }
  }

  /** 首次进入页面时加载筛选项 */
  async function initCategoryFilterOptions() {
    await loadCategoryLargeOptions()
    await loadCategorySegmentOptions()
  }

  /** 大类变更后刷新区隔 */
  async function onCategoryLargeFilterChange() {
    await loadCategorySegmentOptions()
  }

  /** 拼进列表查询参数 */
  function categoryQueryParams() {
    return {
      category_large: resolveFilterValues(
        categoryFilters.category_large,
        categoryLargeOptions.value,
      ),
      category_segment: resolveFilterValues(
        categoryFilters.category_segment,
        categorySegmentOptions.value,
      ),
    }
  }

  function resetCategoryFilters() {
    categoryFilters.category_large = []
    categoryFilters.category_segment = []
  }

  /** 重置并恢复区隔为全量选项 */
  async function resetCategoryFiltersAndOptions() {
    resetCategoryFilters()
    await loadCategorySegmentOptions()
  }

  return {
    categoryFilters,
    categoryLargeOptions,
    categorySegmentOptions,
    initCategoryFilterOptions,
    onCategoryLargeFilterChange,
    categoryQueryParams,
    resetCategoryFilters,
    resetCategoryFiltersAndOptions,
  }
}
