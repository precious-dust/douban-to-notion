"""
快速设置脚本 - 用于初始化项目配置
"""

import os
import yaml
from pathlib import Path


def setup_config():
    """交互式配置设置"""
    print("\n" + "="*50)
    print("豆瓣到Notion同步工具 - 快速设置")
    print("="*50 + "\n")
    
    config_path = Path("config/config.yaml")
    
    # 读取现有配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 豆瓣配置
    print("【豆瓣配置】")
    print("如何获取Cookie：打开豆瓣 -> F12 -> Network -> 找到任何请求 -> Headers中的Cookie")
    cookie = input("请输入豆瓣Cookie (直接按Enter保持不变): ").strip()
    if cookie:
        config['douban']['cookie'] = cookie
    
    user_id = input("请输入豆瓣用户ID (从个人页面URL获取，如 123456789): ").strip()
    if user_id:
        config['douban']['user_id'] = user_id
    
    # Notion配置
    print("\n【Notion配置】")
    print("如何获取API Token：https://www.notion.so/my-integrations -> New integration")
    api_token = input("请输入Notion API Token (secret_...): ").strip()
    if api_token:
        config['notion']['api_token'] = api_token
    
    database_id = input("请输入Notion Database ID (从数据库URL获取): ").strip()
    if database_id:
        config['notion']['database_id'] = database_id
    
    # 同步配置
    print("\n【同步配置】")
    interval = input("定时同步间隔（分钟，默认60）: ").strip()
    if interval:
        try:
            config['sync']['interval_minutes'] = int(interval)
        except ValueError:
            print("无效的数字，使用默认值")
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print("\n✓ 配置已保存！")
    print("现在可以运行：python src/main.py --sync-now")


if __name__ == "__main__":
    try:
        setup_config()
    except KeyboardInterrupt:
        print("\n\n已取消设置")
    except Exception as e:
        print(f"\n设置出错：{e}")
