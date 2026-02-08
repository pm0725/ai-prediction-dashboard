<script setup lang="ts">
import { computed } from 'vue'
import { usePredictionStore } from '@/stores/usePredictionStore'

const predictionStore = usePredictionStore()

const winRate = computed(() => {
  const history = predictionStore.history
  if (!history || history.length === 0) return 0
  
  const completed = history.filter(h => h.correct !== null)
  if (completed.length === 0) return 0
  
  const wins = completed.filter(h => h.correct).length
  return Math.round((wins / completed.length) * 100)
})

const totalPredictions = computed(() => predictionStore.history.length)
</script>

<template>
  <div class="glass-panel p-4 flex items-center justify-between bg-slate-800/40 rounded-xl border border-slate-700/50 h-24">
      <div class="flex flex-col">
         <span class="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1 font-display">历史胜率 ({{ totalPredictions }}次)</span>
         <div class="text-2xl font-black text-white flex items-baseline gap-1 font-tabular">
            {{ winRate }}%
            <span class="text-xs font-bold text-slate-500 font-sans" v-if="totalPredictions === 0">暂无数据</span>
         </div>
      </div>
      
      <!-- Mini Chart Placeholder (Static SVG for performance) -->
      <svg class="w-24 h-12 text-slate-500" viewBox="0 0 100 50" v-if="totalPredictions === 0">
         <path d="M0,25 L100,25" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="4 4" />
      </svg>
      <svg class="w-24 h-12 text-emerald-500" viewBox="0 0 100 50" v-else>
         <path d="M0,50 L0,40 L10,35 L20,45 L30,30 L40,32 L50,20 L60,25 L70,10 L80,15 L90,5 L100,0 L100,50 Z" 
               fill="currentColor" fill-opacity="0.2" />
         <path d="M0,40 L10,35 L20,45 L30,30 L40,32 L50,20 L60,25 L70,10 L80,15 L90,5 L100,0" 
               fill="none" stroke="currentColor" stroke-width="2" />
      </svg>
  </div>
</template>

<style scoped>
.glass-panel {
    background-color: rgba(30, 41, 59, 0.4); /* bg-slate-800/40 */
    backdrop-filter: blur(12px);
    border: 1px solid rgba(51, 65, 85, 0.5); /* border-slate-700/50 */
    border-radius: 0.75rem; /* rounded-xl */
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); /* shadow-lg */
}
</style>
