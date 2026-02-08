<!--
  智链预测 - AI预测卡片组件
  ===========================
  展示DeepSeek AI的预测分析结果
  
  功能：
  1. 可视化展示预测方向（看涨/看跌/震荡）
  2. 进度条显示置信度
  3. 折叠面板展示详细逻辑链和风险警告
  4. 一键生成交易策略按钮
  
  Author: 智链预测团队
  Version: 1.0.0
-->

<template>
  <el-card class="ai-prediction-card" :class="predictionClass" shadow="hover">
    <!-- 卡片头部 -->
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span class="symbol-badge font-display">{{ prediction.symbol }}</span>
          <span class="timeframe font-tabular">{{ prediction.timeframe }}</span>
          <div class="trend-resonance" v-if="prediction.trend_context">
            <el-tooltip :content="`趋势周期(${prediction.trend_context.summary})`" placement="top">
              <el-tag :type="resonanceType" size="small" effect="plain" class="resonance-tag">
                <el-icon><DataAnalysis /></el-icon>
                <span class="font-display">{{ resonanceLabel }}</span>
              </el-tag>
            </el-tooltip>
          </div>
        </div>
        <div class="header-right">
          <el-tag :type="riskTagType" size="small" effect="dark">
            <span class="font-display">风险{{ prediction.risk_level }}</span>
          </el-tag>
          <span class="analysis-time font-tabular">{{ formattedTime }}</span>
        </div>
      </div>
    </template>

    <!-- 核心预测区域 -->
    <div class="prediction-main">
      <!-- 预测方向指示器 -->
      <div class="direction-indicator">
        <div class="direction-icon" :class="directionIconClass">
          <el-icon :size="48">
            <component :is="directionIcon" />
          </el-icon>
        </div>
        <div class="direction-text">
          <span class="direction-label font-display">预测方向</span>
          <span class="direction-value font-display" :class="predictionClass">
            {{ prediction.prediction }}
          </span>
        </div>
      </div>

      <!-- 置信度进度条 -->
      <div class="confidence-section">
        <div class="confidence-header">
          <span class="confidence-label font-display">置信度</span>
          <span class="confidence-value font-tabular" :class="confidenceClass">
            {{ prediction.confidence }}%
          </span>
        </div>
        <el-progress
          :percentage="prediction.confidence"
          :stroke-width="12"
          :color="confidenceColors"
          :format="() => ''"
          class="confidence-bar"
        />
        <div class="confidence-scale font-display">
          <span>保守</span>
          <span>中性</span>
          <span>激进</span>
        </div>
      </div>

      <!-- 关键价位展示 -->
      <div class="key-levels">
        <div class="levels-title font-display">
          <el-icon><TrendCharts /></el-icon>
          <span>关键价位</span>
        </div>
        <div class="levels-list">
          <div class="level-group resistance">
            <span class="group-label font-display">阻力位</span>
            <div class="level-tags">
              <span v-for="price in resistances" :key="price" class="level-tag resistance font-tabular">
                {{ formatPrice(price) }}
              </span>
              <span v-if="!resistances.length" class="level-tag empty font-tabular">-</span>
            </div>
          </div>
          
          <div class="level-group current">
            <span class="group-label font-display">当前价</span>
            <div class="level-tags">
              <span class="level-tag current font-tabular">{{ formatPrice(prediction.key_levels?.current_price) }}</span>
            </div>
          </div>
          
          <div class="level-group support">
            <span class="group-label font-display">支撑位</span>
            <div class="level-tags">
              <span v-for="price in supports" :key="price" class="level-tag support font-tabular">
                {{ formatPrice(price) }}
              </span>
              <span v-if="!supports.length" class="level-tag empty font-tabular">-</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- AI 配置信息 (新增) -->
    <div class="ai-config-info" v-if="prediction.ai_model">
      <div class="config-item font-sans">
        <el-icon><Cpu /></el-icon>
        <span>模型: {{ prediction.ai_model }}</span>
      </div>
      <div class="config-item font-sans">
        <el-icon><Tickets /></el-icon>
        <span>模板: {{ prediction.ai_prompt_template || '系统默认' }}</span>
      </div>
    </div>

    <!-- 分析摘要 -->
    <div class="summary-section">
      <el-icon class="summary-icon"><Document /></el-icon>
      <p class="summary-text font-sans leading-relaxed text-slate-300">{{ prediction.summary }}</p>
    </div>

    <!-- 交易信号 (新增) -->
    <div class="trading-signals" v-if="prediction.trading_signals?.length">
      <div class="signal-card" v-for="(signal, idx) in prediction.trading_signals" :key="idx">
        <div class="signal-header">
          <span class="signal-type font-display" :class="signal.type.toLowerCase()">{{ signal.type }}</span>
          <span class="signal-risk font-tabular">R:R {{ signal.risk_reward_ratio || '-' }}</span>
        </div>
        <div class="signal-details font-tabular">
          <div class="signal-row">
            <span>入场: {{ formatPrice(signal.entry) }}</span>
            <span>止损: {{ formatPrice(signal.stop_loss) }}</span>
          </div>
          <div class="signal-row">
            <span>止盈: {{ signal.take_profit?.map((p: any) => formatPrice(p)).join(', ') || '-' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 折叠面板：详细分析 -->
    <el-collapse v-model="activeCollapse" class="detail-collapse font-sans">
      <!-- 逻辑推理链 -->
      <el-collapse-item name="reasoning" class="reasoning-panel">
        <template #title>
          <div class="collapse-title font-display">
            <el-icon><Compass /></el-icon>
            <span>分析逻辑链</span>
          </div>
        </template>
        
        <!-- 新版Reasoning Object -->
        <div v-if="isReasoningObject(prediction.reasoning)" class="reasoning-grid">
          <div class="reasoning-block">
            <h4 class="font-display">技术面</h4>
            <p class="font-sans leading-relaxed">{{ prediction.reasoning.technical }}</p>
          </div>
          <div class="reasoning-block">
            <h4 class="font-display">情绪面</h4>
            <p class="font-sans leading-relaxed">{{ prediction.reasoning.sentiment }}</p>
          </div>
          <div class="reasoning-block">
            <h4 class="font-display">宏观面</h4>
            <p class="font-sans leading-relaxed">{{ prediction.reasoning.macro }}</p>
          </div>
        </div>
        
        <!-- 旧版Reasoning List -->
        <ul v-else class="reasoning-list">
          <li
            v-for="(reason, index) in prediction.reasoning"
            :key="index"
            class="reasoning-item"
          >
            <span class="reason-number font-tabular">{{ Number(index) + 1 }}</span>
            <span class="reason-text font-sans">{{ reason }}</span>
          </li>
        </ul>
      </el-collapse-item>

      <!-- 风险警告 -->
      <el-collapse-item name="risk" class="risk-panel">
        <template #title>
          <div class="collapse-title font-display">
            <el-icon><Warning /></el-icon>
            <span>风险警告</span>
            <el-tag size="small" type="danger" class="font-tabular">{{ riskFactors.length }}项</el-tag>
          </div>
        </template>
        <ul class="risk-list">
          <li
            v-for="(warning, index) in riskFactors"
            :key="index"
            class="risk-item"
          >
            <el-icon class="risk-icon"><WarningFilled /></el-icon>
            <span class="risk-text font-sans leading-relaxed">{{ warning }}</span>
          </li>
        </ul>
      </el-collapse-item>

      <!-- 策略建议 -->
      <el-collapse-item name="strategy" class="strategy-panel" v-if="prediction.entry_zone">
        <template #title>
          <div class="collapse-title font-display">
            <el-icon><Aim /></el-icon>
            <span>策略建议</span>
          </div>
        </template>
        <div class="strategy-content font-tabular">
          <div class="strategy-row">
            <span class="strategy-label font-display">建议操作：</span>
            <span class="strategy-value action font-display">{{ prediction.suggested_action }}</span>
          </div>
          <div class="strategy-row" v-if="prediction.entry_zone">
            <span class="strategy-label font-display">入场区间：</span>
            <span class="strategy-value">
              {{ formatPrice(prediction.entry_zone.low) }} - {{ formatPrice(prediction.entry_zone.high) }}
            </span>
          </div>
          <div class="strategy-row" v-if="prediction.stop_loss">
            <span class="strategy-label font-display">止损价位：</span>
            <span class="strategy-value stop-loss">{{ formatPrice(prediction.stop_loss) }}</span>
          </div>
          <div class="strategy-row" v-if="prediction.take_profit?.length">
            <span class="strategy-label font-display">止盈目标：</span>
            <span class="strategy-value take-profit">
              <span v-for="(tp, i) in prediction.take_profit" :key="i" class="tp-item">
                {{ getTPLabel(i) }}: {{ formatPrice(tp) }}
              </span>
            </span>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 操作按钮区域 -->
    <div class="action-buttons">
      <el-button
        type="primary"
        size="large"
        :loading="generatingStrategy"
        @click="handleGenerateStrategy"
        class="generate-btn font-display"
      >
        <el-icon><MagicStick /></el-icon>
        <span>据此生成策略</span>
      </el-button>
      <el-button size="large" @click="handleRefresh" :loading="refreshing" class="font-display">
        <el-icon><Refresh /></el-icon>
        <span>刷新分析</span>
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  TrendCharts,
  Document,
  Compass,
  Warning,
  WarningFilled,
  Aim,
  MagicStick,
  Refresh,
  Top,
  Bottom,
  Sort,
  Cpu,
  Tickets
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

// ============================================================
// 类型定义
// ============================================================

import type { PredictionResult } from '@/services/api'

// ============================================================
// Props 定义
// ============================================================

const props = defineProps(['prediction'])

// ============================================================
// Emits 定义
// ============================================================

const emit = defineEmits<{
  /**
   * 生成策略事件
   * @param prediction 当前预测结果
   */
  (e: 'generate-strategy', prediction: PredictionResult): void
  
  /**
   * 刷新分析事件
   * @param symbol 交易对符号
   */
  (e: 'refresh', symbol: string): void
}>()

// ============================================================
// 响应式状态
// ============================================================

/** 展开的折叠面板 */
const activeCollapse = ref<string[]>(['reasoning'])

/** 策略生成加载状态 */
const generatingStrategy = ref(false)

/** 刷新加载状态 */
const refreshing = ref(false)

// ============================================================
// 计算属性
// ============================================================

/** 阻力位列表 */
const resistances = computed(() => {
  if (props.prediction.key_levels?.resistances) {
    return props.prediction.key_levels.resistances
  }
  // 兼容旧格式
  const list = []
  if (props.prediction.key_levels?.strong_resistance) list.push(props.prediction.key_levels.strong_resistance)
  if (props.prediction.key_levels?.weak_resistance) list.push(props.prediction.key_levels.weak_resistance)
  return list.sort((a, b) => b - a)
})

/** 支撑位列表 */
const supports = computed(() => {
  if (props.prediction.key_levels?.supports) {
    return props.prediction.key_levels.supports
  }
  // 兼容旧格式
  const list = []
  if (props.prediction.key_levels?.strong_support) list.push(props.prediction.key_levels.strong_support)
  if (props.prediction.key_levels?.weak_support) list.push(props.prediction.key_levels.weak_support)
  return list.sort((a, b) => b - a)
})

/** 风险因素 */
const riskFactors = computed(() => {
  if (props.prediction.reasoning && typeof props.prediction.reasoning === 'object' && !Array.isArray(props.prediction.reasoning)) {
    return props.prediction.reasoning.risk_factors || props.prediction.risk_warning || []
  }
  return props.prediction.risk_warning || []
})

/**
 * 格式化分析时间
 */
const formattedTime = computed(() => {
  if (!props.prediction.analysis_time) return ''
  return dayjs(props.prediction.analysis_time).format('MM-DD HH:mm')
})

/**
 * 预测方向对应的CSS类
 */
const predictionClass = computed(() => {
  const direction = props.prediction.prediction
  if (direction === '看涨' || direction.toLowerCase() === 'bullish' || direction === 'strong_bullish') {
    return 'bullish'
  } else if (direction === '看跌' || direction.toLowerCase() === 'bearish' || direction === 'strong_bearish') {
    return 'bearish'
  }
  return 'neutral'
})

/**
 * 方向图标组件
 */
const directionIcon = computed(() => {
  const direction = props.prediction.prediction
  if (direction === '看涨' || direction.toLowerCase() === 'bullish' || direction === 'strong_bullish') {
    return Top
  } else if (direction === '看跌' || direction.toLowerCase() === 'bearish' || direction === 'strong_bearish') {
    return Bottom
  }
  return Sort
})

/**
 * 方向图标CSS类
 */
const directionIconClass = computed(() => {
  return predictionClass.value
})

/**
 * 置信度对应的CSS类
 */
const confidenceClass = computed(() => {
  const confidence = props.prediction.confidence
  if (confidence >= 80) return 'high'
  if (confidence >= 60) return 'medium'
  return 'low'
})

/**
 * 置信度进度条颜色配置
 */
const confidenceColors = [
  { color: '#909399', percentage: 40 },
  { color: '#E6A23C', percentage: 60 },
  { color: '#67C23A', percentage: 80 },
  { color: '#409EFF', percentage: 100 }
]

/**
 * 风险标签类型
 */
const riskTagType = computed(() => {
  const level = props.prediction.risk_level
  if (level === '低') return 'success'
  if (level === '中') return 'warning'
  if (level === '高') return 'danger'
  return 'danger' // 极高
})

// ============================================================
// 方法
// ============================================================

function isReasoningObject(reasoning: any): boolean {
  return typeof reasoning === 'object' && !Array.isArray(reasoning)
}

/** 共振状态计算 */
const resonanceType = computed(() => {
  if (!props.prediction.trend_context) return 'info'
  const current = props.prediction.prediction
  const trend = props.prediction.trend_context.trend_status
  
  const isCurrentBull = current.includes('涨') || current.includes('bullish')
  const isTrendBull = trend.includes('bullish')
  
  if (isCurrentBull && isTrendBull) return 'success' // 双多
  if (!isCurrentBull && !isTrendBull) return 'danger' // 双空
  return 'warning' // 背离
})

const resonanceLabel = computed(() => {
  if (!props.prediction.trend_context) return ''
  const type = resonanceType.value
  if (type === 'success') return '多头共振'
  if (type === 'danger') return '空头共振'
  return '趋势背离'
})

// ============================================================
// 方法
// ============================================================

/** 获取止盈标签 */
const getTPLabel = (i: number | string) => `TP${Number(i) + 1}`

/**
 * 格式化价格显示
 * @param price 价格数值
 * @returns 格式化后的价格字符串
 */
function formatPrice(price: number | undefined): string {
  if (price === undefined || price === null) return '-'
  
  // 根据价格大小决定小数位数
  if (price >= 1000) {
    return price.toLocaleString('zh-CN', { 
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })
  } else if (price >= 1) {
    return price.toFixed(4)
  } else {
    return price.toFixed(6)
  }
}

/**
 * 处理生成策略按钮点击
 */
async function handleGenerateStrategy() {
  generatingStrategy.value = true
  
  try {
    // 确认对话框
    await ElMessageBox.confirm(
      `将基于当前分析结果生成 ${props.prediction.symbol} 的交易策略，是否继续？`,
      '生成交易策略',
      {
        confirmButtonText: '确认生成',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    // 触发生成策略事件
    emit('generate-strategy', props.prediction)
    
    // 模拟策略生成过程
    await simulateStrategyGeneration()
    
    ElMessage.success('策略生成成功！')
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('策略生成失败，请稍后重试')
      console.error('策略生成错误:', error)
    }
  } finally {
    generatingStrategy.value = false
  }
}

/**
 * 模拟策略生成过程
 * 实际项目中应替换为真实API调用
 */
async function simulateStrategyGeneration(): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, 1500)
  })
}

/**
 * 处理刷新分析按钮点击
 */
async function handleRefresh() {
  refreshing.value = true
  
  try {
    emit('refresh', props.prediction.symbol)
    
    // 模拟刷新延迟
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('分析已刷新')
  } catch (error) {
    ElMessage.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

// ============================================================
// 卡片主体样式
// ============================================================

.ai-prediction-card {
  background: $bg-surface-2;
  backdrop-filter: blur($blur-md);
  border: 1px solid $border-default;
  border-radius: $radius-lg;
  overflow: hidden;
  transition: all $transition-normal;
  position: relative;

  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-lg;
  }

  // 根据预测方向添加顶部边框高亮
  &.bullish {
    border-top: 3px solid $color-bullish;
    
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 100px;
      background: linear-gradient(180deg, rgba($color-bullish, 0.1) 0%, transparent 100%);
      pointer-events: none;
    }
  }

  &.bearish {
    border-top: 3px solid $color-danger;
    
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 100px;
      background: linear-gradient(180deg, rgba($color-danger, 0.1) 0%, transparent 100%);
      pointer-events: none;
    }
  }

  &.neutral {
    border-top: 3px solid $color-neutral;
  }

  :deep(.el-card__header) {
    background: $bg-glass;
    border-bottom: 1px solid $border-subtle;
    padding: $spacing-md $spacing-lg;
  }

  :deep(.el-card__body) {
    padding: $spacing-lg;
  }
}

// ============================================================
// 卡片头部
// ============================================================

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;

  .symbol-badge {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    background: linear-gradient(135deg, $color-primary 0%, #8b5cf6 100%);
    padding: 4px 12px;
    border-radius: 6px;
  }

  .timeframe {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;

  .analysis-time {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
}

// ============================================================
// 核心预测区域
// ============================================================

.prediction-main {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 24px;
  margin-bottom: 20px;
}

// 方向指示器
.direction-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 24px;

  .direction-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
    transition: all 0.3s ease;

    &.bullish {
      background: rgba($color-bullish, 0.15);
      color: $color-bullish;
      box-shadow: 0 0 30px rgba($color-bullish, 0.3);
    }

    &.bearish {
      background: rgba($color-bearish, 0.15);
      color: $color-bearish;
      box-shadow: 0 0 30px rgba($color-bearish, 0.3);
    }

    &.neutral {
      background: rgba($color-neutral, 0.15);
      color: $color-neutral;
    }
  }

  .direction-text {
    text-align: center;

    .direction-label {
      display: block;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 4px;
    }

    .direction-value {
      font-size: 24px;
      font-weight: 700;

      &.bullish { color: $color-bullish; }
      &.bearish { color: $color-bearish; }
      &.neutral { color: $color-neutral; }
    }
  }
}

// 置信度区域
.confidence-section {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 20px;

  .confidence-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .confidence-label {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.6);
    }

    .confidence-value {
      font-size: 28px;
      font-weight: 700;

      &.high { color: $color-primary; }
      &.medium { color: #f59e0b; }
      &.low { color: $color-neutral; }
    }
  }

  .confidence-bar {
    margin-bottom: 8px;

    :deep(.el-progress-bar__outer) {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 6px;
    }

    :deep(.el-progress-bar__inner) {
      border-radius: 6px;
    }
  }

  .confidence-scale {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
  }
}

// 关键价位
.key-levels {
  grid-column: 1 / -1;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 16px 20px;

  .levels-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 16px;
  }

  .levels-grid {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }

  .level-item {
    flex: 1;
    text-align: center;
    padding: 12px 8px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.03);

    .level-label {
      display: block;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 4px;
    }

    .level-value {
      font-size: 14px;
      font-weight: 600;
      color: #fff;
    }

    &.resistance {
      border-top: 2px solid $color-bearish;
      .level-value { color: $color-bearish; }

      &.weak {
        border-top-color: rgba($color-bearish, 0.5);
        .level-value { color: rgba($color-bearish, 0.8); }
      }
    }

    &.support {
      border-top: 2px solid $color-bullish;
      .level-value { color: $color-bullish; }

      &.weak {
        border-top-color: rgba($color-bullish, 0.5);
        .level-value { color: rgba($color-bullish, 0.8); }
      }
    }

    &.current {
      border-top: 2px solid $color-primary;
      background: rgba($color-primary, 0.1);
      .level-value { color: #fff; font-weight: 700; }
    }
  }
}

// ============================================================
// 摘要区域
// ============================================================

.summary-section {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  margin-bottom: 16px;

  .summary-icon {
    flex-shrink: 0;
    color: $color-primary;
    font-size: 20px;
  }

  .summary-text {
    font-size: 14px;
    line-height: 1.6;
    color: rgba(255, 255, 255, 0.85);
    margin: 0;
  }
}

// ============================================================
// 折叠面板
// ============================================================

.detail-collapse {
  border: none;
  background: transparent;

  :deep(.el-collapse-item) {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 10px;
    margin-bottom: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    overflow: hidden;
  }

  :deep(.el-collapse-item__header) {
    background: transparent;
    border-bottom: none;
    padding: 12px 16px;
    color: rgba(255, 255, 255, 0.8);
    font-size: 14px;
  }

  :deep(.el-collapse-item__content) {
    padding: 0 16px 16px;
    color: rgba(255, 255, 255, 0.7);
  }
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;

  .el-tag {
    margin-left: auto;
  }
}

// 逻辑推理列表
.reasoning-list {
  margin: 0;
  padding: 0;
  list-style: none;

  .reasoning-item {
    display: flex;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    &:last-child {
      border-bottom: none;
    }

    .reason-number {
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      background: $color-primary;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 600;
      color: #fff;
    }

    .reason-text {
      font-size: 13px;
      line-height: 1.5;
    }
  }
}

// 风险警告列表
.risk-list {
  margin: 0;
  padding: 0;
  list-style: none;

  .risk-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 12px;
    background: rgba($color-bearish, 0.1);
    border-radius: 6px;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }

    .risk-icon {
      flex-shrink: 0;
      color: $color-bearish;
      margin-top: 2px;
    }

    .risk-text {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.8);
    }
  }
}

// 策略内容
.strategy-content {
  .strategy-row {
    display: flex;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    &:last-child {
      border-bottom: none;
    }

    .strategy-label {
      width: 100px;
      flex-shrink: 0;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.5);
    }

    .strategy-value {
      font-size: 14px;
      font-weight: 500;

      &.action {
        color: $color-primary;
      }

      &.stop-loss {
        color: $color-bearish;
      }

      &.take-profit {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;

        .tp-item {
          color: $color-bullish;
          background: rgba($color-bullish, 0.1);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
        }
      }
    }
  }
}

// ============================================================
// 操作按钮
// ============================================================

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);

  .generate-btn {
    flex: 1;
    background: linear-gradient(135deg, $color-primary 0%, #8b5cf6 100%);
    border: none;
    font-weight: 600;

    &:hover {
      background: linear-gradient(135deg, lighten($color-primary, 5%) 0%, lighten(#8b5cf6, 5%) 100%);
    }
  }

  .el-button {
    height: 48px;
    border-radius: 10px;
  }
}

// ============================================================
// 响应式适配
// ============================================================

@media (max-width: 768px) {
  .prediction-main {
    grid-template-columns: 1fr;
  }

  .levels-grid {
    flex-wrap: wrap;

    .level-item {
      flex: 0 0 calc(50% - 6px);
    }
  }

  .action-buttons {
    flex-direction: column;
  }
}

// AI 配置信息 (新增)
.ai-config-info {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border: 1px dashed rgba(255, 255, 255, 0.1);

  .config-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);

    .el-icon {
      font-size: 13px;
      color: $color-primary;
    }
  }
}
</style>
