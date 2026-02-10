<!--
  智链预测 - 动态AI预测展示卡片
  ================================
  折叠式设计、渐变背景、环形置信度、智能高亮、历史对比
  
  技术栈: Vue 3 + TypeScript + Element Plus
-->
<template>
  <div 
    class="prediction-card" 
    :class="[directionClass, { expanded: isExpanded, loading: isLoading }]"
  >
    <!-- 骨架屏加载状态 -->
    <template v-if="isLoading">
      <div class="skeleton-header">
        <div class="skeleton-line w-40"></div>
        <div class="skeleton-circle"></div>
      </div>
      <div class="skeleton-body">
        <div class="skeleton-line w-full"></div>
        <div class="skeleton-line w-80"></div>
        <div class="skeleton-line w-60"></div>
      </div>
    </template>

    <!-- 正常内容 -->
    <template v-else-if="prediction">
      <!-- 头部（始终可见） -->
      <div class="card-header" @click="toggleExpand">
        <div class="header-left">
          <!-- 交易对标识 -->
          <div class="symbol-badge font-display">
            <span class="symbol-icon">{{ getSymbolIcon(prediction.symbol) }}</span>
            <span class="symbol-name">{{ prediction.symbol }}</span>
          </div>
          
          <!-- 预测方向标签 -->
          <div class="direction-tag font-display" :class="directionClass">
            <span class="direction-icon">{{ directionIcon }}</span>
            <span class="direction-text">{{ directionLabel }}</span>
          </div>
        </div>

        <div class="header-right">
          <!-- 置信度环形进度条 -->
          <div class="confidence-ring">
            <svg viewBox="0 0 36 36" class="ring-svg">
              <circle 
                cx="18" cy="18" r="14" 
                fill="none" 
                stroke="rgba(255,255,255,0.1)" 
                stroke-width="3"
              />
              <circle 
                cx="18" cy="18" r="14" 
                fill="none" 
                :stroke="confidenceColor"
                stroke-width="3"
                stroke-linecap="round"
                :stroke-dasharray="`${confidenceArc} 88`"
                class="ring-progress"
              />
            </svg>
            <span class="ring-value font-tabular">{{ prediction.confidence }}%</span>
          </div>

          <!-- 时间戳和刷新 -->
          <div class="time-info font-tabular">
            <span class="timestamp">{{ formatTime(prediction.timestamp) }}</span>
            <button class="refresh-btn" @click.stop="handleRefresh" :disabled="isRefreshing">
              <el-icon :class="{ spin: isRefreshing }"><Refresh /></el-icon>
            </button>
          </div>

          <!-- 展开/收起图标 -->
          <el-icon class="expand-icon" :class="{ expanded: isExpanded }">
            <ArrowDown />
          </el-icon>
        </div>
      </div>

      <!-- 折叠状态的关键摘要 -->
      <div class="summary-preview" v-if="!isExpanded">
        <p class="summary-text font-sans leading-relaxed text-slate-300" v-html="highlightKeywords(prediction.summary)"></p>
        
        <!-- 历史准确率 -->
        <div class="accuracy-badge font-display" v-if="accuracyRate !== null">
          <span class="accuracy-label">历史准确率</span>
          <span class="accuracy-value font-tabular" :class="accuracyClass">{{ accuracyRate }}%</span>
        </div>
      </div>

      <!-- 展开状态的完整内容 -->
      <transition name="expand">
        <div v-show="isExpanded" class="card-body">
          <!-- 分析逻辑分段 -->
          <div class="analysis-sections">
            <!-- 技术面分析 -->
            <div class="analysis-section">
              <div class="section-header font-display">
                <el-icon><TrendCharts /></el-icon>
                <span>技术面分析</span>
              </div>
              <div class="section-content font-sans">
                <p class="leading-relaxed text-slate-300" v-html="highlightKeywords(prediction.reasoning?.technical || '暂无技术分析')"></p>
                
                <!-- 技术指标缩略图 -->
                <div class="indicators-mini font-tabular" v-if="prediction.indicators">
                  <div class="indicator-chip" v-for="(value, key) in prediction.indicators" :key="key">
                    <span class="chip-label font-display">{{ key }}</span>
                    <span class="chip-value" :class="getIndicatorClass(String(key), value as any)">{{ formatIndicator(value as any) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 情绪面分析 -->
            <div class="analysis-section">
              <div class="section-header font-display">
                <el-icon><ChatLineRound /></el-icon>
                <span>情绪面分析</span>
              </div>
              <div class="section-content font-sans">
                <p class="leading-relaxed text-slate-300" v-html="highlightKeywords(prediction.reasoning?.sentiment || '暂无情绪分析')"></p>
                
                <!-- 情绪仪表盘 -->
                <div class="sentiment-gauge" v-if="prediction.sentimentScore !== undefined">
                  <div class="gauge-bar">
                    <div 
                      class="gauge-fill" 
                      :style="{ width: prediction.sentimentScore + '%' }"
                      :class="sentimentClass"
                    ></div>
                    <div class="gauge-pointer" :style="{ left: prediction.sentimentScore + '%' }"></div>
                  </div>
                  <div class="gauge-labels font-display">
                    <span>恐惧</span>
                    <span>中性</span>
                    <span>贪婪</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 资金面分析 -->
            <div class="analysis-section">
              <div class="section-header font-display">
                <el-icon><Money /></el-icon>
                <span>资金面分析</span>
              </div>
              <div class="section-content font-sans">
                <p class="leading-relaxed text-slate-300" v-html="highlightKeywords(prediction.reasoning?.macro || '暂无资金分析')"></p>
                
                <!-- 资金流向指示 -->
                <div class="fund-flow font-tabular" v-if="prediction.fundFlow">
                  <div class="flow-item inflow">
                    <span class="flow-label font-display">流入</span>
                    <span class="flow-value">{{ formatFundFlow(prediction.fundFlow.inflow) }}</span>
                  </div>
                  <div class="flow-item outflow">
                    <span class="flow-label font-display">流出</span>
                    <span class="flow-value">{{ formatFundFlow(prediction.fundFlow.outflow) }}</span>
                  </div>
                  <div class="flow-item net" :class="prediction.fundFlow.net >= 0 ? 'positive' : 'negative'">
                    <span class="flow-label font-display">净流入</span>
                    <span class="flow-value">{{ formatFundFlow(prediction.fundFlow.net) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 风险等级评估 -->
          <div class="risk-assessment">
            <span class="risk-label font-display">风险等级</span>
            <div class="risk-stars">
              <span 
                v-for="i in 5" 
                :key="i" 
                class="star"
                :class="{ filled: i <= riskLevel, warning: riskLevel >= 4 && i <= riskLevel }"
              >★</span>
            </div>
            <span class="risk-text font-display">{{ riskLevelText }}</span>
          </div>

          <!-- 交易信号详情 -->
          <div class="trade-signals" v-if="prediction.trading_signals?.length">
            <div class="signals-header font-display">交易信号</div>
            <div class="signal-cards">
              <div 
                v-for="(signal, idx) in prediction.trading_signals" 
                :key="idx"
                class="signal-card font-tabular"
                :class="signal.type.toLowerCase()"
              >
                <div class="signal-type font-display">{{ signal.type }}</div>
                <div class="signal-details">
                  <div class="detail-row">
                    <span class="font-display">入场</span>
                    <span>{{ formatPrice(signal.entry) }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="font-display">止损</span>
                    <span class="stop-loss">{{ formatPrice(signal.stop_loss) }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="font-display">止盈</span>
                    <span class="take-profit">{{ formatPrice(signal.take_profit?.[0]) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 历史对比 -->
          <div class="history-compare" v-if="predictionHistory.length">
            <div class="compare-header font-display">
              <span>历史对比</span>
              <span class="model-version font-tabular">模型: {{ prediction.modelVersion || 'v2.0' }}</span>
            </div>
            <div class="compare-stats font-tabular">
              <div class="stat-item">
                <span class="stat-value font-bold" :class="accuracyClass">{{ accuracyRate }}%</span>
                <span class="stat-label font-display text-xs">准确率</span>
              </div>
              <div class="stat-item">
                <span class="stat-value font-bold">{{ predictionHistory.length }}</span>
                <span class="stat-label font-display text-xs">历史预测</span>
              </div>
              <div class="stat-item">
                <span class="stat-value font-bold" :class="trendChange >= 0 ? 'positive' : 'negative'">
                  {{ trendChange >= 0 ? '+' : '' }}{{ trendChange }}%
                </span>
                <span class="stat-label font-display text-xs">vs 上次</span>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 底部操作区 -->
      <div class="card-footer font-display">
        <button class="action-btn copy" @click="copyStrategy">
          <el-icon><DocumentCopy /></el-icon>
          <span>复制策略</span>
        </button>
        <button class="action-btn watch" @click="addToWatchlist">
          <el-icon><Star /></el-icon>
          <span>关注</span>
        </button>
        <button class="action-btn share" @click="shareAnalysis">
          <el-icon><Share /></el-icon>
          <span>分享</span>
        </button>
        <div class="feedback-btns">
          <button 
            class="feedback-btn correct" 
            :class="{ active: feedback === 'correct' }"
            @click="submitFeedback('correct')"
          >
            <el-icon><Check /></el-icon>
          </button>
          <button 
            class="feedback-btn wrong"
            :class="{ active: feedback === 'wrong' }"
            @click="submitFeedback('wrong')"
          >
            <el-icon><Close /></el-icon>
          </button>
        </div>
      </div>
    </template>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <el-icon><WarningFilled /></el-icon>
      <p>{{ error }}</p>
      <button class="retry-btn" @click="handleRefresh">重试</button>
    </div>

    <!-- 脉动动画（活跃状态） -->
    <div v-if="isActive && !isLoading" class="pulse-indicator"></div>

    <!-- 术语解释浮窗 -->
    <transition name="fade">
      <div 
        v-if="termTooltip.visible" 
        class="term-tooltip"
        :style="{ left: termTooltip.x + 'px', top: termTooltip.y + 'px' }"
      >
        <div class="tooltip-title">{{ termTooltip.term }}</div>
        <p class="tooltip-content">{{ termTooltip.definition }}</p>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Refresh,
  TrendCharts,
  ChatLineRound,
  Money,
  DocumentCopy,
  Star,
  Share,
  Check,
  Close,
  WarningFilled
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

// ============================================================
// Props & Emits
// ============================================================

interface TradingSignal {
  type: 'LONG' | 'SHORT' | 'WAIT'
  entry?: number
  stop_loss?: number
  take_profit?: number[]
}

interface Prediction {
  symbol: string
  prediction: string
  confidence: number
  summary: string
  timestamp: string | number
  reasoning?: {
    technical?: string
    sentiment?: string
    macro?: string
  }
  risk_level?: string
  indicators?: Record<string, number>
  sentimentScore?: number
  fundFlow?: {
    inflow: number
    outflow: number
    net: number
  }
  trading_signals?: TradingSignal[]
  modelVersion?: string
}

const props = defineProps(['prediction', 'isLoading', 'error', 'isActive', 'predictionHistory'])

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'copy', strategy: string): void
  (e: 'watch', symbol: string): void
  (e: 'share', prediction: Prediction): void
  (e: 'feedback', type: 'correct' | 'wrong'): void
}>()

// ============================================================
// 状态
// ============================================================

const isExpanded = ref(false)
const isRefreshing = ref(false)
const feedback = ref<'correct' | 'wrong' | null>(null)

const termTooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  term: '',
  definition: ''
})

// 技术术语字典
const termDictionary: Record<string, string> = {
  '突破': '价格突破关键支撑或阻力位，通常意味着趋势的延续或反转',
  '回调': '价格在趋势中暂时逆向运动，通常是健康的价格修正',
  '背离': '价格走势与技术指标方向相反，可能预示趋势反转',
  '金叉': '短期均线上穿长期均线，被视为买入信号',
  '死叉': '短期均线下穿长期均线，被视为卖出信号',
  '超买': 'RSI等指标显示资产被过度买入，可能面临回调',
  '超卖': 'RSI等指标显示资产被过度卖出，可能面临反弹',
  '支撑位': '价格下跌时可能遇到买盘的价格水平',
  '阻力位': '价格上涨时可能遇到卖盘的价格水平',
  '趋势线': '连接价格高点或低点形成的斜线，用于判断趋势'
}

// ============================================================
// 计算属性
// ============================================================

const directionClass = computed(() => {
  const dir = props.prediction?.prediction || ''
  if (dir.includes('涨') || dir.includes('bullish')) return 'bullish'
  if (dir.includes('跌') || dir.includes('bearish')) return 'bearish'
  return 'neutral'
})

const directionIcon = computed(() => {
  if (directionClass.value === 'bullish') return '↑'
  if (directionClass.value === 'bearish') return '↓'
  return '→'
})

const directionLabel = computed(() => {
  const conf = props.prediction?.confidence || 0
  if (conf >= 80) {
    return directionClass.value === 'bullish' ? '强烈看涨' : 
           directionClass.value === 'bearish' ? '强烈看跌' : '中性'
  }
  return directionClass.value === 'bullish' ? '看涨' : 
         directionClass.value === 'bearish' ? '看跌' : '中性'
})

const confidenceColor = computed(() => {
  const conf = props.prediction?.confidence || 0
  if (conf < 50) return '#ef4444'
  if (conf < 70) return '#f59e0b'
  return '#10b981'
})

const confidenceArc = computed(() => {
  const conf = props.prediction?.confidence || 0
  return (conf / 100) * 88 // 2 * PI * 14
})

const riskLevel = computed(() => {
  const level = props.prediction?.risk_level || '中'
  if (level === '低' || level === 'low') return 1
  if (level === '中' || level === 'medium') return 3
  if (level === '高' || level === 'high') return 4
  if (level === '极高') return 5
  return 3
})

const riskLevelText = computed(() => {
  if (riskLevel.value <= 1) return '低风险'
  if (riskLevel.value <= 2) return '较低风险'
  if (riskLevel.value <= 3) return '中等风险'
  if (riskLevel.value <= 4) return '较高风险'
  return '高风险'
})

const sentimentClass = computed(() => {
  const score = props.prediction?.sentimentScore || 50
  if (score < 35) return 'fear'
  if (score > 65) return 'greed'
  return 'neutral'
})

const accuracyRate = computed(() => {
  if (!props.predictionHistory.length) return null
  const correct = props.predictionHistory.filter((p: any) => p.correct).length
  return Math.round((correct / props.predictionHistory.length) * 100)
})

const accuracyClass = computed(() => {
  if (accuracyRate.value === null) return ''
  if (accuracyRate.value >= 70) return 'good'
  if (accuracyRate.value >= 50) return 'medium'
  return 'poor'
})

// 上次预测对比变化 (应从 props 或真实数据获取，暂时固定为 0)
const trendChange = ref(0)

// ============================================================
// 方法
// ============================================================

function getSymbolIcon(symbol: string): string {
  if (symbol?.includes('BTC')) return '₿'
  if (symbol?.includes('ETH')) return 'Ξ'
  if (symbol?.includes('SOL')) return '◎'
  if (symbol?.includes('BNB')) return '◆'
  return '◇'
}

function formatTime(timestamp: string | number): string {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('HH:mm:ss')
}

function formatPrice(price?: number): string {
  if (!price) return '-'
  if (price >= 1000) {
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return price.toFixed(4)
}

function formatIndicator(value: string | number): string {
  if (value === undefined || value === null) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  return num.toFixed(2)
}

function formatFundFlow(value: number): string {
  if (!value) return '-'
  const abs = Math.abs(value)
  if (abs >= 1e9) return (value / 1e9).toFixed(2) + 'B'
  if (abs >= 1e6) return (value / 1e6).toFixed(2) + 'M'
  if (abs >= 1e3) return (value / 1e3).toFixed(2) + 'K'
  return value.toFixed(2)
}

function getIndicatorClass(key: string, value: number | string): string {
  const numValue = typeof value === 'string' ? parseFloat(value) : value
  if (key.toUpperCase() === 'RSI') {
    if (numValue < 30) return 'oversold'
    if (numValue > 70) return 'overbought'
  }
  return ''
}

function highlightKeywords(text: string): string {
  if (!text) return ''
  
  let result = text
  const keywords = Object.keys(termDictionary)
  
  keywords.forEach(keyword => {
    const regex = new RegExp(`(${keyword})`, 'g')
    result = result.replace(regex, `<span class="keyword" data-term="${keyword}">$1</span>`)
  })
  
  return result
}

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

async function handleRefresh() {
  isRefreshing.value = true
  emit('refresh')
  await new Promise(resolve => setTimeout(resolve, 1000))
  isRefreshing.value = false
}

function copyStrategy() {
  if (!props.prediction) return
  
  const signals = props.prediction.trading_signals
  if (!signals?.length) {
    ElMessage.warning('暂无交易信号可复制')
    return
  }
  
  const text = signals.map((s: TradingSignal) => 
    `${props.prediction!.symbol} ${s.type}\n入场: ${formatPrice(s.entry)}\n止损: ${formatPrice(s.stop_loss)}\n止盈: ${s.take_profit?.map(formatPrice).join('/')}`
  ).join('\n\n')
  
  navigator.clipboard.writeText(text)
  ElMessage.success('策略已复制到剪贴板')
  emit('copy', text)
}

function addToWatchlist() {
  if (props.prediction?.symbol) {
    emit('watch', props.prediction.symbol)
    ElMessage.success(`${props.prediction.symbol} 已添加到观察列表`)
  }
}

function shareAnalysis() {
  if (props.prediction) {
    emit('share', props.prediction)
    ElMessage.info('分享功能开发中')
  }
}

function submitFeedback(type: 'correct' | 'wrong') {
  feedback.value = type
  emit('feedback', type)
  ElMessage.success(type === 'correct' ? '感谢反馈！预测正确' : '感谢反馈！我们会继续改进')
}

// 监听点击高亮关键词
function handleKeywordClick(event: Event) {
  const target = event.target as HTMLElement
  if (target.classList.contains('keyword')) {
    const term = target.dataset.term || ''
    const rect = target.getBoundingClientRect()
    
    termTooltip.value = {
      visible: true,
      x: rect.left,
      y: rect.bottom + 8,
      term,
      definition: termDictionary[term] || ''
    }
    
    setTimeout(() => {
      termTooltip.value.visible = false
    }, 4000)
  }
}

// 监听展开状态变化
const keywordClickHandlers: Array<{ el: Element, handler: (e: Event) => void }> = []

watch(isExpanded, (expanded) => {
  if (expanded) {
    // 展开时添加关键词点击监听
    setTimeout(() => {
      document.querySelectorAll('.prediction-card .keyword').forEach(el => {
        const handler = (e: Event) => handleKeywordClick(e)
        el.addEventListener('click', handler)
        keywordClickHandlers.push({ el, handler })
      })
    }, 100)
  } else {
    // 收起时移除监听器
    keywordClickHandlers.forEach(({ el, handler }) => {
      el.removeEventListener('click', handler)
    })
    keywordClickHandlers.length = 0
  }
})

// 组件卸载时清理
onUnmounted(() => {
  keywordClickHandlers.forEach(({ el, handler }) => {
    el.removeEventListener('click', handler)
  })
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.prediction-card {
  position: relative;
  background: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
  transition: all 0.3s ease;
  
  &.bullish {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(30, 41, 59, 0.8) 50%);
    border-color: rgba(16, 185, 129, 0.3);
  }
  
  &.bearish {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(30, 41, 59, 0.8) 50%);
    border-color: rgba(239, 68, 68, 0.3);
  }
  
  &.expanded {
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }
  
  &.loading {
    min-height: 200px;
  }
}

// 骨架屏
.skeleton-header,
.skeleton-body {
  padding: 16px;
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 10px;
  
  &.w-40 { width: 40%; }
  &.w-60 { width: 60%; }
  &.w-80 { width: 80%; }
  &.w-full { width: 100%; }
}

.skeleton-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

// 头部
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  cursor: pointer;
  
  &:hover {
    background: rgba(255, 255, 255, 0.02);
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.symbol-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  
  .symbol-icon {
    font-size: 18px;
  }
  
  .symbol-name {
    font-weight: 600;
    font-size: 14px;
    color: #fff;
  }
}

.direction-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 13px;
  
  &.bullish {
    background: linear-gradient(135deg, #10b981, #34d399);
    color: #fff;
  }
  
  &.bearish {
    background: linear-gradient(135deg, #ef4444, #f87171);
    color: #fff;
  }
  
  &.neutral {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.7);
  }
  
  .direction-icon {
    font-size: 16px;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.confidence-ring {
  position: relative;
  width: 48px;
  height: 48px;
  
  .ring-svg {
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
  }
  
  .ring-progress {
    transition: stroke-dasharray 0.5s ease;
  }
  
  .ring-value {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 11px;
    font-weight: 700;
    color: #fff;
  }
}

.time-info {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .timestamp {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
  
  .refresh-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 6px;
    color: rgba(255, 255, 255, 0.6);
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: rgba($color-primary, 0.2);
      color: $color-primary;
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    
    .spin {
      animation: spin 1s linear infinite;
    }
  }
}

.expand-icon {
  transition: transform 0.3s ease;
  color: rgba(255, 255, 255, 0.5);
  
  &.expanded {
    transform: rotate(180deg);
  }
}

// 摘要预览
.summary-preview {
  padding: 0 16px 16px;
  
  .summary-text {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.6;
    margin-bottom: 12px;
    
    :deep(.keyword) {
      color: $color-primary-light;
      cursor: pointer;
      border-bottom: 1px dashed $color-primary;
      
      &:hover {
        color: $color-primary;
      }
    }
  }
  
  .accuracy-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    font-size: 12px;
    
    .accuracy-label {
      color: rgba(255, 255, 255, 0.5);
    }
    
    .accuracy-value {
      font-weight: 600;
      
      &.good { color: $color-success; }
      &.medium { color: $color-warning; }
      &.poor { color: $color-danger; }
    }
  }
}

// 展开内容
.card-body {
  padding: 0 16px 16px;
}

.analysis-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;
}

.analysis-section {
  padding: 14px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  
  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-weight: 600;
    font-size: 13px;
    color: $color-primary-light;
  }
  
  .section-content {
    p {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.6;
      margin: 0 0 12px;
      
      :deep(.keyword) {
        color: $color-primary-light;
        cursor: pointer;
        border-bottom: 1px dashed $color-primary;
      }
    }
  }
}

.indicators-mini {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  
  .indicator-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    font-size: 11px;
    
    .chip-label {
      color: rgba(255, 255, 255, 0.5);
    }
    
    .chip-value {
      font-weight: 600;
      color: #fff;
      
      &.oversold { color: $color-success; }
      &.overbought { color: $color-danger; }
    }
  }
}

.sentiment-gauge {
  .gauge-bar {
    position: relative;
    height: 8px;
    background: linear-gradient(to right, #ef4444, #f59e0b, #10b981);
    border-radius: 4px;
    margin-bottom: 6px;
    
    .gauge-fill {
      position: absolute;
      top: 0;
      left: 0;
      height: 100%;
      background: rgba(255, 255, 255, 0.3);
      border-radius: 4px;
    }
    
    .gauge-pointer {
      position: absolute;
      top: -4px;
      width: 4px;
      height: 16px;
      background: #fff;
      border-radius: 2px;
      transform: translateX(-50%);
    }
  }
  
  .gauge-labels {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: rgba(255, 255, 255, 0.4);
  }
}

.fund-flow {
  display: flex;
  gap: 12px;
  
  .flow-item {
    flex: 1;
    padding: 8px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    text-align: center;
    
    .flow-label {
      display: block;
      font-size: 10px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 4px;
    }
    
    .flow-value {
      font-size: 13px;
      font-weight: 600;
      color: #fff;
    }
    
    &.inflow .flow-value { color: $color-success; }
    &.outflow .flow-value { color: $color-danger; }
    &.net.positive .flow-value { color: $color-success; }
    &.net.negative .flow-value { color: $color-danger; }
  }
}

// 风险评估
.risk-assessment {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  margin-bottom: 16px;
  
  .risk-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
  
  .risk-stars {
    display: flex;
    gap: 2px;
    
    .star {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.2);
      
      &.filled {
        color: $color-warning;
      }
      
      &.warning {
        color: $color-danger;
      }
    }
  }
  
  .risk-text {
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
  }
}

// 交易信号
.trade-signals {
  margin-bottom: 16px;
  
  .signals-header {
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 10px;
  }
  
  .signal-cards {
    display: flex;
    gap: 12px;
  }
  
  .signal-card {
    flex: 1;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    border-left: 3px solid;
    
    &.long { border-color: $color-success; }
    &.short { border-color: $color-danger; }
    &.wait { border-color: $color-warning; }
    
    .signal-type {
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 8px;
      
      .long & { color: $color-success; }
      .short & { color: $color-danger; }
      .wait & { color: $color-warning; }
    }
    
    .signal-details {
      .detail-row {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        margin-bottom: 4px;
        
        span:first-child {
          color: rgba(255, 255, 255, 0.5);
        }
        
        span:last-child {
          font-weight: 600;
          color: #fff;
          
          &.stop-loss { color: $color-danger; }
          &.take-profit { color: $color-success; }
        }
      }
    }
  }
}

// 历史对比
.history-compare {
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  
  .compare-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    
    span:first-child {
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.7);
    }
    
    .model-version {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.4);
    }
  }
  
  .compare-stats {
    display: flex;
    gap: 16px;
    
    .stat-item {
      flex: 1;
      text-align: center;
      
      .stat-value {
        display: block;
        font-size: 18px;
        font-weight: 700;
        color: #fff;
        
        &.good { color: $color-success; }
        &.medium { color: $color-warning; }
        &.poor { color: $color-danger; }
        &.positive { color: $color-success; }
        &.negative { color: $color-danger; }
      }
      
      .stat-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
      }
    }
  }
}

// 底部操作区
.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba($color-primary, 0.15);
    border-color: $color-primary;
    color: $color-primary;
  }
  
  span {
    @media (max-width: 600px) {
      display: none;
    }
  }
}

.feedback-btns {
  display: flex;
  gap: 6px;
  margin-left: auto;
  
  .feedback-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    
    &.correct {
      color: rgba(255, 255, 255, 0.5);
      
      &:hover, &.active {
        background: rgba($color-success, 0.15);
        border-color: $color-success;
        color: $color-success;
      }
    }
    
    &.wrong {
      color: rgba(255, 255, 255, 0.5);
      
      &:hover, &.active {
        background: rgba($color-danger, 0.15);
        border-color: $color-danger;
        color: $color-danger;
      }
    }
  }
}

// 错误状态
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
  
  .el-icon {
    font-size: 48px;
    color: $color-danger;
    margin-bottom: 16px;
  }
  
  p {
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 16px;
  }
  
  .retry-btn {
    padding: 10px 24px;
    background: $color-primary;
    border: none;
    border-radius: 8px;
    color: #fff;
    cursor: pointer;
    
    &:hover {
      background: $color-primary-light;
    }
  }
}

// 脉动指示器
.pulse-indicator {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 10px;
  height: 10px;
  background: $color-success;
  border-radius: 50%;
  animation: pulse 2s infinite;
  
  &::before {
    content: '';
    position: absolute;
    top: -4px;
    left: -4px;
    width: 18px;
    height: 18px;
    background: rgba($color-success, 0.3);
    border-radius: 50%;
    animation: pulse-ring 2s infinite;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; }
}

// 术语浮窗
.term-tooltip {
  position: fixed;
  z-index: 1000;
  max-width: 280px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  
  .tooltip-title {
    font-weight: 600;
    font-size: 13px;
    color: $color-primary-light;
    margin-bottom: 6px;
  }
  
  .tooltip-content {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.5;
    margin: 0;
  }
}

// 动画
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 1000px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
