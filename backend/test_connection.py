import os
import sys
from binance.client import Client

# 尝试读取环境变量
proxy = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
print(f"当前测试使用的代理: {proxy}")

try:
    print("正在尝试初始化 Binance Client...")
    requests_params = {'proxies': {'http': proxy, 'https': proxy}}
    client = Client(requests_params=requests_params)
    
    print("正在 Ping Binance API...")
    client.ping()
    print("✅ 连接成功！您的网络和代理配置没有问题。")
    print("代码中的问题可能是因为环境变量没有被正确读取。")
    
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("\n可能的解决方案：")
    print("1. 确认您的代理软件（Clash/V2Ray）已开启")
    print("2. 确认代理端口是否为 7890 (有些是 1080 或 1087)")
    print("3. 尝试在终端运行: export HTTP_PROXY=http://127.0.0.1:7890")
    print("4. 尝试更换代理节点（全局模式）")
