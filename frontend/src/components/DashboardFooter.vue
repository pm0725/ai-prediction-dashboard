<template>
  <footer class="h-8 bg-slate-900 border-t border-slate-800 flex flex-shrink-0 items-center justify-between px-6 text-[10px] text-slate-500 z-40 backdrop-blur-sm bg-opacity-90">
     <div class="flex gap-4">
       <button @click="$emit('open-monitor')" class="flex items-center gap-1 hover:bg-slate-800 px-2 rounded transition-colors group cursor-pointer">
          <span>System:</span>
          <span class="text-emerald-500 font-bold group-hover:shadow-[0_0_10px_rgba(16,185,129,0.5)] transition-shadow">Online</span>
       </button>
       <span class="flex items-center">Latency: <span class="text-slate-300 ml-1">24ms</span></span>
       <span class="flex items-center">Version: <span class="text-slate-300 ml-1">v1.2.0 (Pro)</span></span>
     </div>
     <div class="flex items-center gap-4">
       <router-link to="/performance" class="flex items-center gap-1 hover:text-blue-400 transition-colors">
          <el-icon><DataAnalysis /></el-icon> AI Performance
       </router-link>
       <span>© 2026 DeepSeek Quant Engine. All rights reserved.</span>
     </div>
  </footer>
</template>

<script setup lang="ts">
import { DataAnalysis } from '@element-plus/icons-vue'

defineEmits(['open-monitor'])
</script>
