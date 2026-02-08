<!--
  智链预测 - 市场概览组件
  =============================
  Integrates global market indices, top coins heatmap, market status, and key events.
-->
<template>
  <div class="flex flex-col gap-6 h-full overflow-y-auto no-scrollbar pr-1">
    
     <!-- 1. 全局市场指数 (Global Indices) -->
    <div class="glass-panel p-4">
      <div class="flex justify-between items-center mb-4">
        <h3 class="panel-title font-display">全局市场指标</h3>
        <span class="text-xs font-tabular text-slate-500 uppercase tracking-widest">24H 涨跌</span>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <!-- 恐惧贪婪指数 -->
        <div class="stat-card">
           <div class="text-sm text-slate-400 mb-1 font-sans">恐惧与贪婪</div>
           <div class="flex items-end gap-2">
             <span class="text-3xl font-bold font-tabular" :class="fearGreedClass">{{ marketStats.fearGreed }}</span>
             <span class="text-base mb-1 font-sans" :class="fearGreedClass">{{ fearGreedLabel_CN }}</span>
           </div>
           
           <div class="w-full h-1.5 bg-slate-700/50 rounded-full mt-2 overflow-hidden">
             <div class="h-full rounded-full transition-all duration-1000"
                  :class="fearGreedBg"
                  :style="{ width: marketStats.fearGreed + '%' }">
             </div>
           </div>
        </div>

        <!-- 市场总值 -->
        <div class="stat-card">
           <div class="text-sm text-slate-400 mb-1 font-sans">全场行情摘要</div>
           <div class="flex items-end gap-2">
             <span class="text-xl font-bold text-white font-sans">综合表现</span>
             <span class="text-sm mb-1 font-tabular" :class="marketStats.marketChange >= 0 ? 'text-emerald-400' : 'text-rose-400'">
               {{ marketStats.marketChange >= 0 ? '+' : '' }}{{ marketStats.marketChange }}%
             </span>
           </div>
           <div class="text-sm text-slate-500 mt-1 font-sans">基于主流币种</div>
           <!-- Mini Sparkline (CSS only for now) -->
           <div class="flex items-end h-3 gap-0.5 mt-2 opacity-50">
             <div class="w-1 bg-emerald-500/50 h-[40%]"></div>
             <div class="w-1 bg-emerald-500/50 h-[60%]"></div>
             <div class="w-1 bg-emerald-500/50 h-[50%]"></div>
             <div class="w-1 bg-emerald-500/50 h-[80%]"></div>
             <div class="w-1 bg-emerald-500/50 h-[70%]"></div>
             <div class="w-1 bg-emerald-500/80 h-[90%]"></div>
           </div>
        </div>
      </div>

      <!-- 情绪热力图 (Sector Performance) -->
      <div class="mt-4">
         <div class="text-sm text-slate-400 mb-2 font-display">板块表现</div>
         <div class="grid grid-cols-4 gap-1 h-12">
            <div v-for="sector in sectors" :key="sector.name"
                 class="rounded flex flex-col items-center justify-center text-xs font-bold border font-display"
                 :class="sector.change >= 0 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'"
                 :title="sector.name"
            >
              <span>{{ sector.name }}</span>
              <span class="font-tabular">{{ sector.change >= 0 ? '+' : '' }}{{ sector.change }}%</span>
            </div>
         </div>
      </div>
    </div>

    <!-- 2. 市场状态指示器 (Status Indicator) -->
    <div class="glass-panel p-4">
       <h3 class="panel-title mb-3 font-display">多维市场状态</h3>
       <div class="status-grid">
          <!-- Trend -->
          <div class="status-item">
             <span class="label font-display">趋势</span>
             <span class="value flex items-center gap-1 font-sans" :class="marketStatus.trend === '看涨' ? 'text-emerald-400' : (marketStatus.trend === '看跌' ? 'text-rose-400' : 'text-slate-400')">
               <el-icon v-if="marketStatus.trend === '看涨'"><Top /></el-icon>
               <el-icon v-else-if="marketStatus.trend === '看跌'"><Bottom /></el-icon>
               {{ marketStatus.trend }}
             </span>
          </div>
          <!-- Volatility -->
          <div class="status-item">
             <span class="label font-display">波动率</span>
             <span class="value font-sans" :class="marketStatus.volatility === '高' ? 'text-amber-400' : 'text-slate-400'">{{ marketStatus.volatility }}</span>
          </div>
          <!-- Risk -->
          <div class="status-item">
             <span class="label font-display">风险等级</span>
             <span class="value font-sans" :class="marketStatus.riskLevel === '正常' ? 'text-blue-400' : 'text-rose-400'">{{ marketStatus.riskLevel }}</span>
          </div>
       </div>
       
       <div class="mt-3 pt-3 border-t border-slate-700/50">
          <div class="flex justify-between text-xs mb-1 font-sans">
             <span class="text-slate-400">资金流向 (24h)</span>
             <span class="text-emerald-400 font-tabular font-bold">净流入 +$1.2B</span>
          </div>
          <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden flex">
             <div class="h-full bg-emerald-500 w-[65%]"></div>
             <div class="h-full bg-rose-500 w-[35%]"></div>
          </div>
       </div>
    </div>

    <!-- Section Removed: Key Events (Now in Dashboard Stream) -->

    <!-- 3. 主流币种速览 (Top Coins) -->
    <div class="glass-panel flex-1 flex flex-col min-h-0">
       <div class="p-3 border-b border-slate-700/30 flex justify-between items-center bg-slate-800/20">
          <h3 class="panel-title font-display">热门波动</h3>
          <button class="text-xs text-blue-400 hover:text-blue-300 font-display">更多</button>
       </div>
       
       <div class="overflow-y-auto overflow-x-auto max-h-[250px] custom-scroll">
          <table class="w-full text-left border-collapse">
             <thead class="bg-slate-800/50 text-[10px] text-slate-500 uppercase sticky top-0 backdrop-blur-md z-10 font-display">
                <tr>
                   <th class="p-2 pl-4 font-medium">币种</th>
                   <th class="p-2 font-medium text-right">价格</th>
                   <th class="p-2 font-medium text-right">24H</th>
                   <th class="p-2 pr-4 font-medium text-right">AI 评分</th>
                </tr>
             </thead>
             <tbody class="text-sm font-sans">
                <tr v-for="coin in topCoins" :key="coin.symbol" 
                    class="border-b border-slate-700/30 hover:bg-slate-700/50 cursor-pointer transition-colors"
                    @click="$emit('select-symbol', coin.symbol)"
                >
                   <td class="p-3 pl-4">
                      <div class="flex items-center gap-2">
                         <span class="font-bold text-slate-200 font-display">{{ coin.symbol }}</span>
                         <span v-if="coin.hot" class="text-[10px]">🔥</span>
                      </div>
                   </td>
                   <td class="p-3 text-right font-tabular text-slate-300">{{ coin.price }}</td>
                   <td class="p-3 text-right font-tabular" :class="coin.change >= 0 ? 'text-emerald-400' : 'text-rose-400'">
                      {{ coin.change >= 0 ? '+' : '' }}{{ coin.change }}%
                   </td>
                   <td class="p-3 pr-4 text-right">
                      <span class="status-badge font-display" :class="getRatingClass(coin.rating)">{{ ratingMap[coin.rating] || coin.rating }}</span>
                   </td>
                </tr>
             </tbody>
          </table>
       </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Top, Bottom } from '@element-plus/icons-vue'
import { usePredictionStore } from '@/stores/usePredictionStore'

const marketStore = usePredictionStore()

// ================= Data Handling =================

onMounted(async () => {
    // Initial fetch
    await marketStore.fetchGlobalStats()
    await marketStore.loadAllTickers()
})

// Global Market Stats
const globalStats = computed(() => marketStore.globalStats)

const marketStats = computed(() => ({
    fearGreed: globalStats.value?.fear_greed.value || 50,
    fearGreedLabel: globalStats.value?.fear_greed.classification || 'Neutral',
    marketChange: globalStats.value?.market_change || 0
}))

const fearGreedLabel_CN = computed(() => {
    const l = marketStats.value.fearGreedLabel
    if (l === 'Greed') return '贪婪'
    if (l === 'Extreme Greed') return '极度贪婪'
    if (l === 'Fear') return '恐慌'
    if (l === 'Extreme Fear') return '极度恐慌'
    if (l === 'Neutral') return '中性'
    return l // Return raw if already localized or unknown
})

// Top Coins from Tickers
const topCoins = computed(() => {
    const tickers = marketStore.tickers
    const symbols = Object.keys(tickers)
    
    return symbols.slice(0, 10).map(s => {
        const t = tickers[s]
        return {
            symbol: t.symbol.replace('USDT', ''),
            fullSymbol: t.symbol,
            price: t.price > 1 ? t.price.toLocaleString(undefined, { minimumFractionDigits: 2 }) : t.price.toFixed(4),
            change: t.change_percent,
            rating: Math.abs(t.change_percent) > 3 ? (t.change_percent > 0 ? 'Strong Buy' : 'Bearish') : 'Neutral',
            hot: Math.abs(t.change_percent) > 5
        }
    }).sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
})

// Sectors from Global Stats
const sectors = computed(() => {
    return globalStats.value?.sector_performance || [
        { name: 'Layer 1', change: 0 },
        { name: 'DeFi', change: 0 },
        { name: 'Layer 2', change: 0 },
        { name: 'Meme', change: 0 }
    ]
})

// Proxy for Market Status (derived from global stats)
const marketStatus = computed(() => {
    const change = marketStats.value.marketChange
    return {
        trend: change > 0.5 ? '看涨' : (change < -0.5 ? '看跌' : '震荡'),
        volatility: Math.abs(change) > 2 ? '高' : '低',
        riskLevel: marketStats.value.fearGreed < 25 ? '极高' : (marketStats.value.fearGreed < 40 ? '高' : '正常')
    }
})

const ratingMap: Record<string, string> = {
    'Bullish': '看涨',
    'Strong Buy': '强力买入',
    'Neutral': '中性',
    'Bearish': '看跌',
    'Risky': '风险'
}

// ================= Computed =================

const fearGreedClass = computed(() => {
    const v = marketStats.value.fearGreed
    if (v >= 75) return 'text-emerald-400'
    if (v >= 50) return 'text-blue-400'
    if (v >= 25) return 'text-amber-400'
    return 'text-rose-400'
})

const fearGreedBg = computed(() => {
    const v = marketStats.value.fearGreed
    if (v >= 75) return 'bg-emerald-500'
    if (v >= 50) return 'bg-blue-500'
    if (v >= 25) return 'bg-amber-500'
    return 'bg-rose-500'
})

// ================= Helpers =================

function getRatingClass(rating: string) {
    if (rating === 'Strong Buy' || rating === 'Bullish') return 'live'
    if (rating === 'Risky' || rating === 'Bearish') return 'danger'
    return 'neutral'
}

async function refreshData() {
    await marketStore.fetchGlobalStats()
    await marketStore.loadAllTickers()
}

defineExpose({ refreshData })
</script>

<style scoped>
.glass-panel {
    background-color: rgba(30, 41, 59, 0.4); /* bg-slate-800/40 */
    backdrop-filter: blur(12px);
    border: 1px solid rgba(51, 65, 85, 0.5); /* border-slate-700/50 */
    border-radius: 0.75rem; /* rounded-xl */
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); /* shadow-lg */
}

.panel-title {
    font-size: 1.0rem; /* 16px */
    line-height: 1.5rem;
    font-weight: 800;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.stat-card {
    background-color: rgba(15, 23, 42, 0.3); /* bg-slate-900/30 */
    border-radius: 0.25rem;
    padding: 0.5rem;
    border: 1px solid rgba(30, 41, 59, 0.5); /* border-slate-800/50 */
    display: flex;
    flex-direction: column;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.5rem;
    margin-top: 0.5rem;
}
.status-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: rgba(30, 41, 59, 0.3); /* bg-slate-800/30 */
    padding: 0.5rem;
    border-radius: 0.25rem;
}
.status-item .label {
    font-size: 12px; /* 12px minimum */
    color: #94a3b8; /* text-slate-400 */
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.25rem;
}
.status-item .value {
    font-size: 1.0rem; /* 16px */
    font-weight: 700;
}

.status-badge {
    padding: 0.25rem 0.6rem;
    border-radius: 0.25rem;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-width: 1px;
    text-align: center;
    display: inline-block;
    min-width: 72px;
}
.status-badge.live {
    border-color: rgba(16, 185, 129, 0.3);
    color: #34d399; /* text-emerald-400 */
    background-color: rgba(16, 185, 129, 0.1);
}
.status-badge.danger {
    border-color: rgba(244, 63, 94, 0.3);
    color: #fb7185; /* text-rose-400 */
    background-color: rgba(244, 63, 94, 0.1);
}
.status-badge.neutral {
    border-color: rgba(100, 116, 139, 0.3);
    color: #94a3b8; /* text-slate-400 */
    background-color: rgba(100, 116, 139, 0.1);
}

/* Scrollbar Hide */
.no-scrollbar::-webkit-scrollbar {
    display: none;
}
.no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
