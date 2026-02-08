<!--
  智链预测 - 专业AI预测仪表盘
  =============================
  集成K线图表、预测信息卡片、交易信号表格、控制面板
  
  技术栈: Vue 3 + TypeScript + ECharts + Element Plus
-->
<template>
  <div class="ai-prediction-dashboard">
    <!-- 背景装饰 -->
    <div class="bg-orbs">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
    </div>

    <!-- 页面头部 -->
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="gradient-text">AI 预测仪表盘</h1>
        <p class="header-subtitle">实时市场分析 · 智能交易决策</p>
      </div>
      <div class="header-right">
        <div class="live-indicator">
          <span class="pulse-dot"></span>
          <span>实时更新</span>
        </div>
        <span class="last-update">最后更新: {{ lastUpdateTime }}</span>
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="dashboard-content">
      <!-- 左侧：主分析区域 (70%) -->
      <div class="main-panel">

        <!-- 预测信息卡片 -->
        <section class="prediction-section">
          <div class="prediction-cards">
            <!-- 预测方向卡片 -->
            <div class="glass-card prediction-direction-card">
              <div class="card-header-mini">预测方向</div>
              <div class="direction-display" :class="predictionDirectionClass">
                <el-icon :size="32">
                  <component :is="predictionDirectionIcon" />
                </el-icon>
                <span class="direction-text">{{ prediction.direction || '等待分析' }}</span>
              </div>
              <div class="direction-label" :class="predictionDirectionClass">
                {{ predictionDirectionLabel }}
              </div>
            </div>

            <!-- 置信度卡片 -->
            <div class="glass-card confidence-card">
              <div class="card-header-mini">置信度</div>
              <div class="confidence-gauge">
                <svg viewBox="0 0 100 100" class="gauge-svg">
                  <circle 
                    cx="50" cy="50" r="40" 
                    fill="none" 
                    stroke="rgba(255,255,255,0.1)" 
                    stroke-width="8"
                  />
                  <circle 
                    cx="50" cy="50" r="40" 
                    fill="none" 
                    :stroke="confidenceColor"
                    stroke-width="8"
                    stroke-linecap="round"
                    :stroke-dasharray="`${confidenceArc} 251.2`"
                    :style="{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }"
                    class="gauge-progress"
                  />
                </svg>
                <div class="gauge-value">
                  <span class="value-num">{{ prediction.confidence || 0 }}</span>
                  <span class="value-unit">%</span>
                </div>
              </div>
              <div class="confidence-label">{{ confidenceLabel }}</div>
            </div>

            <!-- 时间周期建议卡片 -->
            <div class="glass-card timeframe-card">
              <div class="card-header-mini">建议周期</div>
              <div class="timeframe-badges">
                <span 
                  v-for="tf in suggestedTimeframes" 
                  :key="tf"
                  class="tf-badge"
                  :class="{ recommended: tf === prediction.recommendedTimeframe }"
                >
                  {{ tf }}
                </span>
              </div>
              <div class="timeframe-reason">{{ prediction.timeframeReason || '综合技术指标分析' }}</div>
            </div>

            <!-- 风险等级卡片 -->
            <div class="glass-card risk-card">
              <div class="card-header-mini">风险等级</div>
              <div class="risk-meter">
                <div class="risk-bar">
                  <div 
                    class="risk-fill" 
                    :style="{ width: riskPercentage + '%' }"
                    :class="riskLevelClass"
                  ></div>
                </div>
                <span class="risk-label" :class="riskLevelClass">{{ prediction.riskLevel || '中' }}</span>
              </div>
              <div class="risk-factors">
                <span v-for="(factor, i) in (prediction.riskFactors || []).slice(0, 2)" :key="i" class="risk-tag">
                  {{ factor }}
                </span>
              </div>
            </div>

            <!-- 机构级预警卡片 (新增) -->
            <div class="glass-card alert-card" v-if="prediction.volatilityScore !== undefined">
              <div class="card-header-mini">
                <el-icon><Warning /></el-icon>
                机构预警
              </div>
              <div class="alert-score-container">
                 <div class="score-circle" :class="volatilityClass">
                   {{ prediction.volatilityScore }}
                 </div>
                 <div class="score-label">波动率指数</div>
              </div>
              
              <div class="whale-tags">
                <span v-if="prediction.whaleActivity" class="whale-tag" :class="prediction.whaleActivity.trend">
                   🐋 {{ prediction.whaleActivity.label }}
                </span>
                <span v-for="gap in prediction.liquidityGaps" :key="gap" class="gap-tag warning">
                   🕳️ {{ formatGap(gap) }}
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- 交易信号详情表格 -->
        <section class="signals-section glass-card">
          <div class="section-header">
            <div class="section-title">
              <el-icon><Aim /></el-icon>
              <span>交易信号详情</span>
            </div>
            <button class="copy-btn" @click="copySignals">
              <el-icon><DocumentCopy /></el-icon>
              复制策略
            </button>
          </div>
          
          <div class="signals-table-wrapper">
            <table class="signals-table">
              <thead>
                <tr>
                  <th>预测时间</th>
                  <th>信号类型</th>
                  <th>入场价</th>
                  <th>止损价</th>
                  <th>止盈1</th>
                  <th>止盈2</th>
                  <th>止盈3</th>
                  <th>仓位建议</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(signal, idx) in tradingSignals" :key="idx" class="signal-row">
                  <td class="time-cell">{{ signal.time }}</td>
                  <td>
                    <span class="signal-type-badge" :class="signal.type.toLowerCase()">
                      {{ formatSignalType(signal.type) }}
                    </span>
                  </td>
                  <td class="price-cell">{{ formatPrice(signal.entry) }}</td>
                  <td class="price-cell stop-loss">{{ formatPrice(signal.stopLoss) }}</td>
                  <td class="price-cell take-profit">{{ formatPrice(signal.takeProfit1) }}</td>
                  <td class="price-cell take-profit">{{ formatPrice(signal.takeProfit2) }}</td>
                  <td class="price-cell take-profit">{{ formatPrice(signal.takeProfit3) }}</td>
                  <td>
                    <span class="position-badge">{{ signal.positionSize }}%</span>
                  </td>
                </tr>
                <tr v-if="!tradingSignals.length" class="empty-row">
                  <td colspan="7">暂无交易信号，请先运行 AI 分析</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 分析摘要（可展开） -->
        <section class="summary-section glass-card" v-if="prediction.summary">
          <div class="section-header clickable" @click="summaryExpanded = !summaryExpanded">
            <div class="section-title">
              <el-icon><Document /></el-icon>
              <span>AI 分析逻辑</span>
            </div>
            <el-icon class="expand-icon" :class="{ expanded: summaryExpanded }">
              <ArrowDown />
            </el-icon>
          </div>
          <transition name="slide-fade">
            <div v-show="summaryExpanded" class="summary-content">
              <div class="reasoning-grid">
                <div class="reasoning-block" v-if="prediction.reasoning?.technical">
                  <h4>技术面</h4>
                  <p>{{ prediction.reasoning.technical }}</p>
                </div>
                <div class="reasoning-block" v-if="prediction.reasoning?.sentiment">
                  <h4>情绪面</h4>
                  <p>{{ prediction.reasoning.sentiment }}</p>
                </div>
                <div class="reasoning-block" v-if="prediction.reasoning?.macro">
                  <h4>宏观面</h4>
                  <p>{{ prediction.reasoning.macro }}</p>
                </div>
              </div>
              <p class="summary-text">{{ prediction.summary }}</p>
            </div>
          </transition>
        </section>
      </div>

      <!-- 右侧：控制面板 (30%) -->
      <aside class="control-panel">
        <!-- 交易对选择器 -->
        <div class="glass-card control-card">
          <div class="control-title">交易对选择</div>
          <el-select 
            v-model="selectedSymbol" 
            size="large" 
            class="symbol-select"
            placeholder="选择交易对"
          >
            <el-option 
              v-for="symbol in availableSymbols" 
              :key="symbol.value"
              :label="symbol.label"
              :value="symbol.value"
            >
              <div class="symbol-option">
                <span class="symbol-icon">{{ symbol.icon }}</span>
                <span class="symbol-name">{{ symbol.label }}</span>
              </div>
            </el-option>
          </el-select>
          
          <div class="control-subtitle">时间周期</div>
          <div class="timeframe-grid">
            <button 
              v-for="tf in timeframes" 
              :key="tf.value"
              :class="['timeframe-btn', { active: selectedTimeframe === tf.value }]"
              @click="selectedTimeframe = tf.value"
            >
              {{ tf.label }}
            </button>
          </div>
        </div>

        <!-- AI 分析参数 -->
        <div class="glass-card control-card">
          <div class="control-title">AI 分析参数</div>
          
          <div class="param-group">
            <label>分析深度</label>
            <el-slider 
              v-model="analysisDepth" 
              :step="1" 
              :min="1" 
              :max="3"
              :marks="depthMarks"
              :show-tooltip="false"
            />
          </div>
          
          <div class="param-group">
            <label>风险偏好</label>
            <div class="risk-pref-btns">
              <button 
                v-for="pref in riskPreferences" 
                :key="pref.value"
                :class="['pref-btn', { active: riskPreference === pref.value }]"
                @click="riskPreference = pref.value"
              >
                {{ pref.label }}
              </button>
            </div>
          </div>
          
          <button class="analyze-btn glow" @click="runAnalysis" :disabled="isAnalyzing">
            <el-icon v-if="!isAnalyzing"><MagicStick /></el-icon>
            <el-icon v-else class="spin"><Loading /></el-icon>
            <span>{{ isAnalyzing ? '分析中...' : '运行 AI 分析' }}</span>
          </button>
        </div>

        <!-- 历史预测记录 -->
        <div class="glass-card control-card history-card">
          <div class="control-header-row">
            <div class="control-title">历史预测记录</div>
            <el-button 
              v-if="marketStore.history.length"
              type="primary" 
              link 
              size="small" 
              @click="handleClearHistory"
            >
              清除
            </el-button>
          </div>
          <div class="history-list">
            <div 
              v-for="(record, idx) in marketStore.history" 
              :key="idx"
              class="history-item"
              @click="loadHistoryRecord(record)"
            >
              <div class="history-main">
                <span class="history-symbol">{{ record.symbol }}</span>
                <span 
                  class="history-direction" 
                  :class="record.direction.includes('涨') ? 'bullish' : 'bearish'"
                >
                  {{ record.direction }}
                </span>
              </div>
              <div class="history-meta">
                <span class="history-time">{{ record.time }}</span>
                <span 
                  class="history-result" 
                  :class="record.correct === null ? 'pending' : record.correct ? 'correct' : 'wrong'"
                >
                  {{ record.correct === null ? '待验证' : record.correct ? '✓ 正确' : '✗ 错误' }}
                </span>
              </div>
            </div>
            <div v-if="!marketStore.history.length" class="history-empty">
              暂无历史记录
            </div>
          </div>
        </div>

        <!-- 快捷操作 -->
        <div class="glass-card control-card">
          <div class="control-title">快捷操作</div>
          <div class="quick-actions">
            <button class="quick-btn" @click="refreshData">
              <el-icon><Refresh /></el-icon>
              刷新数据
            </button>
            <button class="quick-btn" @click="exportReport">
              <el-icon><Download /></el-icon>
              导出报告
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Aim,
  DocumentCopy,
  Document,
  ArrowDown,
  MagicStick,
  Loading,
  Refresh,
  Download,
  Top,
  Bottom,
  Sort,
  Warning
} from '@element-plus/icons-vue'
import { usePredictionStore } from '@/stores/usePredictionStore'
import dayjs from 'dayjs'

// Store
const marketStore = usePredictionStore()

// ============================================================
// 响应式状态
// ============================================================

const selectedSymbol = ref('BTCUSDT')
const selectedTimeframe = ref('4h')
const analysisDepth = ref(2)
const riskPreference = ref('moderate')
const isAnalyzing = ref(false)
const summaryExpanded = ref(false)
// Note: chartContainer used for future chart ref features

// 可用交易对
const availableSymbols = [
  { value: 'BTCUSDT', label: 'BTC/USDT', icon: '₿' },
  { value: 'ETHUSDT', label: 'ETH/USDT', icon: 'Ξ' },
  { value: 'SOLUSDT', label: 'SOL/USDT', icon: '◎' },
  { value: 'BNBUSDT', label: 'BNB/USDT', icon: '◆' },
  { value: 'XRPUSDT', label: 'XRP/USDT', icon: '✕' },
  { value: 'DOGEUSDT', label: 'DOGE/USDT', icon: 'Ð' }
]

// 时间周期
const timeframes = [
  { value: '5m', label: '5分' },
  { value: '15m', label: '15分' },
  { value: '1h', label: '1小时' },
  { value: '4h', label: '4小时' },
  { value: '1d', label: '日线' }
]

const suggestedTimeframes = ['1H', '4H', '1D']

// 分析深度标记
const depthMarks = {
  1: '浅层',
  2: '标准',
  3: '深度'
}

// 风险偏好选项
const riskPreferences = [
  { value: 'conservative', label: '保守' },
  { value: 'moderate', label: '稳健' },
  { value: 'aggressive', label: '激进' }
]

// 预测结果
const prediction = ref<{
  direction?: string
  confidence?: number
  recommendedTimeframe?: string
  timeframeReason?: string
  riskLevel?: string
  riskFactors?: string[]
  summary?: string
  reasoning?: {
    technical?: string
    sentiment?: string
    macro?: string
  }
  // 新增机构数据
  volatilityScore?: number
  whaleActivity?: { label: string; trend: string }
  liquidityGaps?: string[]
}>({})

// 交易信号
const tradingSignals = ref<Array<{
  time: string
  type: string
  entry: number
  stopLoss: number
  takeProfit1: number
  takeProfit2: number
  takeProfit3: number
  positionSize: number
}>>([])

// 关键价位
const keyLevels = ref<{
  resistances: number[]
  supports: number[]
  entryPoints: Array<{ price: number; type: string }>
}>({
  resistances: [],
  supports: [],
  entryPoints: []
})

// ============================================================
// 计算属性
// ============================================================

const lastUpdateTime = ref(dayjs().format('HH:mm:ss'))

const predictionDirectionClass = computed(() => {
  const dir = prediction.value.direction || ''
  if (dir.includes('看涨') || dir.includes('bullish')) return 'bullish'
  if (dir.includes('看跌') || dir.includes('bearish')) return 'bearish'
  return 'neutral'
})

const predictionDirectionLabel = computed(() => {
  const dir = prediction.value.direction || ''
  const conf = prediction.value.confidence || 0
  if (conf >= 80) {
    return dir.includes('涨') ? '强烈看涨' : dir.includes('跌') ? '强烈看跌' : '中性'
  }
  return dir.includes('涨') ? '看涨' : dir.includes('跌') ? '看跌' : '中性'
})

const predictionDirectionIcon = computed(() => {
  const dir = prediction.value.direction || ''
  if (dir.includes('涨')) return Top
  if (dir.includes('跌')) return Bottom
  return Sort
})

const confidenceArc = computed(() => {
  const conf = prediction.value.confidence || 0
  return (conf / 100) * 251.2 // 2 * PI * 40
})

const confidenceColor = computed(() => {
  const conf = prediction.value.confidence || 0
  if (conf >= 80) return '#10b981'
  if (conf >= 60) return '#3b82f6'
  if (conf >= 40) return '#f59e0b'
  return '#6b7280'
})

const confidenceLabel = computed(() => {
  const conf = prediction.value.confidence || 0
  if (conf >= 80) return '高置信度'
  if (conf >= 60) return '中高置信度'
  if (conf >= 40) return '中等置信度'
  return '低置信度'
})

const riskPercentage = computed(() => {
  const level = prediction.value.riskLevel || '中'
  if (level === '低') return 25
  if (level === '中') return 50
  if (level === '高') return 75
  return 100
})

const riskLevelClass = computed(() => {
  const level = prediction.value.riskLevel || '中'
  if (level === '低') return 'low'
  if (level === '中') return 'medium'
  return 'high'
})

const volatilityClass = computed(() => {
  const score = prediction.value.volatilityScore || 0
  if (score >= 70) return 'critical'
  if (score >= 30) return 'active'
  return 'calm'
})

// ============================================================
// 方法
// ============================================================

function formatPrice(price: number | undefined): string {
  if (!price) return '-'
  if (price >= 1000) {
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return price.toFixed(4)
}

function formatSignalType(type: string): string {
  const t = type.toUpperCase()
  if (t === 'LONG' || t === 'BUY') return '做多 (LONG)'
  if (t === 'SHORT' || t === 'SELL') return '做空 (SHORT)'
  if (t === 'HOLD' || t === 'WAIT') return '观望 (WAIT)'
  return type
}

function formatGap(gap: string): string {
  if (gap === 'upward_liquidity_gap') return '上方真空'
  if (gap === 'downward_liquidity_gap') return '下方真空'
  return gap
}



function calculateTargets(type: string, entry: number, stopLoss: number | undefined, takeProfits: number[] | undefined) {
  const isShort = type.toUpperCase().includes('SHORT') || type.toUpperCase().includes('SELL') || type.includes('空') || type.includes('Bearish')
  
  // 止损默认: 做多 -2%, 做空 +2%
  const defaultSl = isShort ? entry * 1.02 : entry * 0.98
  const sl = stopLoss || defaultSl

  // 止盈默认: 做多 +2%/+4%/+6%, 做空 -2%/-4%/-6%
  const tp1 = takeProfits?.[0] || (isShort ? entry * 0.98 : entry * 1.02)
  const tp2 = takeProfits?.[1] || (isShort ? entry * 0.96 : entry * 1.04)
  const tp3 = takeProfits?.[2] || (isShort ? entry * 0.94 : entry * 1.06)

  return { sl, tp1, tp2, tp3 }
}

function formatAnalysisTime(timeStr: string | undefined): string {
  if (!timeStr) return '-'
  const t = dayjs(timeStr)
  return t.isValid() ? t.format('MM-DD HH:mm') : timeStr
}

async function runAnalysis() {
  if (isAnalyzing.value) return
  isAnalyzing.value = true
  
  try {
    // 设置当前交易对
    marketStore.selectSymbol(selectedSymbol.value)
    
    // 运行流式分析并获取结果
    const pred = await marketStore.analyzeStream(selectedTimeframe.value, analysisDepth.value, riskPreference.value)
    
    if (pred) {
      // 映射到组件本地状态
      prediction.value = {
        direction: pred.prediction,
        confidence: pred.confidence,
        recommendedTimeframe: selectedTimeframe.value.toUpperCase(),
        timeframeReason: '基于最新市场波动分析',
        riskLevel: pred.risk_level,
        riskFactors: pred.risk_warning?.slice(0, 3) || [],
        summary: pred.summary,
        reasoning: typeof pred.reasoning === 'object' && !Array.isArray(pred.reasoning) 
          ? pred.reasoning 
          : undefined,
        volatilityScore: (pred as any).trend_context?.volatility_score || 0
      }
      
      // 这里的 vScore 逻辑保留作为 UI 演示兼容
      let vScore = 20
      if (pred.risk_level === '极高') vScore = 85
      else if (pred.risk_level === '高') vScore = 60
      else if (pred.risk_level === '中') vScore = 40
      
      prediction.value.volatilityScore = vScore
      
      if (vScore > 70) {
          prediction.value.whaleActivity = { label: '主力异动', trend: 'warning' }
          prediction.value.liquidityGaps = ['上方真空']
      }
      
      // 更新交易信号
      if (pred.trading_signals?.length) {
        tradingSignals.value = pred.trading_signals.map((sig: { type: string; entry?: number; stop_loss?: number; take_profit?: number[] }) => {
          const { sl, tp1, tp2, tp3 } = calculateTargets(sig.type, sig.entry || 0, sig.stop_loss, sig.take_profit)
          return {
            time: formatAnalysisTime(pred.analysis_time),
            type: sig.type,
            entry: sig.entry || 0,
            stopLoss: sl,
            takeProfit1: tp1,
            takeProfit2: tp2,
            takeProfit3: tp3,
            positionSize: 5
          }
        })
      } else if (pred.entry_zone) {
        let type = (pred.prediction.includes('涨') || pred.prediction.toLowerCase().includes('bullish')) ? 'LONG' : 
                   (pred.prediction.includes('跌') || pred.prediction.toLowerCase().includes('bearish')) ? 'SHORT' : 'WAIT'
        
        const entry = (pred.entry_zone.low + pred.entry_zone.high) / 2
        const { sl, tp1, tp2, tp3 } = calculateTargets(type, entry, pred.stop_loss, pred.take_profit)
        
        tradingSignals.value = [{
          time: formatAnalysisTime(pred.analysis_time),
          type,
          entry,
          stopLoss: sl,
          takeProfit1: tp1,
          takeProfit2: tp2,
          takeProfit3: tp3,
          positionSize: 5
        }]
      }
      
      // 设置关键价位
      if (pred.key_levels) {
        keyLevels.value = {
          resistances: (pred.key_levels.resistances || [pred.key_levels.strong_resistance]).filter((v: unknown): v is number => v !== undefined && v !== null),
          supports: (pred.key_levels.supports || [pred.key_levels.strong_support]).filter((v: unknown): v is number => v !== undefined && v !== null),
          entryPoints: tradingSignals.value.map(s => ({ price: s.entry, type: s.type }))
        }
      }
      
      // 更新最后更新时间
      lastUpdateTime.value = dayjs().format('HH:mm:ss')
      
      // 添加到历史记录
      marketStore.addToHistory({
        symbol: selectedSymbol.value,
        direction: pred.prediction,
        time: dayjs().format('MM-DD HH:mm'),
        correct: null, // 待验证
        confidence: pred.confidence,
        summary: pred.summary,
        fullData: pred // 保存完整数据用于回放
      })
      
      ElMessage.success('AI 分析完成')
    }
  } catch (error) {
    console.error('Analysis failed:', error)
    ElMessage.error('分析失败，请稍后重试')
  } finally {
    isAnalyzing.value = false
  }
}


function copySignals() {
  if (!tradingSignals.value.length) {
    ElMessage.warning('暂无可复制的交易信号')
    return
  }
  
  const text = tradingSignals.value.map(s => 
    `${s.type} | 入场: ${formatPrice(s.entry)} | 止损: ${formatPrice(s.stopLoss)} | 止盈: ${formatPrice(s.takeProfit1)}/${formatPrice(s.takeProfit2)}/${formatPrice(s.takeProfit3)}`
  ).join('\n')
  
  navigator.clipboard.writeText(text)
  ElMessage.success('交易策略已复制到剪贴板')
}

function loadHistoryRecord(record: any) {
  // 如果历史记录里有足够信息，可以直接恢复界面状态
  selectedSymbol.value = record.symbol
  
  // 恢复完整预测数据
  if (record.fullData) {
    const pred = record.fullData
    
    // 恢复预测信息
    prediction.value = {
        direction: pred.prediction,
        confidence: pred.confidence,
        recommendedTimeframe: selectedTimeframe.value.toUpperCase(), // 历史记录暂时没存 timeframe，沿用当前或默认
        timeframeReason: '历史记录回放',
        riskLevel: pred.risk_level,
        riskFactors: pred.risk_warning?.slice(0, 3) || [],
        summary: pred.summary,
        reasoning: typeof pred.reasoning === 'object' && !Array.isArray(pred.reasoning) 
          ? pred.reasoning 
          : undefined
    }

    // 恢复交易信号
    if (pred.trading_signals?.length) {
        tradingSignals.value = pred.trading_signals.map((sig: any) => ({
          time: pred.analysis_time || record.time,
          type: sig.type,
          entry: sig.entry || 0,
          stopLoss: sig.stop_loss || 0,
          takeProfit1: sig.take_profit?.[0] || (sig.entry || 0) * 1.02,
          takeProfit2: sig.take_profit?.[1] || (sig.entry || 0) * 1.04,
          takeProfit3: sig.take_profit?.[2] || (sig.entry || 0) * 1.06,
          positionSize: 5
        }))
    } else if (pred.entry_zone) {
        // Smart Type Inference (History)
        let type = 'WAIT'
        if (pred.prediction.includes('涨') || pred.prediction.toLowerCase().includes('bullish')) type = 'LONG'
        else if (pred.prediction.includes('跌') || pred.prediction.toLowerCase().includes('bearish')) type = 'SHORT'
        else {
           const entry = (pred.entry_zone.low + pred.entry_zone.high) / 2
           const tp = pred.take_profit?.[0]
           if (tp && entry) {
               type = tp > entry ? 'LONG' : 'SHORT'
           }
        }

        tradingSignals.value = [{
          time: pred.analysis_time || record.time,
          type,
          entry: (pred.entry_zone.low + pred.entry_zone.high) / 2,
          stopLoss: pred.stop_loss || 0,
          takeProfit1: pred.take_profit?.[0] || 0,
          takeProfit2: pred.take_profit?.[1] || 0,
          takeProfit3: pred.take_profit?.[2] || 0,
          positionSize: 5
        }]
    }

    // 恢复关键价位
    if (pred.key_levels) {
        keyLevels.value = {
          resistances: (pred.key_levels.resistances || [pred.key_levels.strong_resistance]).filter((v: any): v is number => v !== undefined && v !== null),
          supports: (pred.key_levels.supports || [pred.key_levels.strong_support]).filter((v: any): v is number => v !== undefined && v !== null),
          entryPoints: tradingSignals.value.map(s => ({ price: s.entry, type: s.type }))
        }
    }
    
    ElMessage.success(`已加载 ${record.time} 的历史分析`)
  } else {
    ElMessage.info(`加载历史记录: ${record.symbol} ${record.direction} (无详细数据)`)
  }
}

function refreshData() {
  marketStore.loadMarketContext()
  ElMessage.success('数据已刷新')
}

function exportReport() {
  ElMessage.info('报告导出功能开发中...')
}

function handleClearHistory() {
  ElMessageBox.confirm('确定要清空所有历史分析记录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    marketStore.clearHistory()
    ElMessage.success('历史记录已清空')
  }).catch(() => {})
}

// ============================================================
// 生命周期
// ============================================================

onMounted(async () => {
  // 加载初始行情和上下文
  await marketStore.loadMarketContext()
  // 加载当前所有交易对行情
  await marketStore.loadAllTickers()
})

watch(selectedSymbol, () => {
  marketStore.loadMarketContext()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ai-prediction-dashboard {
  position: relative;
  min-height: 100vh;
  padding: 24px;
  background: #0f172a;
  overflow: hidden;
}

// 背景装饰
.bg-orbs {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  
  .orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(120px);
  }
  
  .orb-1 {
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
    top: -200px;
    right: -100px;
  }
  
  .orb-2 {
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(168, 85, 247, 0.12) 0%, transparent 70%);
    bottom: -100px;
    left: -100px;
  }
}

// 头部
.dashboard-header {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-left {
  h1 {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 4px;
  }
  
  .header-subtitle {
    color: rgba(255, 255, 255, 0.5);
    font-size: 14px;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: $color-success;
  font-size: 13px;
  
  .pulse-dot {
    width: 8px;
    height: 8px;
    background: $color-success;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }
}

.last-update {
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
}

// 主内容
.dashboard-content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
  
  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

// 玻璃卡片
.glass-card {
  background: rgba(30, 41, 59, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
}

// 主面板
.main-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  
  &.clickable {
    cursor: pointer;
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

// 图表区域
.chart-section {
  .chart-actions {
    display: flex;
    gap: 8px;
  }
  
  .tf-btn {
    padding: 6px 14px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.6);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    
    &.active {
      background: $color-primary;
      border-color: $color-primary;
      color: #fff;
    }
    
    &:hover:not(.active) {
      border-color: $color-primary;
      color: $color-primary;
    }
  }
}

.chart-container {
  height: 400px;
  
  .kline-chart {
    height: 100%;
    width: 100%;
  }
}

.chart-legend {
  display: flex;
  gap: 24px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    
    .legend-line {
      width: 24px;
      height: 2px;
      border-radius: 1px;
    }
    
    .legend-marker {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    
    &.resistance {
      .legend-line { background: #ef4444; }
    }
    
    &.support {
      .legend-line { background: #10b981; }
    }
    
    &.entry {
      .legend-marker { background: #3b82f6; }
    }
  }
}

// 预测卡片区
.prediction-section {
  .prediction-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    
    @media (max-width: 1400px) {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}

.card-header-mini {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

// 方向卡片
.prediction-direction-card {
  .direction-display {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    
    &.bullish { color: $color-success; }
    &.bearish { color: $color-danger; }
    &.neutral { color: rgba(255, 255, 255, 0.5); }
    
    .direction-text {
      font-size: 24px;
      font-weight: 700;
    }
  }
  
  .direction-label {
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    text-align: center;
    
    &.bullish {
      background: rgba($color-success, 0.15);
      color: $color-success;
    }
    
    &.bearish {
      background: rgba($color-danger, 0.15);
      color: $color-danger;
    }
    
    &.neutral {
      background: rgba(255, 255, 255, 0.1);
      color: rgba(255, 255, 255, 0.6);
    }
  }
}

// 置信度卡片
.confidence-card {
  .confidence-gauge {
    position: relative;
    width: 100px;
    height: 100px;
    margin: 0 auto 12px;
    
    .gauge-svg {
      width: 100%;
      height: 100%;
    }
    
    .gauge-progress {
      transition: stroke-dasharray 0.5s ease;
    }
    
    .gauge-value {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      
      .value-num {
        font-size: 28px;
        font-weight: 700;
        color: #fff;
      }
      
      .value-unit {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.5);
      }
    }
  }
  
  .confidence-label {
    text-align: center;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
  }
}

// 时间周期卡片
.timeframe-card {
  .timeframe-badges {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    
    .tf-badge {
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.6);
      
      &.recommended {
        background: rgba($color-primary, 0.2);
        border-color: $color-primary;
        color: $color-primary-light;
      }
    }
  }
  
  .timeframe-reason {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.4);
  }
}

// 风险卡片
.risk-card {
  .risk-meter {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    
    .risk-bar {
      flex: 1;
      height: 8px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
      overflow: hidden;
      
      .risk-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
        
        &.low { background: $color-success; }
        &.medium { background: $color-warning; }
        &.high { background: $color-danger; }
      }
    }
    
    .risk-label {
      font-size: 14px;
      font-weight: 600;
      
      &.low { color: $color-success; }
      &.medium { color: $color-warning; }
      &.high { color: $color-danger; }
    }
  }
  
  .risk-factors {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    
    .risk-tag {
      padding: 3px 8px;
      background: rgba($color-danger, 0.1);
      border-radius: 4px;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.6);
    }
  }
}

// 信号表格
.signals-section {
  .copy-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: rgba($color-primary, 0.1);
      border-color: $color-primary;
      color: $color-primary;
    }
  }
}

.signals-table-wrapper {
  overflow-x: auto;
}

.signals-table {
  width: 100%;
  border-collapse: collapse;
  
  th, td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  th {
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  td {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
  }
  
  .signal-row {
    transition: background 0.2s;
    
    &:hover {
      background: rgba(255, 255, 255, 0.02);
    }
  }
  
  .signal-type-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    
    &.long {
      background: rgba($color-success, 0.15);
      color: $color-success;
    }
    
    &.short {
      background: rgba($color-danger, 0.15);
      color: $color-danger;
    }
  }
  
  .price-cell {
    font-family: $font-mono;
    
    &.stop-loss { color: $color-danger; }
    &.take-profit { color: $color-success; }
  }
  
  .position-badge {
    display: inline-block;
    padding: 4px 10px;
    background: rgba($color-primary, 0.15);
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    color: $color-primary-light;
  }
  
  .empty-row td {
    text-align: center;
    color: rgba(255, 255, 255, 0.4);
    padding: 40px;
  }
}

// 分析摘要
.summary-section {
  .expand-icon {
    transition: transform 0.3s;
    color: rgba(255, 255, 255, 0.5);
    
    &.expanded {
      transform: rotate(180deg);
    }
  }
  
  .summary-content {
    padding-top: 16px;
  }
  
  .reasoning-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 16px;
    
    @media (max-width: 900px) {
      grid-template-columns: 1fr;
    }
  }
  
  .reasoning-block {
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    
    h4 {
      font-size: 13px;
      font-weight: 600;
      color: $color-primary-light;
      margin-bottom: 8px;
    }
    
    p {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.6;
    }
  }
  
  .summary-text {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.6);
    line-height: 1.7;
  }
}

// 控制面板
.control-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.control-card {
  .control-title {
    font-size: 14px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 0;
  }
  
  .control-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  
  .control-subtitle {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    margin: 16px 0 12px;
  }
}

.symbol-select {
  width: 100%;
  
  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: none;
  }
}

.symbol-option {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .symbol-icon {
    font-size: 18px;
  }
}

.timeframe-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  
  .timeframe-btn {
    padding: 10px 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.6);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    
    &.active {
      background: $color-primary;
      border-color: $color-primary;
      color: #fff;
    }
    
    &:hover:not(.active) {
      border-color: $color-primary;
      color: $color-primary;
    }
  }
}

.param-group {
  margin-bottom: 20px;
  
  label {
    display: block;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 10px;
  }
}

.risk-pref-btns {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  
  .pref-btn {
    padding: 10px 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.6);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    
    &.active {
      background: $color-primary;
      border-color: $color-primary;
      color: #fff;
    }
  }
}

.analyze-btn {
  width: 100%;
  padding: 14px;
  background: $gradient-primary;
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all 0.3s;
  
  &.glow {
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
  }
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5);
  }
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
  
  .spin {
    animation: spin 1s linear infinite;
  }
}

// 历史记录
.history-card {
  .history-list {
    max-height: 300px;
    overflow-y: auto;
  }
  
  .history-item {
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: rgba(255, 255, 255, 0.06);
    }
    
    &:last-child {
      margin-bottom: 0;
    }
  }
  
  .history-main {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    
    .history-symbol {
      font-weight: 600;
      color: #fff;
    }
    
    .history-direction {
      font-size: 12px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 4px;
      
      &.bullish {
        background: rgba($color-success, 0.15);
        color: $color-success;
      }
      
      &.bearish {
        background: rgba($color-danger, 0.15);
        color: $color-danger;
      }
    }
  }
  
  .history-meta {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
    
    .history-result {
      &.correct { color: $color-success; }
      &.wrong { color: $color-danger; }
    }
  }
  
  .history-empty {
    text-align: center;
    color: rgba(255, 255, 255, 0.4);
    padding: 20px;
  }
}

// 快捷操作
.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  
  .quick-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: rgba($color-primary, 0.1);
      border-color: $color-primary;
      color: $color-primary;
    }
  }
}

// 动画
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

// 渐变文字
.gradient-text {
  background: linear-gradient(135deg, #818cf8 0%, #a78bfa 50%, #c084fc 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
</style>
