<!--
  MarketDepth.vue - 市场深度透视组件
  =================================
  可视化展示订单簿深度、多空挂单比和主力买卖墙
-->
<template>
  <el-card class="market-depth-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="title-left">
          <el-icon><DataLine /></el-icon>
          <span>市场深度透视</span>
        </div>
        <el-tag :type="biasType" size="small" effect="dark" class="animate-pulse">
          {{ biasLabel }} (实时)
        </el-tag>
      </div>
    </template>

    <div class="depth-content" v-if="orderBook && orderBook.major_support">
      <!-- 1. 多空力量对比 (仪表盘) -->
      <div class="ratio-section">
        <div class="ratio-label">
          <span>买盘 (Bids)</span>
          <span>卖盘 (Asks)</span>
        </div>
        <el-progress 
          :percentage="bidPercentage" 
          :stroke-width="16" 
          :show-text="false"
          class="ratio-bar"
        >
          <template #default>
            <div class="ratio-marker" :style="{ left: bidPercentage + '%' }"></div>
          </template>
        </el-progress>
        <div class="ratio-values">
          <span class="bid-vol font-tabular text-[#10b981]">{{ (orderBook.total_bid_volume || 0).toFixed(2) }}</span>
          <span class="ratio-text">多空比 {{ orderBook.bid_ask_ratio }}</span>
          <span class="ask-vol font-tabular text-[#ef4444]">{{ (orderBook.total_ask_volume || 0).toFixed(2) }}</span>
        </div>
      </div>

      <!-- 2. 主力买卖墙 -->
      <div class="walls-section">
        <!-- 阻力墙 (卖) -->
        <div class="wall-item resistance">
          <div class="wall-header">
            <span class="label">上方阻力墙</span>
            <span class="price font-tabular">{{ formatPrice(orderBook.major_resistance?.price) }}</span>
          </div>
          <div class="wall-bar-container">
            <div 
              class="wall-bar" 
              :style="{ width: getVolumePercentage(orderBook.major_resistance?.volume) + '%' }"
            ></div>
            <span class="volume font-tabular">{{ (orderBook.major_resistance?.volume || 0).toFixed(2) }}</span>
          </div>
        </div>

        <!-- 支撑墙 (买) -->
        <div class="wall-item support">
          <div class="wall-header">
            <span class="label">下方支撑墙</span>
            <span class="price font-tabular">{{ formatPrice(orderBook.major_support?.price) }}</span>
          </div>
          <div class="wall-bar-container">
            <div 
              class="wall-bar" 
              :style="{ width: getVolumePercentage(orderBook.major_support?.volume) + '%' }"
            ></div>
            <span class="volume font-tabular">{{ (orderBook.major_support?.volume || 0).toFixed(2) }}</span>
          </div>
        </div>
      </div>
      
      <!-- 说明 -->
      <div class="depth-footer">
        <el-icon><InfoFilled /></el-icon>
        <span>基于 Binance 实时 20 档盘口计算</span>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <div class="loading-placeholder">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载深度数据...</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { DataLine, InfoFilled, Loading } from '@element-plus/icons-vue'
import { useMarketStore } from '@/stores/market'

const marketStore = useMarketStore()


const orderBook = computed(() => marketStore.marketContext?.order_book)

// 计算多头占比 (用于进度条)
// 计算多头占比 (用于进度条)
const bidPercentage = computed(() => {
  const book = orderBook.value
  if (!book) return 50
  const total = book.total_bid_volume + book.total_ask_volume
  if (total === 0) return 50
  return (book.total_bid_volume / total) * 100
})

// 计算最大量百分比 (用于条形图归一化)
// 计算最大量百分比 (用于条形图归一化)
const maxVolume = computed(() => {
  const book = orderBook.value
  if (!book) return 100
  const supportVol = book.major_support?.volume || 0
  const resistanceVol = book.major_resistance?.volume || 0
  return Math.max(supportVol, resistanceVol) * 1.2
})

const getVolumePercentage = (vol: number | undefined) => {
  if (!vol) return 0
  return (vol / maxVolume.value) * 100
}

const biasType = computed(() => {
  const book = orderBook.value
  if (!book) return 'info'
  if (book.bid_ask_ratio > 1.2) return 'success'
  if (book.bid_ask_ratio < 0.8) return 'danger'
  return 'info'
})

const biasLabel = computed(() => {
  const book = orderBook.value
  if (!book) return '中性'
  if (book.bid_ask_ratio > 1.5) return '多头主导'
  if (book.bid_ask_ratio > 1.1) return '多头占优'
  if (book.bid_ask_ratio < 0.5) return '空头主导'
  if (book.bid_ask_ratio < 0.9) return '空头占优'
  return '中性博弈'
})

function formatPrice(price: any): string {
  if (price === undefined || price === null) return '---'
  if (typeof price !== 'number') return '---'
  if (isNaN(price)) return '---'
  
  if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2 })
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}

// 轮询控制
onMounted(() => {
  marketStore.startDepthPolling()
})

onUnmounted(() => {
  marketStore.stopDepthPolling()
})

// 监听交易对切换，重启轮询
watch(() => marketStore.currentSymbol, () => {
    marketStore.startDepthPolling()
})
</script>

<style lang="scss" scoped>
.market-depth-card {
  background: rgba(30, 41, 59, 0.4);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  min-height: 380px;
  display: flex;
  flex-direction: column;
  
  :deep(.el-card__header) {
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  }
  :deep(.el-card__body) {
    padding: 12px 16px;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .title-left {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #fff;
  }
}

.depth-content {
  padding: 16px 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.ratio-section {
  margin-bottom: 24px;
  
  .ratio-label {
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 6px;
  }
  
  .ratio-bar {
    :deep(.el-progress-bar__outer) {
      background-color: #ef4444; // 卖盘背景 (右侧)
      border-radius: 4px;
    }
    :deep(.el-progress-bar__inner) {
      background-color: #10b981; // 买盘 (左侧)
      border-radius: 4px;
    }
  }
  
  .ratio-values {
    display: flex;
    justify-content: space-between;
    margin-top: 6px;
    font-size: 15px;
    font-weight: 600;
    
    .bid-vol { color: #10b981; }
    .ask-vol { color: #ef4444; }
    .ratio-text { font-size: 13px; color: rgba(255, 255, 255, 0.4); font-weight: 400; }
  }
}

.walls-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;
}

.wall-item {
  &.resistance {
    .wall-bar { background: rgba(239, 68, 68, 0.3); border-right: 2px solid #ef4444; }
    .price { color: #ef4444; }
  }
  
  &.support {
    .wall-bar { background: rgba(16, 185, 129, 0.3); border-right: 2px solid #10b981; }
    .price { color: #10b981; }
  }
  
  .wall-header {
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    margin-bottom: 4px;
    
    .label { color: rgba(255, 255, 255, 0.6); }
    .price { font-weight: 600; }
  }
  
  .wall-bar-container {
    position: relative;
    height: 24px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    overflow: hidden;
    display: flex;
    align-items: center;
    padding: 0 8px;
    
    .wall-bar {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      transition: width 0.5s ease;
    }
    
    .volume {
      position: relative;
      z-index: 1;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.8);
    }
  }
}

.depth-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.3);
  margin-top: 12px;
}

.loading-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: rgba(255, 255, 255, 0.4);
  gap: 8px;
  font-size: 13px;
  
  .el-icon {
    font-size: 20px;
  }
}
</style>
