<template>
  <!-- 有提示词时悬停显示全文；无提示词时不启用 Tooltip -->
  <el-tooltip
    :disabled="!normalizedHint"
    :content="normalizedHint"
    placement="top"
    :show-after="200"
    :hide-after="0"
    popper-class="field-hint-tooltip"
  >
    <div class="field-hint-wrap">
      <slot />
    </div>
  </el-tooltip>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 规则下发的完整提示文案 */
  hint: { type: String, default: '' },
})

const normalizedHint = computed(() => String(props.hint || '').trim())
</script>

<style scoped>
.field-hint-wrap {
  width: 100%;
  min-width: 0;
}
</style>

<style>
/* 全局：提示气泡可换行，避免长文案撑出屏幕 */
.field-hint-tooltip {
  max-width: 360px;
  line-height: 1.5;
  white-space: normal;
  word-break: break-word;
}
</style>
