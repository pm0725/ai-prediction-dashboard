/**
 * 智链预测 - 市场数据状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { analysisApi, type PredictionResult, type MarketContext, type SymbolInfo, type MarketTicker } from '@/services/api'

export const useMarketStore = defineStore('market', () => {
    // ============================================================
    // 状态
    // ============================================================

    /** 当前选中的交易对 */
    const currentSymbol = ref<string>('ETHUSDT')

    /** 支持的交易对列表 */
    const symbols = ref<SymbolInfo[]>([])

    /** 多交易对行情数据 */
    const tickers = ref<Record<string, MarketTicker>>({})

    /** 当前市场上下文 */
    const marketContext = ref<MarketContext | null>(null)

    /** 当前预测结果 */
    const prediction = ref<PredictionResult | null>(null)

    /** 加载状态 */
    const loading = ref({
        symbols: false,
        context: false,
        prediction: false,
        tickers: false
    })

    /** 错误信息 */
    const error = ref<string | null>(null)

    /** 全局市场统计 (贪婪指数等) */
    const globalStats = ref<any>(null)

    /** 深度轮询定时器 */
    let depthTimer: any = null

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

    // ============================================================
    // 方法
    // ============================================================

    /**
     * 加载支持的交易对列表
     */
    async function loadSymbols() {
        loading.value.symbols = true
        try {
            const result = await analysisApi.getSymbols()
            symbols.value = result.symbols
        } catch (e: any) {
            error.value = e.message
        } finally {
            loading.value.symbols = false
        }
    }

    /**
     * 批量加载行情数据
     */
    async function loadAllTickers() {
        if (symbols.value.length === 0) return

        loading.value.tickers = true
        try {
            const symbolList = symbols.value.map(s => s.symbol)
            if (symbolList.length > 0) {
                // 分批请求，避免每次请求太多？API里是并行获取的，应该没事
                // 为了性能，只请求前4个（Dashboard展示的），或者全部？
                // Dashboard 目前展示 topSymbols (marketStore.symbols.slice(0, 4))
                // 我们先请求前10个
                const targetSymbols = symbolList.slice(0, 10)
                const results = await analysisApi.getTickers(targetSymbols)

                // 更新tickers map
                results.forEach(t => {
                    tickers.value[t.symbol] = t
                })
            }
        } catch (e: any) {
            console.error('Failed to load tickers:', e)
            // 不阻断其他流程，行情失败只显示旧数据或loading
        } finally {
            loading.value.tickers = false
        }
    }

    /**
     * 切换当前交易对
     */
    function selectSymbol(symbol: string) {
        currentSymbol.value = symbol
        // 自动加载市场上下文
        loadMarketContext()
    }

    /**
     * 加载市场上下文
     */
    async function loadMarketContext() {
        loading.value.context = true
        error.value = null
        try {
            marketContext.value = await analysisApi.getMarketContext(currentSymbol.value)
        } catch (e: any) {
            error.value = e.message
        } finally {
            loading.value.context = false
        }
    }

    /**
     * 执行AI预测分析
     */
    async function analyze(symbol: string = '', timeframe: string = '4h', depth: string = 'standard', risk: number = 50) {
        loading.value.prediction = true
        error.value = null
        try {
            // 注意: getPrediction 已经更新支持 depth 和 risk
            prediction.value = await analysisApi.getPrediction(symbol || currentSymbol.value, timeframe, true, depth, risk)
            return prediction.value
        } catch (e: any) {
            error.value = e.message
            throw e
        } finally {
            loading.value.prediction = false
        }
    }

    /**
     * 清除预测结果
     */
    function clearPrediction() {
        prediction.value = null
    }

    /**
     * 加载全局市场统计
     */
    async function loadGlobalStats() {
        try {
            globalStats.value = await analysisApi.getGlobalStats()
        } catch (e) {
            console.error('Failed to load global stats:', e)
        }
    }

    /**
     * 开始深度轮询
     */
    function startDepthPolling() {
        stopDepthPolling()
        if (!currentSymbol.value) return

        const fetchDepth = async () => {
            try {
                const depth = await analysisApi.getDepth(currentSymbol.value)
                if (marketContext.value) {
                    marketContext.value.order_book = depth
                } else {
                    // 如果上下文还没加载，先初始化一个外壳以便让 MarketDepth.vue 拿到数据
                    marketContext.value = {
                        symbol: currentSymbol.value,
                        current_price: 0,
                        kline_summary: '',
                        indicators: {
                            rsi_14: 0,
                            macd_line: 0,
                            macd_signal: 0,
                            macd_histogram: 0,
                            sma_20: 0,
                            sma_50: 0,
                            bb_upper: 0,
                            bb_lower: 0,
                            trend_status: 'neutral',
                            ma_cross_status: 'none'
                        },
                        funding_rate: 0,
                        open_interest: 0,
                        news_headlines: [],
                        market_sentiment: 'neutral',
                        order_book: depth
                    }
                }
            } catch (e) {
                console.warn('深度轮询失败:', e)
            }
        }

        // 立即执行一次
        fetchDepth()
        // 每 3000ms 轮询
        depthTimer = setInterval(fetchDepth, 3000)
    }

    /**
     * 停止深度轮询
     */
    function stopDepthPolling() {
        if (depthTimer) {
            clearInterval(depthTimer)
            depthTimer = null
        }
    }

    // 返回store内容
    return {
        // 状态
        currentSymbol,
        symbols,
        marketContext,
        prediction,
        loading,
        error,
        // 计算属性
        currentSymbolInfo,
        currentPrice,
        isAnalyzing,
        // 方法
        loadSymbols,
        selectSymbol,
        loadMarketContext,
        analyze,
        clearPrediction,
        loadAllTickers,
        tickers,
        globalStats,
        loadGlobalStats,
        startDepthPolling,
        stopDepthPolling,
        klines: ref<any[]>([]) // Add klines state to satisfy type check
    }
})
