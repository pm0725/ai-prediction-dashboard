<!--
  智链预测 - 核心预测聚焦组件 (Spotlight)
  ==========================================
  Auto-carousel showcasing high-confidence AI predictions and Real-time Market Alerts.
  Features:
  - Hero Card: Large animated direction, confidence ring, key levels.
  - Side List: Vertical thumbnails of other hot predictions + Prominent Alerts.
  - Interaction: Auto-play (30s), Pause on hover, Click to select.
  - Alerts: Audio feedback, visual pulse for High severity, Volume Spike handling.
-->
<template>
  <div class="spotlight-container h-auto w-full flex flex-col lg:flex-row bg-slate-900 border-b border-slate-700/50 relative overflow-hidden"
       @mouseenter="pauseCarousel" @mouseleave="resumeCarousel">
    
     <!-- 1. Main Hero (70% - but flex-grow) -->
    <div class="hero-card flex-1 min-w-0 lg:min-w-[500px] p-4 flex flex-col relative overflow-hidden">
       <!-- Background Gradient (Dynamic based on direction/alert) -->
       <div class="absolute inset-0 opacity-10 pointer-events-none transition-colors duration-700"
            :class="heroGradientClass"></div>
            
       <!-- Header -->
       <div class="flex justify-between items-start z-10 mb-4">
          <div class="flex items-center gap-3">
             <div class="text-4xl font-extrabold text-white tracking-tight font-display">{{ currentItem.symbol }}</div>
              <div class="px-2.5 py-1 rounded-md text-sm font-sans font-semibold bg-slate-800/80 text-slate-400 border border-slate-700/50 backdrop-blur-sm">
                 {{ currentItem.timeframe }}
              </div>
              <div v-if="currentItem.currentPrice" class="flex items-center gap-2 px-2.5 py-1 bg-amber-500/10 border border-amber-500/20 rounded-md text-xs font-tabular font-bold text-amber-500 relative">
                 <span class="absolute -right-0.5 -top-0.5 flex h-2 w-2">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                 </span>
                 <span class="opacity-50 tracking-tighter font-display uppercase">BASE</span>
                 <span class="tracking-wide">{{ currentItem.currentPrice }}</span>
                 <span class="w-px h-3 bg-amber-500/20 mx-1"></span>
                 <span class="text-[10px] opacity-80 font-sans tracking-tight">Binance Futures</span>
              </div>
           </div>
           <div class="flex flex-col items-end">
              <div class="text-xs text-slate-500 font-sans font-medium mb-1 uppercase tracking-wide">有效期至</div>
              <div class="font-tabular text-2xl font-bold tracking-widest" :class="timeColorClass">
                {{ countdownDisplay }}
             </div>
          </div>
       </div>

       <!-- Center Visuals -->
       <div class="flex-1 flex flex-col lg:flex-row items-center justify-center z-10 gap-10 lg:gap-20">
          
          <!-- Direction Arrow & Confidence -->
          <div class="relative w-32 h-32 flex-shrink-0 flex items-center justify-center">
             <!-- Spinner Ring -->
             <svg class="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" class="stroke-slate-800" stroke-width="6" />
                <circle cx="50" cy="50" r="45" fill="none" 
                        :stroke="confidenceColor" 
                        stroke-width="6" 
                        :stroke-dasharray="confidenceDashArray"
                        stroke-dashoffset="0"
                        stroke-linecap="round"
                        class="transition-all duration-1000 ease-out" />
             </svg>
             
             <!-- Inner Content -->
             <div class="absolute inset-0 flex flex-col items-center justify-center">
                <el-icon :class="['text-5xl mb-2 filter drop-shadow-xl transition-transform duration-500', directionIconClass]"
                         :style="{ transform: directionTransform }">
                   <!-- Alert Type Icons -->
                   <Warning v-if="currentItem.isAlert && currentItem.type === 'volume_spike'" />
                   <Top v-else-if="currentItem.direction === 'Bullish'" />
                   <Bottom v-else-if="currentItem.direction === 'Bearish'" />
                   <ArrowRight v-else />
                 </el-icon>
                 <div class="text-4xl font-tabular font-bold text-white leading-none tracking-tighter">{{ currentItem.confidence }}%</div>
                 <div class="text-[10px] text-slate-500 mt-1 uppercase tracking-widest font-sans font-semibold">
                    {{ currentItem.isAlert ? '波动幅度' : 'AI 置信度' }}
                 </div>
              </div>
          </div>

          <!-- Key Stats & Levels -->
          <div class="flex-1 space-y-6">
             <!-- AI Analysis Summary / Alert Message -->
             <div class="w-full bg-slate-800/40 rounded-xl p-4 border border-slate-700/50 backdrop-blur-sm shadow-lg">
                <div class="flex items-center gap-2 mb-3">
                   <el-icon :class="currentItem.isAlert ? 'text-orange-400' : 'text-indigo-400'">
                       <Warning v-if="currentItem.isAlert" />
                       <DataAnalysis v-else />
                   </el-icon>
                   <span class="text-xs font-bold text-slate-400 uppercase tracking-wider font-sans">
                       {{ currentItem.isAlert ? '市场预警 (Market Alert)' : '价格行为分析 (Price Action)' }}
                   </span>
                </div>
                <p class="text-sm text-slate-300 leading-relaxed font-sans text-center">
                   {{ currentItem.reason }}
                </p>
             </div>

              <!-- Key Levels (Progress Bars) -->
              <div class="space-y-2 w-full mt-2">
                 <!-- Resistance -->
                 <div class="level-item group">
                    <div class="flex justify-between items-end mb-2 pl-1">
                       <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider font-sans group-hover:text-rose-400 transition-colors">阻力位 (Res)</span>
                       <span class="font-tabular text-lg font-bold text-rose-400">{{ currentItem.resistance }}</span>
                    </div>
                    <div class="h-2.5 flex-1 bg-slate-800 rounded-full overflow-hidden ring-1 ring-white/5">
                       <div class="h-full bg-gradient-to-r from-rose-900/50 to-rose-500 w-[90%] ml-auto rounded-full shadow-[0_0_10px_rgba(244,63,94,0.3)]"></div>
                    </div>
                </div>

                <!-- Entry Zone -->
                <div class="level-item group">
                    <div class="flex justify-between items-end mb-2 pl-1">
                       <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider font-sans group-hover:text-blue-400 transition-colors">入场区间 (Entry)</span>
                       <span class="font-tabular text-lg font-bold text-blue-400">{{ currentItem.entry }}</span>
                    </div>
                    <div class="h-2.5 flex-1 bg-slate-800 rounded-full overflow-hidden ring-1 ring-white/5 relative">
                       <!-- Range Indicator -->
                       <div class="absolute left-[30%] w-[40%] h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full shadow-[0_0_10px_rgba(59,130,246,0.3)] opacity-80 group-hover:opacity-100 transition-opacity"></div>
                    </div>
                </div>

                 <!-- Support -->
                 <div class="level-item group">
                    <div class="flex justify-between items-end mb-2 pl-1">
                       <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider font-sans group-hover:text-emerald-400 transition-colors">支撑位 (Sup)</span>
                       <span class="font-tabular text-lg font-bold text-emerald-400">{{ currentItem.support }}</span>
                    </div>
                    <div class="h-2.5 flex-1 bg-slate-800 rounded-full overflow-hidden ring-1 ring-white/5">
                       <div class="h-full bg-gradient-to-r from-emerald-500 to-emerald-900/50 w-[90%] mr-auto rounded-full shadow-[0_0_10px_rgba(16,185,129,0.3)]"></div>
                    </div>
                </div>
             </div>
          </div>

       </div>

       <!-- Footer Actions -->
        <div class="mt-auto flex justify-between items-center z-10 pt-4 border-t border-slate-800/50">
           <div class="flex items-center gap-2 text-xs font-medium text-slate-500 font-sans">
              <el-icon><Cpu /></el-icon> AI 模型 v3.2 · 响应 {{ currentItem.processTime }}ms
           </div>
           <button 
              class="text-xs font-bold text-blue-400 hover:text-white transition-colors flex items-center gap-1 group font-sans"
              @click="handleDeepAnalysis(currentItem.symbol)"
           >
              查看深度分析 <el-icon class="group-hover:translate-x-1 transition-transform"><ArrowRight /></el-icon>
           </button>
        </div>
    </div>

      <!-- 2. Side List (Fixed 240px width to prevent squeezing) -->
     <div class="side-list w-full lg:w-[260px] h-[200px] lg:h-auto flex-shrink-0 border-t lg:border-t-0 lg:border-l border-slate-700/50 bg-slate-900/80 flex flex-col backdrop-blur-md">
        <div class="p-4 border-b border-slate-800/50 text-xs font-extrabold text-slate-500 uppercase tracking-widest flex justify-between items-center font-sans">
           <span class="flex items-center gap-2 text-orange-500">
              <el-icon class="animate-pulse"><Warning /></el-icon>
              暴涨暴跌预警
           </span>
           <span class="text-[10px] bg-orange-900/30 px-2 py-0.5 rounded text-orange-400 font-mono">{{ listItems.length }}</span>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scroll">
           <div v-for="(item, index) in listItems" :key="item.id"
                class="p-4 border-b border-slate-800/30 cursor-pointer transition-colors group relative"
                :class="[
                   activeIndex === index ? 'bg-slate-800/30' : 'hover:bg-slate-800/50',
                   getDirectionClass(translationMap[item.direction] || item.direction, item).includes('text-emerald') ? 'hover:bg-emerald-900/10' : 'hover:bg-rose-900/10',
                   item.severity === 'high' ? 'bg-red-900/10' : ''
                ]"
                @click="setActive(index)">
              
              <!-- Active Indicator -->
              <div v-if="activeIndex === index" 
                   class="absolute left-0 top-0 bottom-0 w-0.5 bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>

              <!-- High Severity Flashing Border -->
              <div v-if="item.severity === 'high'" 
                   class="absolute inset-0 border border-red-500/30 animate-pulse pointer-events-none"></div>

              <div class="flex justify-between items-start mb-1.5">
                 <span class="font-bold text-base text-slate-300 group-hover:text-white transition-colors font-sans">{{ item.symbol }}</span>
                 <span class="text-[10px] font-medium font-sans px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">{{ item.timeframe }}</span>
              </div>
              
              <div class="flex items-center justify-between">
                 <!-- Direction Warning -->
                 <span :class="getDirectionClass(translationMap[item.direction] || item.direction, item)" class="text-xs font-bold flex items-center gap-1 font-sans">
                    <!-- Alert Icon -->
                    <el-icon v-if="item.isAlert" class="animate-ping absolute opacity-75 mr-4"><Warning /></el-icon>
                    <el-icon v-if="item.isAlert" class="mr-1"><Warning /></el-icon>
                    
                    <el-icon v-else-if="getDirectionClass(translationMap[item.direction] || item.direction, item).includes('text-emerald')"><Top /></el-icon>
                    <el-icon v-else><Bottom /></el-icon>
                    
                    <span v-if="item.isAlert">
                       <template v-if="item.type === 'volume_spike'">交易量激增</template>
                       <template v-else>{{ item.direction === 'Bullish' ? '极速拉升' : '极速下跌' }}</template>
                    </span>
                    <span v-else>
                       {{ (translationMap[item.direction] || item.direction).replace('看涨', '潜力看涨').replace('看跌', '风险看跌') }}
                    </span>
                 </span>
                 
                 <!-- Confidence / Volatility -->
                  <div class="flex items-center gap-1.5">
                     <template v-if="item.isAlert">
                        <span class="text-xs font-tabular font-bold" :class="item.direction === 'Bullish' ? 'text-emerald-500' : (item.type === 'volume_spike' ? 'text-indigo-400' : 'text-rose-500')">
                           {{ item.type === 'volume_spike' ? 'VOL' : (item.change * 100).toFixed(2) + '%' }}
                        </span>
                     </template>
                     <template v-else>
                        <el-icon class="text-xs animate-pulse" :style="{ color: getConfidenceColor(item.confidence) }">
                           <Bell />
                        </el-icon>
                        <span class="text-xs font-tabular font-bold" :style="{ color: getConfidenceColor(item.confidence) }">{{ item.confidence }}%</span>
                     </template>
                  </div>
              </div>

              <!-- Progress Bar (Timer) for Active Item -->
              <div v-if="activeIndex === index" class="absolute bottom-0 left-0 h-0.5 bg-blue-500/50 w-full">
                 <div class="h-full bg-blue-400 transition-all duration-[30000ms] ease-linear w-full"
                      :style="{ width: progressWidth + '%' }"></div>
              </div>
           </div>
        </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, defineEmits } from 'vue'
import { Top, Bottom, ArrowRight, Cpu, Warning, Bell, DataAnalysis } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { usePredictionStore } from '@/stores/usePredictionStore'

const marketStore = usePredictionStore()
const emit = defineEmits(['analyze'])

// ================= Audio =================
const audioContext = ref<AudioContext | null>(null)

// Simple "Ping" sound generator using Web Audio API (No external file needed)
function playAlertSound(severity: string = 'low') {
    if (!audioContext.value) {
        audioContext.value = new (window.AudioContext || (window as any).webkitAudioContext)()
    }
    const ctx = audioContext.value
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    
    osc.connect(gain)
    gain.connect(ctx.destination)
    
    if (severity === 'high') {
        osc.frequency.value = 880 // High pitch for High Severity
        osc.type = 'sawtooth'
    } else {
        osc.frequency.value = 440 // Normal pitch
        osc.type = 'sine'
    }
    
    gain.gain.setValueAtTime(0.1, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + 0.5)
    
    osc.start()
    osc.stop(ctx.currentTime + 0.5)
}

// ================= State =================
const activeIndex = ref(0)
const progressWidth = ref(100)
let timer: any = null
const CYCLE_TIME = 30000 // 30s
let countdownTimer: any
const countdownDisplay = ref('00:00:00')
const lastAlertTimestamp = ref(0) // Track last alert to trigger sound

// ================= Computed =================

const predictions = computed(() => {
    // 1. Get Batch Results
    const results = marketStore.batchResults
    let items = Object.values(results)

    // 2. Prepend Current Prediction if exists
    if (marketStore.prediction) {
        // Avoid duplicate if it's already in batch
        if (!results[marketStore.prediction.symbol]) {
             items.unshift(marketStore.prediction)
        } else {
            // Move to front if exists
            items = items.filter(i => i.symbol !== marketStore.prediction!.symbol)
            items.unshift(marketStore.prediction)
        }
    }
    
    // 3. [NEW] Prepend Market Alerts (Real-time Pump/Dump)
    const alerts = marketStore.marketAlerts || []

    // Check for new alerts to play sound (Side effect in computed is discouraged but effective here for real-time trigger without watchers on deep arrays)
    // actually watcher is better. Added watcher below.
    
    // Filter for specific coins as requested (BTC, ETH, SOL, XRP, DOGE)
    const ALLOWED_COINS = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE']
    const isAllowed = (symbol: string) => ALLOWED_COINS.some(coin => symbol.includes(coin))

    const alertItems = alerts
        .filter(alert => isAllowed(alert.symbol))
        .map(alert => ({
        id: `alert-${alert.symbol}-${alert.timestamp}`,
        symbol: alert.symbol,
        timeframe: alert.timeframe,
        direction: alert.type === 'pump' ? 'Bullish' : (alert.type === 'dump' ? 'Bearish' : 'Neutral'),
        confidence: 100, // Alerts are facts
        reason: alert.message,
        isAlert: true, // Marker for styling
        change: alert.change_percent,
        type: alert.type, // 'pump' | 'dump' | 'volume_spike'
        severity: alert.severity || 'low', // 'low' | 'medium' | 'high'
        resistance: '--', support: '--', entry: '--', currentPrice: 0,
        processTime: 0, validUntil: dayjs().add(5, 'minute')
    }))

    // Merge: Alerts -> Current Prediction -> Batch Results
    const alertSymbols = new Set(alertItems.map(a => a.symbol))
    items = items.filter(i => !alertSymbols.has(i.symbol || i.id))
    
    // Combine raw items (we need to unify shape later in map)
    const mappedRegularItems = items.map((item: any) => {
        // Format Entry
        let entryText = '--'
        if (item.entry_zone) {
            entryText = `${item.entry_zone.low} - ${item.entry_zone.high}`
        }

        // Format Levels
        const resistance = item.key_levels?.strong_resistance || (item.take_profit && item.take_profit[0]) || '--'
        const support = item.key_levels?.strong_support || item.stop_loss || '--'

        return {
            id: item.symbol,
            symbol: item.symbol,
            timeframe: item.timeframe || '4H', 
            direction: (item.prediction_cn || item.prediction || 'Neutral').split(' ')[0], // Handle "看涨 (Bullish)" format
            confidence: item.confidence || 0,
            reason: Array.isArray(item.reasoning) ? item.reasoning[0] : (item.summary || 'AI 分析中'),
            resistance: resistance, 
            support: support, 
            entry: entryText,
            currentPrice: item.key_levels?.current_price || item.current_price,
            processTime: Math.floor(Math.random() * 200) + 100, // Simulated
            validUntil: dayjs().add(30, 'minute'),
            isAlert: false,
            type: 'prediction',
            severity: 'low',
            change: 0 // Regular predictions don't have sudden change % like alerts
        }
    })

    const finalItems = [...alertItems, ...mappedRegularItems]
    
    if (finalItems.length === 0) {
        // Return a default placeholder if nothing loaded yet
        return [{
            id: 'loading', symbol: '扫描中...', timeframe: '--', 
            direction: 'Neutral', confidence: 0, reason: '请稍候...',
            resistance: '--', support: '--', entry: '--', currentPrice: 0,
            processTime: 0, validUntil: dayjs().add(1, 'hour'),
            isAlert: false,
            type: 'prediction',
            severity: 'low',
            change: 0
        }]
    }

    return finalItems
})

const currentItem = computed(() => predictions.value[activeIndex.value])
const listItems = computed(() => predictions.value)

const translationMap: Record<string, string> = {
    'Bullish': '看涨',
    'Bearish': '看跌',
    'Neutral': '中性',
    '看涨': '看涨',
    '看跌': '看跌',
    '中性': '中性'
}

// Visual Classes
const heroGradientClass = computed(() => {
    if (!currentItem.value) return 'bg-gradient-to-br from-slate-500 to-transparent'
    
    // Handle Alerts Special Gradients
    if (currentItem.value.isAlert) {
         if (currentItem.value.type === 'volume_spike') return 'bg-gradient-to-br from-indigo-500 to-purple-900'
         if (currentItem.value.severity === 'high') return 'bg-gradient-to-br from-red-600 to-orange-900 animate-pulse'
    }

    const d = currentItem.value.direction
    if (d === 'Bullish' || d === '看涨') return 'bg-gradient-to-br from-emerald-500 to-transparent'
    if (d === 'Bearish' || d === '看跌') return 'bg-gradient-to-br from-rose-500 to-transparent'
    return 'bg-gradient-to-br from-slate-500 to-transparent'
})

 const directionIconClass = computed(() => {
    if (!currentItem.value) return 'text-slate-400'
    const d = currentItem.value.direction
    
    if (currentItem.value.isAlert) {
        if (currentItem.value.type === 'volume_spike') return 'text-indigo-400'
        return 'text-orange-500' // Default alert color
    }
    
    if (d === 'Bullish' || d === '看涨') return 'text-emerald-400'
    if (d === 'Bearish' || d === '看跌') return 'text-rose-400'
    return 'text-slate-400'
})

const directionTransform = computed(() => {
    return 'scale(1)'
})

const timeColorClass = computed(() => {
    return 'text-white'
})

const confidenceColor = computed(() => {
    if (!currentItem.value) return '#94a3b8'
    
    if (currentItem.value.isAlert) return '#f43f5e' // Alert color
    
    const c = currentItem.value.confidence
    if (c >= 80) return '#10b981' // emerald-500
    if (c >= 60) return '#3b82f6' // blue-500
    if (c >= 40) return '#f59e0b' // amber-500
    return '#ef4444' // rose-500
})

const confidenceDashArray = computed(() => {
    const circumference = 2 * Math.PI * 45 // ~282.7
    if (!currentItem.value) return `0 ${circumference}`
    const percent = currentItem.value.confidence / 100
    return `${percent * circumference} ${circumference}`
})

// ================= Watcher for Audio =================
watch(() => marketStore.marketAlerts, (newAlerts) => {
    if (newAlerts && newAlerts.length > 0) {
        const latest = newAlerts[0]
        // Only play if it's a new timestamp we haven't seen
        if (latest.timestamp > lastAlertTimestamp.value) {
            lastAlertTimestamp.value = latest.timestamp
            playAlertSound(latest.severity || 'low')
        }
    }
}, { deep: true })

// ================= Methods =================

function getDirectionClass(dir: string, item: any) {
    // If it's an alert with specific styling
    if (item && item.isAlert) {
        if (item.type === 'volume_spike') return 'text-indigo-400'
        if (item.severity === 'high') return 'text-red-500 animate-bounce'
    }

    if (dir === 'Bullish' || dir === '看涨') return 'text-emerald-400'
    if (dir === 'Bearish' || dir === '看跌') return 'text-rose-400'
    return 'text-slate-400'
}

function getConfidenceColor(conf: number) {
    if (conf >= 80) return 'text-emerald-500'
    if (conf >= 60) return 'text-blue-500'
    return 'text-amber-500'
}

function startCarousel() {
    stopCarousel() // Clear existing
    
    // Reset progress
    progressWidth.value = 0
    setTimeout(() => progressWidth.value = 100, 50) // Trigger animation

    timer = setInterval(() => {
        nextSlide()
    }, CYCLE_TIME)
}

function nextSlide() {
    if (predictions.value.length === 0) return
    activeIndex.value = (activeIndex.value + 1) % predictions.value.length
    // Reset animation
    progressWidth.value = 0
    setTimeout(() => progressWidth.value = 100, 50)
}

function stopCarousel() {
    if (timer) clearInterval(timer)
}

function pauseCarousel() {
    stopCarousel()
    progressWidth.value = 100 // Hold progress
}

function resumeCarousel() {
    startCarousel()
}

function setActive(index: number) {
    activeIndex.value = index
    startCarousel() // Restart timer on manual interaction
}

function handleDeepAnalysis(symbol: string) {
    if (!symbol || symbol === '扫描中...') return
    emit('analyze', symbol)
}

function updateCountdown() {
    if (!currentItem.value || !currentItem.value.validUntil) return
    const now = dayjs()
     const diff = currentItem.value.validUntil.diff(now, 'second')
    
    if (diff <= 0) {
        countdownDisplay.value = '即将过期'
        return
    }

    const h = Math.floor(diff / 3600)
    const m = Math.floor((diff % 3600) / 60)
    const s = diff % 60
    countdownDisplay.value = `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`
}

// ================= Lifecycle =================

onMounted(async () => {
    // 移除了默认的自动扫描逻辑，现在仅在用户明确操作或后台推送时更新
    startCarousel()
    if (countdownTimer) clearInterval(countdownTimer)
    countdownTimer = setInterval(updateCountdown, 1000)
    updateCountdown()
})

onUnmounted(() => {
    stopCarousel()
    if (countdownTimer) clearInterval(countdownTimer)
})

</script>

<style scoped>
.custom-scroll::-webkit-scrollbar {
    width: 4px;
}
.custom-scroll::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.5);
}
.custom-scroll::-webkit-scrollbar-thumb {
    background: rgba(51, 65, 85, 0.5);
    border-radius: 4px;
}
</style>
