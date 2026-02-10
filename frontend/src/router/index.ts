/**
 * 智链预测 - 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
    {
        path: '/',
        name: 'Layout',
        component: () => import('@/layouts/MainLayout.vue'),
        children: [
            {
                path: '',
                name: 'PredictionDashboard',
                component: () => import('@/views/PredictionDashboard.vue'),
                meta: { title: 'AI预测仪表盘 Pro' }
            },
            {
                path: 'legacy-dashboard',
                name: 'AIPredictionDashboard',
                component: () => import('@/views/AIPredictionDashboard.vue'),
                meta: { title: 'AI预测仪表盘 (旧版)' }
            },
            {
                path: 'market-overview',
                name: 'Dashboard',
                component: () => import('@/views/Dashboard.vue'),
                meta: { title: '市场概览' }
            },
            {
                path: 'analysis',
                name: 'Analysis',
                component: () => import('@/views/Analysis.vue'),
                meta: { title: 'AI分析' }
            },
            {
                path: 'strategy',
                name: 'Strategy',
                component: () => import('@/views/Strategy.vue'),
                meta: { title: '策略生成' }
            },
            {
                path: 'backtest',
                name: 'Backtest',
                component: () => import('@/views/Backtest.vue'),
                meta: { title: '回测验证' }
            },
            {
                path: 'performance',
                name: 'Performance',
                component: () => import('@/views/PerformanceTracker.vue'),
                meta: { title: 'AI表现透视' }
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach((to, _from, next) => {
    document.title = `${to.meta.title || '智链预测'} - 智链预测`
    next()
})

export default router
