<!--
  智链预测 - AI分析页面 v2.0
  Premium Glassmorphism Design
-->
<template>
  <div class="analysis-page">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="orb orb-primary"></div>
      <div class="orb orb-accent"></div>
    </div>

    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1>
          <span class="icon-wrapper">
            <el-icon><MagicStick /></el-icon>
          </span>
          <span class="gradient-text">AI 预测分析</span>
        </h1>
        <p class="header-desc">基于多维数据的智能预测，提供概率性方向判断</p>
      </div>
      
      <div class="header-actions">
        <!-- 视图模式切换 -->
        <div class="view-toggle">
          <button 
            :class="['toggle-btn', { active: viewMode === 'wizard' }]" 
            @click="viewMode = 'wizard'"
          >
            🧙 向导模式
          </button>
          <button 
            :class="['toggle-btn', { active: viewMode === 'classic' }]" 
            @click="viewMode = 'classic'"
          >
            📊 传统模式
          </button>
        </div>
        
        <template v-if="viewMode === 'classic'">
          <div class="mode-controls">
            <el-tooltip content="开启后可看到AI实时推理过程" placement="bottom">
              <label class="stream-toggle">
                <input type="checkbox" v-model="streamingEnabled">
                <span class="toggle-slider"></span>
                <span class="toggle-label">流式模式</span>
              </label>
            </el-tooltip>
            
            <div class="timeframe-select">
              <button 
                v-for="tf in ['1h', '4h', '1d']" 
                :key="tf"
                :class="['tf-btn', { active: selectedTimeframe === tf }]"
                @click="selectedTimeframe = tf"
              >
                {{ tf.toUpperCase() }}
              </button>
            </div>

            <button class="action-btn secondary" @click="handleForceRefresh" :disabled="predictionStore.isAnalyzing">
              <el-icon><Refresh /></el-icon>
              <span>刷新缓存</span>
            </button>

            <button class="action-btn primary glow" @click="runAnalysis" :disabled="predictionStore.isAnalyzing">
              <el-icon v-if="!predictionStore.isAnalyzing"><MagicStick /></el-icon>
              <el-icon v-else class="animate-spin"><Loading /></el-icon>
              <span>{{ predictionStore.isAnalyzing ? '分析中...' : '开始分析' }}</span>
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- 向导模式 -->
    <PredictionWizard v-if="viewMode === 'wizard'" />

    <!-- 传统模式 -->
    <div v-else class="analysis-content">
      <!-- 左侧：K线图和市场数据 -->
      <div class="left-panel">

        <!-- AI 预测结果 -->
        <div class="prediction-section" v-if="predictionStore.prediction || predictionStore.streamingReasoning">
          <!-- 流式思考展示 -->
          <div v-if="predictionStore.isAnalyzing && predictionStore.streamingReasoning" class="glass-card streaming-card">
            <div class="streaming-header">
              <div class="pulse-dot"></div>
              <span>AI 正在实时推理中...</span>
            </div>
            <div ref="streamingContentRef" class="streaming-content markdown-body" v-html="renderedReasoning"></div>
          </div>

          <AIPredictionCard 
            v-if="predictionStore.prediction"
            :prediction="predictionStore.prediction" 
            :loading="predictionStore.isAnalyzing"
          />
        </div>

        <!-- 技术指标面板 -->
        <div class="glass-card indicators-card" v-if="predictionStore.marketContext">
          <div class="card-header">
            <el-icon><DataAnalysis /></el-icon>
            <span>技术指标</span>
          </div>
          
          <div class="indicators-grid">
            <div class="indicator-item">
              <span class="indicator-label">RSI(14)</span>
              <span class="indicator-value" :class="getRsiClass(predictionStore.marketContext.indicators.rsi_14)">
                {{ predictionStore.marketContext.indicators.rsi_14.toFixed(2) }}
              </span>
              <div class="indicator-bar">
                <div 
                  class="indicator-fill" 
                  :style="{ width: predictionStore.marketContext.indicators.rsi_14 + '%' }"
                  :class="getRsiClass(predictionStore.marketContext.indicators.rsi_14)"
                ></div>
              </div>
            </div>
            
            <div class="indicator-item">
              <span class="indicator-label">MACD</span>
              <span class="indicator-value" :class="predictionStore.marketContext.indicators.macd_histogram > 0 ? 'bullish' : 'bearish'">
                {{ predictionStore.marketContext.indicators.macd_histogram.toFixed(4) }}
              </span>
            </div>
            
            <div class="indicator-item">
              <span class="indicator-label">MA20</span>
              <span class="indicator-value">{{ formatPrice(predictionStore.marketContext.indicators.sma_20) }}</span>
            </div>
            
            <div class="indicator-item">
              <span class="indicator-label">MA50</span>
              <span class="indicator-value">{{ formatPrice(predictionStore.marketContext.indicators.sma_50) }}</span>
            </div>
            
            <div class="indicator-item">
              <span class="indicator-label">趋势状态</span>
              <span class="indicator-tag" :class="getTrendClass(predictionStore.marketContext.indicators.trend_status)">
                {{ predictionStore.marketContext.indicators.trend_status }}
              </span>
            </div>
            
            <div class="indicator-item">
              <span class="indicator-label">均线状态</span>
              <span class="indicator-value small">{{ predictionStore.marketContext.indicators.ma_cross_status }}</span>
            </div>
          </div>
        </div>
 
        <!-- 市场情绪 -->
        <div class="glass-card sentiment-card" v-if="predictionStore.marketContext">
          <div class="card-header">
            <el-icon><ChatLineRound /></el-icon>
            <span>市场情绪</span>
          </div>
          
          <div class="sentiment-content">
            <div class="sentiment-row">
              <span class="sentiment-label">资金费率</span>
              <span class="sentiment-value" :class="(predictionStore.marketContext.funding_rate || 0) > 0 ? 'bullish' : 'bearish'">
                {{ ((predictionStore.marketContext.funding_rate || 0) * 100).toFixed(4) }}%
              </span>
            </div>
            <div class="sentiment-row">
              <span class="sentiment-label">市场情绪</span>
              <span class="sentiment-value">{{ predictionStore.marketContext.market_sentiment }}</span>
            </div>
            
            <div class="news-section">
              <div class="news-title">相关新闻</div>
              <div class="news-list">
                <div
                  v-for="(news, index) in predictionStore.marketContext.news_headlines"
                  :key="index"
                  class="news-item"
                >
                  <span class="news-dot"></span>
                  {{ news }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：空状态 -->
      <div class="right-panel">
        <div v-if="!predictionStore.isAnalyzing && !predictionStore.prediction" class="glass-card empty-state">
          <div class="empty-icon">
            <el-icon :size="64"><MagicStick /></el-icon>
          </div>
          <h3>等待分析</h3>
          <p>点击"开始分析"获取 AI 预测结果</p>
          <button class="action-btn primary glow" @click="runAnalysis">
            <el-icon><MagicStick /></el-icon>
            <span>开始分析</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import {
  MagicStick,
  ChatLineRound,
  Loading,
  Refresh,
  DataAnalysis
} from '@element-plus/icons-vue'
import { usePredictionStore } from '@/stores/usePredictionStore'
import AIPredictionCard from '@/components/AIPredictionCard.vue'
import PredictionWizard from '@/components/PredictionWizard.vue'


const predictionStore = usePredictionStore()

const selectedTimeframe = ref('4h')
const streamingEnabled = ref(true)
const viewMode = ref<'wizard' | 'classic'>('wizard')
const streamingContentRef = ref<HTMLElement | null>(null)

// Markdown 渲染
const renderedReasoning = computed(() => {
  return marked.parse(predictionStore.streamingReasoning)
})

// 自动滚动到底部
watch(() => predictionStore.streamingReasoning, () => {
  nextTick(() => {
    if (streamingContentRef.value) {
      const container = streamingContentRef.value.parentElement
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }
  })
})

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

function getTrendClass(trend: string): string {
  if (trend === 'bullish') return 'bullish'
  if (trend === 'bearish') return 'bearish'
  return 'neutral'
}

const runAnalysis = async () => {
  try {
    if (streamingEnabled.value) {
      await predictionStore.analyzeStream(selectedTimeframe.value)
    } else {
      await predictionStore.analyze(selectedTimeframe.value)
    }
    ElMessage.success(`${predictionStore.currentSymbol} 分析完成`)
  } catch (error) {
    console.error('Analysis failed:', error)
    ElMessage.error('分析失败，请稍后重试')
  }
}

const handleForceRefresh = async () => {
  try {
    await predictionStore.forceRefresh(selectedTimeframe.value)
    ElMessage.success('缓存已清除，正在重新分析...')
  } catch (error) {
    console.error('Force refresh failed:', error)
    ElMessage.error('刷新缓存失败，请稍后重试')
  }
}

onMounted(async () => {
  if (!predictionStore.marketContext) {
    await predictionStore.loadMarketContext()
  }
})

watch(() => predictionStore.currentSymbol, () => {
  predictionStore.loadMarketContext()
  predictionStore.clearPrediction()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.analysis-page {
  position: relative;
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 24px 48px;
}

// 背景装饰
.bg-decoration {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: -1;
  
  .orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(100px);
  }
  
  .orb-primary {
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, transparent 70%);
    top: -100px;
    right: 10%;
  }
  
  .orb-accent {
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(168, 85, 247, 0.15) 0%, transparent 70%);
    bottom: 20%;
    left: -100px;
  }
}

// 页面头部
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 20px;
}

.header-left {
  h1 {
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 8px;
  }
  
  .icon-wrapper {
    width: 48px;
    height: 48px;
    background: $gradient-primary;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }
  
  .header-desc {
    color: $text-muted;
    font-size: 14px;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

// 视图切换
.view-toggle {
  display: flex;
  background: $bg-surface-2;
  border: 1px solid $border-default;
  border-radius: $radius-md;
  padding: 4px;
  
  .toggle-btn {
    padding: 10px 20px;
    background: transparent;
    border: none;
    border-radius: $radius-sm;
    color: $text-secondary;
    font-size: 14px;
    cursor: pointer;
    transition: all $transition-fast;
    
    &.active {
      background: $gradient-primary;
      color: white;
    }
    
    &:hover:not(.active) {
      color: $text-primary;
    }
  }
}

.mode-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

// 流式开关
.stream-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  
  input {
    display: none;
  }
  
  .toggle-slider {
    width: 44px;
    height: 24px;
    background: $bg-surface-3;
    border-radius: $radius-full;
    position: relative;
    transition: all $transition-fast;
    
    &::after {
      content: '';
      position: absolute;
      width: 18px;
      height: 18px;
      background: white;
      border-radius: 50%;
      top: 3px;
      left: 3px;
      transition: all $transition-fast;
    }
  }
  
  input:checked + .toggle-slider {
    background: $color-primary;
    
    &::after {
      left: 23px;
    }
  }
  
  .toggle-label {
    color: $text-secondary;
    font-size: 14px;
  }
}

// 时间周期
.timeframe-select {
  display: flex;
  background: $bg-surface-2;
  border: 1px solid $border-default;
  border-radius: $radius-md;
  padding: 4px;
  
  .tf-btn {
    padding: 8px 16px;
    background: transparent;
    border: none;
    border-radius: $radius-sm;
    color: $text-secondary;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all $transition-fast;
    
    &.active {
      background: $color-primary;
      color: white;
    }
    
    &:hover:not(.active) {
      color: $text-primary;
    }
  }
}

// 操作按钮
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: $radius-md;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all $transition-normal;
  
  &.primary {
    background: $gradient-primary;
    color: white;
    
    &.glow {
      box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
      
      &:hover {
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5);
        transform: translateY(-2px);
      }
    }
  }
  
  &.secondary {
    background: $bg-surface-3;
    color: $text-primary;
    border: 1px solid $border-default;
    
    &:hover {
      background: $bg-surface-2;
      border-color: $color-primary;
    }
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none !important;
  }
}

// 分析内容
.analysis-content {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 24px;
  
  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-panel {
  min-height: 600px;
}

// 玻璃卡片
.glass-card {
  background: $bg-surface-2;
  backdrop-filter: blur($blur-md);
  border: 1px solid $border-default;
  border-radius: $radius-lg;
  padding: 24px;
  transition: all $transition-normal;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 20px;
}

// 图表卡片
.chart-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  
  .symbol-info {
    display: flex;
    align-items: baseline;
    gap: 16px;
    
    .symbol-name {
      font-size: 24px;
      font-weight: 700;
      color: $text-primary;
    }
    
    .symbol-price {
      font-size: 28px;
      font-weight: 600;
      font-family: $font-mono;
      background: $gradient-primary;
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }
  
  .timeframe-pills {
    display: flex;
    gap: 8px;
    
    .pill {
      padding: 6px 14px;
      background: $bg-surface-3;
      border: 1px solid $border-subtle;
      border-radius: $radius-full;
      color: $text-secondary;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all $transition-fast;
      
      &.active {
        background: $color-primary;
        border-color: $color-primary;
        color: white;
      }
      
      &:hover:not(.active) {
        border-color: $color-primary;
        color: $color-primary;
      }
    }
  }
}

.chart-container {
  height: 400px;
}

.chart-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: $bg-glass;
  border: 1px dashed $border-subtle;
  border-radius: $radius-md;
  color: $text-muted;
  
  .placeholder-icon {
    width: 80px;
    height: 80px;
    background: $bg-surface-3;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }
  
  p {
    font-size: 16px;
    margin-bottom: 8px;
  }
  
  .hint {
    font-size: 13px;
  }
}

// 流式卡片
.streaming-card {
  border-color: rgba($color-primary, 0.4);
  position: relative;
  overflow: hidden;
  margin-bottom: 20px;
  
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba($color-primary, 0.05) 0%, transparent 50%);
    pointer-events: none;
  }
  
  .streaming-header {
    display: flex;
    align-items: center;
    gap: 12px;
    color: $color-primary-light;
    font-weight: 600;
    margin-bottom: 16px;
  }
  
  .pulse-dot {
    width: 10px;
    height: 10px;
    background: $color-primary;
    border-radius: 50%;
    animation: pulse-glow 1.5s infinite;
  }
  
  .streaming-content {
    max-height: 300px;
    overflow-y: auto;
    font-size: 14px;
    line-height: 1.8;
    color: $text-secondary;
    
    :deep(p) { margin-bottom: 12px; }
    :deep(ul, ol) { padding-left: 20px; margin-bottom: 12px; }
    :deep(code) {
      background: rgba(255, 255, 255, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
    }
  }
}

// 指标卡片
.indicators-card {
  .indicators-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    
    @media (max-width: 768px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  .indicator-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  .indicator-label {
    font-size: 12px;
    color: $text-muted;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .indicator-value {
    font-size: 18px;
    font-weight: 600;
    font-family: $font-mono;
    color: $text-primary;
    
    &.bullish { color: $color-success; }
    &.bearish { color: $color-danger; }
    &.overbought { color: $color-danger; }
    &.oversold { color: $color-success; }
    &.small { font-size: 14px; }
  }
  
  .indicator-bar {
    height: 4px;
    background: $bg-surface-3;
    border-radius: $radius-full;
    overflow: hidden;
    
    .indicator-fill {
      height: 100%;
      border-radius: $radius-full;
      background: $color-info;
      transition: width $transition-normal;
      
      &.overbought { background: $color-danger; }
      &.oversold { background: $color-success; }
    }
  }
  
  .indicator-tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: $radius-full;
    font-size: 12px;
    font-weight: 600;
    
    &.bullish {
      background: rgba($color-success, 0.15);
      color: $color-success;
    }
    
    &.bearish {
      background: rgba($color-danger, 0.15);
      color: $color-danger;
    }
    
    &.neutral {
      background: rgba($color-info, 0.15);
      color: $color-info;
    }
  }
}

// 情绪卡片
.sentiment-card {
  .sentiment-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .sentiment-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .sentiment-label {
    font-size: 14px;
    color: $text-secondary;
  }
  
  .sentiment-value {
    font-weight: 600;
    
    &.bullish { color: $color-success; }
    &.bearish { color: $color-danger; }
  }
  
  .news-section {
    padding-top: 16px;
    border-top: 1px solid $border-subtle;
  }
  
  .news-title {
    font-size: 12px;
    color: $text-muted;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }
  
  .news-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .news-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 13px;
    color: $text-secondary;
    line-height: 1.5;
  }
  
  .news-dot {
    width: 6px;
    height: 6px;
    background: $color-primary;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
  }
}

// 空状态
.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px;
  
  .empty-icon {
    width: 120px;
    height: 120px;
    background: $bg-surface-3;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text-muted;
    margin-bottom: 24px;
  }
  
  h3 {
    font-size: 20px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 8px;
  }
  
  p {
    font-size: 14px;
    color: $text-muted;
    margin-bottom: 24px;
  }
}

// 动画
@keyframes pulse-glow {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba($color-primary, 0.4);
  }
  50% {
    opacity: 0.8;
    box-shadow: 0 0 0 8px rgba($color-primary, 0);
  }
}
</style>
