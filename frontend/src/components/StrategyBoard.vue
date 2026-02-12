<template>
  <div class="strategy-board space-y-4">
    <!-- 策略头部 (Premium Glass) -->
    <div class="glass-header p-6 rounded-2xl border border-white/5 relative overflow-hidden group">
      <div class="absolute inset-0 bg-gradient-to-r from-blue-600/10 via-purple-600/10 to-blue-600/10 opacity-50 group-hover:opacity-80 transition-opacity"></div>
      <div class="relative z-10 flex justify-between items-center">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 shadow-xl">
            <el-icon class="text-2xl text-blue-400"><Aim /></el-icon>
          </div>
          <div>
            <div class="flex items-center gap-3">
              <h2 class="text-xl font-black text-white tracking-tight uppercase">AI 交易策略</h2>
              <div 
                class="px-3 py-0.5 rounded-lg text-xl font-black uppercase tracking-wider shadow-lg transform -skew-x-12"
                :class="directionClass"
              >
                {{ strategy.direction }}
              </div>
            </div>
            <div class="flex items-center gap-2 mt-1">
              <span class="text-xs font-mono text-slate-400">{{ strategy.symbol }}</span>
              <span class="text-xs text-slate-600">•</span>
              <span class="text-xs text-slate-500">{{ formatTime(strategy.generated_at) }}</span>
            </div>
          </div>
        </div>
        <div class="flex flex-col items-end gap-2">
           <!-- Removed previous direction badge location -->
        </div>
      </div>
    </div>

    <!-- 核心板块网格 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- 仓位管理 (Ring Chart) -->
      <div class="glass-panel p-5 rounded-xl border border-white/5 hover:border-white/10 transition-all flex items-center justify-between relative overflow-hidden group">
         <!-- BG Effect -->
         <div class="absolute -right-10 -bottom-10 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-all"></div>
         
         <div class="flex flex-col gap-1 z-10">
            <div class="flex items-center gap-2 mb-2">
              <el-icon class="text-amber-400"><Coin /></el-icon>
              <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">AI 建议仓位</h3>
            </div>
            <div class="flex flex-col gap-1 mt-1">
                <div class="text-[10px] text-slate-500 font-medium">风险系数: <span :class="riskClass" class="font-bold">{{ strategy.position_sizing.risk_per_trade }}</span></div>
                <div class="text-[10px] text-slate-500 font-medium">最大杠杆: <span class="text-slate-300 font-mono">{{ strategy.position_sizing.max_leverage }}x</span></div>
            </div>
         </div>

         <!-- Interactive Ring Chart -->
         <div class="relative w-24 h-24 flex items-center justify-center cursor-pointer hover:scale-105 transition-transform" title="拖拽调整仓位 (模拟)">
            <svg class="w-full h-full transform -rotate-90">
               <!-- Track -->
               <circle cx="48" cy="48" r="36" stroke="currentColor" stroke-width="8" fill="transparent" class="text-slate-700/30" />
               <!-- Progress -->
               <circle 
                 cx="48" cy="48" r="36" 
                 stroke="currentColor" stroke-width="8" 
                 fill="transparent" 
                 :class="positionColorClass" 
                 :stroke-dasharray="226" 
                 :stroke-dashoffset="226 - (226 * strategy.position_sizing.percentage_of_capital / 100)" 
                 stroke-linecap="round" 
                 class="transition-all duration-1000 ease-out"
               />
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
               <span class="text-xl font-black text-white tracking-tighter">{{ strategy.position_sizing.percentage_of_capital }}<span class="text-xs align-top">%</span></span>
               <span class="text-[9px] text-slate-500 uppercase font-bold">Total</span>
            </div>
         </div>
      </div>

      <!-- 入场策略 -->
      <div class="glass-panel p-5 rounded-xl border border-white/5 hover:border-white/10 transition-all relative overflow-hidden">
        <div class="flex items-center gap-2 mb-4">
          <div class="p-1 rounded bg-blue-500/10 text-blue-400"><el-icon><Position /></el-icon></div>
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">入场策略</span>
        </div>
        
        <div class="space-y-4">
          <!-- Entry Type -->
          <div class="flex justify-between items-center group">
             <span class="text-sm text-slate-500 flex items-center gap-1">
                入场方式
                <el-icon class="text-slate-600 cursor-help text-xs" title="限价单: 挂单等待成交; 市价单: 立即成交"><QuestionFilled /></el-icon>
             </span>
             <span class="px-2.5 py-1 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 text-blue-400 rounded-md text-xs font-bold border border-blue-500/20 shadow-sm">
                {{ strategy.entry.type }}
             </span>
          </div>

          <!-- Entry Zone -->
          <div class="flex flex-col gap-1.5">
             <span class="text-xs text-slate-500">建议入场区间</span>
             <div 
                class="flex items-center justify-between bg-slate-800/50 rounded-lg p-2 border border-slate-700/50 hover:border-blue-500/30 hover:bg-slate-800/80 transition-all cursor-pointer group"
                @click="copyPrice(strategy.entry.zone)"
                title="点击复制价格区间"
             >
                <span class="font-mono font-bold text-slate-200 group-hover:text-blue-300 transition-colors">{{ formatPrice(strategy.entry.zone.low) }}</span>
                <span class="text-slate-500 font-bold mx-1">→</span>
                <span class="font-mono font-bold text-slate-200 group-hover:text-blue-300 transition-colors">{{ formatPrice(strategy.entry.zone.high) }}</span>
             </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 止盈止损 (Wide Section) -->
    <div class="glass-panel p-6 rounded-xl border border-white/5">
      <div class="flex items-center gap-2 mb-6">
        <el-icon class="text-emerald-400"><Stopwatch /></el-icon>
        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">风控管理 (SL / TP)</span>
      </div>

      <div class="flex flex-col md:flex-row gap-8">
        <!-- Stop Loss -->
        <div class="flex-shrink-0 w-full md:w-1/3">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></div>
            <span class="text-xs font-bold text-rose-400 uppercase">强制止损 (SL)</span>
          </div>
          <div class="text-4xl font-mono font-black text-rose-500 tracking-tighter shadow-rose-500/20 drop-shadow-lg">
            {{ formatPrice(strategy.stop_loss.price) }}
          </div>
          <div class="mt-2 text-[10px] text-slate-500 uppercase tracking-widest opacity-60">
            {{ strategy.stop_loss.note || '严格执行点位，触发即出场' }}
          </div>
        </div>

        <!-- Take Profit -->
        <div class="flex-1 border-t md:border-t-0 md:border-l border-white/5 pt-6 md:pt-0 md:pl-8">
          <div class="flex items-center gap-2 mb-4">
            <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
            <span class="text-xs font-bold text-emerald-400 uppercase">分批止盈 (TP)</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div 
              v-for="tp in strategy.take_profit" 
              :key="tp.level"
              class="bg-emerald-500/5 p-3 rounded-lg border border-emerald-500/10 flex justify-between items-center group hover:bg-emerald-500/15 hover:border-emerald-500/30 hover:shadow-[0_0_15px_rgba(16,185,129,0.1)] transition-all cursor-default relative overflow-hidden"
            >
              <!-- Glass Shine for TP1 -->
              <div v-if="tp.level === 1" class="absolute inset-0 bg-gradient-to-r from-emerald-500/10 to-transparent pointer-events-none"></div>
              
              <div class="relative z-10">
                <div class="flex items-center gap-1.5">
                    <div class="text-[10px] text-emerald-500 font-bold uppercase">TP{{ tp.level }}</div>
                    <span v-if="tp.level === 1" class="text-[9px] px-1 bg-emerald-500/20 text-emerald-400 rounded leading-none py-0.5 border border-emerald-500/30">1:1 保本位</span>
                </div>
                <div class="font-mono font-bold text-white tracking-widest">{{ formatPrice(tp.price) }}</div>
              </div>
              <div class="text-[10px] font-mono text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 relative z-10">
                平{{ tp.close_percentage }}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- SMC & VPVR 深度情报 (New Section) -->
    <div v-if="strategy.pro_context" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="glass-panel p-4 rounded-xl border border-blue-500/10 bg-blue-500/5">
            <div class="flex items-center gap-2 mb-3">
                <el-icon class="text-blue-400"><Compass /></el-icon>
                <span class="text-[11px] font-bold text-blue-300 uppercase tracking-wider">SMC 机构订单块 (Order Blocks)</span>
            </div>
            <div class="flex flex-wrap gap-2">
                <div v-for="(ob, i) in strategy.pro_context.order_blocks" :key="i"
                     class="text-[10px] px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 flex items-center gap-1.5"
                >
                    <span :class="ob.type === 'bullish' ? 'text-emerald-400' : 'text-rose-400'">{{ ob.type === 'bullish' ? '▲' : '▼' }} {{ ob.symbol }}</span>
                    <span class="text-slate-500">@</span>
                    <span class="font-mono">{{ formatPrice(ob.bottom) }}-{{ formatPrice(ob.top) }}</span>
                </div>
                <div v-if="!strategy.pro_context.order_blocks?.length" class="text-[10px] text-slate-500 italic">暂无活跃机构订单块</div>
            </div>
        </div>
        <div class="glass-panel p-4 rounded-xl border border-purple-500/10 bg-purple-500/5">
            <div class="flex items-center gap-2 mb-3">
                <el-icon class="text-purple-400"><Orange /></el-icon>
                <span class="text-[11px] font-bold text-purple-300 uppercase tracking-wider">价格分布 (VPVR Context)</span>
            </div>
            <div class="flex flex-col gap-2">
                <div class="flex justify-between items-center">
                    <span class="text-[10px] text-slate-400">成交密集区 (POC)</span>
                    <span class="text-[10px] font-mono text-white">{{ formatPrice(strategy.pro_context.vp_hvn) || '-' }}</span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-[10px] text-slate-400">止损真空位 (LVN)</span>
                    <span class="text-[10px] font-mono text-purple-400">{{ formatPrice(strategy.pro_context.vp_lvn) || '-' }}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- 逻辑与摘要 -->
    <div class="glass-panel p-6 rounded-xl border border-white/5 bg-slate-900/40">
       <div class="flex items-center gap-2 mb-4">
          <el-icon class="text-slate-400"><List /></el-icon>
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">执行备注与风控</span>
       </div>
       <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="space-y-3">
             <div 
               v-for="(item, index) in strategy.trade_management" 
               :key="index"
               class="flex items-start gap-3 p-3 bg-white/5 rounded-lg border border-white/5 text-sm text-slate-300 group hover:bg-white/10 transition-colors"
             >
                <el-icon class="text-emerald-400 mt-0.5 group-hover:scale-110 transition-transform"><Check /></el-icon>
                <span>{{ item }}</span>
             </div>
          </div>
          <div class="space-y-3">
             <div 
               v-for="(warning, index) in strategy.warnings" 
               :key="index"
               class="flex items-start gap-3 p-3 bg-rose-500/5 rounded-lg border border-rose-500/10 text-sm text-rose-300 group hover:bg-rose-500/10 transition-colors"
             >
                <el-icon class="text-rose-500 mt-0.5 animate-pulse"><Warning /></el-icon>
                <span class="font-medium leading-relaxed tracking-wide text-rose-200/90 group-hover:text-rose-100 transition-colors">{{ warning }}</span>
             </div>
          </div>
       </div>
    </div>

    <!-- 操作按钮 -->
    <div class="flex justify-end items-center gap-3 pt-4">
      <button 
        @click="$emit('back')" 
        class="px-6 py-2.5 rounded-xl border border-white/10 text-slate-400 text-sm font-bold hover:bg-white/5 transition-all"
      >
        返回分析
      </button>
      <button 
        @click="copyStrategy" 
        class="px-8 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold transition-all shadow-xl shadow-blue-600/20 flex items-center gap-2"
      >
        <el-icon><DocumentCopy /></el-icon>
        复制完整指令
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Aim,
  Coin,
  Position,
  Stopwatch,
  List,
  Warning,
  Check,
  DocumentCopy,
  QuestionFilled,
  Compass,
  Orange
} from '@element-plus/icons-vue'
import { formatPrice, formatTime } from '@/utils/formatters'

// Interface definitions removed for runtime safety compliance

const props = defineProps(['strategy'])
defineEmits(['back'])

// Computations
const directionClass = computed(() => {
  const dir = props.strategy.direction
  if (dir.includes('多')) return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
  if (dir.includes('空')) return 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
  return 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
})

const riskClass = computed(() => {
  const risk = props.strategy.position_sizing.risk_per_trade
  if (risk === '低') return 'text-emerald-400'
  if (risk === '中') return 'text-amber-400'
  return 'text-rose-400'
})

const positionColorClass = computed(() => {
  const size = props.strategy.position_sizing.percentage_of_capital
  if (size < 30) return 'text-emerald-500'
  if (size < 60) return 'text-amber-500'
  return 'text-rose-500'
})

function copyPrice(zone: any) {
    const text = `${formatPrice(zone.low)} - ${formatPrice(zone.high)}`
    navigator.clipboard.writeText(text).then(() => {
        ElMessage.success('入场价格区间已复制')
    })
}

function copyStrategy() {
  const s = props.strategy
  
  let text = `🚀 智链预测 - AI 交易指令
=================================
📝 标的: ${s.symbol}
📈 方向: ${s.direction} ${s.direction.includes('多') ? '🟢' : '🔴'}
💰 仓位: ${s.position_sizing.percentage_of_capital}% (资金) | 杠杆: ${s.position_sizing.max_leverage}x
---------------------------------
🎯 入场区间: ${formatPrice(s.entry.zone?.low || 0)} - ${formatPrice(s.entry.zone?.high || 0)}
🛡️ 止损价格: ${formatPrice(s.stop_loss.price)} (${s.stop_loss.note || '触价即出'})

✅ 分批止盈:
${s.take_profit.map((tp: any) => `   [TP${tp.level}] ${formatPrice(tp.price)} (平仓${tp.close_percentage}%)`).join('\n')}

📋 执行计划:
${s.trade_management.map((item: string) => `   • ${item}`).join('\n')}

⚠️ 风险提示:
${s.warnings.map((w: string) => `   • ${w}`).join('\n')}

🔗 链上数据:
   • 巨鲸行为: ${s.on_chain_context?.whale_activity || '无显著异常'}
   • 波动评分: ${s.on_chain_context?.volatility_score || 0}/100
   • 流动性缺口: ${s.on_chain_context?.liquidity_gaps?.length ? s.on_chain_context.liquidity_gaps.join(', ') : '无'}
---------------------------------
🤖 生成时间: ${formatTime(s.generated_at)}
`
  
  if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
          ElMessage.success('完整交易指令已复制')
      }).catch(err => {
          console.error('Copy failed', err)
          ElMessage.error('复制失败，请手动截图')
      })
  } else {
       // Fallback
       const textarea = document.createElement('textarea')
       textarea.value = text
       document.body.appendChild(textarea)
       textarea.select()
       try {
           document.execCommand('copy')
           ElMessage.success('完整交易指令已复制')
       } catch (err) {
           ElMessage.error('复制失败')
       }
       document.body.removeChild(textarea)
  }
}
</script>

<style scoped lang="scss">
.glass-panel {
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(12px);
}
.glass-header {
  background: rgba(30, 41, 59, 0.4);
  backdrop-filter: blur(16px);
}
</style>
