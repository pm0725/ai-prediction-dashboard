<!--
  智链预测 - 主布局组件
  包含顶部导航栏、侧边栏和主内容区
-->
<template>
  <el-container class="main-layout">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-left">
        <div class="logo">
          <el-icon :size="28"><TrendCharts /></el-icon>
          <span class="logo-text">智链预测</span>
        </div>
        <el-tag type="primary" effect="dark" size="small">AI驱动</el-tag>
      </div>
      
      <div class="header-center">
        <el-menu
          :default-active="activeRoute"
          mode="horizontal"
          :ellipsis="false"
          background-color="transparent"
          text-color="#a0aec0"
          active-text-color="#60a5fa"
          @select="handleMenuSelect"
          class="nav-menu"
        >
          <el-menu-item index="/">
            <el-icon><Monitor /></el-icon>
            <span>AI仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/market-overview">
            <el-icon><TrendCharts /></el-icon>
            <span>市场概览</span>
          </el-menu-item>
          <el-menu-item index="/analysis">
            <el-icon><MagicStick /></el-icon>
            <span>智能分析</span>
          </el-menu-item>
          <el-menu-item index="/strategy">
            <el-icon><Aim /></el-icon>
            <span>策略生成的</span>
          </el-menu-item>
          <el-menu-item index="/backtest">
            <el-icon><DataLine /></el-icon>
            <span>回测验证</span>
          </el-menu-item>
        </el-menu>
      </div>
      
      <div class="header-right">
        <el-select
          v-model="predictionStore.currentSymbol"
          placeholder="选择交易对"
          size="large"
          style="width: 160px"
          @change="handleSymbolChange"
        >
          <el-option
            v-for="item in predictionStore.symbols"
            :key="item.symbol"
            :label="item.symbol"
            :value="item.symbol"
          >
            <span>{{ item.base }}</span>
            <span style="color: #8b949e; margin-left: 8px">{{ item.name }}</span>
          </el-option>
        </el-select>
        
        <el-button circle>
          <el-icon><Setting /></el-icon>
        </el-button>
      </div>
    </el-header>
    
    <!-- 主内容区 -->
    <el-main class="main-content" :class="{ 'full-bleed': isFullBleed }">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>
    
    <!-- 底部状态栏 -->
    <el-footer class="footer">
      <div class="footer-left">
        <el-tag :type="apiStatus === 'healthy' ? 'success' : 'danger'" size="small" effect="plain">
          API {{ apiStatus === 'healthy' ? '正常' : '异常' }}
        </el-tag>
        <span class="connection-info">后端连接: localhost:8000</span>
      </div>
      <div class="footer-right">
        <span>数据仅供参考，不构成投资建议</span>
      </div>
    </el-footer>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  TrendCharts,
  Monitor,
  MagicStick,
  Aim,
  DataLine,
  Setting
} from '@element-plus/icons-vue'
import { usePredictionStore } from '@/stores/usePredictionStore'
import { analysisApi } from '@/services/api'

const router = useRouter()
const route = useRoute()
const predictionStore = usePredictionStore()

// API状态
const apiStatus = ref<'healthy' | 'error'>('healthy')

// 当前激活的路由
const activeRoute = computed(() => route.path)

// 是否全屏铺满（针对主仪表盘）
const isFullBleed = computed(() => route.path === '/' || route.path === '/prediction')

// 处理菜单选择
function handleMenuSelect(index: string) {
  router.push(index)
}

// 处理交易对切换
function handleSymbolChange(symbol: string) {
  predictionStore.selectSymbol(symbol)
}

// 检查API健康状态
async function checkApiHealth() {
  try {
    await analysisApi.healthCheck()
    apiStatus.value = 'healthy'
  } catch {
    apiStatus.value = 'error'
  }
}

onMounted(async () => {
  try {
    // 加载交易对列表
    await predictionStore.loadSymbols()
  } catch (e) {
    console.error('Failed to load symbols', e)
  }
  
  try {
    // 检查API状态
    await checkApiHealth()
  } catch (e) {
    console.error('Health check failed', e)
    apiStatus.value = 'error'
  }
  
  // 定时检查
  setInterval(checkApiHealth, 30000)
})
</script>

<style lang="scss" scoped>
.main-layout {
  min-height: 100vh;
  background: transparent;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  background: rgba(10, 10, 15, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #60a5fa;

    .logo-text {
      font-size: 20px;
      font-weight: 700;
      background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;

  .nav-menu {
    border-bottom: none;
    
    :deep(.el-menu-item) {
      border-bottom: none;
      font-size: 14px;
      
      &:hover {
        background: rgba(96, 165, 250, 0.1);
      }
      
      &.is-active {
        background: rgba(96, 165, 250, 0.15);
      }
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  padding: 24px;
  overflow-y: auto;
  height: calc(100vh - 64px - 40px); /* Header + Footer heights */
  
  &.full-bleed {
    padding: 0;
    overflow: hidden;
  }
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 40px;
  background: rgba(10, 10, 15, 0.8);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;

  .connection-info {
    color: rgba(255, 255, 255, 0.3);
  }
}

// 页面切换动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
