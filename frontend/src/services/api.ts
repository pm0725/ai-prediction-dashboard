/**
 * 智链预测 - API服务层
 */
import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const api: AxiosInstance = axios.create({
    baseURL: '/api',
    timeout: 300000, // 5分钟超时，AI深度思考可能需要较长时间
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
api.interceptors.request.use(
    (config) => {
        // 可以在这里添加token等
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// 响应拦截器
api.interceptors.response.use(
    (response: AxiosResponse) => {
        return response.data
    },
    (error) => {
        let message = '请求失败'
        const detail = error.response?.data?.detail

        if (detail) {
            if (typeof detail === 'string') message = detail
            else if (typeof detail === 'object') message = JSON.stringify(detail)
        } else if (error.message) {
            message = error.message
        }

        ElMessage.error(message)
        return Promise.reject(error)
    }
)

// ============================================================
// API接口定义
// ============================================================

/** 交易信号类型 */
export interface TradingSignal {
    type: 'LONG' | 'SHORT' | 'WAIT'
    entry?: number
    stop_loss?: number
    take_profit?: number[]
    position_size: string
    risk_reward_ratio?: number
}

/** 预测结果类型 */
export interface PredictionResult {
    symbol: string
    analysis_time: string
    timeframe: string
    prediction: string
    prediction_cn?: string
    confidence: number
    reasoning: any
    key_levels: {
        supports?: number[]
        resistances?: number[]
        current_price?: number
        // 兼容旧字段
        strong_resistance?: number
        weak_resistance?: number
        weak_support?: number
        strong_support?: number
        [key: string]: any
    }
    trading_signals?: TradingSignal[]
    // 兼容旧字段
    suggested_action?: string
    entry_zone?: {
        low: number
        high: number
    }
    stop_loss?: number
    take_profit?: number[]
    risk_level: string
    risk_warning: string[]
    summary: string
    // [新增] AI配置元数据
    ai_model?: string
    ai_prompt_template?: string

    // 新增透传字段
    trend_context?: {
        summary: string
        rsi: number
        trend_status: string
    }
    order_book_context?: {
        bid_ask_ratio: number
        total_bid_volume: number
        total_ask_volume: number
        major_support: { price: number; volume: number }
        major_resistance: { price: number; volume: number }
    }
    on_chain_context?: {
        whale_activity: any
        liquidity_gaps: string[]
        volatility_score: number
    }
}

/** 策略请求类型 */
export interface StrategyRequest {
    symbol: string
    prediction: string
    confidence: number
    entry_zone?: { low: number; high: number }
    stop_loss?: number
    take_profit?: number[]
    risk_level: string
    on_chain_context?: any
}

/** 策略结果类型 */
export interface StrategyResult {
    symbol: string
    generated_at: string
    direction: string
    position_sizing: {
        percentage_of_capital: number
        max_leverage: number
        risk_per_trade: string
    }
    entry: {
        type: string
        zone?: { low: number; high: number }
        condition: string
    }
    stop_loss: {
        price: number
        type: string
        note: string
    }
    take_profit: Array<{
        level: number
        price: number
        close_percentage: number
    }>
    trade_management: string[]
    warnings: string[]
    on_chain_context?: any
}

/** 交易对信息 */
export interface SymbolInfo {
    symbol: string
    name: string
    base: string
}

/** 市场上下文 */
export interface MarketContext {
    symbol: string
    current_price: number
    price_change_24h?: number
    volume_24h?: number
    kline_summary: string
    klines?: Array<{
        timestamp: number
        open: number
        high: number
        low: number
        close: number
        volume: number
    }>
    indicators: {
        rsi_14: number
        macd_line: number
        macd_signal: number
        macd_histogram: number
        sma_20: number
        sma_50: number
        bb_upper: number
        bb_lower: number
        trend_status: string
        ma_cross_status: string
        volatility_level?: string
    }
    funding_rate: number
    open_interest: number
    volatility_score?: number
    whale_activity?: any
    liquidity_gaps?: string[]
    news_headlines: string[]
    market_sentiment: string
    // 新增核心字段
    order_book?: {
        bid_ask_ratio: number
        total_bid_volume: number
        total_ask_volume: number
        major_support: { price: number; volume: number }
        major_resistance: { price: number; volume: number }
    }
    trend_context?: {
        summary: string
        rsi: number
        trend_status: string
    }
}

/** 市场简报类型 */
export interface MarketTicker {
    symbol: string
    price: number
    change_percent: number
}

// ============================================================
// API方法
// ============================================================

export const analysisApi = {
    /**
     * 健康检查
     */
    healthCheck: (): Promise<{ status: string; timestamp: string; version: string }> => {
        return api.get('/analysis/health')
    },

    /**
     * 获取AI预测分析
     */
    getPrediction: (symbol: string, timeframe: string = '4h', useCache: boolean = true, depth: string = 'standard', risk: number = 50, model?: string, promptTemplate?: string): Promise<PredictionResult> => {
        return api.post(`/analysis/predict?use_cache=${useCache}`, {
            symbol,
            timeframe,
            analysis_depth: depth,
            risk_preference: risk,
            model,
            prompt_template: promptTemplate
        })
    },

    /**
     * 获取市场上下文数据
     */
    getMarketContext: (symbol: string): Promise<MarketContext> => {
        return api.get(`/analysis/context/${symbol}`)
    },

    /**
     * 生成交易策略
     */
    generateStrategy: (request: StrategyRequest): Promise<StrategyResult> => {
        return api.post('/analysis/strategy/generate', request)
    },

    /**
     * 获取支持的交易对列表
     */
    getSymbols: (): Promise<{ symbols: SymbolInfo[] }> => {
        return api.get('/analysis/symbols')
    },

    /**
     * 获取AI预测分析 (流式)
     */
    getStreamPrediction: async (symbol: string, timeframe: string = '4h', depth: string = 'standard', risk: number = 50, onChunk: (text: string) => void, model?: string, promptTemplate?: string): Promise<void> => {
        const response = await fetch('/api/analysis/predict/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol,
                timeframe,
                analysis_depth: depth,
                risk_preference: risk,
                model,
                prompt_template: promptTemplate
            })
        })

        if (!response.body) throw new Error('ReadableStream not supported')

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            const chunk = decoder.decode(value, { stream: true })
            const lines = chunk.split('\n')

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6)
                    if (data === '[DONE]') break
                    try {
                        const parsed = JSON.parse(data)
                        if (parsed.content) onChunk(parsed.content)
                    } catch (e) {
                        console.error('Failed to parse SSE chunk:', data)
                    }
                }
            }
        }
    },

    /**
     * 全场批量扫描
     */
    getBatchScan: (symbols: string[], timeframe: string = '4h', model?: string, promptTemplate?: string): Promise<any> => {
        return api.post('/analysis/batch-scan', {
            symbols,
            timeframe,
            model,
            prompt_template: promptTemplate
        })
    },

    /**
     * 批量获取行情
     */
    getTickers: (symbols: string[]): Promise<MarketTicker[]> => {
        return api.get('/market/tickers', { params: { symbols: symbols.join(',') } })
    },

    /**
     * 清空缓存
     */
    clearCache: (): Promise<any> => {
        return api.post('/analysis/cache/clear')
    },

    /**
     * 获取全局市场状态
     */
    getGlobalStats: (): Promise<any> => {
        return api.get('/market/global')
    },

    /**
     * 获取实时深度摘要
     */
    getDepth: (symbol: string): Promise<any> => {
        return api.get('/market/depth', { params: { symbol } })
    }
}

export default api
