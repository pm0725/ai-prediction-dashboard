<!--
  智链预测 - 核心预测仪表盘 (Unified Dashboard)
  =============================================
  Final integrated dashboard with 3-column CSS GRID layout.
-->
<template>
  <div class="h-full bg-[#0b0f1a] text-slate-200 font-sans flex flex-col overflow-y-auto lg:overflow-hidden selection:bg-blue-500/30 relative">
    <!-- 0. Ambient Background Effects -->
    <div class="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <!-- Dynamic Glow Blob -->
        <div 
            class="absolute top-[-20%] left-[20%] w-[60%] h-[60%] rounded-full blur-[120px] opacity-20 transition-all duration-1000 ease-in-out"
            :class="ambientGlowClass"
        ></div>
        <div 
            class="absolute bottom-[-20%] right-[10%] w-[40%] h-[60%] rounded-full blur-[100px] opacity-10 transition-all duration-1000 ease-in-out delay-500"
            :class="ambientGlowClass"
        ></div>
    </div>

    <!-- Cinematic Noise Overlay -->
    <div class="fixed inset-0 pointer-events-none z-[100] opacity-[0.03] mix-blend-overlay bg-noise"></div>

    <!-- 1. Top Market Bar (Fixed Height) -->
    <div class="h-12 border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md flex items-center px-4 justify-between z-30 flex-shrink-0 relative font-sans overflow-x-auto no-scrollbar">
       <div class="flex items-center gap-6 min-w-max">
          <div class="flex items-center gap-4 text-sm text-slate-400">
             <div class="flex items-center gap-2">
                <span class="font-bold text-slate-500 tracking-wide text-xs font-display">BTC</span>
                <span class="text-slate-200 font-tabular font-bold">{{ predictionStore.tickers['BTCUSDT']?.price || '---' }}</span>
                <span :class="predictionStore.tickers['BTCUSDT']?.change_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'" class="font-tabular text-xs">
                   {{ predictionStore.tickers['BTCUSDT']?.change_percent > 0 ? '+' : '' }}{{ predictionStore.tickers['BTCUSDT']?.change_percent }}%
                </span>
             </div>
             
             <div class="w-px h-3 bg-slate-800"></div>
             
             <div class="flex items-center gap-2">
                <span class="font-bold text-slate-500 tracking-wide text-xs font-display">ETH</span>
                <span class="text-slate-200 font-tabular font-bold">{{ predictionStore.tickers['ETHUSDT']?.price || '---' }}</span>
                <span :class="predictionStore.tickers['ETHUSDT']?.change_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'" class="font-tabular text-xs">
                   {{ predictionStore.tickers['ETHUSDT']?.change_percent > 0 ? '+' : '' }}{{ predictionStore.tickers['ETHUSDT']?.change_percent }}%
                </span>
             </div>

             <div class="w-px h-3 bg-slate-800"></div>
             <div class="flex items-center gap-2">
                <span class="font-bold text-slate-500 tracking-wide text-xs font-display">情绪</span>
                <span :class="predictionStore.globalStats?.fear_greed.classification === 'Greed' ? 'text-emerald-400' : 'text-rose-400'" class="font-bold text-xs">
                   <span class="font-tabular text-base mr-1">{{ predictionStore.globalStats?.fear_greed.value || 50 }}</span>
                   <span class="font-sans">{{ predictionStore.globalStats?.fear_greed.classification || 'Neutral' }}</span>
                </span>
             </div>
          </div>
       </div>
       <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 px-3 py-1 bg-slate-800/40 rounded-full border border-slate-700/50">
             <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
             <span class="text-xs text-slate-500 uppercase tracking-widest font-bold font-display">Node: DeepSeek-V3</span>
          </div>
           <el-popover :teleported="true" placement="bottom-end" :width="380" trigger="click" popper-class="!bg-[#0b0f1a] !border-slate-800 !p-0 !min-w-[380px] z-50 shadow-2xl">
               <template #reference>
                   <button class="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-white text-xs font-bold transition-colors shadow-lg shadow-blue-500/20 tracking-wide font-display">
                       <el-icon><Setting /></el-icon>
                       <span>分析配置</span>
                   </button>
               </template>
               <div class="h-[600px] overflow-hidden flex flex-col bg-[#0b0f1a] border border-slate-700/50 rounded-lg shadow-2xl">
                   <AnalysisControlPanel 
                       v-model:symbol="selectedSymbol"
                       v-model:timeframe="selectedTimeframe"
                       v-model:depth="analysisDepth"
                       v-model:risk="riskPreference"
                       :is-analyzing="predictionStore.loading.prediction"
                       @analyze="handleAnalyze" 
                   />
               </div>
           </el-popover>
       </div>
    </div>
    
    <!-- 2. Main Layout (Bento Grid) -->
    <div class="flex-1 lg:overflow-hidden bg-[#0b0f1a] relative z-10 p-4">
      <div class="h-auto lg:h-full flex flex-col lg:grid lg:grid-cols-12 gap-4 lg:min-w-[1280px]">
          
          <!-- Left Column (Market Context) -->
          <div class="lg:col-span-2 w-full flex flex-col gap-4 min-h-0 lg:overflow-y-auto custom-scroll pr-1">
              <MarketSnapshot @select-symbol="(s: string) => { selectedSymbol = s; }" />
              
              <!-- Smart Insight Stream -->
              <div class="glass-panel p-4 bg-slate-800/30 border border-slate-700/50 rounded-xl flex-1 flex flex-col min-h-[300px] max-h-[500px]">
                  <h3 class="panel-title mb-4 flex items-center gap-2 text-sm font-bold text-slate-300 font-display">
                      <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                      智能洞察流
                  </h3>
                  <div class="flex-1 overflow-y-auto custom-scroll space-y-3 pr-1">
                      <div v-if="predictionStore.globalStats?.key_events?.length" 
                           v-for="(event, i) in predictionStore.globalStats.key_events" 
                           :key="i" 
                           class="event-item p-3 rounded-lg border border-white/5 bg-slate-900/40 hover:bg-slate-800/60 transition-all border-l-2"
                           :class="getEventBorderClass(event.type)"
                      >
                           <div class="flex justify-between items-start mb-2">
                               <span class="text-[10px] uppercase font-bold tracking-wider font-display" :class="getEventColorBase(event.type)">
                                  {{ event.category }}
                               </span>
                               <span class="text-[10px] font-tabular text-slate-500">{{ event.time }}</span>
                           </div>
                           <p class="text-xs text-slate-300 leading-relaxed font-medium font-sans">{{ event.title }}</p>
                      </div>
                      <div v-else-if="predictionStore.loading.globalStats" class="h-full flex flex-col items-center justify-center text-xs text-slate-500 italic p-8">
                           <el-icon class="text-2xl mb-2 animate-spin"><Refresh /></el-icon>
                           <div class="font-sans">正在同步全网情报...</div>
                      </div>
                      <div v-else class="h-full flex flex-col items-center justify-center text-xs text-slate-500 italic text-center p-4 border border-dashed border-slate-800 rounded-lg bg-slate-900/40">
                          <el-icon class="text-2xl mb-2 opacity-50"><MagicStick /></el-icon>
                          <div class="font-sans">AI 正在实时监控全网数据...</div>
                          <div class="mt-1 opacity-50 font-sans">暂无重大异常事件</div>
                      </div>
                  </div>
              </div>

              <DataSourceWidget @open="showMonitor = true" />
          </div>

          <!-- Center Column (Analysis & Depth) -->
          <div class="lg:col-span-8 w-full flex flex-col gap-4 min-h-[600px] lg:min-h-0 lg:overflow-y-auto custom-scroll pr-1">
              <div class="h-auto relative rounded-2xl overflow-hidden glass-panel border border-indigo-500/20 shadow-2xl bg-slate-900/40">
                   <div class="absolute top-4 right-4 z-20 flex gap-2">
                       <div class="flex items-center gap-2 px-3 py-1 bg-slate-950/50 backdrop-blur rounded-lg border border-slate-800">
                           <span class="text-[10px] text-slate-500 uppercase tracking-wider font-display font-bold">基准价:</span>
                           <span class="text-sm font-tabular font-bold text-amber-400">
                               {{ predictionStore.prediction?.key_levels?.current_price || '--' }}
                           </span>
                           <span class="w-px h-3 bg-slate-700 mx-1"></span>
                           <div class="flex items-center gap-1.5 opacity-60">
                               <span class="relative flex h-1.5 w-1.5">
                                 <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                 <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-500"></span>
                               </span>
                               <span class="text-[10px] text-slate-300 font-sans tracking-tight">Binance Futures</span>
                           </div>
                       </div>
                       <div class="flex items-center gap-2 px-3 py-1 bg-slate-950/50 backdrop-blur rounded-lg border border-slate-800 mr-4">
                           <span class="text-xs text-slate-400 font-bold tracking-wide font-display">AI 信心:</span>
                           <span class="text-lg font-tabular font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                               {{ predictionStore.prediction?.confidence || 0 }}%
                           </span>
                       </div>
                       <button 
                          class="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2 font-display"
                          @click="handleAnalyze"
                          :disabled="predictionStore.loading.prediction"
                       >
                          <el-icon :class="{'animate-spin': predictionStore.loading.prediction}"><Refresh /></el-icon>
                          {{ predictionStore.loading.prediction ? '深度分析中...' : '重新分析' }}
                       </button>
                   </div>

                   <div class="h-auto overflow-hidden flex flex-col">
                       <SmartStrategyPanel 
                          class="flex-shrink-0 border-none !bg-transparent"
                          :prediction="predictionStore.prediction"
                          @reset="predictionStore.prediction = null"
                          @scan="handleAnalyze"
                       />

                       <div class="h-auto min-h-0 border-t border-slate-800/50 bg-slate-900/30 px-4 pt-4 pb-2 flex flex-col relative group">
                           <div class="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
                           <div class="flex justify-between items-center mb-3 flex-shrink-0 relative z-10">
                              <h3 class="panel-title flex items-center gap-2 font-display text-sm font-bold text-slate-300"><el-icon><MagicStick /></el-icon>今日推选</h3>
                              <div class="flex items-center gap-2">
                                  <span class="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded border border-slate-700 font-sans">AI 实时监控</span>
                                  <button class="text-xs text-blue-400 hover:text-blue-300 font-display font-medium disabled:opacity-50" @click="predictionStore.runBatchScanner" :disabled="predictionStore.loading.batch">
                                      {{ predictionStore.loading.batch ? '扫描中...' : '刷新' }}
                                  </button>
                              </div>
                           </div>
                           <SpotlightPredictions class="h-auto" @analyze="handleSpotlightAnalyze" />
                       </div>
                   </div>
              </div>

              <div class="flex-1 min-h-[380px] flex-shrink-0 glass-panel bg-slate-800/20 border border-slate-700/50 rounded-xl overflow-hidden flex flex-col">
                   <MarketDepth :key="marketStore.currentSymbol" class="h-full" />
              </div>
          </div>

          <!-- Right Column (Execution & Signals) -->
          <div class="lg:col-span-2 w-full flex flex-col gap-4 min-h-0 lg:overflow-y-auto custom-scroll pl-1">
               <div class="flex-1 min-h-[350px] glass-panel bg-slate-800/20 border border-slate-700/50 rounded-xl overflow-hidden flex flex-col">
                   <RiskMonitorPanel class="h-full" />
               </div>
               <PerformanceWidget class="h-24 flex-shrink-0" />
          </div>
      </div>
    </div>

    <!-- Modals -->
    <DataSourceMonitor v-model="showMonitor" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useMarketStore, usePredictionStore } from '@/stores'
import { MagicStick, Setting, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// Components
import MarketSnapshot from '@/components/MarketSnapshot.vue'
import SpotlightPredictions from '@/components/SpotlightPredictions.vue'
import AnalysisControlPanel from '@/components/AnalysisControlPanel.vue'
import RiskMonitorPanel from '@/components/RiskMonitorPanel.vue'
import DataSourceMonitor from '@/components/DataSourceMonitor.vue'
import DataSourceWidget from '@/components/DataSourceWidget.vue'
import PerformanceWidget from '@/components/PerformanceWidget.vue'
import MarketDepth from '@/components/MarketDepth.vue'
import SmartStrategyPanel from '@/components/SmartStrategyPanel.vue'

// Stores
const marketStore = useMarketStore()
const predictionStore = usePredictionStore()

// State
const ambientGlowClass = computed(() => {
  const sentiment = predictionStore.globalStats?.fear_greed.classification || 'Neutral'
  if (sentiment === 'Greed' || sentiment === 'Extreme Greed') return 'bg-emerald-500'
  if (sentiment === 'Fear' || sentiment === 'Extreme Fear') return 'bg-rose-500'
  return 'bg-blue-500'
})
const showMonitor = ref(false)
const selectedSymbol = ref('BTCUSDT')

// Initialize from store preferences if available
const selectedTimeframe = ref(predictionStore.preferences.timeframe || '4h')
const analysisDepth = ref(predictionStore.preferences.depth || 'standard')
const riskPreference = ref(predictionStore.preferences.risk || 50)

// Sync with Store
watch(selectedSymbol, (newSymbol) => {
    if (newSymbol) {
        marketStore.selectSymbol(newSymbol)
        predictionStore.selectSymbol(newSymbol) // Ensure store symbol is updated
    }
})

// Actions
const handleAnalyze = async () => {
    // Determine risk as string for store
    let riskStr = 'moderate'
    const riskVal = Number(riskPreference.value)
    if (riskVal <= 30) riskStr = 'conservative'
    else if (riskVal >= 70) riskStr = 'aggressive'

    try {
        console.log(`[Dashboard] Starting analysis: ${selectedSymbol.value} | ${selectedTimeframe.value} | ${analysisDepth.value} | ${riskStr}`)
        
        // Ensure store knows the current symbol before analysis
        if (predictionStore.currentSymbol !== selectedSymbol.value) {
            predictionStore.selectSymbol(selectedSymbol.value)
        }

        const result = await predictionStore.analyze(
            selectedTimeframe.value, 
            false, // Force fresh analysis when clicking 'Re-analyze'
            analysisDepth.value === 'deep' ? 3 : (analysisDepth.value === 'quick' ? 1 : 2), 
            riskStr
        )
        
        if (result) {
            ElMessage.success({
                message: `${selectedSymbol.value} 分析完成`,
                duration: 2000
            })
            
            predictionStore.addToHistory({
                symbol: result.symbol || selectedSymbol.value,
                direction: (result.prediction_cn || result.prediction || 'Unknown').split(' ')[0], 
                time: new Date().toLocaleString(),
                confidence: result.confidence,
                summary: result.summary,
                correct: null, 
                fullData: result 
            })
        }
    } catch (e: any) {
        console.error('[Dashboard] Analysis failed:', e)
        ElMessage.error(e.message || '分析失败')
    }
}

const handleSpotlightAnalyze = async (symbol: string) => {
    const targetSymbol = symbol.includes('USDT') ? symbol : `${symbol}USDT`
    console.log(`[Dashboard] Spotlight requested analysis for: ${targetSymbol}`)
    
    // 如果是切换币种，先设置好状态
    if (selectedSymbol.value !== targetSymbol) {
        selectedSymbol.value = targetSymbol
    }
    
    // 立即执行分析
    await handleAnalyze()
}

// Event Styling Helpers
const getEventBorderClass = (type: string) => {
    if (type === 'high') return 'border-l-rose-500 shadow-[2px_0_10px_rgba(244,63,94,0.1)]'
    if (type === 'medium') return 'border-l-amber-500'
    return 'border-l-blue-500'
}

const getEventColorBase = (type: string) => {
    if (type === 'high') return 'text-rose-400'
    if (type === 'medium') return 'text-amber-400'
    return 'text-blue-400'
}

onMounted(async () => {
    try {
        await marketStore.loadSymbols()
        await predictionStore.loadSymbols() // Ensure prediction store symbols are loaded too
        await predictionStore.loadAllTickers() 
        
        marketStore.selectSymbol(selectedSymbol.value)
        predictionStore.selectSymbol(selectedSymbol.value) // Important: Sync currentSymbol
        
        await predictionStore.fetchGlobalStats()
        
        predictionStore.loadPreferences()
        await predictionStore.loadHistory()
        
        // Update local refs from loaded preferences
        if (predictionStore.preferences.timeframe) selectedTimeframe.value = predictionStore.preferences.timeframe
        if (predictionStore.preferences.depth) analysisDepth.value = predictionStore.preferences.depth
        if (predictionStore.preferences.risk) riskPreference.value = predictionStore.preferences.risk
        
        watch([selectedTimeframe, analysisDepth, riskPreference], ([tf, depth, risk]) => {
            predictionStore.updatePreferences({
                timeframe: tf,
                depth: depth,
                risk: Number(risk)
            })
        })
    } catch (e) {
        console.error('Init failed', e)
    }
})
</script>

<style scoped>
.panel-title {
    font-size: 0.875rem; 
    line-height: 1.25rem;
    font-weight: 700;
    color: #94a3b8; 
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.glass-panel {
    backdrop-filter: blur(12px);
}
.bg-noise {
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
}
.custom-scroll::-webkit-scrollbar {
    width: 4px;
}
.custom-scroll::-webkit-scrollbar-track {
    background: rgba(30, 41, 59, 0.5);
}
.custom-scroll::-webkit-scrollbar-thumb {
    background: rgba(71, 85, 105, 0.8);
    border-radius: 4px;
}
.custom-scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.8);
}
.no-scrollbar::-webkit-scrollbar {
    display: none;
}
.no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
