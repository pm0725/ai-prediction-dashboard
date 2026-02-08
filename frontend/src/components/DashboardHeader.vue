<template>
  <header class="h-16 border-b border-slate-700/50 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-6">
    
    <!-- Logo & Title -->
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
         <el-icon class="text-white text-lg"><opportunity /></el-icon>
      </div>
      <div>
         <h1 class="text-lg font-bold text-white tracking-tight leading-none">DEEPSEEK</h1>
         <div class="text-[10px] text-blue-400 font-mono tracking-widest uppercase">Quant Engine</div>
      </div>
    </div>

    <!-- Center Navigation (Optional in future) -->
    <nav class="hidden md:flex items-center gap-1 bg-slate-800/50 p-1 rounded-full border border-slate-700/50">
       <button class="px-4 py-1.5 rounded-full text-xs font-bold text-white bg-slate-700 shadow-sm transition-all">Dashboard</button>
       <button class="px-4 py-1.5 rounded-full text-xs font-bold text-slate-400 hover:text-white transition-all">Markets</button>
       <button class="px-4 py-1.5 rounded-full text-xs font-bold text-slate-400 hover:text-white transition-all">Strategies</button>
       <button class="px-4 py-1.5 rounded-full text-xs font-bold text-slate-400 hover:text-white transition-all">Backtest</button>
    </nav>

    <!-- Right Actions -->
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2 bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700/50">
         <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
         <span class="text-xs font-mono font-bold text-emerald-400">LIVE</span>
      </div>
      
      <div class="h-8 w-[1px] bg-slate-700"></div>

      <el-avatar :size="32" class="border border-slate-600 bg-slate-800 text-xs">USER</el-avatar>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Opportunity } from '@element-plus/icons-vue'
</script>
