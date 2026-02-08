<template>
  <div class="glass-panel p-4 bg-slate-800/40 rounded-xl border border-slate-700/50">
    <div class="flex justify-between items-center mb-3">
       <h3 class="text-sm font-bold text-slate-400 uppercase tracking-widest">数据健康度</h3>
       <el-button size="small" text bg circle class="!px-1" @click="$emit('open')">
          <el-icon><Expand /></el-icon>
       </el-button>
    </div>
    
    <div class="space-y-3">
       <div class="flex justify-between items-center bg-slate-800/50 p-2 rounded">
          <div class="flex items-center gap-2">
             <div class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.5)]"></div>
             <span class="text-sm font-bold text-slate-300">Binance</span>
          </div>
          <span class="font-mono text-xs text-emerald-400">45ms</span>
       </div>
       
       <div class="flex justify-between items-center bg-slate-800/50 p-2 rounded">
          <div class="flex items-center gap-2">
             <div class="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
             <span class="text-sm font-bold text-slate-300">Coinbase</span>
          </div>
          <span class="font-mono text-xs text-emerald-400">120ms</span>
       </div>

       <div class="flex justify-between items-center bg-slate-800/50 p-2 rounded">
          <div class="flex items-center gap-2">
             <div class="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
             <span class="text-sm font-bold text-slate-300">链上数据</span>
          </div>
          <span class="font-mono text-xs text-slate-400">稳定</span>
       </div>
    </div>
    
    <div class="mt-3 pt-3 border-t border-slate-700/30 flex justify-between text-xs">
       <span class="text-slate-500">综合质量评分</span>
       <span class="text-amber-400 font-bold">★★★★☆</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Expand } from '@element-plus/icons-vue'
defineEmits(['open'])
</script>

<style scoped>
.glass-panel {
    background-color: rgba(30, 41, 59, 0.4); /* bg-slate-800/40 */
    backdrop-filter: blur(12px);
    border: 1px solid rgba(51, 65, 85, 0.5); /* border-slate-700/50 */
    border-radius: 0.75rem; /* rounded-xl */
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); /* shadow-lg */
}
</style>
