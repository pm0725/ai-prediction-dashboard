/**
 * 智链预测 - 预测状态管理
 * ========================
 * 管理预测分析相关的全局状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { analysisApi, type PredictionResult, type MarketContext, type SymbolInfo, type StrategyResult } from '@/services/api'

export const usePredictionStore = defineStore('prediction', () => {
    // ============================================================
    // 状态
    // ============================================================

    /** 当前选中的交易对 */
    const currentSymbol = ref<string>('ETHUSDT')

    /** 支持的交易对列表 */
    const symbols = ref<SymbolInfo[]>([])

    /** 多交易对行情数据 (从 marketStore 合并而来) */
    const tickers = ref<Record<string, any>>({})

    /** K线数据 */
    const klines = ref<Array<{
        timestamp: number
        open: number
        high: number
        low: number
        close: number
        volume: number
    }>>([])

    /** 当前市场上下文 */
    const marketContext = ref<MarketContext | null>(null)

    /** 当前预测结果 */
    const prediction = ref<PredictionResult | null>(null)

    /** 流式推理过程 */
    const streamingReasoning = ref<string>('')

    /** 全场扫描结果 */
    const batchResults = ref<Record<string, any>>({})

    /** 全局市场统计 (恐贪指数、板块表现等) */
    const globalStats = ref<{
        fear_greed: { value: number, classification: string, timestamp: string },
        market_change: number,
        sector_performance: Array<{ name: string, change: number }>,
        key_events: Array<{ time: string, category: string, title: string, type: string }>, // Added
        timestamp: string
    } | null>(null)

    /** 当前策略 */
    const strategy = ref<StrategyResult | null>(null)

    /** 是否处于策略模式 */
    const isStrategyMode = ref(false)

    /** 预测历史记录 */
    const history = ref<Array<{
        symbol: string
        direction: string
        time: string
        correct: boolean | null
        confidence: number
        summary: string
        fullData?: PredictionResult // 新增：保存完整数据用于回看
    }>>([])

    /** 加载状态 */
    const loading = ref({
        symbols: false,
        context: false,
        prediction: false,
        strategy: false,
        tickers: false,
        batch: false,
        history: false,
        globalStats: false
    })

    /** 扫描进度 (当前/总数) */
    const scanProgress = ref({
        current: 0,
        total: 0
    })

    /** 错误信息 */
    const error = ref<string | null>(null)

    /** 实时雷达数据 (补充分值) */
    const radarData = ref({
        volatility_score: 0,
        whale_activity: null as any,
        liquidity_gaps: [] as string[]
    })

    /** 实时市场预警 (Pump/Dump) */
    const marketAlerts = ref<Array<{
        symbol: string
        type: string // "pump" | "dump"
        change_percent: number
        timeframe: string
        message: string
        timestamp: number
        severity?: string
    }>>([])

    /** 用户偏好设置 (持久化) */
    /** 用户偏好设置 (持久化) */
    const preferences = ref({
        timeframe: '4h',
        depth: 'standard', // 'quick' | 'standard' | 'deep'
        risk: 50, // numeric value
        model: 'deepseek-chat',
        promptTemplate: ''
    })

    // ============================================================
    // 计算属性
    // ============================================================

    /** 当前交易对信息 */
    const currentSymbolInfo = computed(() => {
        return symbols.value.find(s => s.symbol === currentSymbol.value)
    })

    /** 当前价格 */
    const currentPrice = computed(() => {
        return marketContext.value?.current_price || 0
    })

    /** 是否正在分析中 */
    const isAnalyzing = computed(() => {
        return loading.value.prediction
    })

    /** 是否正在生成策略 */
    const isGeneratingStrategy = computed(() => {
        return loading.value.strategy
    })

    // ============================================================
    // 方法
    // ============================================================

    /**
     * 设置当前交易对
     */
    function setSymbol(symbol: string) {
        currentSymbol.value = symbol
        // 清除旧数据
        prediction.value = null
        strategy.value = null
        isStrategyMode.value = false
    }

    /**
     * 加载支持的交易对列表
     */
    async function loadSymbols() {
        loading.value.symbols = true
        error.value = null

        try {
            const result = await analysisApi.getSymbols()
            symbols.value = result.symbols
        } catch (e: any) {
            error.value = e.message || '加载交易对失败'
            // 使用默认列表
            symbols.value = [
                { symbol: 'BTCUSDT', name: 'Bitcoin', base: 'BTC' },
                { symbol: 'ETHUSDT', name: 'Ethereum', base: 'ETH' },
                { symbol: 'BNBUSDT', name: 'BNB', base: 'BNB' },
                { symbol: 'SOLUSDT', name: 'Solana', base: 'SOL' }
            ]
        } finally {
            loading.value.symbols = false
        }
    }

    /**
     * 加载市场上下文
     */
    async function loadMarketContext() {
        loading.value.context = true
        error.value = null

        try {
            const result = await analysisApi.getMarketContext(currentSymbol.value)
            marketContext.value = result

            // 使用API返回的K线数据
            if (result.klines && result.klines.length > 0) {
                klines.value = result.klines
            } else {
                // 如果没有K线数据，清空
                klines.value = []
                console.warn('后端未返回K线数据')
            }
        } catch (e: any) {
            error.value = e.message || '加载市场数据失败'
            // 清空数据，避免显示错误的旧数据
            marketContext.value = null
            klines.value = []
        } finally {
            loading.value.context = false
        }
    }

    /**
     * 静默轮询雷达数据 (不触发AI)
     */
    async function pollRadarData() {
        try {
            const result = await analysisApi.getMarketContext(currentSymbol.value)
            if (result) {
                radarData.value = {
                    volatility_score: result.volatility_score || 0,
                    whale_activity: result.whale_activity,
                    liquidity_gaps: result.liquidity_gaps || []
                }

                // 同时尝试同步到当前 prediction 如果存在，保持界面一致性
                if (prediction.value && prediction.value.symbol === currentSymbol.value) {
                    (prediction.value as any).volatility_score = result.volatility_score;
                    (prediction.value as any).whale_activity = result.whale_activity;
                    (prediction.value as any).liquidity_gaps = result.liquidity_gaps;
                }
            }
        } catch (e) {
            console.warn('Radar polling failed:', e)
        }
    }

    /**
     * 执行AI预测分析
     */
    async function analyze(timeframe: string = '4h', useCache: boolean = true, depth: number = 2, risk: string = 'moderate') {
        loading.value.prediction = true
        error.value = null
        streamingReasoning.value = '' // 清空旧的思考内容

        // Map parameters to API expected types
        const depthMap: Record<number, string> = { 1: 'quick', 2: 'standard', 3: 'deep' }
        const riskMap: Record<string, number> = { 'conservative': 20, 'moderate': 50, 'aggressive': 80 }

        const depthStr = depthMap[depth] || 'standard'
        const riskNum = riskMap[risk] || 50

        try {
            // Get advanced preferences
            const model = preferences.value.model
            const promptTemplate = preferences.value.promptTemplate

            // 注意：这里由于后端 predict 接口现在返回 AnalysisResult，
            // 且我们的 api.ts getPrediction 已经对应
            const result = await analysisApi.getPrediction(currentSymbol.value, timeframe, useCache, depthStr, riskNum, model, promptTemplate)
            prediction.value = result
            return result
        } catch (e: any) {
            error.value = e.message || '分析失败'
            throw e
        } finally {
            loading.value.prediction = false
        }
    }

    /**
     * 执行流式AI预测分析
     */
    async function analyzeStream(timeframe: string = '4h', depth: number = 2, risk: string = 'moderate') {
        loading.value.prediction = true
        error.value = null
        streamingReasoning.value = ''
        prediction.value = null

        const depthMap: Record<number, string> = { 1: 'quick', 2: 'standard', 3: 'deep' }
        const riskMap: Record<string, number> = { 'conservative': 20, 'moderate': 50, 'aggressive': 80 }

        const depthStr = depthMap[depth] || 'standard'
        const riskNum = riskMap[risk] || 50

        try {
            const model = preferences.value.model
            const promptTemplate = preferences.value.promptTemplate

            await analysisApi.getStreamPrediction(
                currentSymbol.value,
                timeframe,
                depthStr,
                riskNum,
                (chunk) => {
                    streamingReasoning.value += chunk
                },
                model,
                promptTemplate
            )

            // 流式结束后再拉取一次完整结果以更新界面结构化数据 (或者让后端在流结束最后发一个完整JSON)
            // 目前策略是流结束后手动刷新一次标准分析以获取结构化数据
            return await analyze(timeframe, true, depth, risk)
        } catch (e: any) {
            error.value = e.message || '流式分析请求失败'
            throw e
        } finally {
            loading.value.prediction = false
        }
    }

    /**
     * 执行全场扫描
     */
    async function runBatchScanner() {
        if (symbols.value.length === 0) await loadSymbols()

        loading.value.batch = true
        batchResults.value = {} // 重置之前的扫描结果

        // 用户指定：仅分析 BTC 和 ETH
        const targetSymbols = ['BTCUSDT', 'ETHUSDT']
        scanProgress.value = { current: 0, total: targetSymbols.length }

        try {
            // 注意：后端的 batch_scan 是并发处理的，所以直接发一个请求即可
            // 如果后端不支持大批量，前端可以分批发送，但目前的后端实现是支持异步并发的
            const model = preferences.value.model
            const promptTemplate = preferences.value.promptTemplate

            const result = await analysisApi.getBatchScan(targetSymbols, '4h', model, promptTemplate)

            if (result.results) {
                result.results.forEach((r: any) => {
                    batchResults.value[r.symbol] = r
                    scanProgress.value.current++
                })
            }
            return result
        } catch (e: any) {
            console.error('Batch scan failed:', e)
            // throw e // Silent failure to prevent app crash
        } finally {
            loading.value.batch = false
        }
    }

    /**
     * 清除本地缓存并重新分析
     */
    async function forceRefresh(timeframe: string = '4h') {
        await analysisApi.clearCache()
        return await analyze(timeframe, false)
    }

    /**
     * 生成交易策略
     */
    async function generateStrategy() {
        if (!prediction.value) {
            throw new Error('请先执行预测分析')
        }

        loading.value.strategy = true
        error.value = null

        try {
            const result = await analysisApi.generateStrategy({
                symbol: prediction.value.symbol,
                prediction: prediction.value.prediction,
                confidence: prediction.value.confidence,
                entry_zone: prediction.value.entry_zone,
                stop_loss: prediction.value.stop_loss,
                take_profit: prediction.value.take_profit,
                risk_level: prediction.value.risk_level,
                on_chain_context: prediction.value.on_chain_context
            })

            strategy.value = result
            isStrategyMode.value = true
            return result
        } catch (e: any) {
            error.value = e.message || '策略生成失败'
            throw e
        } finally {
            loading.value.strategy = false
        }
    }

    /**
     * 批量加载行情数据 (从 marketStore 迁移)
     */
    async function loadAllTickers() {
        if (symbols.value.length === 0) return

        loading.value.tickers = true
        try {
            const symbolList = symbols.value.map(s => s.symbol)
            if (symbolList.length > 0) {
                const targetSymbols = symbolList.slice(0, 10)
                const results = await analysisApi.getTickers(targetSymbols)

                // 更新tickers map
                results.forEach(t => {
                    tickers.value[t.symbol] = t
                })
            }
        } catch (e: any) {
            console.error('Failed to load tickers:', e)
        } finally {
            loading.value.tickers = false
        }
    }

    /**
     * 加载全局市场统计
     */
    async function fetchGlobalStats() {
        loading.value.globalStats = true
        try {
            const result = await analysisApi.getGlobalStats()
            globalStats.value = result
            return result
        } catch (e: any) {
            console.error('Failed to fetch global stats:', e)
        } finally {
            loading.value.globalStats = false
        }
    }

    /**
     * 切换当前交易对 (替代 selectSymbol)
     */
    function selectSymbol(symbol: string) {
        setSymbol(symbol)
        loadMarketContext()
    }

    /**
     * 设置策略模式
     */
    function setStrategyMode(pred: PredictionResult) {
        prediction.value = pred
        isStrategyMode.value = true
    }

    /**
     * 退出策略模式
     */
    function exitStrategyMode() {
        isStrategyMode.value = false
        strategy.value = null
    }

    /**
     * 清除预测结果
     */
    function clearPrediction() {
        prediction.value = null
        strategy.value = null
        isStrategyMode.value = false
    }

    /**
     * 加载历史记录
     */
    function loadHistory() {
        try {
            const saved = localStorage.getItem('prediction_history')
            if (saved) {
                history.value = JSON.parse(saved)

                // 自动恢复最近一次的详细预测结果
                if (history.value.length > 0 && history.value[0].fullData && !prediction.value) {
                    // Only restore if we don't have a fresh one (though on init we typically don't)
                    const lastRec = history.value[0]
                    // Check if it's not too old (e.g. within 24 hours)? Optional but good practice.
                    // For now, just restore it to match user expectation "last prediction shows up".
                    if (lastRec.fullData) {
                        prediction.value = lastRec.fullData
                    }
                    // Restore symbol context too if needed
                    if (lastRec.symbol) {
                        currentSymbol.value = lastRec.symbol
                    }
                }
            }
        } catch (e) {
            console.error('Failed to load history:', e)
        }
    }

    /**
     * 添加历史记录
     */
    function addToHistory(record: {
        symbol: string
        direction: string
        time: string
        correct: boolean | null
        confidence: number
        summary: string
        fullData?: PredictionResult // 新增
    }) {
        history.value.unshift(record)
        // 限制只保存最近 50 条
        if (history.value.length > 50) {
            history.value.pop()
        }
        saveHistory()
    }

    /**
     * 保存历史记录到本地
     */
    function saveHistory() {
        try {
            localStorage.setItem('prediction_history', JSON.stringify(history.value))
        } catch (e) {
            console.error('Failed to save history:', e)
        }
    }

    /**
     * 清空历史记录
     */
    function clearHistory() {
        history.value = []
        localStorage.removeItem('prediction_history')
    }

    /**
     * 加载用户偏好设置
     */
    function loadPreferences() {
        try {
            const saved = localStorage.getItem('ai_analysis_preferences')
            if (saved) {
                const parsed = JSON.parse(saved)
                // Merge with defaults to ensure structure
                preferences.value = { ...preferences.value, ...parsed }
            }
        } catch (e) {
            console.error('Failed to load preferences:', e)
        }
    }

    /**
     * 更新并保存用户偏好设置
     */
    function updatePreferences(newPrefs: Partial<typeof preferences.value>) {
        preferences.value = { ...preferences.value, ...newPrefs }
        try {
            localStorage.setItem('ai_analysis_preferences', JSON.stringify(preferences.value))
        } catch (e) {
            console.error('Failed to save preferences:', e)
        }
    }

    // ============================================================
    // WebSocket 实时推送
    // ============================================================

    let ws: WebSocket | null = null
    const isConnected = ref(false)
    let wsRetryCount = 0
    const WS_MAX_RETRIES = 10
    const WS_BASE_DELAY = 1000

    function connectWebSocket() {
        if (ws) return

        // 使用环境变量配置 WebSocket URL，默认开发环境地址
        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws'

        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            isConnected.value = true
            wsRetryCount = 0 // 连接成功，重置重试计数
        }

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data)
                if (msg.type === 'ticker_update') {
                    handleTickerUpdate(msg.data)
                } else if (msg.type === 'market_alerts') {
                    handleMarketAlerts(msg.data)
                }
            } catch (e) {
                console.error('WS 消息解析失败:', e)
            }
        }

        ws.onclose = () => {
            isConnected.value = false
            ws = null
            // 指数退避重连
            if (wsRetryCount < WS_MAX_RETRIES) {
                const delay = Math.min(WS_BASE_DELAY * Math.pow(2, wsRetryCount), 30000)
                wsRetryCount++
                setTimeout(connectWebSocket, delay)
            } else {
                console.warn('WebSocket 重连次数已达上限，停止重连')
            }
        }

        ws.onerror = (error) => {
            console.error('WebSocket 错误:', error)
            ws?.close()
        }
    }

    function handleTickerUpdate(tickers_data: any[]) {
        // 更新全量 tickers (用于 Dashboard 等)
        tickers_data.forEach(t => {
            tickers.value[t.symbol] = t
        })

        // 如果当前有市场上下文，同步更新价格
        if (marketContext.value && tickers_data) {
            const ticker = tickers_data.find((t: any) => t.symbol === marketContext.value?.symbol)
            if (ticker) {
                const newPrice = parseFloat(ticker.price)
                if (marketContext.value.current_price !== newPrice) {
                    marketContext.value.current_price = newPrice

                    // 深度优化：同步更新K线图最后一根柱子
                    if (klines.value.length > 0) {
                        const lastIdx = klines.value.length - 1
                        klines.value[lastIdx].close = newPrice
                        if (newPrice > klines.value[lastIdx].high) klines.value[lastIdx].high = newPrice
                        if (newPrice < klines.value[lastIdx].low) klines.value[lastIdx].low = newPrice
                    }
                }
            }
        }
    }

    function handleMarketAlerts(alerts: any[]) {
        // 将新警报添加到列表头部
        // 简单去重策略：如果在同一个时间戳已经有了同一个 symbol 的 alert，则不添加？
        // 或者直接全部添加，显示最新的

        alerts.forEach(alert => {
            // Check if we already have this specific alert (by timestamp + symbol)
            const exists = marketAlerts.value.some(a =>
                a.symbol === alert.symbol &&
                a.timestamp === alert.timestamp &&
                a.type === alert.type
            )

            if (!exists) {
                marketAlerts.value.unshift(alert)
            }
        })

        // 限制列表长度，只保留最近 20 条
        if (marketAlerts.value.length > 20) {
            marketAlerts.value = marketAlerts.value.slice(0, 20)
        }
    }

    // 初始化时自动连接
    connectWebSocket()

    // 初始化时加载历史和偏好
    loadHistory()
    loadPreferences()

    // 返回store内容
    return {
        // 状态
        currentSymbol,
        symbols,
        tickers,
        klines,
        marketContext,
        prediction,
        history,
        strategy,
        isStrategyMode,
        loading,
        error,
        isConnected,
        streamingReasoning,
        batchResults,
        scanProgress,
        globalStats,
        marketAlerts,
        // 计算属性
        currentSymbolInfo,
        currentPrice,
        isAnalyzing,
        isGeneratingStrategy,
        // 方法
        setSymbol,
        selectSymbol,
        loadSymbols,
        loadAllTickers,
        loadMarketContext,
        analyze,
        analyzeStream,
        runBatchScanner,
        fetchGlobalStats,
        forceRefresh,
        generateStrategy,
        setStrategyMode,
        exitStrategyMode,
        clearPrediction,
        connectWebSocket,
        loadHistory,
        addToHistory,
        clearHistory,
        pollRadarData,
        radarData,
        preferences,
        loadPreferences,
        updatePreferences
    }
})
