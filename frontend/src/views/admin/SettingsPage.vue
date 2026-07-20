<template>
  <div>
    <el-card shadow="never">
      <template #header>系统设置</template>
      <el-form label-width="200px">
        <el-form-item label="允许操作员导出数据">
          <el-switch
            v-model="operatorExport"
            active-text="允许"
            inactive-text="禁止"
            @change="handleToggle"
          />
        </el-form-item>
      </el-form>
      <el-text type="info" size="small">默认禁止操作员导出，可按需开启。</el-text>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfigApi, updateConfigApi } from '@/api/config'

const operatorExport = ref(false)

async function loadConfig() {
  const res = await getConfigApi()
  operatorExport.value = res.data?.operator_export_enabled === 'true'
}

async function handleToggle(val) {
  await updateConfigApi('operator_export_enabled', val ? 'true' : 'false')
  ElMessage.success('设置已保存')
}

onMounted(loadConfig)
</script>
