/**
 * 智链预测 - 前端入口文件
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import App from './App.vue'
import router from './router'
import './styles/main.scss'

// Debugging: Capture errors and show in DOM
// Debugging: Capture errors and show in DOM
function showError(msg: any) {
    let detail = '';
    try {
        if (msg instanceof Error) {
            detail = `${msg.message}\n\nStack:\n${msg.stack}`;
        } else if (typeof msg === 'object') {
            detail = '[Object Error] - Check console for details';
        } else {
            detail = String(msg);
        }
    } catch (e) {
        detail = '[Complex Error Object]';
    }

    const errorBox = document.createElement('div');
    errorBox.style.position = 'fixed';
    errorBox.style.top = '0';
    errorBox.style.left = '0';
    errorBox.style.width = '100vw';
    errorBox.style.height = '100vh';
    errorBox.style.zIndex = '999999';
    errorBox.style.backgroundColor = 'rgba(0,0,0,0.95)';
    errorBox.style.color = '#ff5555';
    errorBox.style.padding = '20px';
    errorBox.style.overflow = 'auto';
    errorBox.style.fontFamily = 'monospace';
    errorBox.style.fontSize = '14px';
    errorBox.style.whiteSpace = 'pre-wrap';
    errorBox.innerText = 'CRITICAL ERROR:\n\n' + detail;
    document.body.appendChild(errorBox);
}

window.onerror = function (message, source, lineno, colno, error) {
    // Ignore benign ResizeObserver error
    if (String(message).includes('ResizeObserver loop completed with undelivered notifications')) {
        return;
    }
    showError(error || message);
    console.error('Global Error:', error || message);
};
window.addEventListener('unhandledrejection', event => {
    showError(event.reason);
    console.error('Unhandled Rejection:', event.reason);
});


// Patch console.warn to avoid "Cannot convert object to primitive value" crashes
const originalWarn = console.warn
console.warn = (...args) => {
    try {
        originalWarn(...args)
    } catch (e) {
        // Silently swallow errors during warning printing (often caused by Proxy stringification)
        console.error('Scalped console.warn error:', e)
    }
}

const app = createApp(App)

// 注册所有Element Plus图标 (使用 markRaw 包装可选，但 app.component 本身不具响应式)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, {
    locale: zhCn,
})

app.mount('#app')
