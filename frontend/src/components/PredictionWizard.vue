<!--
  智链预测 - 预测向导组件
  ========================
  步骤化引导用户完成AI预测分析流程
-->
<template>
  <div class="prediction-wizard">
    <!-- 进度步骤 -->
    <el-steps :active="currentStep" finish-status="success" class="wizard-steps">
      <el-step title="选择标的" description="选择交易对和时间周期">
        <template #icon>
          <el-icon><Coin /></el-icon>
        </template>
      </el-step>
      <el-step title="AI分析" description="DeepSeek正在分析市场">
        <template #icon>
          <el-icon><MagicStick /></el-icon>
        </template>
      </el-step>
      <el-step title="策略生成" description="基于分析生成具体策略">
        <template #icon>
          <el-icon><Aim /></el-icon>
        </template>
      </el-step>
      <el-step title="风险管理" description="设置止损止盈和仓位">
        <template #icon>
          <el-icon><Warning /></el-icon>
        </template>
      </el-step>
    </el-steps>

    <!-- 步骤内容区域 -->
    <div class="wizard-content">
      <!-- Step 1: 选择标的 -->
      <div v-show="currentStep === 0" class="step-panel">
        <SymbolSelector 
          :symbols="symbols"
          :selected-symbol="selectedSymbol"
          :selected-timeframe="selectedTimeframe"
          @select-symbol="handleSymbolSelect"
          @select-timeframe="handleTimeframeSelect"
        />
        
        <div class="step-actions">
          <el-button 
            type="primary" 
            size="large" 
            @click="startAnalysis"
            :disabled="!selectedSymbol"
          >
            开始AI分析
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Step 2: AI分析 -->
      <div v-show="currentStep === 1" class="step-panel">
        <div class="analysis-progress">
          <div class="analysis-header">
            <el-icon class="spinning" :size="48"><Loading /></el-icon>
            <h3>AI 正在深度分析中...</h3>
          </div>
          
          <div class="progress-steps">
            <div 
              v-for="(item, index) in analysisSteps" 
              :key="index"
              class="progress-step"
              :class="{ active: analysisProgress >= index, done: analysisProgress > index }"
            >
              <el-icon v-if="analysisProgress > index"><Check /></el-icon>
              <el-icon v-else-if="analysisProgress === index" class="spinning"><Loading /></el-icon>
              <span v-else class="step-number">{{ index + 1 }}</span>
              <span class="step-text">{{ item }}</span>
            </div>
          </div>
          
          <el-progress 
            :percentage="(analysisProgress / analysisSteps.length) * 100" 
            :stroke-width="8"
            :show-text="false"
            class="main-progress"
          />
        </div>
      </div>

      <!-- Step 3: 策略生成 -->
      <div v-show="currentStep === 2" class="step-panel">
        <div class="prediction-result" v-if="prediction">
          <div class="result-header">
            <div class="direction-badge" :class="predictionClass">
              <el-icon :size="32">
                <Top v-if="predictionClass === 'bullish'" />
                <Bottom v-else-if="predictionClass === 'bearish'" />
                <Sort v-else />
              </el-icon>
              <span>{{ prediction.prediction_cn || prediction.prediction }}</span>
            </div>
            <div class="confidence-ring">
              <el-progress 
                type="circle" 
                :percentage="prediction.confidence" 
                :width="80"
                :stroke-width="6"
                :color="confidenceColor"
              />
              <span class="confidence-label">置信度</span>
            </div>
          </div>
          
          <div class="result-summary">
            <p>{{ prediction.summary }}</p>
          </div>
          
          <div class="key-levels-preview">
            <h4>关键价位</h4>
            <div class="levels-row">
              <span class="level resistance">阻力: {{ formatLevels(resistanceLevels) }}</span>
              <span class="level support">支撑: {{ formatLevels(supportLevels) }}</span>
            </div>
          </div>
        </div>
        
        <div class="step-actions">
          <el-button size="large" @click="currentStep = 0">
            <el-icon class="el-icon--left"><ArrowLeft /></el-icon>
            重新选择
          </el-button>
          <el-button type="primary" size="large" @click="goToRiskManagement">
            设置风险管理
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Step 4: 风险管理 -->
      <div v-show="currentStep === 3" class="step-panel">
        <div class="risk-management">
          <el-form :model="riskForm" label-position="top" class="risk-form">
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="仓位比例 (%)">
                  <el-slider 
                    v-model="riskForm.positionSize" 
                    :min="1" 
                    :max="20"
                    :marks="positionMarks"
                    show-stops
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="杠杆倍数">
                  <el-input-number 
                    v-model="riskForm.leverage" 
                    :min="1" 
                    :max="20"
                    size="large"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="止损价格">
                  <el-input-number 
                    v-model="riskForm.stopLoss" 
                    :precision="4"
                    size="large"
                    class="full-width"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="止盈价格">
                  <el-input-number 
                    v-model="riskForm.takeProfit" 
                    :precision="4"
                    size="large"
                    class="full-width"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="风险等级">
              <el-radio-group v-model="riskForm.riskLevel" size="large">
                <el-radio-button label="low">保守</el-radio-button>
                <el-radio-button label="medium">平衡</el-radio-button>
                <el-radio-button label="high">激进</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-form>
          
          <!-- 风险预览 -->
          <div class="risk-preview">
            <div class="risk-stat">
              <span class="label">预计风险金额</span>
              <span class="value danger">{{ calculateRisk() }}</span>
            </div>
            <div class="risk-stat">
              <span class="label">盈亏比</span>
              <span class="value">{{ calculateRR() }}</span>
            </div>
          </div>
        </div>
        
        <div class="step-actions">
          <el-button size="large" @click="currentStep = 2">
            <el-icon class="el-icon--left"><ArrowLeft /></el-icon>
            返回
          </el-button>
          <el-button type="success" size="large" @click="completeWizard">
            <el-icon class="el-icon--left"><Check /></el-icon>
            完成并生成策略
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Coin,
  MagicStick,
  Aim,
  Warning,
  ArrowRight,
  ArrowLeft,
  Loading,
  Check,
  Top,
  Bottom,
  Sort
} from '@element-plus/icons-vue'
import { usePredictionStore } from '@/stores/usePredictionStore'
import SymbolSelector from './SymbolSelector.vue'

const predictionStore = usePredictionStore()

// 状态
const currentStep = ref(0)
const analysisProgress = ref(0)
const selectedSymbol = ref('ETHUSDT')
const selectedTimeframe = ref('4h')

// 分析步骤
const analysisSteps = [
  '获取市场数据',
  '计算技术指标',
  'AI深度分析',
  '生成预测报告'
]

// 风险表单
const riskForm = reactive({
  positionSize: 5,
  leverage: 3,
  stopLoss: 0,
  takeProfit: 0,
  riskLevel: 'medium'
})

const positionMarks = {
  1: '1%',
  5: '5%',
  10: '10%',
  20: '20%'
}

// 计算属性
const symbols = computed(() => predictionStore.symbols)
const prediction = computed(() => predictionStore.prediction)

const resistanceLevels = computed(() => {
  if (!prediction.value?.key_levels) return []
  const k = prediction.value.key_levels
  const levels: number[] = []
  
  if (k.resistances && Array.isArray(k.resistances)) {
    levels.push(...k.resistances)
  } else {
    // 兼容扁平结构
    if (k.strong_resistance) levels.push(k.strong_resistance)
    if (k.weak_resistance) levels.push(k.weak_resistance)
  }
  
  return levels.sort((a, b) => b - a).slice(0, 3)
})

const supportLevels = computed(() => {
  if (!prediction.value?.key_levels) return []
  const k = prediction.value.key_levels
  const levels: number[] = []
  
  if (k.supports && Array.isArray(k.supports)) {
    levels.push(...k.supports)
  } else {
    // 兼容扁平结构
    if (k.strong_support) levels.push(k.strong_support)
    if (k.weak_support) levels.push(k.weak_support)
  }
  
  return levels.sort((a, b) => b - a).slice(0, 3)
})

const predictionClass = computed(() => {
  if (!prediction.value) return 'neutral'
  const dir = prediction.value.prediction?.toLowerCase()
  if (dir?.includes('bullish') || dir?.includes('涨')) return 'bullish'
  if (dir?.includes('bearish') || dir?.includes('跌')) return 'bearish'
  return 'neutral'
})

const confidenceColor = computed(() => {
  if (!prediction.value) return '#909399'
  const c = prediction.value.confidence
  if (c >= 80) return '#67C23A'
  if (c >= 60) return '#E6A23C'
  return '#909399'
})

// 方法
function handleSymbolSelect(symbol: string) {
  selectedSymbol.value = symbol
  predictionStore.setSymbol(symbol)
}

function handleTimeframeSelect(tf: string) {
  selectedTimeframe.value = tf
}

async function startAnalysis() {
  currentStep.value = 1
  analysisProgress.value = 0
  
  // 模拟分析进度
  const progressInterval = setInterval(() => {
    if (analysisProgress.value < analysisSteps.length - 1) {
      analysisProgress.value++
    }
  }, 1200)
  
  try {
    await predictionStore.analyze(selectedTimeframe.value)
    analysisProgress.value = analysisSteps.length
    
    setTimeout(() => {
      currentStep.value = 2
      
      // 预填止损止盈
      if (prediction.value) {
        const price = prediction.value.key_levels?.current_price || 0
        riskForm.stopLoss = price * 0.97
        riskForm.takeProfit = price * 1.05
      }
    }, 500)
    
  } catch (error: any) {
    ElMessage.error(error.message || '分析失败')
    currentStep.value = 0
  } finally {
    clearInterval(progressInterval)
  }
}

function goToRiskManagement() {
  currentStep.value = 3
}

function formatLevels(levels: number[] | undefined): string {
  if (!levels || levels.length === 0) return '-'
  return levels.slice(0, 2).map(l => l.toFixed(2)).join(', ')
}

function calculateRisk(): string {
  const capital = 10000 // 假设总资金
  const risk = capital * (riskForm.positionSize / 100)
  return `$${risk.toFixed(2)}`
}

function calculateRR(): string {
  if (!riskForm.stopLoss || !riskForm.takeProfit) return '-'
  const currentPrice = prediction.value?.key_levels?.current_price || 0
  if (!currentPrice) return '-'
  
  const riskPct = Math.abs(currentPrice - riskForm.stopLoss) / currentPrice
  const rewardPct = Math.abs(riskForm.takeProfit - currentPrice) / currentPrice
  
  if (riskPct === 0) return '-'
  return (rewardPct / riskPct).toFixed(2)
}

function completeWizard() {
  ElMessage.success('策略已生成！')
  // 可以跳转到策略页面或显示策略详情
}

// 初始化
import { onMounted } from 'vue'

onMounted(async () => {
  // 加载交易对列表
  if (predictionStore.symbols.length === 0) {
    await predictionStore.loadSymbols()
  }
})

watch(() => predictionStore.symbols, (newSymbols) => {
  if (newSymbols.length && !selectedSymbol.value) {
    selectedSymbol.value = newSymbols[0].symbol
  }
}, { immediate: true })
</script>

<style lang="scss" scoped>
.prediction-wizard {
  max-width: 900px;
  margin: 0 auto;
}

.wizard-steps {
  margin-bottom: 40px;
  
  :deep(.el-step__icon) {
    width: 40px;
    height: 40px;
    font-size: 18px;
  }
  
  :deep(.el-step__title) {
    font-weight: 600;
  }
}

.wizard-content {
  min-height: 400px;
}

.step-panel {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

// Step 2: 分析进度
.analysis-progress {
  text-align: center;
  padding: 40px 20px;
  
  .analysis-header {
    margin-bottom: 40px;
    
    h3 {
      margin-top: 16px;
      font-size: 20px;
      color: #fff;
    }
  }
  
  .progress-steps {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-width: 300px;
    margin: 0 auto 32px;
  }
  
  .progress-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.4);
    transition: all 0.3s ease;
    
    &.active {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
    }
    
    &.done {
      color: #10b981;
    }
    
    .step-number {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
    }
  }
  
  .main-progress {
    max-width: 400px;
    margin: 0 auto;
  }
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// Step 3: 预测结果
.prediction-result {
  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }
  
  .direction-badge {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 24px;
    border-radius: 12px;
    font-size: 24px;
    font-weight: 700;
    
    &.bullish {
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
    }
    
    &.bearish {
      background: rgba(239, 68, 68, 0.15);
      color: #ef4444;
    }
    
    &.neutral {
      background: rgba(107, 114, 128, 0.15);
      color: #6b7280;
    }
  }
  
  .confidence-ring {
    text-align: center;
    
    .confidence-label {
      display: block;
      margin-top: 8px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }
  }
  
  .result-summary {
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    margin-bottom: 24px;
    
    p {
      margin: 0;
      line-height: 1.6;
      color: rgba(255, 255, 255, 0.8);
    }
  }
  
  .key-levels-preview {
    h4 {
      margin: 0 0 12px;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.6);
    }
    
    .levels-row {
      display: flex;
      gap: 24px;
    }
    
    .level {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 14px;
      
      &.resistance {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }
      
      &.support {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }
    }
  }
}

// Step 4: 风险管理
.risk-management {
  .risk-form {
    max-width: 600px;
    margin: 0 auto;
  }
  
  .full-width {
    width: 100%;
  }
  
  .risk-preview {
    display: flex;
    justify-content: center;
    gap: 48px;
    margin-top: 32px;
    padding: 24px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
  }
  
  .risk-stat {
    text-align: center;
    
    .label {
      display: block;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 8px;
    }
    
    .value {
      font-size: 24px;
      font-weight: 700;
      color: #fff;
      
      &.danger {
        color: #ef4444;
      }
    }
  }
}
</style>
