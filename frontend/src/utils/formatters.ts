/**
 * 智链预测 - 通用格式化工具
 */

/**
 * 格式化价格显示
 * 支持加密货币多位小数，自动根据数值大小调整精度
 * @param price 价格数值
 * @returns 格式化后的字符串
 */
export function formatPrice(price: number | string): string {
    const val = typeof price === 'string' ? parseFloat(price.replace(/,/g, '')) : price
    if (isNaN(val) || val === 0) return '-'

    if (val >= 1000) {
        // 大于1000的价格，保留2位小数，支持千分位
        return val.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })
    } else if (val >= 1) {
        // 1 - 1000 之间的价格，保留2-4位小数
        return val.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 4
        })
    } else if (val >= 0.0001) {
        // 小微币种价格，保留6位小数
        return val.toFixed(6)
    } else {
        // 极小价格（如萨摩币等），保留8位小数
        return val.toFixed(8)
    }
}

/**
 * 格式化日期时间
 * @param timeStr ISO日期字符串或时间戳
 * @param formatType 格式类型 'full' | 'short'
 */
export function formatTime(timeStr: string | number, formatType: 'full' | 'short' = 'full'): string {
    if (!timeStr) return '-'
    try {
        const date = new Date(timeStr)
        if (formatType === 'short') {
            return date.toLocaleString('zh-CN', {
                month: 'numeric',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            })
        }
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        })
    } catch (e) {
        return String(timeStr)
    }
}
