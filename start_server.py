#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树莓派衰减器控制系统启动脚本
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def load_config():
    """加载配置文件"""
    config_file = current_dir / "config.json"
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f"警告: 配置文件 {config_file} 不存在，使用默认配置")
        return {
            "server": {"host": "0.0.0.0", "port": 8000},
            "logging": {"level": "INFO"}
        }

def setup_logging(config):
    """设置日志"""
    log_level = getattr(logging, config.get("logging", {}).get("level", "INFO"))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                current_dir / config.get("logging", {}).get("log_file", "attenuator_control.log"),
                encoding='utf-8'
            )
        ]
    )

def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'serial',
        'pandas',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("错误: 缺少以下依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="树莓派衰减器控制系统")
    parser.add_argument("--host", help="服务器地址")
    parser.add_argument("--port", type=int, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--config", help="配置文件路径")
    
    args = parser.parse_args()
    
    # 加载配置
    if args.config:
        config_file = Path(args.config)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            print(f"错误: 配置文件 {config_file} 不存在")
            return 1
    else:
        config = load_config()
    
    # 设置日志
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 获取服务器配置
    server_config = config.get("server", {})
    host = args.host or server_config.get("host", "0.0.0.0")
    port = args.port or server_config.get("port", 8000)
    reload = args.reload or server_config.get("reload", False)
    debug = args.debug or server_config.get("debug", False)
    
    logger.info("=" * 50)
    logger.info("树莓派衰减器控制系统启动")
    logger.info("=" * 50)
    logger.info(f"服务器地址: {host}:{port}")
    logger.info(f"调试模式: {debug}")
    logger.info(f"自动重载: {reload}")
    logger.info(f"工作目录: {current_dir}")
    
    try:
        # 导入并启动Web服务器
        import uvicorn
        from web_server import app
        
        logger.info("正在启动Web服务器...")
        
        uvicorn.run(
            "web_server:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info" if debug else "warning",
            access_log=debug
        )
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"启动服务器失败: {e}")
        return 1
    finally:
        logger.info("服务器已关闭")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())