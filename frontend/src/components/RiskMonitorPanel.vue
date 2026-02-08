<!--
  智链预测 - 风险监控面板 (Risk Monitor)
  =======================================
  Displays institutional alerts, volatility radar, and risk breakdown.
-->
<template>
  <div class="flex flex-col gap-4 h-full overflow-hidden">
    
    <!-- 机构预警雷达 (Fixed Top) -->
   <div class="glass-panel p-5 bg-gradient-to-b from-slate-800/60 to-slate-900/60 border-t-2" :class="alertBorderClass">
       <div class="flex items-center gap-2 mb-4">
         <el-icon class="text-amber-400"><Warning /></el-icon>
         <h2 class="panel-title text-amber-100">机构预警雷达</h2>
       </div>
       
       <div class="flex flex-col items-center py-2">
          <!-- 仪表盘分数 -->
          <div class="relative w-24 h-24 flex items-center justify-center mb-1">
             <div class="absolute inset-0 rounded-full border-4 border-slate-700"></div>
             <div class="absolute inset-0 rounded-full border-4 border-t-transparent border-l-transparent transform -rotate-45"
                  :class="volatilityColorText"
                  :style="{ borderColor: volatilityColorStyle }"
             ></div>
             
             <div class="flex flex-col items-center">
                <span class="text-3xl font-black text-white tracking-tighter font-mono">{{ displayVolatilityScore }}</span>
                <span class="text-[11px] text-slate-400 uppercase tracking-widest mt-0.5">波动率</span>
             </div>
          </div>
          
          <div class="flex gap-2 flex-wrap justify-center mt-1">
             <span v-if="prediction.whaleActivity" class="tag-pill bg-blue-900/50 text-blue-300 border-blue-700/50">
               🐋 {{ prediction.whaleActivity.label }}
             </span>
             <span v-for="gap in prediction.liquidityGaps" :key="gap" class="tag-pill bg-rose-900/50 text-rose-300 border-rose-700/50">
               🩸 {{ formatGap(gap) }}
             </span>
          </div>
       </div>
    </div>

    <!-- 风险分析 (Fixed Middle) -->
    <div class="glass-panel p-3">
       <div class="flex justify-between items-center mb-2">
         <h2 class="panel-title">风险画像</h2>
         <span :class="riskLevelColorText" class="text-base font-bold">{{ prediction.riskLevel || '未知' }}</span>
       </div>
       <div class="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden mb-3">
         <div class="h-full rounded-full transition-all duration-1000" 
              :class="riskLevelBg" 
              :style="{ width: riskPercentage + '%' }"></div>
       </div>
       <div class="flex flex-wrap gap-2">
         <div v-for="(f, i) in prediction.riskFactors.slice(0, 3)" :key="i" class="flex items-center gap-1.5 text-sm text-slate-300 bg-slate-800/50 px-2 py-1 rounded border border-slate-700/30">
            <el-icon class="text-amber-500"><WarningCaller /></el-icon>
            <span>{{ f }}</span>
         </div>
       </div>
    </div>

    <!-- 历史记录列表 (Scrollable Fill) -->
    <div class="glass-panel flex-1 flex flex-col min-h-0 overflow-hidden">
       <div class="p-3 border-b border-slate-700/30 bg-slate-800/30">
          <h2 class="panel-title">最近分析信号</h2>
       </div>
       <div class="flex-1 overflow-y-auto space-y-2 p-3 no-scrollbar">
          <div 
            v-for="(rec, i) in predictionStore.history" 
            :key="i"
            @click="restorePrediction(rec)"
            class="p-2.5 rounded bg-slate-800/20 hover:bg-slate-700/40 transition-colors cursor-pointer border border-transparent hover:border-slate-600/30"
          >
             <div class="flex justify-between items-center mb-1">
                <span class="font-bold text-base text-slate-300">{{ rec.symbol }}</span>
                <span class="text-sm text-slate-500 font-mono">{{ rec.time.split(' ')[1] }}</span>
             </div>
             <div class="flex justify-between items-center">
                <span :class="['text-base font-bold', rec.direction.includes('涨') ? 'text-emerald-400' : 'text-rose-400']">
                  {{ rec.direction }}
                </span>
                <span class="text-sm px-1.5 py-0.5 rounded bg-slate-900/50 text-slate-400 border border-slate-700/30 font-mono">
                  {{ rec.confidence }}%
                </span>
             </div>
          </div>
       </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { usePredictionStore } from '@/stores'
import { Warning, WarningFilled as WarningCaller } from '@element-plus/icons-vue'

const predictionStore = usePredictionStore()

const prediction = computed(() => {
    const raw = predictionStore.prediction as any || {}
    // 优先使用轮询得到的实时雷达数据
    const vScore = predictionStore.radarData.volatility_score || raw.volatility_score || 0
    const whaleData = predictionStore.radarData.whale_activity || raw.whale_activity
    const gaps = predictionStore.radarData.liquidity_gaps || raw.liquidity_gaps || []
    
    return {
        direction: raw.direction || '---',
        confidence: raw.confidence || 0,
        riskLevel: raw.risk_level,
        riskFactors: raw.risk_warning || [],
        volatilityScore: vScore,
        whaleActivity: whaleData ? { 
            label: whaleData.whale_ratio > 0.4 ? '异常活跃' : '平稳', 
            trend: whaleData.net_whale_vol > 0 ? 'bullish' : 'bearish' 
        } : (vScore > 70 ? { label: '活跃', trend: 'warning' } : null),
        liquidityGaps: gaps.length > 0 ? gaps : (vScore > 80 ? ['真空区'] : [])
    }
})

// Visual Helpers
const displayVolatilityScore = computed(() => Math.round(prediction.value.volatilityScore))

const volatilityColorText = computed(() => {
    const s = displayVolatilityScore.value
    if (s > 75) return 'border-rose-500' 
    if (s > 40) return 'border-amber-400'
    return 'border-emerald-500'
})

const volatilityColorStyle = computed(() => {
    const s = displayVolatilityScore.value
    if (s > 75) return '#f43f5e' 
    if (s > 40) return '#fbbf24' 
    return '#10b981' 
})

const alertBorderClass = computed(() => {
    const s = displayVolatilityScore.value
    if (s > 75) return 'border-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.3)]'
    return 'border-transparent' // Standard
})

const riskLevelColorText = computed(() => {
    const l = prediction.value.riskLevel
    if (l === '极高') return 'text-rose-500'
    if (l === '高') return 'text-orange-500'
    return 'text-emerald-400'
})

const riskLevelBg = computed(() => {
    const l = prediction.value.riskLevel
    if (l === '极高') return 'bg-rose-500'
    if (l === '高') return 'bg-orange-500'
    return 'bg-emerald-500'
})

const riskPercentage = computed(() => {
    const l = prediction.value.riskLevel
    if (l === '极高') return 100
    if (l === '高') return 75
    if (l === '中') return 50
    return 25
})

function formatGap(g: string) {
    if (g === 'upward_liquidity_gap') return '上方真空'
    if (g === 'downward_liquidity_gap') return '下方真空'
    return g
}

function restorePrediction(rec: any) {
    if (rec.fullData) {
        // Restore full prediction context
        predictionStore.prediction = rec.fullData
        // Also switch symbol context if different
        if (rec.symbol !== predictionStore.currentSymbol) {
             predictionStore.currentSymbol = rec.symbol
        }
    } else {
        console.warn('Full prediction data missing for this record')
    }
}

// 轮询逻辑
let pollInterval: any = null

onMounted(() => {
    // 初始加载一次
    predictionStore.pollRadarData()
    // 每 10 秒轮询一次
    pollInterval = setInterval(() => {
        predictionStore.pollRadarData()
    }, 10000)
})

onUnmounted(() => {
    if (pollInterval) {
        clearInterval(pollInterval)
    }
})
</script>

<style scoped>
 .panel-title {
    font-size: 1.0rem; /* 16px */
    line-height: 1.5rem;
    font-weight: 800;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.glass-panel {
    background-color: rgba(30, 41, 59, 0.4); /* bg-slate-800/40 */
    backdrop-filter: blur(12px);
    border: 1px solid rgba(51, 65, 85, 0.5); /* border-slate-700/50 */
    border-radius: 0.75rem; /* rounded-xl */
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); /* shadow-lg */
}
.tag-pill {
    padding: 0.25rem 0.5rem; /* px-2 py-1 */
    border-radius: 0.25rem;
    font-size: 11px;
    border-width: 1px;
    font-weight: 500;
}
.no-scrollbar::-webkit-scrollbar {
    display: none;
}
.no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
