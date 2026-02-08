<template>
  <div>
    <!-- Connected State: Strategy Board -->
    <div v-if="formattedStrategy && !predictionStore.isAnalyzing" class="glass-panel p-6 bg-slate-800/30 border border-slate-700/50 rounded-xl animate-fade-in-up">
       <StrategyBoard :strategy="formattedStrategy" @back="$emit('reset')" />
    </div>

    <!-- Loading State: Deep Analysis in progress -->
    <div v-if="predictionStore.isAnalyzing" class="flex-1 min-h-[400px] flex flex-col items-center justify-center glass-panel bg-slate-900/40 rounded-xl border border-blue-500/20 shadow-2xl relative overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-b from-blue-500/5 via-transparent to-transparent"></div>
        <div class="w-32 h-32 relative mb-8">
            <div class="absolute inset-0 rounded-full border-4 border-blue-500/10"></div>
            <div class="absolute inset-0 rounded-full border-t-4 border-blue-500 animate-spin"></div>
            <div class="absolute inset-4 rounded-full border-4 border-indigo-500/10"></div>
            <div class="absolute inset-4 rounded-full border-b-4 border-indigo-500 animate-spin-reverse"></div>
            <div class="absolute inset-0 flex items-center justify-center">
                <el-icon class="text-4xl text-blue-400 animate-pulse"><Cpu /></el-icon>
            </div>
        </div>
        <h3 class="text-2xl font-black text-white mb-2 tracking-widest uppercase italic">AI 深度推理中</h3>
        <p class="text-sm text-slate-400 max-w-sm text-center font-medium opacity-80 mb-6">
            正在聚合全网订单簿、技术指标及实时新闻...
        </p>
        <!-- Progress Bar Simulation -->
        <div class="w-64 h-1.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
            <div class="h-full bg-gradient-to-r from-blue-600 to-indigo-600 animate-loading-bar"></div>
        </div>
    </div>

    <!-- System Idle State (When no prediction and not loading) -->
    <div v-else-if="!formattedStrategy" class="flex-1 min-h-[400px] flex flex-col items-center justify-center glass-panel bg-slate-900/20 rounded-xl border-2 border-dashed border-slate-700/50">
        <div class="w-24 h-24 rounded-full bg-slate-800/50 flex items-center justify-center mb-6 relative">
           <div class="absolute inset-0 rounded-full border border-blue-500/20 animate-ping"></div>
           <el-icon class="text-4xl text-slate-500"><Monitor /></el-icon>
        </div>
        <h3 class="text-xl font-bold text-slate-300 mb-2">系统待命</h3>
        <p class="text-sm text-slate-500 max-w-md text-center mb-8">
           AI 神经网络正在后台持续扫描市场。请从左侧列表选择一个交易对，或查看上方的今日推选以获取即时预测。
        </p>
        <div class="flex gap-4">
           <button @click="$emit('scan')" class="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold transition-colors shadow-lg shadow-blue-500/20 flex items-center gap-2">
              <el-icon><MagicStick /></el-icon> 智能扫描
           </button>
        </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Monitor, MagicStick, Cpu } from '@element-plus/icons-vue'
import StrategyBoard from '@/components/StrategyBoard.vue'
import { formatPrice } from '@/utils/formatters'
import { usePredictionStore } from '@/stores'

const predictionStore = usePredictionStore()

const props = defineProps(['prediction'])

defineEmits(['reset', 'scan'])

// Adapter for StrategyBoard (Mock or converted from prediction)
const formattedStrategy = computed(() => {
    const p = props.prediction
    if (!p) return null
    
    // Determine direction from prediction string or signal
    let direction = '中性'
    if (p.prediction_cn?.includes('看涨') || p.prediction?.toLowerCase().includes('bullish')) {
        direction = '做多'
    } else if (p.prediction_cn?.includes('看跌') || p.prediction?.toLowerCase().includes('bearish')) {
        direction = '做空'
    }

    // Parse entry zone robustly
    let entryLow = 0, entryHigh = 0
    const z = p.entry_zone
    if (typeof z === 'string') {
        const parts = z.split('-').map(s => parseFloat(s.trim().replace(/,/g, '')))
        if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
            entryLow = parts[0]
            entryHigh = parts[1]
        } else {
            // Fallback for malformed string or single price
            const singlePrice = parseFloat(z.replace(/,/g, ''))
            if (!isNaN(singlePrice)) {
                entryLow = singlePrice * 0.998
                entryHigh = singlePrice * 1.002
            }
        }
    } else if (z && typeof z === 'object') {
        entryLow = Number(z.low) || Number(z.entry_low) || 0
        entryHigh = Number(z.high) || Number(z.entry_high) || 0
    }
    
    // Final fallback if still 0
    if (entryLow === 0 && p.current_price) {
        entryLow = p.current_price * 0.995
        entryHigh = p.current_price * 1.005
    }

    // --- Validation Logic Start ---
    const warnings = [...(p.risk_warning || p.warnings || ['市场波动大，请谨慎操作'])]
    
    // 1. Infer Direction if Neutral
    if (direction === '中性' || direction === 'Neutral') {
        const current = p.current_price || (entryLow + entryHigh) / 2
        const tpRaw = Array.isArray(p.take_profit) ? p.take_profit[0] : p.take_profit
        
        if (Number(tpRaw) > current) direction = '做多'
        else if (Number(tpRaw) < current) direction = '做空'
    }

    // 2. Validate SL/Entry Logic
    if (direction === '做多') {
        if (Number(p.stop_loss) >= entryLow) {
             warnings.unshift(`⚠️ 逻辑警告: 止损价 (${formatPrice(p.stop_loss)}) 高于入场低点 (${formatPrice(entryLow)})`)
        }
    } else if (direction === '做空') {
        if (Number(p.stop_loss) <= entryHigh) {
             warnings.unshift(`⚠️ 逻辑警告: 止损价 (${formatPrice(p.stop_loss)}) 低于入场高点 (${formatPrice(entryHigh)})`)
        }
    }
    // --- Validation Logic End ---

    return {
        symbol: p.symbol,
        generated_at: p.analysis_time || new Date().toISOString(),
        direction: direction,
        position_sizing: {
            percentage_of_capital: p.position_size || 10,
            max_leverage: p.leverage || 20,
            risk_per_trade: p.risk_level || '低'
        },
        entry: {
            type: p.entry_type || '建议入场',
            zone: { low: entryLow, high: entryHigh },
            condition: p.summary || p.technical_analysis?.sentiment || '建议分批入场'
        },
        stop_loss: {
            price: Number(p.stop_loss) || 0,
            type: '硬止损',
            note: (p.trade_management && Array.isArray(p.trade_management)) ? 
                  p.trade_management.find((m: string) => m.includes('止损')) || '严格执行' : 
                  '严格执行'
        },
        take_profit: (Array.isArray(p.take_profit) ? p.take_profit : [p.take_profit]).map((tp: any, idx: number) => ({
            level: idx + 1,
            price: Number(tp),
            close_percentage: Math.floor(100 / ((Array.isArray(p.take_profit) ? p.take_profit : [p.take_profit]).length || 1))
        })),
        trade_management: p.trade_management || ['建议设置保本损', '注意重要支撑位数据'],
        warnings: warnings
    }
})
</script>

<style scoped>
.glass-panel {
    backdrop-filter: blur(12px);
}
@keyframes spin-reverse {
    from { transform: rotate(360deg); }
    to { transform: rotate(0deg); }
}
.animate-spin-reverse {
    animation: spin-reverse 2s linear infinite;
}
@keyframes loading-bar {
    0% { transform: translateX(-100%); }
    50% { transform: translateX(0); }
    100% { transform: translateX(100%); }
}
.animate-loading-bar {
    animation: loading-bar 3s infinite ease-in-out;
}
</style>
