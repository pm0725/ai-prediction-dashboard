<!--
  智链预测 - 高级智能K线图组件
  ================================
  集成ECharts、AI分析可视化、WebSocket实时数据
  
  技术栈: Vue 3 + TypeScript + ECharts
-->
<template>
  <div class="smart-kline-chart" ref="containerRef">
    <!-- 工具栏 -->
    <div class="chart-toolbar">
      <div class="toolbar-left">
        <!-- 时间周期选择 -->
        <div class="timeframe-group">
          <button 
            v-for="tf in timeframes" 
            :key="tf.value"
            :class="['tf-btn', { active: activeTimeframe === tf.value }]"
            @click="switchTimeframe(tf.value)"
          >
            {{ tf.label }}
          </button>
        </div>
        
        <!-- 技术指标选择 -->
        <el-dropdown trigger="click" @command="toggleIndicator">
          <button class="indicator-btn">
            <el-icon><DataAnalysis /></el-icon>
            指标
            <el-icon class="arrow"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item 
                v-for="ind in availableIndicators" 
                :key="ind.key"
                :command="ind.key"
              >
                <span class="indicator-check" v-if="activeIndicators.includes(ind.key)">✓</span>
                {{ ind.name }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      
      <div class="toolbar-center">
        <!-- 连接状态 -->
        <div class="connection-status" :class="wsStatus">
          <span class="status-dot"></span>
          <span>{{ wsStatusText }}</span>
        </div>
        
        <!-- 当前价格 -->
        <div class="current-price" v-if="currentPrice">
          <span class="price-value" :class="priceDirection">
            {{ formatPrice(currentPrice) }}
          </span>
          <span class="price-change" :class="priceDirection">
            {{ priceChangePercent }}
          </span>
        </div>
      </div>
      
      <div class="toolbar-right">
        <!-- AI分析开关 -->
        <label class="ai-toggle">
          <input type="checkbox" v-model="showAIOverlay">
          <span class="toggle-slider"></span>
          <span class="toggle-label">AI叠加</span>
        </label>
        
        <!-- 截图 -->
        <button class="tool-btn" @click="captureScreenshot" title="截图">
          <el-icon><Camera /></el-icon>
        </button>
        
        <!-- 全屏 -->
        <button class="tool-btn" @click="toggleFullscreen" title="全屏">
          <el-icon><FullScreen /></el-icon>
        </button>
      </div>
    </div>

    <!-- 主图表区域 -->
    <div class="chart-main">
      <v-chart 
        ref="mainChartRef"
        class="main-chart" 
        :option="mainChartOption" 
        :autoresize="true"
        @click="handleChartClick"
        @contextmenu="handleContextMenu"
        @mousemove="handleMouseMove"
      />
      
      <!-- AI分析悬浮提示 -->
      <transition name="fade">
        <div 
          v-if="hoverInfo.visible && showAIOverlay" 
          class="ai-tooltip"
          :style="{ left: hoverInfo.x + 'px', top: hoverInfo.y + 'px' }"
        >
          <div class="tooltip-header">
            <span class="tooltip-time">{{ hoverInfo.time }}</span>
            <span class="tooltip-price">{{ formatPrice(hoverInfo.price) }}</span>
          </div>
          <div class="tooltip-content" v-if="hoverInfo.aiSummary">
            <div class="ai-badge">AI分析</div>
            <p>{{ hoverInfo.aiSummary }}</p>
          </div>
        </div>
      </transition>
      
      <!-- 信号标记图例 -->
      <div class="signal-legend" v-if="showAIOverlay">
        <span class="legend-item buy">
          <span class="legend-icon">▲</span> 买入信号
        </span>
        <span class="legend-item sell">
          <span class="legend-icon">▼</span> 卖出信号
        </span>
        <span class="legend-item hold">
          <span class="legend-icon">●</span> 观望
        </span>
      </div>
    </div>

    <!-- 多周期迷你图 -->
    <div class="multi-timeframe-panel" v-if="showMultiTimeframe">
      <div 
        v-for="tf in ['1h', '4h', '1d']" 
        :key="tf"
        :class="['mini-chart-wrapper', { active: activeTimeframe === tf }]"
        @click="switchTimeframe(tf)"
      >
        <div class="mini-chart-header">
          <span class="mini-tf">{{ tfLabel(tf) }}</span>
          <span class="mini-trend" :class="getTrendClass(tf)">
            {{ getTrendIcon(tf) }}
          </span>
        </div>
        <v-chart 
          class="mini-chart" 
          :option="getMiniChartOption(tf)" 
          :autoresize="true"
        />
      </div>
    </div>

    <!-- 信号详情弹窗 -->
    <transition name="slide-up">
      <div v-if="selectedSignal" class="signal-detail-panel">
        <div class="panel-header">
          <span class="signal-type" :class="selectedSignal.type">
            {{ selectedSignal.type === 'BUY' ? '买入信号' : selectedSignal.type === 'SELL' ? '卖出信号' : '观望' }}
          </span>
          <button class="close-btn" @click="selectedSignal = null">×</button>
        </div>
        <div class="panel-body">
          <div class="detail-row">
            <span class="label">信号时间</span>
            <span class="value">{{ selectedSignal.time }}</span>
          </div>
          <div class="detail-row">
            <span class="label">信号价格</span>
            <span class="value">{{ formatPrice(selectedSignal.price) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">置信度</span>
            <span class="value">{{ selectedSignal.confidence }}%</span>
          </div>
          <div class="detail-row full">
            <span class="label">AI分析</span>
            <p class="value">{{ selectedSignal.reason }}</p>
          </div>
        </div>
      </div>
    </transition>

    <!-- 价格预警弹窗 -->
    <transition name="bounce">
      <div v-if="priceAlert.visible" class="price-alert" :class="priceAlert.type">
        <el-icon><WarningFilled /></el-icon>
        <div class="alert-content">
          <div class="alert-title">{{ priceAlert.title }}</div>
          <div class="alert-message">{{ priceAlert.message }}</div>
        </div>
        <button class="alert-close" @click="priceAlert.visible = false">×</button>
      </div>
    </transition>

    <!-- 右键菜单 -->
    <div 
      v-if="contextMenu.visible" 
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      @click.stop
    >
      <div class="menu-item" @click="runAIAnalysisAtPoint">
        <el-icon><MagicStick /></el-icon>
        AI分析此时间点
      </div>
      <div class="menu-item" @click="addTrendLine">
        <el-icon><Edit /></el-icon>
        添加趋势线
      </div>
      <div class="menu-item" @click="addFibonacci">
        <el-icon><Operation /></el-icon>
        斐波那契回撤
      </div>
      <div class="menu-divider"></div>
      <div class="menu-item" @click="setAlert">
        <el-icon><Bell /></el-icon>
        设置价格预警
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, LineChart, BarChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  MarkAreaComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import {
  DataAnalysis,
  ArrowDown,
  Camera,
  FullScreen,
  WarningFilled,
  MagicStick,
  Edit,
  Operation,
  Bell
} from '@element-plus/icons-vue'
import { useMarketStore } from '@/stores'
import { debounce } from 'lodash-es'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  CandlestickChart,
  LineChart,
  BarChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent,
  MarkAreaComponent
])

// ============================================================
// Props & Emits
// ============================================================

const props = defineProps(['symbol', 'initialTimeframe', 'wsUrl', 'showMultiTimeframe'])

const emit = defineEmits<{
  (e: 'signal-click', signal: any): void
  (e: 'timeframe-change', tf: string): void
  (e: 'price-alert', alert: any): void
}>()

// ============================================================
// Store & Refs
// ============================================================

const marketStore = useMarketStore()
const containerRef = ref<HTMLElement | null>(null)
const mainChartRef = ref<any>(null)

// ============================================================
// 状态
// ============================================================

// 时间周期
const timeframes = [
  { value: '5m', label: '5分线' },
  { value: '15m', label: '15分线' },
  { value: '1h', label: '1小时' },
  { value: '4h', label: '4小时' },
  { value: '1d', label: '日线' }
]
const activeTimeframe = ref(props.initialTimeframe || '4h')

// 技术指标
const availableIndicators = [
  { key: 'MA', name: 'MA 移动均线' },
  { key: 'EMA', name: 'EMA 指数均线' },
  { key: 'MACD', name: 'MACD' },
  { key: 'RSI', name: 'RSI 相对强弱' },
  { key: 'BOLL', name: '布林带' }
]
const activeIndicators = ref<string[]>(['MA'])

// AI叠加层
const showAIOverlay = ref(true)

// WebSocket
const ws = ref<WebSocket | null>(null)
const wsStatus = ref<'connected' | 'connecting' | 'disconnected'>('disconnected')
const wsStatusText = computed(() => {
  if (wsStatus.value === 'connected') return '实时连接'
  if (wsStatus.value === 'connecting') return '连接中...'
  return '已断开'
})

// 价格数据
const currentPrice = ref(0)
const previousPrice = ref(0)
const priceDirection = computed(() => {
  if (currentPrice.value > previousPrice.value) return 'up'
  if (currentPrice.value < previousPrice.value) return 'down'
  return ''
})
const priceChangePercent = computed(() => {
  if (!previousPrice.value) return ''
  const change = ((currentPrice.value - previousPrice.value) / previousPrice.value) * 100
  return (change >= 0 ? '+' : '') + change.toFixed(2) + '%'
})

// K线数据
const klineData = ref<number[][]>([])
const multiTimeframeData = ref<Record<string, number[][]>>({
  '1h': [],
  '4h': [],
  '1d': []
})

// AI分析数据
const keyLevels = ref<{
  supports: number[]
  resistances: number[]
}>({ supports: [], resistances: [] })

const signals = ref<Array<{
  time: string
  price: number
  type: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reason: string
  dataIndex: number
}>>([])

const predictionZone = ref<{
  low: number
  high: number
  confidence: number
} | null>(null)

// 交互状态
const hoverInfo = ref({
  visible: false,
  x: 0,
  y: 0,
  time: '',
  price: 0,
  aiSummary: ''
})

const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  dataIndex: 0
})

const selectedSignal = ref<any>(null)

const priceAlert = ref({
  visible: false,
  type: 'warning' as 'warning' | 'danger',
  title: '',
  message: ''
})

// ============================================================
// 计算图表配置
// ============================================================

const mainChartOption = computed(() => {
  const upColor = '#10b981'
  const downColor = '#ef4444'
  
  // 基础K线系列
  const series: any[] = [
    {
      name: 'K线',
      type: 'candlestick',
      data: klineData.value.map(k => [k[0], k[1], k[2], k[3]]),
      itemStyle: {
        color: upColor,
        color0: downColor,
        borderColor: upColor,
        borderColor0: downColor
      },
      markLine: showAIOverlay.value ? {
        symbol: 'none',
        silent: true,
        lineStyle: { width: 1 },
        data: [
          ...keyLevels.value.resistances.map(price => ({
            yAxis: price,
            lineStyle: { color: '#ef4444', type: 'dashed' },
            label: {
              formatter: `阻力 ${formatPrice(price)}`,
              color: '#ef4444',
              backgroundColor: 'rgba(239,68,68,0.1)',
              padding: [2, 6],
              borderRadius: 2
            }
          })),
          ...keyLevels.value.supports.map(price => ({
            yAxis: price,
            lineStyle: { color: '#10b981', type: 'dashed' },
            label: {
              formatter: `支撑 ${formatPrice(price)}`,
              color: '#10b981',
              backgroundColor: 'rgba(16,185,129,0.1)',
              padding: [2, 6],
              borderRadius: 2
            }
          }))
        ]
      } : undefined,
      markArea: showAIOverlay.value && predictionZone.value ? {
        silent: true,
        data: [[
          { yAxis: predictionZone.value.low },
          { yAxis: predictionZone.value.high }
        ]],
        itemStyle: {
          color: `rgba(99, 102, 241, ${predictionZone.value.confidence / 200})`
        }
      } : undefined
    },
    // 成交量
    {
      name: '成交量',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: klineData.value.map(k => k[4] || 0),
      itemStyle: {
        color: (params: any) => {
          const k = klineData.value[params.dataIndex]
          return k && k[1] >= k[0] ? upColor : downColor
        }
      }
    }
  ]

  // 添加技术指标
  if (activeIndicators.value.includes('MA')) {
    series.push(
      {
        name: 'MA7',
        type: 'line',
        data: calculateMA(7),
        smooth: true,
        lineStyle: { width: 1, color: '#f59e0b' },
        symbol: 'none'
      },
      {
        name: 'MA25',
        type: 'line',
        data: calculateMA(25),
        smooth: true,
        lineStyle: { width: 1, color: '#3b82f6' },
        symbol: 'none'
      },
      {
        name: 'MA99',
        type: 'line',
        data: calculateMA(99),
        smooth: true,
        lineStyle: { width: 1, color: '#a855f7' },
        symbol: 'none'
      }
    )
  }

  if (activeIndicators.value.includes('BOLL')) {
    const boll = calculateBollinger(20, 2)
    series.push(
      {
        name: 'BOLL Upper',
        type: 'line',
        data: boll.upper,
        smooth: true,
        lineStyle: { width: 1, color: '#ef4444', type: 'dashed' },
        symbol: 'none'
      },
      {
        name: 'BOLL Middle',
        type: 'line',
        data: boll.middle,
        smooth: true,
        lineStyle: { width: 1, color: '#6b7280' },
        symbol: 'none'
      },
      {
        name: 'BOLL Lower',
        type: 'line',
        data: boll.lower,
        smooth: true,
        lineStyle: { width: 1, color: '#10b981', type: 'dashed' },
        symbol: 'none'
      }
    )
  }

  // 添加AI信号点
  if (showAIOverlay.value && signals.value.length) {
    series.push({
      name: '信号',
      type: 'scatter',
      data: signals.value.map(s => ({
        value: [s.dataIndex, s.price],
        itemStyle: {
          color: s.type === 'BUY' ? '#10b981' : s.type === 'SELL' ? '#ef4444' : '#f59e0b'
        },
        symbol: s.type === 'BUY' ? 'triangle' : s.type === 'SELL' ? 'pin' : 'circle',
        symbolSize: 16,
        signalData: s
      }))
    })
  }

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const k = params.find((p: any) => p.seriesName === 'K线')
        if (!k) return ''
        const data = k.data
         return `
          <div style="font-size:13px">
            <div style="margin-bottom:4px;color:rgba(255,255,255,0.6)">${k.axisValue}</div>
            <div>开盘: <span style="color:${data[0] <= data[1] ? upColor : downColor}">${formatPrice(data[0])}</span></div>
            <div>最高: <span style="color:${upColor}">${formatPrice(data[3])}</span></div>
            <div>最低: <span style="color:${downColor}">${formatPrice(data[2])}</span></div>
            <div>收盘: <span style="color:${data[0] <= data[1] ? upColor : downColor}">${formatPrice(data[1])}</span></div>
          </div>
        `
      }
    },
    grid: [
      { left: '60px', right: '60px', top: '60px', height: '55%' },
      { left: '60px', right: '60px', top: '72%', height: '18%' }
    ],
    xAxis: [
      {
        type: 'category',
        data: klineData.value.map((_, i) => formatKlineTime(i)),
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
        axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 10 },
        splitLine: { show: false }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: klineData.value.map((_, i) => formatKlineTime(i)),
        axisLabel: { show: false },
        axisLine: { show: false },
        splitLine: { show: false }
      }
    ],
    yAxis: [
      {
        type: 'value',
        scale: true,
        position: 'right',
        axisLine: { show: false },
        axisLabel: { 
          color: 'rgba(255,255,255,0.5)', 
          fontSize: 10,
          formatter: (v: number) => formatPrice(v)
        },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
      },
      {
        type: 'value',
        gridIndex: 1,
        scale: true,
        position: 'right',
        axisLine: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { 
        type: 'slider', 
        xAxisIndex: [0, 1], 
        start: 60, 
        end: 100, 
        height: 20, 
        bottom: 10,
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: 'rgba(255,255,255,0.5)' }
      }
    ],
    series
  }
})

// ============================================================
// 方法
// ============================================================

function formatPrice(price: number): string {
  if (!price) return '-'
  if (price >= 1000) {
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return price.toFixed(4)
}

function formatKlineTime(index: number): string {
  const now = new Date()
  const tfMinutes = activeTimeframe.value === '1d' ? 1440 :
                    activeTimeframe.value === '4h' ? 240 :
                    activeTimeframe.value === '1h' ? 60 :
                    activeTimeframe.value === '15m' ? 15 : 5
  const time = new Date(now.getTime() - (klineData.value.length - index) * tfMinutes * 60000)
  if (activeTimeframe.value === '1d') {
    return `${time.getMonth() + 1}/${time.getDate()}`
  }
  return `${time.getHours().toString().padStart(2, '0')}:${time.getMinutes().toString().padStart(2, '0')}`
}

function calculateMA(period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < klineData.value.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += klineData.value[i - j][1] // 收盘价
      }
      result.push(sum / period)
    }
  }
  return result
}

function calculateBollinger(period: number, stdDev: number) {
  const ma = calculateMA(period)
  const upper: (number | null)[] = []
  const lower: (number | null)[] = []
  
  for (let i = 0; i < klineData.value.length; i++) {
    if (i < period - 1 || ma[i] === null) {
      upper.push(null)
      lower.push(null)
    } else {
      let sumSq = 0
      for (let j = 0; j < period; j++) {
        const diff = klineData.value[i - j][1] - (ma[i] as number)
        sumSq += diff * diff
      }
      const std = Math.sqrt(sumSq / period)
      upper.push((ma[i] as number) + stdDev * std)
      lower.push((ma[i] as number) - stdDev * std)
    }
  }
  
  return { upper, middle: ma, lower }
}

function switchTimeframe(tf: string) {
  activeTimeframe.value = tf
  emit('timeframe-change', tf)
  loadKlineData(tf)
}

function toggleIndicator(key: string) {
  const idx = activeIndicators.value.indexOf(key)
  if (idx >= 0) {
    activeIndicators.value.splice(idx, 1)
  } else {
    activeIndicators.value.push(key)
  }
}

function getMiniChartOption(tf: string) {
  const data = multiTimeframeData.value[tf] || []
  return {
    backgroundColor: 'transparent',
    animation: false,
    grid: { left: 0, right: 0, top: 5, bottom: 5 },
    xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
    yAxis: { type: 'value', show: false, scale: true },
    series: [{
      type: 'candlestick',
      data: data.map(k => [k[0], k[1], k[2], k[3]]),
      itemStyle: {
        color: '#10b981',
        color0: '#ef4444',
        borderColor: '#10b981',
        borderColor0: '#ef4444'
      }
    }]
  }
}

function getTrendClass(tf: string): string {
  const data = multiTimeframeData.value[tf]
  if (!data || data.length < 2) return ''
  const last = data[data.length - 1][1]
  const prev = data[data.length - 2][1]
  return last >= prev ? 'up' : 'down'
}

function getTrendIcon(tf: string): string {
  const cls = getTrendClass(tf)
  return cls === 'up' ? '↑' : cls === 'down' ? '↓' : '-'
}

function tfLabel(tf: string) {
    if (tf === '1h') return '1小时'
    if (tf === '4h') return '4小时'
    if (tf === '1d') return '日线'
    return tf.toUpperCase()
}

// 交互处理
function handleChartClick(params: any) {
  contextMenu.value.visible = false
  
  if (params.seriesName === '信号' && params.data?.signalData) {
    selectedSignal.value = params.data.signalData
    emit('signal-click', params.data.signalData)
  }
}

const handleMouseMove = debounce((params: any) => {
  if (!params.event || !showAIOverlay.value) {
    hoverInfo.value.visible = false
    return
  }
  
  const { offsetX, offsetY } = params.event
  const dataIndex = params.dataIndex
  
  if (dataIndex !== undefined && klineData.value[dataIndex]) {
    const k = klineData.value[dataIndex]
    hoverInfo.value = {
      visible: true,
      x: offsetX + 15,
      y: offsetY + 15,
      time: formatKlineTime(dataIndex),
      price: k[1],
      aiSummary: getAISummaryForIndex(dataIndex)
    }
  }
}, 50)

function handleContextMenu(params: any) {
  if (params.event) {
    params.event.event.preventDefault()
    contextMenu.value = {
      visible: true,
      x: params.event.offsetX,
      y: params.event.offsetY,
      dataIndex: params.dataIndex || 0
    }
  }
}

function getAISummaryForIndex(index: number): string {
  // 模拟AI分析摘要
  const signal = signals.value.find(s => s.dataIndex === index)
  if (signal) return signal.reason
  return ''
}

function runAIAnalysisAtPoint() {
  contextMenu.value.visible = false
  ElMessage.info('正在分析该时间点...')
  // 实际调用AI分析
}

function addTrendLine() {
  contextMenu.value.visible = false
  ElMessage.info('请在图表上拖动绘制趋势线')
}

function addFibonacci() {
  contextMenu.value.visible = false
  ElMessage.info('请在图表上选择两点绘制斐波那契回撤')
}

function setAlert() {
  contextMenu.value.visible = false
  ElMessage.info('价格预警功能开发中')
}

function captureScreenshot() {
  if (mainChartRef.value) {
    const dataUrl = mainChartRef.value.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#0f172a'
    })
    const link = document.createElement('a')
    link.download = `${props.symbol}_${activeTimeframe.value}_${Date.now()}.png`
    link.href = dataUrl
    link.click()
    ElMessage.success('截图已保存')
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    containerRef.value?.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

// WebSocket
function connectWebSocket() {
  if (ws.value?.readyState === WebSocket.OPEN) return
  
  wsStatus.value = 'connecting'
  ws.value = new WebSocket(props.wsUrl)
  
  ws.value.onopen = () => {
    wsStatus.value = 'connected'
    ws.value?.send(JSON.stringify({
      action: 'subscribe',
      symbol: props.symbol,
      timeframe: activeTimeframe.value
    }))
  }
  
  ws.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleWSMessage(data)
    } catch (e) {
      console.error('WS parse error:', e)
    }
  }
  
  ws.value.onclose = () => {
    wsStatus.value = 'disconnected'
    // 自动重连
    setTimeout(connectWebSocket, 3000)
  }
  
  ws.value.onerror = () => {
    wsStatus.value = 'disconnected'
  }
}

function handleWSMessage(data: any) {
  if (data.type === 'kline') {
    // 更新K线
    previousPrice.value = currentPrice.value
    currentPrice.value = data.close
    
    // 检查价格变动预警
    if (previousPrice.value) {
      const change = Math.abs((currentPrice.value - previousPrice.value) / previousPrice.value)
      if (change > 0.02) {
        priceAlert.value = {
          visible: true,
          type: change > 0.05 ? 'danger' : 'warning',
          title: `${props.symbol} 价格剧烈波动`,
          message: `价格变动 ${(change * 100).toFixed(2)}%，当前价格 ${formatPrice(currentPrice.value)}`
        }
        emit('price-alert', priceAlert.value)
      }
    }
  } else if (data.type === 'ai_signal') {
    signals.value.push(data.signal)
  }
}


// 数据同步
watch(() => marketStore.klines, (newKlines) => {
  if (newKlines && newKlines.length) {
    updateChartData()
  }
}, { deep: true, immediate: true })

watch(() => marketStore.marketContext, () => {
  updateAIOverlay()
}, { deep: true })

watch(() => marketStore.prediction, () => {
  updateAIOverlay()
}, { deep: true })

watch(() => props.symbol, (newVal) => {
  if (newVal) {
    // 切换交易对时重新连接WS并加载数据
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        action: 'unsubscribe',
        symbol: props.symbol // Note: logic might refer to old prop, but here newVal is new. 
                             // Actually better to just reload data, WS handles subscription in connect/message logic or we can add explicit resubscribe.
                             // For now, simpler: just load data.
      }))
      ws.value.send(JSON.stringify({
        action: 'subscribe',
        symbol: newVal,
        timeframe: activeTimeframe.value
      }))
    }
    loadKlineData(activeTimeframe.value)
  }
})

// 数据加载
async function loadKlineData(tf: string) {
  try {
    // 真实数据加载
    // 检查 symbol 是否一致，或者数据为空
    if (marketStore.klines.length === 0 || props.symbol !== marketStore.currentSymbol) {
      if (props.symbol !== marketStore.currentSymbol) {
        marketStore.selectSymbol(props.symbol)
      }
      // Use the passed timeframe
      console.log('Loading data for timeframe:', tf) 
      await marketStore.loadMarketContext()
    } else {
      // 已有数据，直接更新
      updateChartData()
    }
  } catch (error) {
    console.error('Failed to load kline data:', error)
    ElMessage.error('无法加载图表数据')
  }
}

function updateChartData() {
  const klines = marketStore.klines
  if (!klines || !klines.length) return

  const data: number[][] = []
  
  // 转换数据格式: [open, close, low, high, volume]
  // store data: { timestamp, open, high, low, close, volume }
  // 增加安全性检查和类型转换
  klines.forEach(k => {
    if (!k) return
    data.push([
      parseFloat(String(k.open)),
      parseFloat(String(k.close)),
      parseFloat(String(k.low)),
      parseFloat(String(k.high)),
      parseFloat(String(k.volume || 0))
    ])
  })
  
  if (data.length > 0) {
    klineData.value = data
    currentPrice.value = data[data.length - 1][1]
    
    // 更新多周期数据 (目前假定暂时只用当前周期，后续需完善多周期API)
    if (props.showMultiTimeframe) {
      multiTimeframeData.value[activeTimeframe.value] = data.slice(-50)
    }
  }
}

function updateAIOverlay() {
  const pred = marketStore.prediction
  const lastPrice = currentPrice.value

  // 1. 更新支撑阻力位
  if (pred && pred.key_levels) {
    const res = pred.key_levels.resistances || pred.key_levels.strong_resistance ? [pred.key_levels.strong_resistance] : []
    const sup = pred.key_levels.supports || pred.key_levels.strong_support ? [pred.key_levels.strong_support] : []
    
    // 如果 key_levels.resistances 是数组，优先使用
    const finalRes = Array.isArray(pred.key_levels.resistances) ? pred.key_levels.resistances : res
    const finalSup = Array.isArray(pred.key_levels.supports) ? pred.key_levels.supports : sup

    keyLevels.value = {
      supports: finalSup as number[],
      resistances: finalRes as number[]
    }
  }

  // 2. 更新预测区间
  if (pred && pred.entry_zone && typeof pred.entry_zone === 'object') {
    predictionZone.value = {
      low: pred.entry_zone.low,
      high: pred.entry_zone.high,
      confidence: pred.confidence
    }
  }

  // 3. 更新信号
  // 这里可以把 prediction 转换为一个信号显示在最新K线上
  if (pred) {
    const lastTimeIdx = klineData.value.length - 1
    // 注意：api.ts 中 define interface PredictionResult { prediction: string, ... }
    const predictionText = pred.prediction || ''
    const signalType = predictionText.includes('涨') || predictionText.includes('做多') || predictionText.includes('Bullish') ? 'BUY' :
                       predictionText.includes('跌') || predictionText.includes('做空') || predictionText.includes('Bearish') ? 'SELL' : 'HOLD'
    
    // 只添加最新的一个信号，避免重复
    signals.value = [{
      time: formatKlineTime(lastTimeIdx),
      price: lastPrice,
      type: signalType,
      confidence: pred.confidence,
      reason: (pred.reasoning && typeof pred.reasoning === 'string' ? pred.reasoning : pred.summary) || 'AI分析生成',
      dataIndex: lastTimeIdx
    }]
  }
}

// 辅助函数：生成 Mock 数据已移除

// 生命周期
onMounted(() => {
  connectWebSocket()
  loadKlineData(activeTimeframe.value)
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})

</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.smart-kline-chart {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 600px;
  background: #0f172a;
  border-radius: 16px;
  overflow: hidden;
}

// 工具栏
.chart-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-center {
  display: flex;
  align-items: center;
  gap: 20px;
}

.timeframe-group {
  display: flex;
  gap: 4px;
  
  .tf-btn {
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
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

.indicator-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  cursor: pointer;
  
  .arrow {
    font-size: 10px;
  }
}

.indicator-check {
  color: $color-success;
  margin-right: 6px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  
  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }
  
  &.connected {
    color: $color-success;
    .status-dot { background: $color-success; }
  }
  
  &.connecting {
    color: $color-warning;
    .status-dot { background: $color-warning; animation: pulse 1s infinite; }
  }
  
  &.disconnected {
    color: rgba(255, 255, 255, 0.4);
    .status-dot { background: rgba(255, 255, 255, 0.4); }
  }
}

.current-price {
  display: flex;
  align-items: baseline;
  gap: 8px;
  
  .price-value {
    font-size: 20px;
    font-weight: 700;
    font-family: $font-mono;
    
    &.up { color: $color-success; }
    &.down { color: $color-danger; }
  }
  
  .price-change {
    font-size: 13px;
    font-weight: 600;
    
    &.up { color: $color-success; }
    &.down { color: $color-danger; }
  }
}

.ai-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  
  input {
    display: none;
    
    &:checked + .toggle-slider {
      background: $color-primary;
      
      &::before {
        transform: translateX(14px);
      }
    }
  }
  
  .toggle-slider {
    width: 32px;
    height: 18px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 9px;
    position: relative;
    transition: all 0.2s;
    
    &::before {
      content: '';
      position: absolute;
      width: 14px;
      height: 14px;
      background: #fff;
      border-radius: 50%;
      top: 2px;
      left: 2px;
      transition: transform 0.2s;
    }
  }
  
  .toggle-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
  }
}

.tool-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba($color-primary, 0.1);
    border-color: $color-primary;
    color: $color-primary;
  }
}

// 主图表
.chart-main {
  flex: 1;
  position: relative;
  
  .main-chart {
    width: 100%;
    height: 100%;
  }
}

.ai-tooltip {
  position: absolute;
  z-index: 100;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
  max-width: 280px;
  pointer-events: none;
  
  .tooltip-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 12px;
    
    .tooltip-time {
      color: rgba(255, 255, 255, 0.5);
    }
    
    .tooltip-price {
      font-weight: 600;
      color: #fff;
    }
  }
  
  .tooltip-content {
    .ai-badge {
      display: inline-block;
      padding: 2px 8px;
      background: rgba($color-primary, 0.2);
      border-radius: 4px;
      font-size: 10px;
      color: $color-primary-light;
      margin-bottom: 6px;
    }
    
    p {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.5;
      margin: 0;
    }
  }
}

.signal-legend {
  position: absolute;
  bottom: 60px;
  left: 16px;
  display: flex;
  gap: 16px;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.8);
  border-radius: 6px;
  
  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.6);
    
    .legend-icon {
      font-size: 14px;
    }
    
    &.buy .legend-icon { color: $color-success; }
    &.sell .legend-icon { color: $color-danger; }
    &.hold .legend-icon { color: $color-warning; }
  }
}

// 多周期面板
.multi-timeframe-panel {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.6);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.mini-chart-wrapper {
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
  transition: all 0.2s;
  
  &.active {
    border-color: $color-primary;
    background: rgba($color-primary, 0.1);
  }
  
  &:hover:not(.active) {
    border-color: rgba(255, 255, 255, 0.2);
  }
  
  .mini-chart-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
    
    .mini-tf {
      font-size: 11px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.6);
    }
    
    .mini-trend {
      font-size: 12px;
      font-weight: 700;
      
      &.up { color: $color-success; }
      &.down { color: $color-danger; }
    }
  }
  
  .mini-chart {
    height: 60px;
  }
}

// 信号详情面板
.signal-detail-panel {
  position: absolute;
  bottom: 100px;
  right: 16px;
  width: 300px;
  background: rgba(30, 41, 59, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
  
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    
    .signal-type {
      font-weight: 600;
      font-size: 14px;
      
      &.BUY { color: $color-success; }
      &.SELL { color: $color-danger; }
      &.HOLD { color: $color-warning; }
    }
    
    .close-btn {
      width: 24px;
      height: 24px;
      background: none;
      border: none;
      color: rgba(255, 255, 255, 0.5);
      font-size: 18px;
      cursor: pointer;
      
      &:hover {
        color: #fff;
      }
    }
  }
  
  .panel-body {
    padding: 16px;
  }
  
  .detail-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
    
    &.full {
      flex-direction: column;
      gap: 6px;
      
      .value {
        line-height: 1.5;
      }
    }
    
    .label {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }
    
    .value {
      font-size: 13px;
      color: #fff;
    }
  }
}

// 价格预警
.price-alert {
  position: absolute;
  top: 80px;
  right: 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.95);
  border-radius: 10px;
  max-width: 320px;
  
  &.warning {
    border: 1px solid $color-warning;
    
    > .el-icon { color: $color-warning; font-size: 20px; }
  }
  
  &.danger {
    border: 1px solid $color-danger;
    
    > .el-icon { color: $color-danger; font-size: 20px; }
  }
  
  .alert-content {
    flex: 1;
    
    .alert-title {
      font-size: 13px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 4px;
    }
    
    .alert-message {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
    }
  }
  
  .alert-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    font-size: 16px;
    cursor: pointer;
  }
}

// 右键菜单
.context-menu {
  position: absolute;
  z-index: 200;
  background: rgba(30, 41, 59, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 6px 0;
  min-width: 180px;
  
  .menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.8);
    cursor: pointer;
    transition: background 0.2s;
    
    &:hover {
      background: rgba($color-primary, 0.15);
      color: #fff;
    }
  }
  
  .menu-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    margin: 4px 0;
  }
}

// 动画
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.bounce-enter-active {
  animation: bounce-in 0.4s;
}
.bounce-leave-active {
  animation: bounce-in 0.3s reverse;
}
@keyframes bounce-in {
  0% { transform: scale(0.9); opacity: 0; }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); opacity: 1; }
}
</style>
