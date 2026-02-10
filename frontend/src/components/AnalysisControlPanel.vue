<!--
  智链预测 - AI预测参数控制面板
  ================================
  交易对选择、分析参数、策略模板、自动化设置
  
  技术栈: Vue 3 + TypeScript + Element Plus
-->
<template>
  <div class="analysis-control-panel h-full flex flex-col overflow-hidden">
    <!-- 面板头部 -->
    <div class="panel-header flex-shrink-0">
      <h3 class="panel-title">
        <el-icon><Setting /></el-icon>
        分析配置
      </h3>
      <div class="header-actions">
        <button class="action-btn save-btn" @click="handleManualSave" title="保存为默认配置">
          <el-icon><Select /></el-icon>
        </button>
        <button class="action-btn" @click="resetToDefaults" title="重置默认">
          <el-icon><RefreshRight /></el-icon>
        </button>
        <button class="action-btn" @click="exportSettings" title="导出配置">
          <el-icon><Download /></el-icon>
        </button>
      </div>
    </div>

    <!-- 可滚动区域 -->
    <div class="flex-1 overflow-y-auto custom-scroll p-4 pt-0">
      <!-- 折叠面板 -->
      <el-collapse v-model="activeCollapse" accordion>
        
        <!-- 1. 交易对选择模块 -->
        <el-collapse-item name="symbol">
          <template #title>
            <div class="collapse-title">
              <el-icon><Coin /></el-icon>
              <span>交易对选择</span>
              <el-tag size="small" type="info" class="current-value">{{ selectedSymbol }}</el-tag>
            </div>
          </template>
          
          <div class="collapse-content">
            <!-- 搜索+下拉选择 -->
            <div class="symbol-search">
              <el-select
                v-model="selectedSymbol"
                filterable
                placeholder="搜索交易对"
                class="symbol-select"
                @change="handleSymbolChange"
              >
                <el-option-group 
                  v-for="group in symbolGroups" 
                  :key="group.label" 
                  :label="group.label"
                >
                  <el-option
                    v-for="symbol in group.symbols"
                    :key="symbol.value"
                    :label="symbol.label"
                    :value="symbol.value"
                  >
                    <div class="symbol-option">
                      <span class="symbol-icon">{{ symbol.icon }}</span>
                      <span class="symbol-name">{{ symbol.label }}</span>
                      <span class="symbol-change" :class="symbol.change >= 0 ? 'up' : 'down'">
                        {{ symbol.change >= 0 ? '+' : '' }}{{ symbol.change }}%
                      </span>
                    </div>
                  </el-option>
                </el-option-group>
              </el-select>
            </div>

            <!-- 常用收藏 -->
            <div class="favorites-section">
              <div class="section-label">收藏列表</div>
              <div class="favorites-list">
                <div 
                  v-for="fav in favorites" 
                  :key="fav"
                  :class="['favorite-chip', { active: selectedSymbol === fav }]"
                  @click="selectSymbol(fav)"
                >
                  {{ fav }}
                  <el-icon class="remove-icon" @click.stop="removeFavorite(fav)">
                    <Close />
                  </el-icon>
                </div>
              </div>
            </div>

            <!-- 多交易对比模式 -->
            <div class="compare-mode">
              <label class="toggle-label">
                <span>多交易对比模式</span>
                <el-switch v-model="compareMode" size="small" />
              </label>
              <div v-if="compareMode" class="compare-symbols">
                <el-select
                  v-model="compareSymbols"
                  multiple
                  placeholder="选择对比交易对"
                  :max="3"
                >
                  <el-option
                    v-for="s in allSymbols.filter(x => x !== selectedSymbol)"
                    :key="s"
                    :label="s"
                    :value="s"
                  />
                </el-select>
              </div>
            </div>

            <!-- 交易对基本信息 -->
            <div class="symbol-info" v-if="currentSymbolInfo">
              <div class="info-item">
                <span class="info-label">24h涨跌</span>
                <span class="info-value" :class="currentSymbolInfo.change24h >= 0 ? 'up' : 'down'">
                  {{ currentSymbolInfo.change24h >= 0 ? '+' : '' }}{{ currentSymbolInfo.change24h }}%
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">24h成交量</span>
                <span class="info-value">{{ formatVolume(currentSymbolInfo.volume24h) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">当前价</span>
                <span class="info-value">{{ formatPrice(currentSymbolInfo.price) }}</span>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 2. 分析参数设置 -->
        <el-collapse-item name="params">
          <template #title>
            <div class="collapse-title">
              <el-icon><DataAnalysis /></el-icon>
              <span>分析参数</span>
            </div>
          </template>
          
          <div class="collapse-content">
            <!-- 周期选择 -->
            <div class="param-section">
              <div class="param-label">分析周期</div>
              <div class="depth-options">
                 <button 
                  v-for="opt in timeframeOptions" 
                  :key="opt.value"
                  :class="['depth-btn', { active: selectedTimeframe === opt.value }]"
                  @click="selectedTimeframe = opt.value"
                  style="height: 40px; padding: 0 12px; min-width: 60px;"
                >
                  <div class="depth-name" style="font-size: 14px; font-weight: 600;">{{ opt.label }}</div>
                </button>
              </div>
            </div>

            <!-- AI分析深度 -->
            <div class="param-section">
              <div class="param-label">AI分析深度</div>
              <div class="depth-options">
                <button 
                  v-for="opt in depthOptions" 
                  :key="opt.value"
                  :class="['depth-btn', { active: analysisDepth === opt.value }]"
                  @click="analysisDepth = opt.value"
                >
                  <div class="depth-icon" style="font-size: 1.5rem;">{{ opt.icon }}</div>
                  <div class="depth-name" style="font-size: 0.875rem;">{{ opt.label }}</div>
                  <div class="depth-desc" style="font-size: 0.75rem;">{{ opt.desc }}</div>
                </button>
              </div>
            </div>

            <!-- 风险偏好 -->
            <div class="param-section">
              <div class="param-label">
                风险偏好
                <span class="param-value">{{ riskPreferenceLabel }}</span>
              </div>
              <div class="risk-slider-container">
                <span class="risk-end conservative">保守</span>
                <el-slider
                  v-model="riskPreference"
                  :min="0"
                  :max="100"
                  :show-tooltip="false"
                  class="risk-slider"
                />
                <span class="risk-end aggressive">激进</span>
              </div>
              <p class="param-hint">{{ riskHint }}</p>
            </div>

            <!-- 数据源选择 -->
            <div class="param-section">
              <div class="param-label">数据源</div>
              <div class="data-sources">
                <div 
                  v-for="source in dataSources" 
                  :key="source.key"
                  class="source-item"
                >
                  <div class="source-header">
                    <el-checkbox 
                      v-model="source.enabled" 
                      :label="source.label"
                    />
                    <el-icon class="source-icon" :style="{ color: source.color }">
                      <component :is="iconMap[source.key]" />
                    </el-icon>
                  </div>
                  <el-slider
                    v-if="source.enabled"
                    v-model="source.weight"
                    :min="0"
                    :max="100"
                    size="small"
                    class="source-weight"
                  />
                </div>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 3. 策略模板 -->
        <el-collapse-item name="strategy">
          <template #title>
            <div class="collapse-title">
              <el-icon><Document /></el-icon>
              <span>策略模板</span>
            </div>
          </template>
          
          <div class="collapse-content">
            <!-- 预设模板 -->
            <div class="param-section">
              <div class="param-label">预设模板</div>
              <div class="template-cards">
                <div 
                  v-for="tpl in strategyTemplates" 
                  :key="tpl.value"
                  :class="['template-card', { active: selectedTemplate === tpl.value }]"
                  @click="selectTemplate(tpl.value)"
                >
                  <div class="template-icon">{{ tpl.icon }}</div>
                  <div class="template-name">{{ tpl.label }}</div>
                  <div class="template-desc">{{ tpl.desc }}</div>
                </div>
              </div>
            </div>

            <!-- 自定义框架 -->
            <div class="param-section">
              <div class="param-label">自定义分析框架</div>
              
              <!-- 技术指标组合 -->
              <div class="custom-group">
                <div class="group-title">技术指标组合</div>
                <el-checkbox-group v-model="customIndicators" class="indicator-checks">
                  <el-checkbox label="MA">均线</el-checkbox>
                  <el-checkbox label="RSI">RSI</el-checkbox>
                  <el-checkbox label="MACD">MACD</el-checkbox>
                  <el-checkbox label="BOLL">布林带</el-checkbox>
                  <el-checkbox label="VOL">成交量</el-checkbox>
                  <el-checkbox label="ATR">ATR</el-checkbox>
                </el-checkbox-group>
              </div>

              <!-- 链上指标阈值 -->
              <div class="custom-group">
                <div class="group-title">链上指标阈值</div>
                <div class="threshold-inputs">
                  <div class="threshold-item">
                    <span>大户持仓变化 ></span>
                    <el-input-number v-model="thresholds.whaleChange" :min="0" :max="100" size="small" />
                    <span>%</span>
                  </div>
                  <div class="threshold-item">
                    <span>交易所净流入 ></span>
                    <el-input-number v-model="thresholds.exchangeNetFlow" :min="0" size="small" />
                    <span>M</span>
                  </div>
                </div>
              </div>

              <!-- 风险控制规则 -->
              <div class="custom-group">
                <div class="group-title">风险控制规则</div>
                <div class="risk-rules">
                  <div class="rule-item">
                    <span>最大止损幅度</span>
                    <el-slider v-model="riskRules.maxStopLoss" :min="1" :max="20" :format-tooltip="v => v + '%'" size="small" />
                  </div>
                  <div class="rule-item">
                    <span>最大仓位比例</span>
                    <el-slider v-model="riskRules.maxPosition" :min="5" :max="100" :format-tooltip="v => v + '%'" size="small" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 4. 自动化设置 -->
        <el-collapse-item name="automation">
          <template #title>
            <div class="collapse-title">
              <el-icon><Timer /></el-icon>
              <span>自动化设置</span>
            </div>
          </template>
          
          <div class="collapse-content">
            <!-- 自动刷新 -->
            <div class="param-section">
              <div class="param-label">自动刷新间隔</div>
              <el-radio-group v-model="autoRefresh" class="refresh-options">
                <el-radio-button :label="0">关闭</el-radio-button>
                <el-radio-button :label="60">1分钟</el-radio-button>
                <el-radio-button :label="300">5分钟</el-radio-button>
                <el-radio-button :label="900">15分钟</el-radio-button>
              </el-radio-group>
            </div>

            <!-- 预警条件 -->
            <div class="param-section">
              <div class="param-label">预警条件</div>
              <div class="alert-conditions">
                <label class="condition-item">
                  <el-checkbox v-model="alerts.priceBreakout" />
                  <span>价格突破关键位时提醒</span>
                </label>
                <label class="condition-item">
                  <el-checkbox v-model="alerts.highConfidence" />
                  <span>预测置信度 > 80% 时提醒</span>
                </label>
                <label class="condition-item">
                  <el-checkbox v-model="alerts.riskIncrease" />
                  <span>风险等级升高时提醒</span>
                </label>
              </div>
            </div>

            <!-- 交易信号模式 -->
            <div class="param-section">
              <div class="param-label">交易信号模式</div>
              <div class="signal-mode-cards">
                <div 
                  v-for="mode in signalModes" 
                  :key="mode.value"
                  :class="['mode-card', { active: signalMode === mode.value }]"
                  @click="signalMode = mode.value"
                >
                  <el-icon :size="28"><component :is="signalModeIconMap[mode.value]" /></el-icon>
                  <span class="mode-label" style="font-size: 0.875rem;">{{ mode.label }}</span>
                </div>
              </div>
              <p class="mode-hint" v-if="signalMode === 'live'">
                ⚠️ 实盘模式需要配置交易所 API
              </p>
            </div>
          </div>
        </el-collapse-item>

        <!-- 5. 模型设置 -->
        <el-collapse-item name="model">
          <template #title>
            <div class="collapse-title">
              <el-icon><Cpu /></el-icon>
              <span>模型设置</span>
            </div>
          </template>
          
          <div class="collapse-content">
            <!-- AI模型选择 -->
            <div class="param-section">
              <div class="param-label">AI模型</div>
              <el-select v-model="selectedModel" class="model-select">
                <el-option
                  v-for="model in availableModels"
                  :key="model.value"
                  :label="model.label"
                  :value="model.value"
                >
                  <div class="model-option">
                    <span class="model-name">{{ model.label }}</span>
                    <span class="model-badge" v-if="model.badge">{{ model.badge }}</span>
                  </div>
                </el-option>
              </el-select>
            </div>

            <!-- 提示词模板 -->
            <div class="param-section">
              <div class="param-label">
                提示词模板
                <el-button size="small" text @click="showPromptEditor = true">编辑</el-button>
              </div>
              <div class="prompt-preview">
                <code>{{ promptTemplate.substring(0, 100) }}...</code>
              </div>
            </div>

            <!-- 数据清理 -->
            <div class="param-section">
              <div class="param-label">数据管理</div>
              <div class="data-actions">
                <el-button size="small" @click="clearHistoryData">
                  <el-icon><Delete /></el-icon>
                  清理历史预测
                </el-button>
                <el-button size="small" @click="clearCache">
                  <el-icon><Brush /></el-icon>
                  清除缓存
                </el-button>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 当前配置预览 (Fixed Footer) -->
    <div class="settings-preview flex-shrink-0 bg-[#0b0f1a] z-10 border-t border-slate-700/50">
      <div class="preview-title">当前配置</div>
      <div class="preview-tags">
        <el-tag size="small">{{ selectedSymbol }}</el-tag>
        <el-tag size="small" type="info">{{ depthLabel }}</el-tag>
        <el-tag size="small" :type="riskTagType">{{ riskPreferenceLabel }}</el-tag>
        <el-tag size="small" v-if="autoRefresh">自动刷新 {{ autoRefresh / 60 }}分</el-tag>
      </div>
    </div>


    <!-- 提示词编辑弹窗 -->
    <el-dialog v-model="showPromptEditor" title="编辑提示词模板" width="600px">
      <el-input
        v-model="promptTemplate"
        type="textarea"
        :rows="12"
        placeholder="输入自定义提示词模板..."
      />
      <template #footer>
        <el-button @click="showPromptEditor = false">取消</el-button>
        <el-button type="primary" @click="savePromptTemplate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入配置弹窗 -->
    <el-dialog v-model="showImportDialog" title="导入配置" width="500px">
      <el-input
        v-model="importJson"
        type="textarea"
        :rows="8"
        placeholder="粘贴配置 JSON..."
      />
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="importSettings">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, markRaw } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting,
  Close,
  Monitor,
  Cpu,
  DataAnalysis,
  Timer,
  Delete,
  Brush,
  View,
  Connection,
  TrendCharts,
  Link,
  Document,
  ChatLineRound,
  RefreshRight,
  Download,
  Coin,
} from '@element-plus/icons-vue'

// ============================================================
// Props & Emits
// ============================================================

const props = defineProps(['symbol', 'timeframe', 'depth', 'risk'])

const emit = defineEmits<{
  (e: 'run-analysis', config: any): void
  (e: 'config-change', config: any): void
  (e: 'update:symbol', val: string): void
  (e: 'update:timeframe', val: string): void
  (e: 'update:depth', val: string): void
  (e: 'update:risk', val: number): void
  (e: 'analyze', config: any): void
}>()

// ============================================================
// 静态配置 (避免 Proxy 导致的崩溃)
// ============================================================

const iconMap: Record<string, any> = {
  technical: markRaw(TrendCharts),
  onchain: markRaw(Link),
  news: markRaw(Document),
  social: markRaw(ChatLineRound)
}

const signalModeIconMap: Record<string, any> = {
  display: markRaw(View),
  paper: markRaw(Monitor),
  live: markRaw(Connection)
}

const timeframeOptions = [
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '4h', label: '4h' },
  { value: '1d', label: '1d' }
]

const depthOptions = [
  { value: 'quick', label: '快速扫描', desc: '~15秒', icon: '⚡' },
  { value: 'standard', label: '标准分析', desc: '~30秒', icon: '📊' },
  { value: 'deep', label: '深度研究', desc: '~60秒', icon: '🔬' }
]

const symbolGroups = [
  {
    label: '主流币',
    symbols: [
      { value: 'BTCUSDT', label: 'BTC/USDT', icon: '₿', change: 2.35 },
      { value: 'ETHUSDT', label: 'ETH/USDT', icon: 'Ξ', change: -1.22 },
      { value: 'BNBUSDT', label: 'BNB/USDT', icon: '◆', change: 0.85 },
      { value: 'SOLUSDT', label: 'SOL/USDT', icon: '◎', change: 5.67 }
    ]
  },
  {
    label: '热门币',
    symbols: [
      { value: 'XRPUSDT', label: 'XRP/USDT', icon: '✕', change: 1.12 },
      { value: 'ADAUSDT', label: 'ADA/USDT', icon: '◇', change: -0.56 },
      { value: 'DOGEUSDT', label: 'DOGE/USDT', icon: 'Ð', change: 3.45 },
      { value: 'AVAXUSDT', label: 'AVAX/USDT', icon: '▲', change: -2.10 }
    ]
  }
]

// ============================================================
// 响应式状态
// ============================================================

const activeCollapse = ref('symbol')
const showPromptEditor = ref(false)
const showImportDialog = ref(false)
const importJson = ref('')

// 基础参数同步
const selectedSymbol = ref(props.symbol || 'BTCUSDT')
const selectedTimeframe = ref(props.timeframe || '4h')
const analysisDepth = ref(props.depth || 'standard')
const riskPreference = ref(props.risk || 50)

const compareMode = ref(false)
const compareSymbols = ref<string[]>([])
const favorites = ref(['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])

// 数据源
const dataSources = ref([
  { key: 'technical', label: '技术指标', enabled: true, weight: 40, color: '#3b82f6' },
  { key: 'onchain', label: '链上数据', enabled: true, weight: 30, color: '#10b981' },
  { key: 'news', label: '新闻舆情', enabled: true, weight: 20, color: '#f59e0b' },
  { key: 'social', label: '社交媒体', enabled: false, weight: 10, color: '#ec4899' }
])

// 策略与自动化
const selectedTemplate = ref('trend')
const customIndicators = ref(['MA', 'RSI', 'MACD'])
const thresholds = ref({ whaleChange: 5, exchangeNetFlow: 100 })
const riskRules = ref({ maxStopLoss: 5, maxPosition: 30 })
const autoRefresh = ref(0)
const alerts = ref({ priceBreakout: true, highConfidence: true, riskIncrease: false })
const signalMode = ref('display')
const selectedModel = ref('deepseek-chat')
const promptTemplate = ref(`你是一个专业的加密货币量化分析师...`)

// ============================================================
// 计算属性
// ============================================================

const allSymbols = symbolGroups.flatMap(g => g.symbols.map(s => s.value))

const currentSymbolInfo = computed(() => ({
  change24h: 2.35,
  volume24h: 28500000000,
  price: 78234.56
}))

const riskPreferenceLabel = computed(() => {
  if (riskPreference.value <= 30) return '保守'
  if (riskPreference.value <= 70) return '稳健'
  return '激进'
})

const riskHint = computed(() => {
  if (riskPreference.value <= 30) return '小仓位，紧止损，追求稳定收益'
  if (riskPreference.value <= 70) return '适中仓位，平衡风险与收益'
  return '大仓位，宽止损，追求高收益'
})

const riskTagType = computed(() => {
  if (riskPreference.value <= 30) return 'success'
  if (riskPreference.value <= 70) return 'warning'
  return 'danger'
})

const depthLabel = computed(() => {
  const opt = depthOptions.find(d => d.value === analysisDepth.value)
  return opt?.label || ''
})

const signalModes = [
  { value: 'display', label: '仅显示' },
  { value: 'paper', label: '模拟交易' },
  { value: 'live', label: '实盘API' }
]

const strategyTemplates = [
  { value: 'trend', label: '趋势跟踪', desc: '顺势交易', icon: '📈' },
  { value: 'reversal', label: '反转交易', desc: '逆势抄底', icon: '🔄' },
  { value: 'swing', label: '波段操作', desc: '区间震荡', icon: '📉' }
]

const availableModels = [
  { value: 'deepseek-chat', label: 'DeepSeek Chat', badge: '推荐' },
  { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner', badge: 'R1' },
  { value: 'gpt-4', label: 'GPT-4', badge: '' }
]

// ============================================================
// 方法
// ============================================================

const formatPrice = (p: number) => p ? p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'
const formatVolume = (v: number) => {
  if (!v) return '-'
  if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B'
  if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M'
  return v.toLocaleString()
}

const handleSymbolChange = () => emit('config-change', getConfig())
const selectSymbol = (s: string) => selectedSymbol.value = s
const removeFavorite = (s: string) => {
  const idx = favorites.value.indexOf(s)
  if (idx >= 0) {
    favorites.value.splice(idx, 1)
    saveToLocalStorage()
  }
}

const selectTemplate = (t: string) => {
  selectedTemplate.value = t
  if (t === 'trend') {
    riskPreference.value = 60
    customIndicators.value = ['MA', 'MACD', 'VOL']
  } else if (t === 'reversal') {
    riskPreference.value = 40
    customIndicators.value = ['RSI', 'BOLL', 'VOL']
  } else if (t === 'swing') {
    riskPreference.value = 50
    customIndicators.value = ['MA', 'RSI', 'ATR']
  }
}

const getConfig = () => ({
  symbol: selectedSymbol.value,
  timeframe: selectedTimeframe.value,
  compareMode: compareMode.value,
  compareSymbols: compareSymbols.value,
  analysisDepth: analysisDepth.value,
  riskPreference: riskPreference.value,
  dataSources: dataSources.value.filter(s => s.enabled).map(s => ({ key: s.key, weight: s.weight })),
  template: selectedTemplate.value,
  customIndicators: customIndicators.value,
  thresholds: thresholds.value,
  riskRules: riskRules.value,
  autoRefresh: autoRefresh.value,
  alerts: alerts.value,
  signalMode: signalMode.value,
  model: selectedModel.value
})


import { usePredictionStore } from '@/stores/usePredictionStore'
import { Select } from '@element-plus/icons-vue'

const predictionStore = usePredictionStore()

const handleManualSave = () => {
  // 显式调用 Store 保存
  predictionStore.updatePreferences({
    timeframe: selectedTimeframe.value,
    depth: analysisDepth.value,
    risk: Number(riskPreference.value)
  })
  
  // 同时保存本地组件状态 (Legacy)
  saveToLocalStorage()
  
  ElMessage.success({
    message: '配置已保存为默认设置',
    type: 'success',
    duration: 2000
  })
}

const resetToDefaults = () => {
  ElMessageBox.confirm('确定要重置所有设置为默认值吗？', '重置确认', { type: 'warning' }).then(() => {
    selectedSymbol.value = 'BTCUSDT'
    selectedTimeframe.value = '4h'
    analysisDepth.value = 'standard'
    riskPreference.value = 50
    selectedTemplate.value = 'trend'
    customIndicators.value = ['MA', 'RSI', 'MACD']
    autoRefresh.value = 0
    signalMode.value = 'display'
    dataSources.value.forEach(s => {
      s.enabled = ['technical', 'onchain', 'news'].includes(s.key)
      s.weight = s.key === 'technical' ? 40 : s.key === 'onchain' ? 30 : 20
    })
    saveToLocalStorage()
    ElMessage.success('已重置为默认设置')
  }).catch(() => {})
}

const exportSettings = () => {
  navigator.clipboard.writeText(JSON.stringify(getConfig(), null, 2))
  ElMessage.success('配置已复制到剪贴板')
}

const importSettings = () => {
  try {
    const config = JSON.parse(importJson.value)
    if (config.symbol) selectedSymbol.value = config.symbol
    if (config.timeframe) selectedTimeframe.value = config.timeframe
    if (config.analysisDepth) analysisDepth.value = config.analysisDepth
    if (config.riskPreference !== undefined) riskPreference.value = config.riskPreference
    if (config.template) selectedTemplate.value = config.template
    if (config.customIndicators) customIndicators.value = config.customIndicators
    if (config.autoRefresh !== undefined) autoRefresh.value = config.autoRefresh
    if (config.signalMode) signalMode.value = config.signalMode
    showImportDialog.value = false
    saveToLocalStorage()
    ElMessage.success('配置导入成功')
  } catch (e) { ElMessage.error('配置格式错误') }
}

const savePromptTemplate = () => { saveToLocalStorage(); showPromptEditor.value = false; ElMessage.success('提示词模板已保存') }
const clearHistoryData = () => ElMessageBox.confirm('确定清除吗？', '清理确认').then(() => ElMessage.success('已清理')).catch(() => {})
const clearCache = () => ElMessage.success('缓存已清除')

// Storage
const STORAGE_KEY = 'ai_analysis_config'
const saveToLocalStorage = () => {
  try {
    const config = { ...getConfig(), favorites: favorites.value, promptTemplate: promptTemplate.value }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  } catch (e) { console.error('Save failed', e) }
}

const loadFromLocalStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const config = JSON.parse(saved)
        if (config.symbol) selectedSymbol.value = config.symbol
        
        // Skip core params to respect parent props (Store is the source of truth)
        /*
        if (config.analysisDepth) {
          if (typeof config.analysisDepth === 'number') {
            analysisDepth.value = config.analysisDepth === 1 ? 'quick' : config.analysisDepth === 3 ? 'deep' : 'standard'
          } else {
            analysisDepth.value = config.analysisDepth
          }
        }
        
        if (config.riskPreference !== undefined) {
          if (typeof config.riskPreference === 'string') {
            riskPreference.value = config.riskPreference === 'conservative' ? 30 : config.riskPreference === 'aggressive' ? 70 : 50
          } else {
            riskPreference.value = config.riskPreference
          }
        }
        
        if (config.timeframe) selectedTimeframe.value = config.timeframe
        */
        
        if (config.template) selectedTemplate.value = config.template
        if (config.customIndicators) customIndicators.value = config.customIndicators
        if (config.favorites) favorites.value = config.favorites
        if (config.promptTemplate) promptTemplate.value = config.promptTemplate
        if (config.autoRefresh !== undefined) autoRefresh.value = config.autoRefresh
        if (config.signalMode) signalMode.value = config.signalMode
        
        // [FIX] Restore missing fields
        if (config.model) selectedModel.value = config.model
        if (config.riskRules) riskRules.value = { ...riskRules.value, ...config.riskRules }
        if (config.thresholds) thresholds.value = { ...thresholds.value, ...config.thresholds }
        if (config.alerts) alerts.value = { ...alerts.value, ...config.alerts }
        if (config.compareMode !== undefined) compareMode.value = config.compareMode
        if (config.compareSymbols) compareSymbols.value = config.compareSymbols
      }
  } catch (e) { console.error('Load failed', e) }
}

// Watchers
watch(() => props.symbol, (v) => { if (v) selectedSymbol.value = v })
watch(() => props.timeframe, (v) => { if (v) selectedTimeframe.value = v })
watch(() => props.depth, (v) => { if (v) analysisDepth.value = v })
watch(() => props.risk, (v) => { if (v !== undefined) riskPreference.value = v })

watch(selectedSymbol, (v) => emit('update:symbol', v))
watch(selectedTimeframe, (v) => emit('update:timeframe', v))
watch(analysisDepth, (v) => emit('update:depth', v))
watch(riskPreference, (v) => emit('update:risk', v))

watch([selectedSymbol, selectedTimeframe, analysisDepth, riskPreference, selectedTemplate, customIndicators, autoRefresh, signalMode], () => {
  saveToLocalStorage()
  emit('config-change', getConfig())
}, { deep: true })

onMounted(loadFromLocalStorage)
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.analysis-control-panel {
  background: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  
  .panel-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #fff;
    margin: 0;
  }
  
  .header-actions {
    display: flex;
    gap: 8px;
    
    .action-btn {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      color: rgba(255, 255, 255, 0.6);
      cursor: pointer;
      transition: all 0.2s;
      
      &:hover {
        background: rgba($color-primary, 0.15);
        border-color: $color-primary;
        color: $color-primary;
      }

      &.save-btn:hover {
        background: rgba($color-success, 0.15);
        border-color: $color-success;
        color: $color-success;
      }
    }
  }
}

// 折叠面板
:deep(.el-collapse) {
  border: none;
  
  .el-collapse-item__header {
    background: transparent;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: #fff;
    padding: 0 16px;
    height: 52px;
    
    &:hover {
      background: rgba(255, 255, 255, 0.02);
    }
  }
  
  .el-collapse-item__content {
    background: transparent;
    padding: 0;
  }
  
  .el-collapse-item__wrap {
    border: none;
    background: transparent;
  }
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  
  .current-value {
    margin-left: auto;
    margin-right: 10px;
  }
}

.collapse-content {
  padding: 16px;
}

// 交易对选择
.symbol-search {
  margin-bottom: 16px;
  
  .symbol-select {
    width: 100%;
  }
}

.symbol-option {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .symbol-icon {
    font-size: 16px;
  }
  
  .symbol-name {
    flex: 1;
  }
  
  .symbol-change {
    font-size: 12px;
    font-weight: 600;
    
    &.up { color: $color-success; }
    &.down { color: $color-danger; }
  }
}

.favorites-section {
  margin-bottom: 16px;
  
  .section-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 8px;
  }
  
  .favorites-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .favorite-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover, &.active {
      background: rgba($color-primary, 0.15);
      border-color: $color-primary;
      color: $color-primary;
    }
    
    .remove-icon {
      font-size: 12px;
      opacity: 0;
      transition: opacity 0.2s;
    }
    
    &:hover .remove-icon {
      opacity: 1;
    }
  }
  
  .add-favorite-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border: 1px dashed rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    color: rgba(255, 255, 255, 0.5);
    cursor: pointer;
    
    &:hover {
      border-color: $color-primary;
      color: $color-primary;
    }
  }
}

.compare-mode {
  margin-bottom: 16px;
  
  .toggle-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: 8px;
  }
  
  .compare-symbols {
    :deep(.el-select) {
      width: 100%;
    }
  }
}

.symbol-info {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  
  .info-item {
    flex: 1;
    text-align: center;
    
    .info-label {
      display: block;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 4px;
    }
    
    .info-value {
      font-size: 14px;
      font-weight: 600;
      color: #fff;
      
      &.up { color: $color-success; }
      &.down { color: $color-danger; }
    }
  }
}

// 参数设置
.param-section {
  margin-bottom: 20px;
  
  &:last-child {
    margin-bottom: 0;
  }
  
  .param-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
    margin-bottom: 12px;
    
    .param-value {
      font-weight: 400;
      color: $color-primary-light;
    }
  }

.panel-title {
    font-size: 0.7rem;
    font-weight: 800;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.section-label {
    font-size: 10px;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
}

.config-section {
    padding-left: 1rem;
    padding-right: 1rem;
    margin-bottom: 1.25rem;
}
  
  .param-hint {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
    margin-top: 8px;
    margin-bottom: 0;
  }
}

.depth-options {
  display: flex;
  gap: 10px;
  
  .depth-btn {
    flex: 1;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    cursor: pointer;
    text-align: center;
    transition: all 0.2s;
    
    &.active {
      background: rgba($color-primary, 0.15);
      border-color: $color-primary;
    }
    
    .depth-icon {
      font-size: 20px;
      margin-bottom: 6px;
    }
    
    .depth-name {
      font-size: 12px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 2px;
    }
    
    .depth-desc {
      font-size: 10px;
      color: rgba(255, 255, 255, 0.5);
    }
  }
}

.risk-slider-container {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .risk-end {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.5);
    
    &.conservative { color: $color-success; }
    &.aggressive { color: $color-danger; }
  }
  
  .risk-slider {
    flex: 1;
  }
}

.data-sources {
  display: flex;
  flex-direction: column;
  gap: 12px;
  
  .source-item {
    padding: 10px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    
    .source-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    
    .source-weight {
      margin-top: 8px;
    }
  }
}

// 策略模板
.template-cards {
  display: flex;
  gap: 10px;
  
  .template-card {
    flex: 1;
    padding: 14px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    
    &.active {
      background: rgba($color-primary, 0.15);
      border-color: $color-primary;
    }
    
    .template-icon {
      font-size: 24px;
      margin-bottom: 8px;
    }
    
    .template-name {
      font-size: 13px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 4px;
    }
    
    .template-desc {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
    }
  }
}

.custom-group {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  
  .group-title {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 10px;
  }
  
  .indicator-checks {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .threshold-inputs {
    display: flex;
    flex-direction: column;
    gap: 10px;
    
    .threshold-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
      
      :deep(.el-input-number) {
        width: 80px;
      }
    }
  }
  
  .risk-rules {
    .rule-item {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
      
      span {
        flex-shrink: 0;
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
        width: 100px;
      }
      
      :deep(.el-slider) {
        flex: 1;
      }
    }
  }
}

// 自动化
.refresh-options {
  width: 100%;
  
  :deep(.el-radio-button) {
    flex: 1;
    
    .el-radio-button__inner {
      width: 100%;
    }
  }
}

.alert-conditions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  
  .condition-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    cursor: pointer;
  }
}

.signal-mode-cards {
  display: flex;
  gap: 10px;
  
  .mode-card {
    flex: 1;
    padding: 14px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    
    &.active {
      background: rgba($color-primary, 0.15);
      border-color: $color-primary;
      
      .el-icon {
        color: $color-primary;
      }
    }
    
    .el-icon {
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 6px;
    }
    
    .mode-label {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
    }
  }
}

.mode-hint {
  font-size: 11px;
  color: $color-warning;
  margin-top: 10px;
  margin-bottom: 0;
}

// 模型设置
.model-select {
  width: 100%;
}

.model-option {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .model-badge {
    font-size: 10px;
    padding: 2px 6px;
    background: rgba($color-primary, 0.2);
    border-radius: 4px;
    color: $color-primary-light;
  }
}

.prompt-preview {
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  
  code {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.6);
    font-family: $font-mono;
  }
}

.data-actions {
  display: flex;
  gap: 10px;
}

// 配置预览
.settings-preview {
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  
  .preview-title {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 8px;
  }
  
  .preview-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
}

// 操作按钮
.panel-actions {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  
  .run-analysis-btn {
    width: 100%;
    height: 44px;
    font-size: 15px;
    font-weight: 600;
  }
}

// 弹窗
:deep(.el-dialog) {
  background: rgba(30, 41, 59, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  
  .el-dialog__header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  
  .el-dialog__title {
    color: #fff;
  }
}
</style>
