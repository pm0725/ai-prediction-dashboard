<!--
  智链预测 - 回测页面
-->
<template>
  <div class="backtest-page">
    <div class="page-header">
      <h1>
        <el-icon><DataLine /></el-icon>
        策略回测
      </h1>
    </div>

    <el-card class="backtest-card">
      <el-empty description="策略回测功能开发中">
        <template #image>
          <el-icon :size="100" color="#3b82f6"><DataLine /></el-icon>
        </template>
        <p class="coming-soon">即将上线</p>
        <el-button type="primary" @click="$router.push('/')">返回仪表盘</el-button>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { DataLine } from '@element-plus/icons-vue'
</script>

<style lang="scss" scoped>
.backtest-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  
  h1 {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 24px;
    font-weight: 700;
    color: #fff;
  }
}

.backtest-card {
  min-height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .coming-soon {
    font-size: 18px;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 20px;
  }
}
</style>
