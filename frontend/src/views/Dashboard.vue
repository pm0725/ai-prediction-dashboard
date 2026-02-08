<!--
  智链预测 - 仪表盘页面 v2.0
  Premium Glassmorphism Design
-->
<template>
  <div class="dashboard">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
    </div>

    <!-- Hero Section -->
    <section class="hero-section">
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge-icon">🤖</span>
          <span>AI Powered Trading</span>
        </div>
        <h1 class="hero-title">
          <span class="gradient-text">智链预测</span>
        </h1>
        <p class="hero-subtitle">
          基于 DeepSeek 大模型的专业加密货币合约分析平台
        </p>
        <div class="hero-actions">
          <button class="glow-button primary" @click="goToAnalysis">
            <el-icon><MagicStick /></el-icon>
            <span>开始 AI 分析</span>
          </button>
          <button class="glow-button secondary" @click="handleBatchScan" :disabled="marketStore.loading.batch">
            <el-icon v-if="!marketStore.loading.batch"><Aim /></el-icon>
            <el-icon v-else class="animate-spin"><Loading /></el-icon>
            <span>{{ marketStore.loading.batch ? '扫描中...' : '全场扫描' }}</span>
          </button>
        </div>
      </div>
      <div class="hero-visual">
        <div class="stats-ring">
          <div class="ring-content">
            <span class="ring-value">{{ Object.keys(marketStore.batchResults).length }}</span>
            <span class="ring-label">已分析</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 扫描统计 -->
    <transition name="slide-fade">
      <section v-if="Object.keys(marketStore.batchResults).length > 0" class="stats-section">
        <div class="stat-card bullish">
          <div class="stat-icon">📈</div>
          <div class="stat-info">
            <span class="stat-value">{{ bullishCount }}</span>
            <span class="stat-label">看涨信号</span>
          </div>
        </div>
        <div class="stat-card bearish">
          <div class="stat-icon">📉</div>
          <div class="stat-info">
            <span class="stat-value">{{ bearishCount }}</span>
            <span class="stat-label">看跌信号</span>
          </div>
        </div>
        <div class="stat-card neutral">
          <div class="stat-icon">📊</div>
          <div class="stat-info">
            <span class="stat-value">{{ neutralCount }}</span>
            <span class="stat-label">震荡观望</span>
          </div>
        </div>
      </section>
    </transition>

    <!-- 市场概览 -->
    <section class="market-section">
      <div class="section-header">
        <h2>
          <el-icon><TrendCharts /></el-icon>
          <span>市场概览</span>
        </h2>
        <button class="refresh-btn" @click="refreshMarket" :disabled="loading">
          <el-icon :class="{ 'animate-spin': loading }"><Refresh /></el-icon>
          <span>刷新</span>
        </button>
      </div>

      <div class="market-grid">
        <div
          v-for="symbol in topSymbols"
          :key="symbol.symbol"
          class="market-card"
          :class="getCardClass(symbol.symbol)"
          @click="selectAndAnalyze(symbol.symbol)"
        >
          <!-- 卡片发光边框 -->
          <div class="card-glow" :class="getGlowClass(symbol.symbol)"></div>
          
          <div class="card-content">
            <div class="card-header">
              <div class="symbol-info">
                <span class="symbol-name">{{ symbol.base }}</span>
                <span class="symbol-pair">/USDT</span>
              </div>
              <div class="price-change" :class="getChangePercent(symbol.symbol) >= 0 ? 'up' : 'down'">
                {{ getChangePercent(symbol.symbol) >= 0 ? '+' : '' }}{{ getChangePercent(symbol.symbol).toFixed(2) }}%
              </div>
            </div>

            <div class="card-price">
              <span class="price-value">{{ getDisplayPrice(symbol.symbol) }}</span>
            </div>

            <!-- AI 预测结果 -->
            <div v-if="marketStore.batchResults[symbol.symbol]" class="ai-result">
              <div class="result-direction" :class="getPredictionClass(marketStore.batchResults[symbol.symbol].prediction)">
                <span class="direction-icon">{{ getPredictionIcon(marketStore.batchResults[symbol.symbol].prediction) }}</span>
                <span class="direction-text">{{ marketStore.batchResults[symbol.symbol].prediction }}</span>
              </div>
              <div class="result-confidence">
                <div class="confidence-bar">
                  <div 
                    class="confidence-fill" 
                    :style="{ width: marketStore.batchResults[symbol.symbol].confidence + '%' }"
                    :class="getPredictionClass(marketStore.batchResults[symbol.symbol].prediction)"
                  ></div>
                </div>
                <span class="confidence-value">{{ marketStore.batchResults[symbol.symbol].confidence }}%</span>
              </div>
            </div>
            <div v-else class="ai-pending">
              <span class="pending-icon">⏳</span>
              <span>等待扫描</span>
            </div>

            <div class="card-action">
              <span>查看详情</span>
              <el-icon><Right /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 功能入口 -->
    <section class="features-section">
      <div class="section-header">
        <h2>
          <el-icon><Grid /></el-icon>
          <span>核心功能</span>
        </h2>
      </div>

      <div class="features-grid">
        <div class="feature-card" @click="goToAnalysis">
          <div class="feature-icon" style="--accent: #6366f1;">
            <el-icon :size="28"><MagicStick /></el-icon>
          </div>
          <h3>AI 预测分析</h3>
          <p>多维数据智能预测，提供概率性方向判断</p>
        </div>
        
        <div class="feature-card" @click="goToStrategy">
          <div class="feature-icon" style="--accent: #22c55e;">
            <el-icon :size="28"><Aim /></el-icon>
          </div>
          <h3>策略生成</h3>
          <p>自动生成入场点位、止盈止损建议</p>
        </div>
        
        <div class="feature-card" @click="goToBacktest">
          <div class="feature-icon" style="--accent: #f59e0b;">
            <el-icon :size="28"><DataLine /></el-icon>
          </div>
          <h3>策略回测</h3>
          <p>验证AI策略历史表现，获取胜率指标</p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon" style="--accent: #ef4444;">
            <el-icon :size="28"><Warning /></el-icon>
          </div>
          <h3>风险预警</h3>
          <p>实时监控市场异常，识别潜在风险</p>
        </div>
      </div>
    </section>

    <!-- 使用指南 -->
    <section class="guide-section">
      <div class="guide-card glass-card">
        <div class="guide-header">
          <el-icon><InfoFilled /></el-icon>
          <span>使用指南</span>
        </div>
        <div class="guide-steps">
          <div class="step" v-for="(step, index) in guideSteps" :key="index">
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-content">
              <h4>{{ step.title }}</h4>
              <p>{{ step.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  MagicStick,
  TrendCharts,
  Refresh,
  Grid,
  Aim,
  DataLine,
  Warning,
  InfoFilled,
  Right,
  Loading
} from '@element-plus/icons-vue'
import { useMarketStore } from '@/stores'

const router = useRouter()
const marketStore = useMarketStore()
const loading = ref(false)

const guideSteps = [
  { title: '选择交易对', desc: '在顶部选择要分析的交易对' },
  { title: '获取AI分析', desc: '点击AI分析获取预测结果' },
  { title: '生成策略', desc: '基于分析生成交易策略' },
  { title: '风险管理', desc: '严格执行止损，控制仓位' }
]

// 统计
const bullishCount = computed(() => {
  return Object.values(marketStore.batchResults).filter((r: any) => 
    r.prediction === '看涨' || r.prediction === 'bullish'
  ).length
})

const bearishCount = computed(() => {
  return Object.values(marketStore.batchResults).filter((r: any) => 
    r.prediction === '看跌' || r.prediction === 'bearish'
  ).length
})

const neutralCount = computed(() => {
  return Object.values(marketStore.batchResults).filter((r: any) => 
    r.prediction === '震荡' || r.prediction === 'neutral'
  ).length
})

const topSymbols = computed(() => marketStore.symbols)

function getDisplayPrice(symbol: string): string {
  const ticker = marketStore.tickers[symbol]
  if (!ticker) return '-'
  return ticker.price.toLocaleString('en-US', { 
    style: 'currency', 
    currency: 'USD',
    minimumFractionDigits: 2
  })
}

function getChangePercent(symbol: string): number {
  const ticker = marketStore.tickers[symbol]
  return ticker ? ticker.change_percent : 0
}

function getCardClass(symbol: string) {
  const result = marketStore.batchResults[symbol]
  if (!result) return ''
  if (result.prediction === '看涨' || result.prediction === 'bullish') return 'bullish'
  if (result.prediction === '看跌' || result.prediction === 'bearish') return 'bearish'
  return 'neutral'
}

function getGlowClass(symbol: string) {
  return getCardClass(symbol)
}

function getPredictionClass(prediction: string) {
  if (prediction === '看涨' || prediction === 'bullish') return 'bullish'
  if (prediction === '看跌' || prediction === 'bearish') return 'bearish'
  return 'neutral'
}

function getPredictionIcon(prediction: string) {
  if (prediction === '看涨' || prediction === 'bullish') return '↗'
  if (prediction === '看跌' || prediction === 'bearish') return '↘'
  return '→'
}

async function refreshMarket() {
  loading.value = true
  await Promise.all([
    marketStore.loadSymbols(),
    marketStore.loadAllTickers()
  ])
  loading.value = false
}

const handleBatchScan = async () => {
  try {
    ElMessage.info('正在启动全场 AI 扫描...')
    await marketStore.runBatchScanner()
    ElMessage.success('全场扫描完成')
  } catch (e) {
    ElMessage.error('扫描失败')
  }
}

function selectAndAnalyze(symbol: string) {
  marketStore.selectSymbol(symbol)
  router.push('/analysis')
}

function goToAnalysis() { router.push('/analysis') }
function goToStrategy() { router.push('/strategy') }
function goToBacktest() { router.push('/backtest') }

onMounted(async () => {
  if (marketStore.symbols.length === 0) {
    await marketStore.loadSymbols()
  }
  marketStore.loadAllTickers()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.dashboard {
  position: relative;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px 48px;
}

// 背景装饰
.bg-decoration {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: -1;
  overflow: hidden;
  
  .orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
  }
  
  .orb-1 {
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.3) 0%, transparent 70%);
    top: -200px;
    right: -100px;
  }
  
  .orb-2 {
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(168, 85, 247, 0.25) 0%, transparent 70%);
    top: 50%;
    left: -100px;
  }
  
  .orb-3 {
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(34, 197, 94, 0.2) 0%, transparent 70%);
    bottom: 10%;
    right: 10%;
  }
}

// Hero Section
.hero-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 48px;
  margin-bottom: 32px;
  background: $bg-surface-2;
  backdrop-filter: blur($blur-lg);
  border: 1px solid $border-default;
  border-radius: $radius-xl;
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.05) 100%);
    pointer-events: none;
  }
}

.hero-content {
  position: relative;
  z-index: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: $radius-full;
  font-size: 13px;
  color: $color-primary-light;
  margin-bottom: 16px;
  
  .badge-icon {
    font-size: 16px;
  }
}

.hero-title {
  font-size: 48px;
  font-weight: 800;
  margin-bottom: 12px;
  letter-spacing: -1px;
}

.hero-subtitle {
  font-size: 16px;
  color: $text-secondary;
  margin-bottom: 32px;
  max-width: 400px;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.glow-button {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 16px 32px;
  border: none;
  border-radius: $radius-md;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all $transition-normal;
  
  &.primary {
    background: $gradient-primary;
    color: white;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5);
    }
  }
  
  &.secondary {
    background: $bg-surface-3;
    color: $text-primary;
    border: 1px solid $border-default;
    
    &:hover {
      background: $bg-surface-2;
      border-color: $color-primary;
    }
    
    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
}

.hero-visual {
  position: relative;
  z-index: 1;
}

.stats-ring {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: conic-gradient(
    $color-success 0deg 120deg,
    $color-danger 120deg 200deg,
    $color-info 200deg 360deg
  );
  padding: 6px;
  animation: spin 20s linear infinite;
  
  .ring-content {
    width: 100%;
    height: 100%;
    background: $bg-base;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    animation: spin 20s linear infinite reverse;
    
    .ring-value {
      font-size: 36px;
      font-weight: 700;
      color: $text-primary;
    }
    
    .ring-label {
      font-size: 12px;
      color: $text-muted;
    }
  }
}

// 统计区域
.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: $bg-surface-2;
  backdrop-filter: blur($blur-md);
  border: 1px solid $border-default;
  border-radius: $radius-lg;
  transition: all $transition-normal;
  
  &.bullish {
    border-color: rgba($color-success, 0.3);
    .stat-value { color: $color-success; }
  }
  
  &.bearish {
    border-color: rgba($color-danger, 0.3);
    .stat-value { color: $color-danger; }
  }
  
  .stat-icon {
    font-size: 32px;
  }
  
  .stat-info {
    display: flex;
    flex-direction: column;
  }
  
  .stat-value {
    font-size: 28px;
    font-weight: 700;
  }
  
  .stat-label {
    font-size: 13px;
    color: $text-muted;
  }
}

// Section Header
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  
  h2 {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 20px;
    font-weight: 600;
    color: $text-primary;
  }
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: transparent;
  border: 1px solid $border-default;
  border-radius: $radius-md;
  color: $text-secondary;
  font-size: 14px;
  cursor: pointer;
  transition: all $transition-fast;
  
  &:hover {
    background: $bg-surface-3;
    border-color: $border-strong;
    color: $text-primary;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

// 市场网格
.market-section {
  margin-bottom: 48px;
}

.market-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  
  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.market-card {
  position: relative;
  background: $bg-surface-2;
  backdrop-filter: blur($blur-md);
  border: 1px solid $border-default;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-normal;
  overflow: hidden;
  
  &:hover {
    transform: translateY(-4px);
    border-color: $border-strong;
    
    .card-glow {
      opacity: 1;
    }
  }
  
  &.bullish {
    border-color: rgba($color-success, 0.4);
  }
  
  &.bearish {
    border-color: rgba($color-danger, 0.4);
  }
}

.card-glow {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity $transition-normal;
  pointer-events: none;
  
  &.bullish {
    background: radial-gradient(ellipse at top, rgba($color-success, 0.1) 0%, transparent 60%);
  }
  
  &.bearish {
    background: radial-gradient(ellipse at top, rgba($color-danger, 0.1) 0%, transparent 60%);
  }
}

.card-content {
  position: relative;
  padding: 20px;
  z-index: 1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.symbol-info {
  .symbol-name {
    font-size: 20px;
    font-weight: 700;
    color: $text-primary;
  }
  
  .symbol-pair {
    font-size: 14px;
    color: $text-muted;
  }
}

.price-change {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: $radius-sm;
  
  &.up {
    background: rgba($color-success, 0.15);
    color: $color-success;
  }
  
  &.down {
    background: rgba($color-danger, 0.15);
    color: $color-danger;
  }
}

.card-price {
  margin-bottom: 16px;
  
  .price-value {
    font-size: 28px;
    font-weight: 700;
    font-family: $font-mono;
    color: $text-primary;
  }
}

.ai-result {
  padding: 16px;
  background: $bg-glass;
  border-radius: $radius-md;
  margin-bottom: 16px;
}

.result-direction {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  
  .direction-icon {
    font-size: 20px;
    font-weight: bold;
  }
  
  .direction-text {
    font-size: 16px;
    font-weight: 600;
  }
  
  &.bullish {
    color: $color-success;
  }
  
  &.bearish {
    color: $color-danger;
  }
  
  &.neutral {
    color: $color-info;
  }
}

.result-confidence {
  display: flex;
  align-items: center;
  gap: 12px;
}

.confidence-bar {
  flex: 1;
  height: 6px;
  background: $bg-surface-3;
  border-radius: $radius-full;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: $radius-full;
  transition: width $transition-normal;
  
  &.bullish {
    background: $gradient-success;
  }
  
  &.bearish {
    background: $gradient-danger;
  }
  
  &.neutral {
    background: linear-gradient(90deg, $color-info, #94a3b8);
  }
}

.confidence-value {
  font-size: 14px;
  font-weight: 600;
  font-family: $font-mono;
  color: $text-secondary;
  min-width: 40px;
  text-align: right;
}

.ai-pending {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  background: $bg-glass;
  border-radius: $radius-md;
  border: 1px dashed $border-subtle;
  font-size: 13px;
  color: $text-muted;
  margin-bottom: 16px;
}

.card-action {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  font-size: 13px;
  color: $color-primary-light;
  transition: color $transition-fast;
}

// Features
.features-section {
  margin-bottom: 48px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  
  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.feature-card {
  padding: 28px;
  background: $bg-surface-2;
  backdrop-filter: blur($blur-md);
  border: 1px solid $border-default;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-normal;
  
  &:hover {
    transform: translateY(-4px);
    border-color: var(--accent);
    
    .feature-icon {
      box-shadow: 0 0 30px rgba(var(--accent), 0.3);
    }
  }
}

.feature-icon {
  width: 56px;
  height: 56px;
  border-radius: $radius-md;
  background: linear-gradient(135deg, var(--accent), rgba(var(--accent), 0.6));
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 20px;
  transition: box-shadow $transition-normal;
}

.feature-card h3 {
  font-size: 17px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 8px;
}

.feature-card p {
  font-size: 14px;
  color: $text-muted;
  line-height: 1.5;
}

// Guide
.guide-section {
  margin-bottom: 32px;
}

.guide-card {
  padding: 32px;
}

.guide-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 24px;
}

.guide-steps {
  display: flex;
  gap: 32px;
}

.step {
  flex: 1;
  display: flex;
  gap: 16px;
}

.step-number {
  width: 32px;
  height: 32px;
  background: $gradient-primary;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.step-content h4 {
  font-size: 15px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 4px;
}

.step-content p {
  font-size: 13px;
  color: $text-muted;
}

// Animations
.slide-fade-enter-active {
  transition: all 0.4s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.3s ease-in;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
