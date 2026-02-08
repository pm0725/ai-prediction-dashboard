<!--
  智链预测 - 数据源监控组件 (Data Source Monitor)
  ==============================================
  System status monitor with network topology and latency tracking.
  Features:
  - Network Topology (ECharts Graph)
  - Data Source Health Cards
  - Latency Trends (Heatmap/Line)
  - Fault Simulation Controls
-->
<template>
  <el-dialog
    v-model="visible"
    title="数据源仿真演示 (模拟数据)"
    width="80%"
    :class="'monitor-dialog'"
    :before-close="handleClose"
    append-to-body
    align-center
  >
    <div class="monitor-container p-2 text-slate-200">
      
      <!-- 1. Header Metrics -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="metric-card bg-slate-800/50 p-4 rounded-lg border border-slate-700">
           <div class="text-xs text-slate-400 uppercase font-bold">总体健康度</div>
           <div class="text-2xl font-black text-emerald-400 mt-1 flex items-center gap-2">
             98.5% <el-icon class="text-lg"><CircleCheckFilled /></el-icon>
           </div>
        </div>
        <div class="metric-card bg-slate-800/50 p-4 rounded-lg border border-slate-700">
           <div class="text-xs text-slate-400 uppercase font-bold">平均延迟</div>
           <div class="text-2xl font-black text-blue-400 mt-1">42ms</div>
        </div>
        <div class="metric-card bg-slate-800/50 p-4 rounded-lg border border-slate-700">
           <div class="text-xs text-slate-400 uppercase font-bold">活动数据源</div>
           <div class="text-2xl font-black text-slate-200 mt-1">5/5</div>
        </div>
        <div class="metric-card bg-slate-800/50 p-4 rounded-lg border border-slate-700">
           <div class="text-xs text-slate-400 uppercase font-bold">数据异常</div>
           <div class="text-2xl font-black text-slate-200 mt-1">0</div>
        </div>
      </div>

      <!-- 2. Main Visualizations -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[400px] mb-6">
         <!-- Network Topology -->
         <div class="glass-panel p-4 flex flex-col bg-slate-800/30 rounded-xl border border-slate-700/50">
            <h3 class="panel-title mb-2">数据流拓扑图</h3>
            <div class="flex-1 w-full min-h-0">
               <v-chart class="chart" :option="topologyOption" autoresize />
            </div>
         </div>

         <!-- Latency Matrix -->
         <div class="glass-panel p-4 flex flex-col bg-slate-800/30 rounded-xl border border-slate-700/50">
            <h3 class="panel-title mb-2">延迟热力图 (24h)</h3>
            <div class="flex-1 w-full min-h-0">
               <v-chart class="chart" :option="latencyOption" autoresize />
            </div>
         </div>
      </div>

      <!-- 3. Data Source List -->
      <div class="glass-panel bg-slate-800/30 rounded-xl border border-slate-700/50 overflow-hidden">
         <div class="p-4 border-b border-slate-700/50 bg-slate-800/50 flex justify-between items-center">
            <h3 class="panel-title">数据源详情</h3>
            <el-button size="small" type="primary" plain @click="refreshAll" :loading="refreshing">
               刷新全部
            </el-button>
         </div>
         <table class="w-full text-left text-sm">
            <thead class="text-xs text-slate-500 uppercase bg-slate-800/50">
               <tr>
                  <th class="p-3">来源名称</th>
                  <th class="p-3">类型</th>
                  <th class="p-3">状态</th>
                  <th class="p-3">延迟</th>
                  <th class="p-3">质量</th>
                  <th class="p-3">最后更新</th>
                  <th class="p-3 text-right">操作</th>
               </tr>
            </thead>
            <tbody>
               <tr v-for="source in sources" :key="source.id" class="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors">
                  <td class="p-3 font-bold text-slate-300">{{ source.name }}</td>
                  <td class="p-3 text-xs text-slate-500 font-mono">{{ source.type }}</td>
                  <td class="p-3">
                     <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded textxs font-bold"
                           :class="getStatusClass(source.status)">
                        <span class="w-1.5 h-1.5 rounded-full bg-current"></span>
                        {{ (statusMap as any)[source.status] || source.status }}
                     </span>
                  </td>
                  <td class="p-3 font-mono" :class="getLatencyClass(source.latency)">{{ source.latency }}ms</td>
                  <td class="p-3 text-amber-400">
                     <span v-for="n in 5" :key="n" :class="n <= source.quality ? 'opacity-100' : 'opacity-20'">★</span>
                  </td>
                  <td class="p-3 text-slate-400 text-xs">{{ source.lastUpdate }}</td>
                  <td class="p-3 text-right">
                     <el-button size="small" text bg type="danger" @click="simulateError(source)">故障模拟</el-button>
                  </td>
               </tr>
            </tbody>
         </table>
      </div>

    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { CircleCheckFilled } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart, HeatmapChart } from 'echarts/charts'
import {
  TooltipComponent,
  LegendComponent,
  GridComponent,
  VisualMapComponent
} from 'echarts/components'
import VChart from 'vue-echarts'


use([
  CanvasRenderer,
  GraphChart,
  HeatmapChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  VisualMapComponent
])

const props = defineProps(['modelValue', 'symbol', 'timeframe', 'depth', 'risk'])

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const handleClose = () => {
  visible.value = false
}

// ================= Mock Data =================

const refreshing = ref(false)

const statusMap = {
  'Optimal': '正常',
  'Normal': '一般',
  'Degraded': '异常',
  'Error': '错误',
  '故障': '故障'
}

const sources = ref([
    { id: 1, name: 'Binance API', type: '交易所', status: 'Optimal', latency: 45, quality: 5, lastUpdate: '刚刚' },
    { id: 2, name: 'Coinbase Pro', type: '交易所', status: 'Normal', latency: 120, quality: 4, lastUpdate: '2秒前' },
    { id: 3, name: 'Glassnode', type: '链上数据', status: 'Optimal', latency: 210, quality: 5, lastUpdate: '1分钟前' },
    { id: 4, name: 'CryptoPanic', type: '新闻聚合', status: 'Degraded', latency: 850, quality: 3, lastUpdate: '5分钟前' },
    { id: 5, name: 'Twitter/X', type: '社交媒体', status: 'Normal', latency: 320, quality: 4, lastUpdate: '15秒前' }
])

// Topology Data
const topologyOption = computed(() => ({
    backgroundColor: 'transparent',
    tooltip: {},
    series: [
        {
            type: 'graph',
            layout: 'force',
            symbolSize: 40,
            roam: true,
            label: { show: true, color: '#fff' },
            edgeSymbol: ['circle', 'arrow'],
            edgeSymbolSize: [2, 8],
            force: { repulsion: 300, edgeLength: 100 },
            data: [
                { name: 'AI 核心', symbolSize: 60, itemStyle: { color: '#3b82f6' } },
                { name: 'Binance', itemStyle: { color: '#10b981' } },
                { name: 'Coinbase', itemStyle: { color: '#10b981' } },
                { name: 'Glassnode', itemStyle: { color: '#8b5cf6' } },
                { name: '新闻 API', itemStyle: { color: '#f59e0b' } },
                { name: '数据库', itemStyle: { color: '#64748b' } }
            ],
            links: [
                { source: 'Binance', target: 'AI 核心' },
                { source: 'Coinbase', target: 'AI 核心' },
                { source: 'Glassnode', target: 'AI 核心' },
                { source: '新闻 API', target: 'AI 核心' },
                { source: 'AI 核心', target: '数据库' }
            ],
            lineStyle: { opacity: 0.5, width: 2, curveness: 0.1 }
        }
    ]
}))

// Heatmap Data (Mock)
const hours = ['12a', '2a', '4a', '6a', '8a', '10a', '12p', '2p', '4p', '6p', '8p', '10p']
const days = ['Binance', 'Coinbase', '链上数据', '新闻']
const data = days.map((_, i) => {
    return hours.map((_, j) => [j, i, Math.floor(Math.random() * 100) + (i === 3 ? 200 : 20)])
}).flat()

const latencyOption = computed(() => ({
    backgroundColor: 'transparent',
    tooltip: { position: 'top' },
    grid: { height: '80%', top: '10%' },
    xAxis: { type: 'category', data: hours, axisLine: { lineStyle: { color: '#475569' } } },
    yAxis: { type: 'category', data: days, axisLine: { lineStyle: { color: '#475569' } } },
    visualMap: {
        min: 0, max: 500, calculable: true, orient: 'horizontal', left: 'center', bottom: '0%',
        inRange: { color: ['#10b981', '#f59e0b', '#ef4444'] },
        textStyle: { color: '#fff' }
    },
    series: [{
        type: 'heatmap',
        data: data,
        label: { show: false },
        itemStyle: { borderRadius: 4, borderColor: '#1e293b', borderWidth: 2 }
    }]
}))

// Methods
function getStatusClass(status: string) {
    if (status === 'Optimal') return 'bg-emerald-500/10 text-emerald-400'
    if (status === 'Normal') return 'bg-blue-500/10 text-blue-400'
    if (status === 'Degraded') return 'bg-amber-500/10 text-amber-400'
    if (status === 'Error' || status === '故障') return 'bg-rose-500/10 text-rose-400'
    return 'bg-rose-500/10 text-rose-400' // Default for unknown status
}

function getLatencyClass(ms: number) {
    if (ms < 100) return 'text-emerald-400'
    if (ms < 300) return 'text-amber-400'
    return 'text-rose-400'
}

function refreshAll() {
    refreshing.value = true
    setTimeout(() => {
        sources.value = sources.value.map(s => ({
            ...s,
            latency: Math.floor(Math.random() * 200) + 20,
            lastUpdate: '刚刚'
        }))
        refreshing.value = false
    }, 1000)
}

function simulateError(source: any) {
    source.status = '故障'
    source.latency = 9999
    source.quality = 1
}

</script>

<style scoped>
.panel-title {
    font-size: 0.75rem; /* text-xs */
    line-height: 1rem;
    font-weight: 700;
    color: #94a3b8; /* text-slate-400 */
    text-transform: uppercase;
    letter-spacing: 0.1em; /* tracking-widest */
}
:deep(.el-dialog) {
    background: rgba(15, 23, 42, 0.95) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(51, 65, 85, 0.5);
    border-radius: 16px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}
:deep(.el-dialog__title) {
    color: #e2e8f0;
    font-weight: 700;
}
:deep(.el-dialog__headerbtn .el-dialog__close) {
    color: #94a3b8;
}
</style>
