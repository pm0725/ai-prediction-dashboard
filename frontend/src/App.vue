<!--
  智链预测 - 根组件
-->
<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container" :class="{ 'dark': isDark }">
      <router-view />
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const isDark = ref(true)

onMounted(() => {
  // 默认启用暗色模式
  document.documentElement.classList.add('dark')
})
</script>

<style lang="scss">
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: #0a0a0f;
}

#app {
  height: 100%;
}

.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
  color: #e0e0e0;
}
</style>
