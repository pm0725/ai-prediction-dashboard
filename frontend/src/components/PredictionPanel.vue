<!--
  智链预测 - 预测面板组件
  ========================
  主分析面板，集成交易对选择、K线图和AI预测结果
-->
<template>
  <div class="prediction-panel">
    <!-- 控制栏 -->
    <div class="panel-header">
      <div class="header-left">
        <h2>
          <el-icon><MagicStick /></el-icon>
          AI 预测分析
        </h2>
        <el-tag type="primary" effect="plain" size="small">
          {{ currentTimeframe }}
        </el-tag>
      </div>
      
      <div class="header-controls">
        <!-- 交易对选择 -->
        <el-select
          v-model="selectedSymbol"
          placeholder="选择交易对"
          size="large"
          style="width: 160px"
          @change="handleSymbolChange"
        >
          <el-option
            v-for="item in symbols"
            :key="item.symbol"
            :label="item.symbol"
            :value="item.symbol"
          >
            <span class="symbol-option">
              <span class="base">{{ item.base }}</span>
              <span class="name">{{ item.name }}</span>
            </span>
          </el-option>
        </el-select>
        
        <!-- 周期选择 -->
        <el-radio-group v-model="currentTimeframe" size="default">
          <el-radio-button label="1h">1H</el-radio-button>
          <el-radio-button label="4h">4H</el-radio-button>
          <el-radio-button label="1d">1D</el-radio-button>
        </el-radio-group>
        
        <!-- 分析按钮 -->
        <el-button
          type="primary"
          size="large"
          :loading="isAnalyzing"
          @click="startAnalysis"
        >
          <el-icon v-if="!isAnalyzing"><MagicStick /></el-icon>
          {{ isAnalyzing ? '分析中...' : '开始分析' }}
        </el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="panel-content">
      <!-- 左侧：图表和指标 -->
      <div class="chart-section">
        <!-- K线图 -->
        <el-card class="chart-card">
          <template #header>
            <div class="chart-title">
              <span class="symbol">{{ selectedSymbol }}</span>
              <span class="price" v-if="currentPrice">
                {{ formatPrice(currentPrice) }}
              </span>
              <span 
                class="change" 
                :class="priceChange >= 0 ? 'up' : 'down'"
                v-if="priceChange !== null"
              >
                {{ priceChange >= 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%
              </span>
            </div>
          </template>
          
          <KLineChart
            ref="chartRef"
            :symbol="selectedSymbol"
            :timeframe="currentTimeframe"
            :klines="klineData"
            :key-levels="keyLevels"
            :height="400"
          />
        </el-card>

        <!-- 技术指标面板 -->
        <el-card class="indicators-card" v-if="marketContext">
          <template #header>
            <span>
              <el-icon><DataAnalysis /></el-icon>
              技术指标
            </span>
          </template>
          
          <div class="indicators-grid">
            <div class="indicator">
              <span class="label">RSI(14)</span>
              <span 
                class="value"
                :class="getRsiClass(marketContext.indicators.rsi_14)"
              >
                {{ marketContext.indicators.rsi_14.toFixed(2) }}
              </span>
              <span class="status">
                {{ getRsiStatus(marketContext.indicators.rsi_14) }}
              </span>
            </div>
            
            <div class="indicator">
              <span class="label">MACD</span>
              <span 
                class="value"
                :class="marketContext.indicators.macd_histogram > 0 ? 'bullish' : 'bearish'"
              >
                {{ marketContext.indicators.macd_histogram > 0 ? '多头' : '空头' }}
              </span>
            </div>
            
            <div class="indicator">
              <span class="label">趋势</span>
              <el-tag
                :type="getTrendType(marketContext.indicators.trend_status) as any"
                size="small"
              >
                {{ getTrendLabel(marketContext.indicators.trend_status) }}
              </el-tag>
            </div>
            
            <div class="indicator">
              <span class="label">波动率</span>
              <span class="value">{{ marketContext.indicators.volatility_level }}</span>
            </div>
            
            <div class="indicator">
              <span class="label">MA状态</span>
              <span class="value small">{{ marketContext.indicators.ma_cross_status }}</span>
            </div>
            
            <div class="indicator">
              <span class="label">资金费率</span>
              <span 
                class="value"
                :class="(marketContext.funding_rate || 0) > 0 ? 'bullish' : 'bearish'"
              >
                {{ ((marketContext.funding_rate || 0) * 100).toFixed(4) }}%
              </span>
            </div>
          </div>
        </el-card>

        <!-- 市场深度透视 (新增) -->
        <MarketDepth 
          v-if="marketContext?.order_book"
          :order-book="marketContext.order_book"
        />

        <!-- 置信度显示 -->
        <el-card class="confidence-card" v-if="prediction">
          <template #header>
            <div class="card-title">
              <el-icon><TrendCharts /></el-icon>
              <span>AI 置信度</span>
            </div>
          </template>
          <div class="confidence-display">
            <el-progress 
              type="dashboard" 
              :percentage="prediction.confidence" 
              :color="[
                { color: '#f56c6c', percentage: 40 },
                { color: '#e6a23c', percentage: 70 },
                { color: '#5cb87a', percentage: 100 }
              ]"
            >
              <template #default="{ percentage }">
                <span class="confidence-value">{{ percentage }}%</span>
                <span class="confidence-label">可信度</span>
              </template>
            </el-progress>
          </div>
        </el-card>
      </div>

      <!-- 右侧：预测结果 -->
      <div class="result-section">
        <!-- 加载状态 -->
        <el-card v-if="isAnalyzing" class="loading-card">
          <div class="loading-content">
            <el-icon class="loading-icon" :size="48"><Loading /></el-icon>
            <h3>AI 正在分析中...</h3>
            <p>{{ loadingMessage }}</p>
            <el-progress
              :percentage="loadingProgress"
              :stroke-width="4"
              :show-text="false"
              status="success"
            />
          </div>
        </el-card>

        <!-- 预测结果卡片 -->
        <AIPredictionCard
          v-else-if="prediction"
          :prediction="prediction"
          @generate-strategy="handleGenerateStrategy"
          @refresh="startAnalysis"
        />

        <!-- 空状态 -->
        <el-card v-else class="empty-card">
          <el-empty description="点击"开始分析"获取 AI 预测">
            <el-button type="primary" @click="startAnalysis">
              <el-icon><MagicStick /></el-icon>
              开始分析
            </el-button>
          </el-empty>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, DataAnalysis, Loading, TrendCharts } from '@element-plus/icons-vue'
import { usePredictionStore } from '@/stores/usePredictionStore'
import KLineChart from './KLineChart.vue'
import AIPredictionCard from './AIPredictionCard.vue'
import MarketDepth from './MarketDepth.vue'
// ConfidenceChart removed
import type { PredictionResult } from '@/services/api'

// 使用Store
const predictionStore = usePredictionStore()

// 状态
const selectedSymbol = ref('ETHUSDT')
const currentTimeframe = ref('4h')
const loadingProgress = ref(0)
const loadingMessage = ref('正在获取市场数据...')

// 计算属性
const symbols = computed(() => predictionStore.symbols)
const isAnalyzing = computed(() => predictionStore.isAnalyzing)
const prediction = computed(() => predictionStore.prediction)
const marketContext = computed(() => predictionStore.marketContext)
const klineData = computed(() => predictionStore.klines)
const currentPrice = computed(() => marketContext.value?.current_price || 0)
const priceChange = computed(() => marketContext.value?.price_change_24h || null)

// 方法
function formatPrice(price: number): string {
  if (price >= 1000) {
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return price.toFixed(4)
}

function getRsiClass(rsi: number): string {
  if (rsi > 70) return 'overbought'
  if (rsi < 30) return 'oversold'
  return ''
}

function getRsiStatus(rsi: number): string {
  if (rsi > 70) return '超买'
  if (rsi < 30) return '超卖'
  return '中性'
}

function getTrendType(trend: string): string {
  if (trend === 'bullish') return 'success'
  if (trend === 'bearish') return 'danger'
  return 'info'
}

function getTrendLabel(trend: string): string {
  const labels: Record<string, string> = {
    bullish: '上涨趋势',
    bearish: '下跌趋势',
    neutral: '震荡'
  }
  return labels[trend] || '未知'
}

async function handleSymbolChange(symbol: string) {
  predictionStore.setSymbol(symbol)
  await predictionStore.loadMarketContext()
}

async function startAnalysis() {
  loadingProgress.value = 0
  loadingMessage.value = '正在获取市场数据...'
  
  // 模拟进度
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      
      if (loadingProgress.value >= 30) {
        loadingMessage.value = '正在计算技术指标...'
      }
      if (loadingProgress.value >= 60) {
        loadingMessage.value = 'AI 正在深度分析...'
      }
      if (loadingProgress.value >= 80) {
        loadingMessage.value = '生成预测报告...'
      }
    }
  }, 500)

  try {
    await predictionStore.analyze(currentTimeframe.value)
    loadingProgress.value = 100
    ElMessage.success('分析完成！')
  } catch (error: any) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    clearInterval(progressInterval)
  }
}

function handleGenerateStrategy(pred: any) {
  // 跳转到策略生成页面
  predictionStore.setStrategyMode(pred as PredictionResult)
}

// 计算关键价位
interface KeyLevelItem {
  price: number
  type: 'support' | 'resistance'
  label: string
}

const keyLevels = computed(() => {
  if (!predictionStore.prediction?.key_levels) return []
  
  const levels: KeyLevelItem[] = []
  const kl = predictionStore.prediction.key_levels
  
  // 转换新格式 (supports/resistances数组)
  if (Array.isArray(kl.supports)) {
    kl.supports.forEach((price: number) => {
      levels.push({ price, type: 'support', label: '支撑' })
    })
  }
  if (Array.isArray(kl.resistances)) {
    kl.resistances.forEach((price: number) => {
      levels.push({ price, type: 'resistance', label: '阻力' })
    })
  }
  
  // 兼容旧格式
  if (kl.strong_support) levels.push({ price: kl.strong_support, type: 'support', label: '强支撑' })
  if (kl.weak_support) levels.push({ price: kl.weak_support, type: 'support', label: '弱支撑' })
  if (kl.strong_resistance) levels.push({ price: kl.strong_resistance, type: 'resistance', label: '强阻力' })
  if (kl.weak_resistance) levels.push({ price: kl.weak_resistance, type: 'resistance', label: '弱阻力' })
  
  return levels
})

// 生命周期
onMounted(async () => {
  await predictionStore.loadSymbols()
  await predictionStore.loadMarketContext()
})

// 监听时间周期变化
watch(currentTimeframe, () => {
  predictionStore.clearPrediction()
})
</script>

<style lang="scss" scoped>
.prediction-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(10, 10, 15, 0.8);
  border-radius: 12px;
  margin-bottom: 16px;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
    
    h2 {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 18px;
      font-weight: 600;
      color: #fff;
      margin: 0;
    }
  }
  
  .header-controls {
    display: flex;
    align-items: center;
    gap: 16px;
  }
}

.symbol-option {
  display: flex;
  justify-content: space-between;
  width: 100%;
  
  .base {
    font-weight: 600;
  }
  
  .name {
    color: #8b949e;
    font-size: 12px;
  }
}

.panel-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 480px;
  gap: 20px;
  
  @media (max-width: 1400px) {
    grid-template-columns: 1fr;
  }
}

.chart-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-card {
  .chart-title {
    display: flex;
    align-items: baseline;
    gap: 16px;
    
    .symbol {
      font-size: 20px;
      font-weight: 700;
      color: #fff;
    }
    
    .price {
      font-size: 24px;
      font-weight: 600;
      color: #60a5fa;
    }
    
    .change {
      font-size: 14px;
      font-weight: 500;
      
      &.up { color: #10b981; }
      &.down { color: #ef4444; }
    }
  }
}

.indicators-card {
  .indicators-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    
    @media (max-width: 768px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  .indicator {
    display: flex;
    flex-direction: column;
    gap: 4px;
    
    .label {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }
    
    .value {
      font-size: 16px;
      font-weight: 600;
      color: #fff;
      
      &.bullish { color: #10b981; }
      &.bearish { color: #ef4444; }
      &.overbought { color: #ef4444; }
      &.oversold { color: #10b981; }
      &.small { font-size: 13px; }
    }
    
    .status {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.4);
    }
  }
}

.result-section {
  min-height: 600px;
}

.loading-card {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .loading-content {
    text-align: center;
    padding: 40px;
    
    .loading-icon {
      color: #3b82f6;
      animation: pulse 2s infinite;
    }
    
    h3 {
      margin: 20px 0 8px;
      font-size: 18px;
      color: #fff;
    }
    
    p {
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 24px;
    }
  }
}

.empty-card {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.confidence-display {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  
  .confidence-value {
    display: block;
    font-size: 24px;
    font-weight: 700;
    color: #fff;
  }
  
  .confidence-label {
    display: block;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    margin-top: 4px;
  }
}
</style>
