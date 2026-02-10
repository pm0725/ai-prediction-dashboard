<!--
  智链预测 - 交易对选择器
  ========================
  美观的交易对和时间周期选择组件
-->
<template>
  <div class="symbol-selector">
    <h3 class="selector-title">
      <el-icon><Coin /></el-icon>
      选择交易对
    </h3>
    
    <!-- 热门交易对 -->
    <div class="symbol-grid">
      <div 
        v-for="symbol in popularSymbols" 
        :key="symbol.symbol"
        class="symbol-card"
        :class="{ active: selectedSymbol === symbol.symbol }"
        @click="selectSymbol(symbol.symbol)"
      >
        <div class="symbol-icon">
          {{ getSymbolIcon(symbol.symbol) }}
        </div>
        <div class="symbol-info">
          <span class="symbol-name">{{ symbol.symbol.replace('USDT', '') }}</span>
          <span class="symbol-pair">/USDT</span>
        </div>
        <el-icon v-if="selectedSymbol === symbol.symbol" class="check-icon"><Check /></el-icon>
      </div>
    </div>
    
    <!-- 其他交易对下拉选择 -->
    <div class="more-symbols">
      <el-select 
        v-model="otherSymbol" 
        placeholder="或选择其他交易对..."
        filterable
        clearable
        size="large"
        @change="handleOtherSelect"
      >
        <el-option
          v-for="symbol in otherSymbols"
          :key="symbol.symbol"
          :label="symbol.symbol"
          :value="symbol.symbol"
        />
      </el-select>
    </div>
    
    <!-- 时间周期选择 -->
    <h3 class="selector-title" style="margin-top: 32px;">
      <el-icon><Timer /></el-icon>
      分析周期
    </h3>
    
    <div class="timeframe-tabs">
      <div 
        v-for="tf in timeframes" 
        :key="tf.value"
        class="timeframe-tab"
        :class="{ active: selectedTimeframe === tf.value }"
        @click="selectTimeframe(tf.value)"
      >
        <span class="tf-value">{{ tf.label }}</span>
        <span class="tf-desc">{{ tf.description }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Coin, Timer, Check } from '@element-plus/icons-vue'


const props = defineProps(['symbols', 'selectedSymbol', 'selectedTimeframe'])

const emit = defineEmits<{
  (e: 'select-symbol', symbol: string): void
  (e: 'select-timeframe', tf: string): void
}>()

const otherSymbol = ref('')

const timeframes = [
  { value: '15m', label: '15分钟', description: '超短线' },
  { value: '1h', label: '1小时', description: '短线' },
  { value: '4h', label: '4小时', description: '波段' },
  { value: '1d', label: '日线', description: '趋势' }
]


// Let's remove the import if it's truly unused.
// Actually, simple fix for the filter callbacks first.

// 热门交易对（前6个）
const popularSymbols = computed(() => {
  const popular = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT']
  return props.symbols.filter((s: any) => popular.includes(s.symbol)).slice(0, 6)
})

// 其他交易对
const otherSymbols = computed(() => {
  const popular = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT']
  return props.symbols.filter((s: any) => !popular.includes(s.symbol))
})

function getSymbolIcon(symbol: string): string {
  const icons: Record<string, string> = {
    BTCUSDT: '₿',
    ETHUSDT: 'Ξ',
    SOLUSDT: '◎',
    BNBUSDT: '◆',
    XRPUSDT: '✕',
    DOGEUSDT: 'Ð'
  }
  return icons[symbol] || symbol.charAt(0)
}

function selectSymbol(symbol: string) {
  otherSymbol.value = ''
  emit('select-symbol', symbol)
}

function handleOtherSelect(symbol: string) {
  if (symbol) {
    emit('select-symbol', symbol)
  }
}

function selectTimeframe(tf: string) {
  emit('select-timeframe', tf)
}
</script>

<style lang="scss" scoped>
.symbol-selector {
  padding: 20px;
}

.selector-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 20px;
}

.symbol-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.symbol-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  
  &:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(59, 130, 246, 0.3);
  }
  
  &.active {
    background: rgba(59, 130, 246, 0.1);
    border-color: #3b82f6;
  }
  
  .symbol-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    color: #fff;
  }
  
  .symbol-info {
    flex: 1;
    
    .symbol-name {
      font-size: 16px;
      font-weight: 600;
      color: #fff;
    }
    
    .symbol-pair {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.4);
    }
  }
  
  .check-icon {
    position: absolute;
    top: 8px;
    right: 8px;
    color: #3b82f6;
  }
}

.more-symbols {
  margin-top: 16px;
  
  :deep(.el-select) {
    width: 100%;
  }
}

.timeframe-tabs {
  display: flex;
  gap: 12px;
}

.timeframe-tab {
  flex: 1;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid transparent;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: rgba(255, 255, 255, 0.06);
  }
  
  &.active {
    background: rgba(59, 130, 246, 0.1);
    border-color: #3b82f6;
  }
  
  .tf-value {
    display: block;
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
  }
  
  .tf-desc {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
}
</style>
