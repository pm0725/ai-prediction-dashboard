<!--
  智链预测 - AI表现透视组件 (Performance Tracker)
  ================================================
  Visualizes AI performance metrics using ECharts.
  Features:
  - KPI Cards: Win Rate, PnL, Sharpe Ratio.
  - ECharts: Equity Curve, Confusion Matrix (Heatmap), Confidence Distribution.
  - History Table: Detailed log of past predictions.
-->
<template>
  <div class="min-h-screen bg-slate-900 text-slate-200 font-sans pb-10">
    <!-- Header -->
    <header class="h-16 border-b border-slate-700/50 bg-slate-800/40 backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-6">
      <div class="flex items-center gap-4">
        <button @click="$router.push('/')" class="icon-btn hover:bg-slate-700 p-2 rounded-full transition-colors">
           <el-icon><Back /></el-icon>
        </button>
        <h1 class="text-lg font-bold text-white flex items-center gap-2">
           AI Performance Analytics
           <span class="px-2 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30">BETA</span>
        </h1>
      </div>
      <div class="flex gap-2">
         <el-select v-model="timeRange" size="small" class="w-32">
            <el-option label="Last 7 Days" value="7d" />
            <el-option label="Last 30 Days" value="30d" />
            <el-option label="All Time" value="all" />
         </el-select>
      </div>
    </header>

    <main class="p-6 max-w-7xl mx-auto space-y-6">
       
       <!-- 1. KPI Cards -->
       <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="stat-card">
             <div class="label">Total Signals</div>
             <div class="value">1,248</div>
             <div class="sub text-slate-500">Avg 42/day</div>
          </div>
          <div class="stat-card">
             <div class="label">Win Rate</div>
             <div class="value text-emerald-400">68.5%</div>
             <div class="sub text-emerald-600">Top 5% of Models</div>
          </div>
          <div class="stat-card">
             <div class="label">Profit Factor</div>
             <div class="value text-blue-400">2.14</div>
             <div class="sub text-slate-500">Gross Win / Gross Loss</div>
          </div>
          <div class="stat-card">
             <div class="label">Sharpe Ratio</div>
             <div class="value text-amber-400">1.85</div>
             <div class="sub text-slate-500">Risk-Adjusted Return</div>
          </div>
       </div>

       <!-- 2. Charts Grid -->
       <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          <!-- Equity Curve -->
          <div class="glass-panel p-4 h-[350px] flex flex-col">
             <h3 class="panel-title mb-4">Cumulative Performance (Mock Equity)</h3>
             <div class="flex-1 w-full min-h-0">
                <v-chart class="chart" :option="equityOption" autoresize />
             </div>
          </div>

          <!-- Confusion Matrix (Heatmap) -->
          <div class="glass-panel p-4 h-[350px] flex flex-col">
             <h3 class="panel-title mb-4">Prediction Accuracy Matrix</h3>
             <div class="flex-1 w-full min-h-0">
                <v-chart class="chart" :option="heatmapOption" autoresize />
             </div>
          </div>

       </div>

       <!-- 3. Confidence Distribution -->
       <div class="glass-panel p-4 h-[300px] flex flex-col">
           <h3 class="panel-title mb-4">Win Rate by Confidence Level</h3>
           <div class="flex-1 w-full min-h-0">
              <v-chart class="chart" :option="confidenceOption" autoresize />
           </div>
       </div>

       <!-- 4. Detailed History Table -->
       <div class="glass-panel p-0 overflow-hidden flex flex-col">
          <div class="p-4 border-b border-slate-700/50 flex justify-between items-center bg-slate-800/20">
             <h3 class="panel-title">Signal History</h3>
             <button class="text-xs text-blue-400 hover:text-blue-300">Export CSV</button>
          </div>
          <el-table :data="historyData" style="width: 100%" height="400" class="custom-table">
             <el-table-column prop="time" label="Time" width="160" />
             <el-table-column prop="symbol" label="Symbol" width="100">
                <template #default="scope">
                   <span class="font-bold">{{ scope.row.symbol }}</span>
                </template>
             </el-table-column>
             <el-table-column prop="direction" label="Direction" width="100">
                <template #default="scope">
                   <span :class="scope.row.direction === 'LONG' ? 'text-emerald-400' : 'text-rose-400'">{{ scope.row.direction }}</span>
                </template>
             </el-table-column>
             <el-table-column prop="confidence" label="Conf." width="80">
                <template #default="scope">{{ scope.row.confidence }}%</template>
             </el-table-column>
             <el-table-column prop="result" label="Result" width="100">
                <template #default="scope">
                   <span v-if="scope.row.result > 0" class="text-emerald-400">+{{ scope.row.result }}%</span>
                   <span v-else class="text-rose-400">{{ scope.row.result }}%</span>
                </template>
             </el-table-column>
             <el-table-column prop="model" label="Model Ver." />
             <el-table-column label="Action" width="100" align="center">
                <template #default>
                   <el-button size="small" type="info" plain circle text>
                      <el-icon><View /></el-icon>
                   </el-button>
                </template>
             </el-table-column>
          </el-table>
       </div>

    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Back, View } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, HeatmapChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

// Register ECharts components
use([
  CanvasRenderer,
  LineChart,
  HeatmapChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent
])

// State
const timeRange = ref('30d')

// Mock Data for Charts
const equityOption = computed(() => ({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { top: 20, right: 20, bottom: 20, left: 40, containLabel: true },
    xAxis: {
        type: 'category',
        data: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
        axisLine: { lineStyle: { color: '#475569' } },
        axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#334155', type: 'dashed' } },
        axisLabel: { color: '#94a3b8' }
    },
    series: [{
        data: [1000, 1050, 1030, 1100, 1150, 1120, 1250],
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#10b981', width: 3 },
        areaStyle: {
            color: {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: '#10b98150' }, { offset: 1, color: '#10b98100' }]
            }
        }
    }]
}))

const heatmapOption = computed(() => ({
    backgroundColor: 'transparent',
    tooltip: { position: 'top' },
    grid: { top: 20, right: 20, bottom: 20, left: 20, containLabel: true },
    xAxis: {
        type: 'category',
        data: ['Pred Long', 'Pred Short', 'Pred Neutral'],
        axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
        type: 'category',
        data: ['Actual Long', 'Actual Short', 'Actual Flat'],
        axisLabel: { color: '#94a3b8' }
    },
    visualMap: {
        min: 0, max: 150, show: false,
        inRange: { color: ['#1e293b', '#3b82f6', '#10b981'] }
    },
    series: [{
        type: 'heatmap',
        data: [
            [0, 0, 120], [0, 1, 15], [0, 2, 8],
            [1, 0, 10], [1, 1, 95], [1, 2, 12],
            [2, 0, 5], [2, 1, 8], [2, 2, 45]
        ],
        label: { show: true, color: '#fff' }
    }]
}))

const confidenceOption = computed(() => ({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    grid: { top: 30, right: 20, bottom: 20, left: 40, containLabel: true },
    xAxis: {
        type: 'category',
        data: ['50-60%', '60-70%', '70-80%', '80-90%', '90%+'],
        axisLabel: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: '#475569' } }
    },
    yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#334155', type: 'dashed' } }
    },
    series: [
        {
            name: 'Win Rate',
            type: 'bar',
            data: [45, 52, 65, 78, 88],
            itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
            label: { show: true, position: 'top', color: '#fff', formatter: '{c}%' }
        }
    ]
}))

// Mock History Data
const historyData = Array.from({ length: 20 }).map((_, i) => ({
    time: `2024-02-04 ${10 + i}:00`,
    symbol: Math.random() > 0.5 ? 'BTCUSDT' : 'ETHUSDT',
    direction: Math.random() > 0.5 ? 'LONG' : 'SHORT',
    confidence: Math.floor(60 + Math.random() * 35),
    result: (Math.random() * 10 - 3).toFixed(2),
    model: 'v3.2'
}))

</script>

<style scoped>
.panel-title {
    font-size: 0.75rem;
    line-height: 1rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.glass-panel {
    background-color: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(51, 65, 85, 0.5);
    border-radius: 0.75rem;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}
.stat-card {
    background-color: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(4px);
    border: 1px solid rgba(51, 65, 85, 0.5);
    border-radius: 0.75rem;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}
.stat-card .label {
    font-size: 0.875rem;
    color: #94a3b8;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}
.stat-card .value {
    font-size: 2.25rem;
    font-weight: 900;
    color: #f1f5f9;
    letter-spacing: -0.025em;
}
.stat-card .sub {
    font-size: 0.75rem;
    margin-top: 0.5rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
.icon-btn {
    color: #94a3b8;
    transition-property: color, background-color, border-color, text-decoration-color, fill, stroke;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 150ms;
}
.icon-btn:hover {
    color: #ffffff;
}

/* Custom Table Styles for Dark Mode */
:deep(.el-table) {
    --el-table-bg-color: transparent !important;
    --el-table-tr-bg-color: transparent !important;
    --el-table-header-bg-color: #1e293b !important;
    --el-table-border-color: #334155 !important;
    --el-table-text-color: #cbd5e1 !important;
    --el-table-header-text-color: #94a3b8 !important;
    --el-table-row-hover-bg-color: #334155 !important;
}
:deep(.el-table th.el-table__cell) {
    background-color: #1e293b !important;
}
</style>
