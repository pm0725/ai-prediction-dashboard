<template>
  <div class="tactical-hud relative overflow-hidden rounded-2xl border border-slate-700/50 bg-slate-900/40 backdrop-blur-xl shadow-2xl transition-all duration-500 hover:shadow-cyan-900/20 group">
     <!-- Background Effects -->
     <div class="absolute inset-0 bg-gradient-to-br from-slate-800/10 via-transparent to-slate-900/50 pointer-events-none"></div>
     <div class="absolute -top-24 -right-24 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none group-hover:bg-blue-500/20 transition-all duration-700"></div>

     <div class="relative z-10 p-6 flex flex-col h-full">
         <!-- Header -->
        <div class="flex justify-between items-start mb-8">
           <div>
              <div class="flex items-center gap-2 mb-2">
                  <div class="h-2 w-2 rounded-full animate-pulse" :class="isBullish ? 'bg-emerald-400' : 'bg-rose-400'"></div>
                  <span class="text-xs font-display tracking-[0.2em] text-cyan-400/80 uppercase">Tactical Execution // 战术执行</span>
              </div>
              <h2 class="text-4xl font-black text-white tracking-tight flex items-center gap-3 font-display">
                 {{ prediction.symbol }} 
                 <span class="text-2xl font-tabular text-slate-600 font-light">|</span>
                 <span class="text-2xl bg-clip-text text-transparent bg-gradient-to-r font-display" 
                       :class="isBullish ? 'from-emerald-400 to-teal-300' : 'from-rose-400 to-pink-500'">
                    {{ prediction.prediction_cn || prediction.prediction }}
                 </span>
              </h2>
           </div>
           
           <!-- Live Price Badge -->
           <div class="flex flex-col items-end">
              <div class="flex items-baseline gap-2">
                  <span class="text-sm text-slate-500 font-display">LIVE</span>
                  <span class="text-5xl font-tabular font-bold text-slate-200 tracking-tight shadow-glow">{{ formatPrice(currentPrice) }}</span>
              </div>
              <!-- PnL Estimate (Visual Only) -->
              <span v-if="pnlPercentage" class="text-sm font-tabular font-bold mt-1" :class="pnlPercentage > 0 ? 'text-emerald-400' : 'text-rose-400'">
                  {{ pnlPercentage > 0 ? '+' : '' }}{{ pnlPercentage.toFixed(2) }}%
              </span>
           </div>
        </div>

        <!-- ⚔️ Battlefield Visualizer -->
        <div class="relative h-24 w-full mb-10 select-none">
            <!-- Base Track -->
            <div class="absolute top-1/2 left-0 right-0 h-1.5 bg-slate-700/30 rounded-full"></div>

            <!-- Danger Zone (SL to Entry) -->
            <div class="absolute top-1/2 h-1.5 bg-gradient-to-r from-rose-900/0 via-rose-500/50 to-rose-900/0 blur-[1px]"
                 :style="{ left: `${Math.min(markerPositions.sl, markerPositions.entryStart)}%`, width: `${Math.abs(markerPositions.entryStart - markerPositions.sl)}%` }"></div>

            <!-- Success Zone (Entry to TP) -->
            <div class="absolute top-1/2 h-1.5 bg-gradient-to-r from-emerald-900/0 via-emerald-500/50 to-emerald-900/0 blur-[1px]"
                 :style="{ left: `${Math.min(markerPositions.entryEnd, markerPositions.tp[markerPositions.tp.length-1])}%`, width: `${Math.abs(markerPositions.tp[markerPositions.tp.length-1] - markerPositions.entryEnd)}%` }"></div>

            <!-- SL Marker -->
            <el-tooltip :content="`止损 (Stop Loss): ${formatPrice(Number(prediction.stop_loss))}`" placement="top" effect="dark">
                <div class="absolute top-1/2 -translate-y-1/2 transition-all duration-500 z-20 cursor-help group/sl" 
                     :style="{ left: `${markerPositions.sl}%` }">
                    <div class="w-8 h-8 rounded-full bg-slate-900 border border-rose-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(244,63,94,0.3)] group-hover/sl:scale-110 group-hover/sl:shadow-[0_0_20px_rgba(244,63,94,0.6)] transition-all">
                        <el-icon class="text-rose-500" :size="16"><WarnTriangleFilled /></el-icon>
                    </div>
                    <div class="absolute -bottom-8 left-1/2 -translate-x-1/2 text-xs font-tabular text-rose-400 opacity-0 group-hover/sl:opacity-100 transition-opacity whitespace-nowrap bg-slate-900/80 px-2 py-1 rounded">
                        SL {{ formatPrice(Number(prediction.stop_loss)) }}
                    </div>
                </div>
            </el-tooltip>

            <!-- Entry Zone -->
            <div class="absolute top-1/2 -translate-y-1/2 h-10 border-x-2 border-blue-500/30 bg-blue-500/5 transition-all duration-500 z-10"
                 :style="{ left: `${markerPositions.entryStart}%`, width: `${markerPositions.entryEnd - markerPositions.entryStart}%` }">
                 <div class="absolute -top-7 left-1/2 -translate-x-1/2 text-[10px] font-bold text-blue-400 uppercase tracking-wider whitespace-nowrap font-display">Entry Zone</div>
            </div>

            <!-- Current Price Cursor -->
            <div class="absolute top-1/2 -translate-y-1/2 transition-all duration-300 z-30 pointer-events-none"
                 :style="{ left: `${markerPositions.current}%` }">
                <!-- Pulse Effect -->
                <div class="absolute -top-3 -left-3 w-6 h-6 bg-white rounded-full animate-ping opacity-20"></div>
                <div class="w-0.5 h-12 -mt-6 bg-gradient-to-b from-transparent via-white to-transparent shadow-[0_0_10px_white]"></div>
                <!-- Price Label Bubble -->
                <div class="absolute top-8 left-1/2 -translate-x-1/2 px-3 py-1 bg-slate-800/90 text-xs font-tabular text-white rounded border border-slate-600 shadow-lg whitespace-nowrap backdrop-blur-sm">
                    {{ formatPrice(currentPrice) }}
                </div>
            </div>

            <!-- TP Markers -->
            <template v-for="(tp, idx) in (Array.isArray(prediction.take_profit) ? prediction.take_profit : [prediction.take_profit])" :key="idx">
                <el-tooltip :content="`止盈目标 ${Number(idx) + 1}: ${formatPrice(Number(tp))}`" placement="top" effect="dark">
                    <div class="absolute top-1/2 -translate-y-1/2 transition-all duration-500 z-20 cursor-help group/tp"
                         :style="{ left: `${markerPositions.tp[Number(idx)]}%` }">
                        <div class="w-8 h-8 rounded-full bg-slate-900 border border-emerald-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.3)] group-hover/tp:scale-110 group-hover/tp:shadow-[0_0_20px_rgba(16,185,129,0.6)] transition-all">
                            <el-icon class="text-emerald-500" :size="16"><Trophy /></el-icon>
                        </div>
                        <div class="absolute -bottom-8 left-1/2 -translate-x-1/2 text-xs font-tabular text-emerald-400 opacity-0 group-hover/tp:opacity-100 transition-opacity whitespace-nowrap bg-slate-900/80 px-2 py-1 rounded">
                            TP{{ Number(idx) + 1 }}
                        </div>
                    </div>
                </el-tooltip>
            </template>
        </div>

        <!-- Metrics Grid -->
        <div class="grid grid-cols-4 gap-4 mt-auto">
            <!-- R:R Ratio -->
            <div class="flex items-center gap-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 transition-all duration-300 hover:bg-slate-800 hover:border-slate-600 group">
                <div class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500/20 group-hover:text-indigo-300">
                    <el-icon :size="20"><ScaleToOriginal /></el-icon>
                </div>
                <div>
                   <div class="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1 font-display">风险收益比 (R:R)</div>
                   <div class="text-xl font-tabular font-bold leading-none text-indigo-400">{{ riskRewardRatio }}</div>
                </div>
            </div>

            <!-- Confidence -->
            <div class="flex items-center gap-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 transition-all duration-300 hover:bg-slate-800 hover:border-slate-600 group">
                <div class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20 group-hover:text-blue-300">
                    <el-icon :size="20"><Aim /></el-icon>
                </div>
                <div>
                   <div class="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1 font-display">AI 置信度</div>
                   <div class="text-xl font-tabular font-bold leading-none text-blue-400">{{ prediction.confidence }}%</div>
                </div>
            </div>

            <!-- Duration -->
            <div class="flex items-center gap-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 transition-all duration-300 hover:bg-slate-800 hover:border-slate-600 group">
                 <div class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 bg-slate-500/10 text-slate-400 group-hover:bg-slate-500/20 group-hover:text-slate-300">
                    <el-icon :size="20"><Timer /></el-icon>
                </div>
                <div>
                   <div class="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1 font-display">预计持仓</div>
                   <div class="text-xl font-tabular font-bold leading-none text-slate-300">{{ estimatedDuration }}</div>
                </div>
            </div>

            <!-- Risk Level -->
             <div class="flex items-center gap-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 transition-all duration-300 hover:bg-slate-800 hover:border-slate-600 group">
                 <div class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 bg-amber-500/10 text-amber-400 group-hover:bg-amber-500/20 group-hover:text-amber-300">
                    <el-icon :size="20"><Warning /></el-icon>
                </div>
                <div>
                   <div class="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1 font-display">波动风险</div>
                   <div class="text-xl font-display font-bold leading-none" :class="riskLevelColor">
                      {{ localizedRiskLevel }}
                   </div>
                </div>
            </div>
        </div>
     </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Aim, ScaleToOriginal, Timer, Warning, Trophy, WarnTriangleFilled } from '@element-plus/icons-vue'
import { formatPrice } from '@/utils/formatters'

const props = defineProps(['prediction', 'currentPrice'])

// Computed Helpers
const isBullish = computed(() => {
    const pred = props.prediction.prediction_cn || props.prediction.prediction || ''
    return pred.includes('涨') || pred.toLowerCase().includes('bullish')
})

const pnlPercentage = computed(() => {
    if(!props.currentPrice || !entryZone.value.low) return 0
    const entryAvg = (entryZone.value.low + entryZone.value.high) / 2
    const diff = props.currentPrice - entryAvg
    const percentage = (diff / entryAvg) * 100
    return isBullish.value ? percentage : -percentage
})


// Input Normalization
const entryZone = computed(() => {
    const z = props.prediction.entry_zone
    if (typeof z === 'string') {
        const parts = z.split('-').map(s => parseFloat(s.trim().replace(/,/g, '')))
        if (parts.length === 2 && !isNaN(parts[0])) return { low: parts[0], high: parts[1] }
        return { low: props.currentPrice * 0.99, high: props.currentPrice * 1.01 }
    }
    return z || { low: 0, high: 0 }
})

// Dynamic Positioning Logic
const markerPositions = computed(() => {
    const p = props.prediction
    const tpArr = Array.isArray(p.take_profit) ? p.take_profit.map(Number) : [Number(p.take_profit)]
    const sl = Number(p.stop_loss)
    const entryLow = Number(entryZone.value.low)
    const entryHigh = Number(entryZone.value.high)
    
    // Determine bounds including current price to avoid cursor flying off
    const allPrices = [sl, entryLow, entryHigh, ...tpArr, props.currentPrice].filter(n => !isNaN(n))
    const minVal = Math.min(...allPrices)
    const maxVal = Math.max(...allPrices)
    
    // Add 10% padding
    const padding = (maxVal - minVal) * 0.1
    const min = minVal - padding
    const max = maxVal + padding
    const span = max - min || 1

    const getPos = (val: number) => {
        if(!val) return 50
        const raw = ((val - min) / span) * 100
        return Math.min(Math.max(raw, 0), 100) // Clamp 0-100
    }

    return {
        sl: getPos(sl),
        entryStart: Math.min(getPos(entryLow), getPos(entryHigh)),
        entryEnd: Math.max(getPos(entryLow), getPos(entryHigh)),
        tp: tpArr.map(getPos),
        current: getPos(props.currentPrice)
    }
})

const riskRewardRatio = computed(() => {
    const p = props.prediction
    if (!p || !p.stop_loss || !p.take_profit) return '---'
    
    const entry = (entryZone.value.low + entryZone.value.high) / 2
    const sl = Number(p.stop_loss)
    const tp = Number(Array.isArray(p.take_profit) ? p.take_profit[0] : p.take_profit)
    
    if (!entry || !sl || !tp) return '---'
    
    const risk = Math.abs(entry - sl)
    const reward = Math.abs(tp - entry)
    
    if (risk < 0.00001) return '---'
    return `1:${(reward / risk).toFixed(1)}`
})

const estimatedDuration = computed(() => {
    const tf = props.prediction?.timeframe || '4h'
    const map: Record<string, string> = {
        '15m': '30m - 2h',
        '1h': '2h - 6h',
        '4h': '8h - 24h',
        '1d': '2d - 5d',
        '1w': '1w - 3w'
    }
    return map[tf.toLowerCase()] || '日内'
})

// 风险等级中英文映射
const riskLevelMap: Record<string, string> = {
  'low': '低', 'medium': '中', 'high': '高', 'extreme': '极高',
  '低': '低', '中': '中', '高': '高', '极高': '极高'
}
const localizedRiskLevel = computed(() => {
  const level = props.prediction.risk_level || '中'
  return riskLevelMap[level.toLowerCase()] || level
})
const riskLevelColor = computed(() => {
  const lv = localizedRiskLevel.value
  if (lv === '低') return 'text-emerald-400'
  if (lv === '中') return 'text-amber-400'
  return 'text-rose-400'
})
</script>


