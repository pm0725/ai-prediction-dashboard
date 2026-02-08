<!--
  智链预测 - 策略生成页面
-->
<template>
  <div class="strategy-page">
    <div class="page-header">
      <h1>
        <el-icon><Aim /></el-icon>
        策略生成
      </h1>
    </div>

    <el-row :gutter="24">
      <el-col :span="16">
        <el-card class="strategy-card">
          <template #header>
            <span>策略配置</span>
          </template>
          
          <el-form :model="strategyForm" label-width="120px">
            <el-form-item label="交易对">
              <el-input v-model="strategyForm.symbol" disabled />
            </el-form-item>
            
            <el-form-item label="预测方向">
              <el-radio-group v-model="strategyForm.direction">
                <el-radio-button label="long">做多</el-radio-button>
                <el-radio-button label="short">做空</el-radio-button>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="风险等级">
              <el-slider
                v-model="strategyForm.riskLevel"
                :marks="riskMarks"
                :step="1"
                :min="1"
                :max="3"
                show-stops
              />
            </el-form-item>
            
            <el-form-item label="仓位比例">
              <el-slider
                v-model="strategyForm.positionSize"
                :min="1"
                :max="20"
                :format-tooltip="(val: number) => `${val}%`"
              />
            </el-form-item>
            
            <el-form-item label="杠杆倍数">
              <el-input-number v-model="strategyForm.leverage" :min="1" :max="20" />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" size="large" @click="generateStrategy">
                生成策略
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="tips-card">
          <template #header>
            <span>风险提示</span>
          </template>
          
          <el-alert
            title="交易有风险"
            type="warning"
            :closable="false"
            show-icon
          >
            <p>加密货币合约交易具有高风险性，可能导致本金全部损失。</p>
            <p>请确保您完全理解相关风险后再进行交易。</p>
          </el-alert>
          
          <div class="tips-list">
            <div class="tip-item">
              <el-icon><WarningFilled /></el-icon>
              <span>单笔交易风险建议不超过总资金的2%</span>
            </div>
            <div class="tip-item">
              <el-icon><WarningFilled /></el-icon>
              <span>务必设置止损，严格执行交易纪律</span>
            </div>
            <div class="tip-item">
              <el-icon><WarningFilled /></el-icon>
              <span>避免重仓和过度杠杆</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Aim, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usePredictionStore } from '@/stores/usePredictionStore'

const route = useRoute()
const predictionStore = usePredictionStore()

const strategyForm = reactive({
  symbol: predictionStore.currentSymbol,
  direction: 'long',
  riskLevel: 2,
  positionSize: 5,
  leverage: 5
})

const riskMarks = {
  1: '保守',
  2: '平衡',
  3: '激进'
}

function generateStrategy() {
  ElMessage.success('策略生成功能开发中...')
}

onMounted(() => {
  if (route.query.symbol) {
    strategyForm.symbol = route.query.symbol as string
  }
})
</script>

<style lang="scss" scoped>
.strategy-page {
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

.strategy-card {
  min-height: 500px;
}

.tips-card {
  .tips-list {
    margin-top: 20px;
  }
  
  .tip-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 0;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    
    .el-icon {
      color: #f59e0b;
      margin-top: 2px;
    }
  }
}
</style>
