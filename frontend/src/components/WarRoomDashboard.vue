<template>
  <div class="war-room-dashboard h-full flex flex-col gap-4 relative transition-all duration-1000" :class="data ? getAmbientGlow(data.trend_resonance.summary) : ''">
    <!-- Header / Title -->
    <div class="flex justify-between items-center px-1 relative z-20">
      <div class="flex items-center gap-2">
        <div class="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></div>
        <h3 class="text-base font-bold text-slate-200 font-display tracking-wide uppercase">主力战情室</h3>
        <span class="text-sm text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-black animate-pulse" v-if="isConnected">实时模式</span>
        <span class="text-sm text-slate-500 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/50" v-else>作战中心</span>
      </div>
      
      <!-- AI Verdict Banner -->
      <div v-if="data?.verdict" class="flex-1 mx-4 max-w-xl">
        <div class="bg-slate-950/60 border border-slate-800 rounded px-3 py-1.5 shadow-lg flex items-center gap-3 group hover:border-blue-500/50 transition-all overflow-hidden">
          <span class="text-blue-400 font-black text-xs bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20 whitespace-nowrap">AI 指南</span>
          <div class="text-sm text-slate-300 font-bold tracking-tight marquee-container flex-1 overflow-hidden">
             <span class="marquee-text">{{ data?.verdict || '正在同步极速情报中心数据...' }}</span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- Interactive Symbol Dropdown -->
        <el-dropdown trigger="click" @command="(s: string) => emit('change-symbol', s)">
          <div class="flex items-center gap-1.5 px-3 py-1 bg-slate-800/80 rounded-md border border-slate-700/50 hover:border-blue-500/50 transition-all cursor-pointer group/sym shadow-sm active:scale-95">
            <span class="text-sm font-tabular text-slate-200 group-hover:text-blue-400 font-black tracking-tight">{{ symbol }}</span>
            <el-icon class="text-slate-500 group-hover:text-blue-500 transition-transform group-hover:rotate-180"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="!bg-slate-900 !border-slate-800">
              <el-dropdown-item command="BTCUSDT" class="!text-slate-300 hover:!bg-blue-600/20">BTCUSDT (比特币)</el-dropdown-item>
              <el-dropdown-item command="ETHUSDT" class="!text-slate-300 hover:!bg-blue-600/20">ETHUSDT (以太坊)</el-dropdown-item>
              <el-dropdown-item command="SOLUSDT" class="!text-slate-300 hover:!bg-blue-600/20">SOLUSDT (索拉纳)</el-dropdown-item>
              <el-dropdown-item command="BNBUSDT" class="!text-slate-300 hover:!bg-blue-600/20">BNBUSDT (币安币)</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        
        <!-- Status Indicator -->
        <div class="flex items-center gap-1.5 min-w-[20px]">
           <div v-for="i in 3" :key="i" class="w-1 h-1 rounded-full bg-blue-500 animate-pulse" :style="{animationDelay: (i * 200) + 'ms'}" v-if="loading"></div>
        </div>
        
        <button 
          @click="handleManualRefresh" 
          class="p-1.5 hover:bg-slate-700/50 rounded-md transition-all text-slate-400 hover:text-blue-400 active:scale-95 shadow-sm"
          :class="{'animate-spin text-blue-500': loading}"
          title="强制刷新并重连"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="16 21h5v-5"/></svg>
        </button>  
      </div>
    </div>

    <!-- Main Grid -->
    <div class="grid grid-cols-2 gap-3 flex-1 min-h-[220px]" v-if="data">
      
      <!-- Module 1: Trend Resonance -->
      <div class="bg-slate-900/60 border border-slate-700/50 rounded-lg p-3 flex flex-col relative overflow-hidden group/mod">
        <div class="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-50"></div>
        <div class="text-base text-slate-400 font-black uppercase mb-3 flex justify-between relative z-10 tracking-tight">
          <span>趋势共振</span>
          <span :class="getResonanceColor(data.trend_resonance.summary)" class="bg-black/40 px-2 py-0.5 rounded shadow-sm text-sm border border-white/5">{{ data.trend_resonance.summary }}</span>
        </div>
        
        <div class="flex-1 flex items-center justify-around gap-4 relative z-10 px-2">
          <div v-for="item in data.trend_resonance.details" :key="item.timeframe" class="flex flex-col items-center gap-3 flex-1 p-2 rounded-xl group/resonance transition-all hover:bg-white/5">
             <!-- Larger Trend Bar with Neon Glow -->
             <div 
                class="w-12 h-20 rounded-md relative overflow-hidden bg-slate-800 border-2 transition-all duration-700 group-hover/resonance:scale-110 shadow-[0_0_15px_rgba(0,0,0,0.4)]"
                :class="getTrendBorder(item.status)"
             >
               <!-- Trend Fill Bar -->
               <div 
                  class="absolute bottom-0 left-0 w-full transition-all duration-1000 opacity-100"
                  :class="[getTrendBg(item.status), item.status === 'bullish' ? 'shadow-[0_-5px_15px_rgba(16,185,129,0.5)]' : (item.status === 'bearish' ? 'shadow-[0_-5px_15px_rgba(244,63,94,0.5)]' : '')]"
                  :style="{height: item.status !== 'loading' ? '100%' : '30%' } "
               ></div>
               <!-- Interactive Glass Reflection -->
               <div class="absolute inset-0 bg-gradient-to-tr from-white/20 via-transparent to-black/20 opacity-30"></div>
             </div>
             
             <!-- Numerical & Metadata Section -->
             <div class="flex flex-col items-center gap-1">
               <span class="text-xs font-black text-slate-500 uppercase tracking-[0.2em]">{{ item.timeframe }}</span>
               <div class="flex flex-col items-center">
                 <span class="text-2xl font-tabular text-white font-black drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] tracking-tight">
                   {{ Number.isFinite(item.rsi) ? Math.round(item.rsi) : '--' }}
                 </span>
                 <span class="text-[10px] text-slate-400 font-bold uppercase tracking-widest -mt-1">RSI</span>
               </div>
             </div>
          </div>
        </div>
      </div>

      <!-- Module 2: Key Levels -->
      <div 
        class="bg-slate-900/60 border rounded-lg p-3 flex flex-col relative overflow-hidden transition-all duration-500"
        :class="[
          data.key_levels.in_sniper_zone ? 'border-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)] sniper-alarm' : 'border-slate-700/50'
        ]"
      >
        <div class="absolute inset-0 bg-gradient-to-br from-rose-500/5 to-transparent opacity-50"></div>
        <div class="text-base text-slate-400 font-black uppercase mb-3 flex justify-between relative z-10 tracking-tight">
          <span class="flex items-center gap-1.5">
             <span class="w-1.5 h-1.5 bg-rose-500 rounded-full" v-if="data.key_levels.in_sniper_zone"></span>
             狙击距离
          </span>
          <span v-if="data.key_levels.in_sniper_zone" class="text-amber-400 animate-pulse pointer-events-none text-sm font-black italic">🎯 狙击触发区</span>
        </div>
        
        <div class="flex-1 flex flex-col justify-center gap-4 relative z-10 px-1">
           <div class="flex justify-between items-end">
              <span class="text-rose-400 font-black text-base tracking-tight origin-left">{{ data.key_levels.nearest_resistance.label }}</span>
              <span class="text-rose-400 font-tabular text-lg font-black">{{ formatPrice(data.key_levels.nearest_resistance.price) }}</span>
           </div>
           
           <div class="h-3 bg-slate-950/80 rounded-sm relative shadow-inner border border-slate-800/50">
              <div 
                class="absolute top-0 bottom-0 w-2.5 bg-blue-500 rounded-sm shadow-[0_0_12px_rgba(59,130,246,1)] z-10 border border-white/20 transition-all duration-1000"
                :style="{left: getPricePositionPct(data.key_levels) + '%'}"
              ></div>
              <div class="absolute inset-0 flex justify-between px-1 opacity-20 pointer-events-none">
                <div class="w-px h-full bg-slate-600"></div>
                <div class="w-px h-full bg-slate-600"></div>
                <div class="w-px h-full bg-slate-600"></div>
              </div>
           </div>
           
           <div class="flex justify-between items-start">
              <span class="text-emerald-400 font-black text-base tracking-tight origin-left">{{ data.key_levels.nearest_support.label }}</span>
              <span class="text-emerald-400 font-tabular text-lg font-black">{{ formatPrice(data.key_levels.nearest_support.price) }}</span>
           </div>
           
           <div class="text-center text-sm text-slate-300 font-tabular font-black mt-1 bg-slate-950/40 py-1.5 rounded border border-slate-800/30">
             距阻力 <span class="text-rose-400">{{ data.key_levels.nearest_resistance.distance_pct }}%</span> | 
             距支撑 <span class="text-emerald-400">{{ data.key_levels.nearest_support.distance_pct }}%</span>
           </div>
        </div>
        <div v-if="data.key_levels.in_sniper_zone" class="absolute inset-0 bg-amber-500/10 animate-pulse z-0 pointer-events-none"></div>
      </div>

      <!-- Module 3: Smart Money -->
      <div class="bg-slate-900/60 border border-slate-700/50 rounded-lg p-3 flex flex-col relative overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-50"></div>
        <div class="text-base text-slate-400 font-black uppercase mb-3 relative z-10 tracking-tight">资金异动</div>
        
        <div class="flex-1 flex flex-col items-center justify-center gap-3 relative z-10">
           <div 
             class="w-full text-center py-1.5 rounded bg-slate-800/80 border border-slate-600 shadow-lg text-sm font-black font-display tracking-widest uppercase transition-all hover:border-emerald-500/50"
             :class="getSMSignalClass(data.smart_money.signal)"
           >
             {{ getSMSignalLabel(data.smart_money.signal) }}
           </div>
           
           <div class="w-full grid grid-cols-2 gap-3 mt-1">
             <div class="bg-slate-950/70 rounded-lg p-3 border border-slate-800 text-center shadow-inner group/val hover:border-slate-600 transition-colors relative h-20 overflow-hidden">
                <div class="text-xs text-slate-500 font-black mb-1.5 uppercase tracking-tighter relative z-10">大单净流 (24H)</div>
                <div class="text-2xl font-tabular font-black tracking-tight relative z-10" :class="data.smart_money.net_whale_vol > 0 ? 'text-emerald-400' : 'text-rose-400'">
                   {{ data.smart_money.net_whale_vol > 0 ? '+' : '' }}${{ formatCompact(data.smart_money.net_whale_vol) }}
                </div>
                <!-- Sparkline -->
                <div class="absolute bottom-0 left-0 w-full h-8 opacity-40 z-0">
                   <svg viewBox="0 0 100 30" class="w-full h-full fill-none">
                      <path :d="createSparkline(whaleVolHistory)" :class="data.smart_money.net_whale_vol > 0 ? 'stroke-emerald-500' : 'stroke-rose-500'" stroke-width="2" stroke-linecap="round" />
                   </svg>
                </div>
             </div>
             <div class="bg-slate-950/70 rounded-lg p-3 border border-slate-800 text-center shadow-inner group/val hover:border-slate-600 transition-colors h-20">
                <div class="text-xs text-slate-500 font-black mb-1.5 uppercase tracking-tighter">主力参与度</div>
                <div class="text-2xl font-tabular font-black text-slate-100 italic">
                   {{ Math.round(data.smart_money.whale_ratio * 100) }}%
                </div>
             </div>
           </div>

           <div class="w-full flex justify-between items-center text-xs text-slate-300 mt-1 px-3 py-2 bg-slate-950/30 rounded border border-slate-800/50">
              <div class="flex items-center gap-2">
                 <span class="opacity-60 font-black">资金费率</span>
                 <span class="font-black font-tabular" :class="data.smart_money.funding_rate > 0.0001 ? 'text-amber-400 animate-pulse' : 'text-slate-300'">
                    {{ (data.smart_money.funding_rate * 100).toFixed(4) }}%
                 </span>
              </div>
              <div class="flex items-center gap-2">
                 <span class="opacity-60 font-black">多空人数比</span>
                 <span class="font-black font-tabular text-sm" :class="data.smart_money.long_short_ratio > 1 ? 'text-emerald-400' : 'text-rose-400'">
                    <template v-if="data.smart_money.long_short_ratio > 0">
                      {{ data.smart_money.long_short_ratio >= 1 
                         ? `多 ${data.smart_money.long_short_ratio.toFixed(1)} : 1` 
                         : `1 : 空 ${(1 / data.smart_money.long_short_ratio).toFixed(1)}` 
                      }}
                    </template>
                    <template v-else>-</template>
                 </span>
              </div>
           </div>
        </div>
      </div>

      <!-- Module 4: Volatility -->
      <div class="bg-slate-900/60 border border-slate-700/50 rounded-lg p-3 flex flex-col relative overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-transparent opacity-50"></div>
        <div class="text-base text-slate-400 font-black uppercase mb-3 relative z-10 tracking-tight">变盘预警</div>
        
        <div class="flex-1 flex flex-col items-center justify-center relative z-10">
           <div class="text-3xl mb-2 filter drop-shadow-[0_0_10px_rgba(251,191,36,0.3)]">
              {{ data.volatility.status === 'storm_alert' ? '⛈️' : '🌤️' }}
           </div>
           
           <div class="text-sm font-black uppercase tracking-widest" :class="data.volatility.status === 'storm_alert' ? 'text-amber-400' : 'text-slate-400'">
             {{ data.volatility.status === 'storm_alert' ? '变盘在即 (风暴)' : '行情稳定 (平静)' }}
           </div>
           
           <div class="w-full bg-slate-950 h-3 rounded-full mt-5 overflow-hidden border border-slate-800/50 shadow-inner relative">
              <div 
                class="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-rose-600 transition-all duration-1000 shadow-[0_0_10px_rgba(225,29,72,0.4)]"
                :style="{width: data.volatility.score + '%'}"
              ></div>
              <div class="absolute inset-0 opacity-20 pointer-events-none">
                 <svg viewBox="0 0 200 12" class="w-full h-full fill-none">
                    <path :d="createSparkline(volScoreHistory, 200, 12)" stroke="white" stroke-width="0.5" />
                 </svg>
              </div>
           </div>
           <div class="flex justify-between w-full text-sm text-slate-400 mt-2 font-black font-tabular">
              <span class="flex items-center gap-1">
                <span class="text-xs opacity-60">布林带宽:</span>
                <span class="text-slate-300">{{ (data.volatility.bb_width * 100).toFixed(1) }}%</span>
              </span>
              <span class="flex items-center gap-1">
                <span class="text-xs opacity-60">综合得分:</span>
                <span class="text-slate-200">{{ Math.round(data.volatility.score) }}</span>
              </span>
           </div>
        </div>
      </div>

    </div>
    
    <!-- Loading State -->
    <div v-else class="flex-1 min-h-[220px] flex items-center justify-center flex-col gap-3 text-slate-500">
        <div class="animate-spin text-2xl opacity-50">
           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
        </div>
        <span class="text-xs font-sans">正在连接战情室实时链路...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { analysisApi } from '@/services/api'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps<{
  symbol: string
}>()

const loading = ref(false)
const data = ref<any>(null)

// Websocket State
const isConnected = ref(false)
let ws: WebSocket | null = null

const emit = defineEmits<{
  (e: 'change-symbol', symbol: string): void
}>()

// History tracking for Sparklines
const whaleVolHistory = ref<number[]>([])
const volScoreHistory = ref<number[]>([])

const connectWS = () => {
    if (ws) ws.close()
    
    // Determine WS URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/war-room/${props.symbol}`
    
    console.log(`[WS] Connecting to ${wsUrl}`)
    ws = new WebSocket(wsUrl)
    loading.value = true
    
    ws.onopen = () => {
        isConnected.value = true
        loading.value = false
        console.log('[WS] Connected successfully')
    }
    
    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data)
            if (message.type === 'war_room_update') {
                data.value = message.data
                
                // Update Sparkline History
                if (data.value && data.value.smart_money) {
                    whaleVolHistory.value.push(data.value.smart_money.net_whale_vol)
                    if (whaleVolHistory.value.length > 30) whaleVolHistory.value.shift()
                }
                if (data.value && data.value.volatility) {
                    volScoreHistory.value.push(data.value.volatility.score)
                    if (volScoreHistory.value.length > 50) volScoreHistory.value.shift()
                }
            }
        } catch (e) {
            console.error('[WS] Failed to parse message', e)
        }
    }
    
    ws.onclose = () => {
        isConnected.value = false
        loading.value = false
        console.log('[WS] Disconnected')
    }

    ws.onerror = (err) => {
        console.error('[WS] Error', err)
        loading.value = false
    }
}

const handleManualRefresh = async () => {
    console.log('[WarRoom] Manual refresh triggered')
    loading.value = true
    await prefetchData()
    connectWS()
}

// Sparkline Creator
const createSparkline = (points: number[], width = 100, height = 30) => {
    if (points.length < 2) return ''
    const min = Math.min(...points)
    const max = Math.max(...points)
    const range = max - min || 1
    
    const xStep = width / (points.length - 1)
    return points.map((p, i) => {
        const x = i * xStep
        const y = height - ((p - min) / range * height)
        return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    }).join(' ')
}

// Helpers
const getResonanceColor = (summary: string | undefined) => {
    if (summary && summary.includes('多头')) return 'text-emerald-400'
    if (summary && summary.includes('空头')) return 'text-rose-400'
    return 'text-slate-400'
}

const getAmbientGlow = (summary: string | undefined) => {
    if (!summary) return ''
    if (summary.includes('多头')) return 'shadow-[inset_0_0_100px_rgba(16,185,129,0.08)]'
    if (summary.includes('空头')) return 'shadow-[inset_0_0_100px_rgba(244,63,94,0.08)]'
    return ''
}

const getTrendBg = (status: string) => {
    if (status === 'bullish') return 'bg-emerald-500'
    if (status === 'bearish') return 'bg-rose-500'
    return 'bg-slate-600'
}

const getTrendBorder = (status: string) => {
    if (status === 'bullish') return 'border-emerald-500/30'
    if (status === 'bearish') return 'border-rose-500/30'
    return 'border-slate-600/30'
}

const formatPrice = (p: number) => {
    if (!p) return '-'
    return p < 10 ? p.toFixed(4) : p.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})
}

const formatCompact = (num: number) => {
    if (!num && num !== 0) return '-'
    return Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: 1 }).format(num)
}

const getPricePositionPct = (levels: any) => {
    if (!levels || !levels.nearest_resistance) return 50
    const range = levels.nearest_resistance.price - levels.nearest_support.price
    const current = levels.current_price - levels.nearest_support.price
    if (range <= 0) return 50
    const pct = (current / range) * 100
    return Math.max(5, Math.min(95, pct)) // Clamp 5-95%
}

const getSMSignalLabel = (sig: string) => {
    const map: Record<string, string> = {
        'bullish_accumulation': '🟢 机构吸筹',
        'bullish_confirmed': '🚀 量价齐升',
        'bearish_divergence': '⚠️ 诱多预警',
        'bearish_confirmed': '📉 量价齐跌',
        'neutral': '⚪ 资金中性'
    }
    return map[sig] || sig
}

const getSMSignalClass = (sig: string) => {
    if (!sig) return 'text-slate-400 bg-slate-800'
    if (sig.includes('bullish')) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    if (sig.includes('bearish')) return 'text-rose-400 bg-rose-500/10 border-rose-500/20'
    return 'text-slate-400 bg-slate-800'
}

const prefetchData = async () => {
    if (!props.symbol) return
    try {
        console.log('[WarRoom] Pre-fetching initial data...')
        const response = await analysisApi.getWarRoomDashboard(props.symbol)
        if (response) data.value = response
    } catch (e) {
        console.warn('[WarRoom] Pre-fetch failed, waiting for WS...', e)
    }
}

// Hooks
onMounted(async () => {
    await prefetchData()
    connectWS()
})

onUnmounted(() => {
    if (ws) ws.close()
})

watch(() => props.symbol, async () => {
    console.log(`[WarRoom] Symbol changed to ${props.symbol}, refreshing...`)
    whaleVolHistory.value = []
    volScoreHistory.value = []
    await prefetchData()
    connectWS()
})
</script>

<style scoped>
.sniper-alarm {
  animation: sniper-border-pulse 2s infinite;
}

@keyframes sniper-border-pulse {
  0% { border-color: rgba(245, 158, 11, 0.5); background-color: rgba(245, 158, 11, 0.05); }
  50% { border-color: rgba(244, 63, 94, 0.8); background-color: rgba(244, 63, 94, 0.1); }
  100% { border-color: rgba(245, 158, 11, 0.5); background-color: rgba(245, 158, 11, 0.05); }
}

.marquee-container {
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
}

.marquee-text {
  display: inline-block;
  white-space: nowrap;
  animation: marquee 30s linear infinite;
  padding-left: 20px;
}

@keyframes marquee {
  0% { transform: translateX(0); }
  100% { transform: translateX(-100%); }
}

.war-room-dashboard {
  transition: all 1s ease;
}
</style>
