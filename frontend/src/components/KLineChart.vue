<!--
  智链预测 - K线图组件
  ====================
  基于Lightweight Charts的K线图组件
-->
<template>
  <div class="kline-chart" ref="chartContainer">
    <div v-if="!klines.length && !loading" class="chart-placeholder">
      <el-icon :size="48"><TrendCharts /></el-icon>
      <p>暂无K线数据</p>
    </div>
    <div v-if="loading" class="chart-loading">
      <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { TrendCharts, Loading } from '@element-plus/icons-vue'
import { createChart, ColorType, CrosshairMode, type IChartApi, type ISeriesApi } from 'lightweight-charts'

// Props
const props = defineProps(['symbol', 'timeframe', 'klines', 'height', 'loading', 'keyLevels'])

// Refs
const chartContainer = ref<HTMLElement>()
let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null

// 图表配置
const chartOptions = {
  layout: {
    background: { type: ColorType.Solid, color: 'transparent' },
    textColor: 'rgba(255, 255, 255, 0.6)'
  },
  grid: {
    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
    horzLines: { color: 'rgba(255, 255, 255, 0.05)' }
  },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: {
      color: 'rgba(96, 165, 250, 0.5)',
      style: 2
    },
    horzLine: {
      color: 'rgba(96, 165, 250, 0.5)',
      style: 2
    }
  },
  timeScale: {
    borderColor: 'rgba(255, 255, 255, 0.1)',
    timeVisible: true,
    secondsVisible: false
  },
  rightPriceScale: {
    borderColor: 'rgba(255, 255, 255, 0.1)'
  }
}

// 初始化图表
function initChart() {
  if (!chartContainer.value || chart) return
  
  chart = createChart(chartContainer.value, {
    ...chartOptions,
    width: chartContainer.value.clientWidth,
    height: props.height
  })
  
  // K线序列
  candlestickSeries = chart.addCandlestickSeries({
    upColor: '#10b981',
    downColor: '#ef4444',
    borderUpColor: '#10b981',
    borderDownColor: '#ef4444',
    wickUpColor: '#10b981',
    wickDownColor: '#ef4444'
  })
  
  // 成交量序列
  volumeSeries = chart.addHistogramSeries({
    color: '#3b82f6',
    priceFormat: {
      type: 'volume'
    },
    priceScaleId: ''
  })
  
  // 更新数据
  updateData()
  
  // 响应式调整
  const resizeObserver = new ResizeObserver(() => {
    window.requestAnimationFrame(() => {
      if (chart && chartContainer.value) {
        chart.applyOptions({ width: chartContainer.value.clientWidth })
      }
    })
  })
  resizeObserver.observe(chartContainer.value)
}

// 更新图表数据
function updateData() {
  if (!candlestickSeries || !volumeSeries || !props.klines.length) return
  
  // 转换K线数据
  const candleData = props.klines.map((k: any) => ({
    time: Math.floor(k.timestamp / 1000) as any,
    open: k.open,
    high: k.high,
    low: k.low,
    close: k.close
  }))
  
  // 转换成交量数据
  const volumeData = props.klines.map((k: any) => ({
    time: Math.floor(k.timestamp / 1000) as any,
    value: k.volume,
    color: k.close >= k.open ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'
  }))
  
  candlestickSeries.setData(candleData)
  volumeSeries.setData(volumeData)
  
  // 自动调整视图
  chart?.timeScale().fitContent()
}

// 销毁图表
function destroyChart() {
  if (chart) {
    chart.remove()
    chart = null
    candlestickSeries = null
    volumeSeries = null
  }
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
  })
})

onUnmounted(() => {
  destroyChart()
})

// 监听数据变化
watch(() => props.klines, () => {
  if (chart) {
    updateData()
  } else {
    nextTick(() => {
      initChart()
    })
  }
}, { deep: true })

// 监听高度变化
watch(() => props.height, (newHeight) => {
  if (chart) {
    chart.applyOptions({ height: newHeight })
  }
})

// 暴露方法
defineExpose({
  refresh: updateData,
  updatePriceLines
})

// 添加KeyLevels支持
interface KeyLevel {
  price: number
  type: 'support' | 'resistance'
  label?: string
}

const priceLines = ref<any[]>([])

function updatePriceLines(levels: KeyLevel[]) {
  if (!candlestickSeries) return
  
  // 清除现有价格线
  priceLines.value.forEach(line => candlestickSeries!.removePriceLine(line))
  priceLines.value = []
  
  // 添加新的价格线
  levels.forEach(level => {
    const color = level.type === 'resistance' ? '#ef4444' : '#10b981'
    const line = candlestickSeries!.createPriceLine({
      price: level.price,
      color: color,
      lineWidth: 1,
      lineStyle: 2, // Dashed
      axisLabelVisible: true,
      title: level.label || (level.type === 'resistance' ? '阻力' : '支撑'),
    })
    priceLines.value.push(line)
  })
}

// 监听keyLevels变化（如果有prop传入）
watch(() => props.keyLevels, (newLevels) => {
  if (newLevels) {
    updatePriceLines(newLevels)
  }
}, { deep: true })
</script>

<style lang="scss" scoped>
.kline-chart {
  width: 100%;
  height: v-bind('`${props.height}px`');
  position: relative;
  background: rgba(10, 10, 15, 0.5);
  border-radius: 8px;
}

.chart-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.3);
  
  p {
    margin-top: 12px;
    font-size: 14px;
  }
}

.chart-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(10, 10, 15, 0.8);
  color: rgba(255, 255, 255, 0.6);
  gap: 12px;
  
  .loading-icon {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
