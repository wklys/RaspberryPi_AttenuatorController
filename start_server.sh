#!/bin/bash
# 树莓派衰减器控制系统启动脚本

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    log_info "检查Python版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        log_success "找到Python3: $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        if [[ $PYTHON_VERSION == 3.* ]]; then
            PYTHON_CMD="python"
            log_success "找到Python: $PYTHON_VERSION"
        else
            log_error "需要Python 3.x，当前版本: $PYTHON_VERSION"
            return 1
        fi
    else
        log_error "未找到Python，请先安装Python 3.x"
        return 1
    fi
    
    return 0
}

# 检查虚拟环境
check_venv() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        log_success "检测到虚拟环境: $VIRTUAL_ENV"
        return 0
    else
        log_warning "未检测到虚拟环境"
        
        # 检查是否存在venv目录
        if [[ -d "venv" ]]; then
            log_info "发现venv目录，尝试激活..."
            source venv/bin/activate
            if [[ "$VIRTUAL_ENV" != "" ]]; then
                log_success "虚拟环境激活成功"
                return 0
            fi
        fi
        
        log_warning "建议使用虚拟环境运行程序"
        return 0
    fi
}

# 检查依赖包
check_dependencies() {
    log_info "检查依赖包..."
    
    if [[ ! -f "requirements.txt" ]]; then
        log_error "未找到requirements.txt文件"
        return 1
    fi
    
    # 检查关键依赖
    local missing_deps=()
    
    if ! $PYTHON_CMD -c "import fastapi" &> /dev/null; then
        missing_deps+=("fastapi")
    fi
    
    if ! $PYTHON_CMD -c "import uvicorn" &> /dev/null; then
        missing_deps+=("uvicorn")
    fi
    
    if ! $PYTHON_CMD -c "import serial" &> /dev/null; then
        missing_deps+=("pyserial")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "缺少以下依赖包: ${missing_deps[*]}"
        log_info "正在安装依赖包..."
        
        if ! $PYTHON_CMD -m pip install -r requirements.txt; then
            log_error "安装依赖包失败"
            return 1
        fi
        
        log_success "依赖包安装完成"
    else
        log_success "所有依赖包已安装"
    fi
    
    return 0
}

# 检查串口权限
check_serial_permissions() {
    log_info "检查串口权限..."
    
    # 检查用户是否在dialout组中
    if groups | grep -q dialout; then
        log_success "用户已在dialout组中"
    else
        log_warning "用户不在dialout组中，可能无法访问串口设备"
        log_info "请运行: sudo usermod -a -G dialout \$USER"
        log_info "然后重新登录或重启系统"
    fi
    
    # 检查ACM串口设备
    local serial_devices=()
    for device in /dev/ttyACM*; do
        if [[ -e "$device" ]]; then
            serial_devices+=("$device")
        fi
    done
    
    if [[ ${#serial_devices[@]} -gt 0 ]]; then
        log_success "发现串口设备: ${serial_devices[*]}"
    else
        log_warning "未发现串口设备"
    fi
}

# 创建频率补偿示例文件
create_sample_frequency_file() {
    local freq_file="frequency_loss1.xlsx"
    
    if [[ ! -f "$freq_file" ]]; then
        log_warning "未找到频率补偿文件: $freq_file"
        log_info "将使用默认补偿数据"
        
        # 创建示例CSV文件（如果pandas可用的话）
        if $PYTHON_CMD -c "import pandas" &> /dev/null; then
            log_info "创建示例频率补偿文件..."
            $PYTHON_CMD -c "
import pandas as pd
import numpy as np

# 创建示例数据
frequencies = np.arange(10, 230, 10)  # 10MHz到220MHz，步长10MHz
losses = -1.8 - 0.001 * frequencies  # 简单的线性损耗模型

df = pd.DataFrame({
    '频率(MHz)': frequencies,
    '插入损耗(dB)': losses
})

df.to_excel('$freq_file', index=False)
print('示例频率补偿文件已创建')
"
        fi
    else
        log_success "找到频率补偿文件: $freq_file"
    fi
}

# 启动服务器
start_server() {
    log_info "启动树莓派衰减器控制系统..."
    
    # 解析命令行参数
    local host="0.0.0.0"
    local port="8000"
    local reload=""
    local debug=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                host="$2"
                shift 2
                ;;
            --port)
                port="$2"
                shift 2
                ;;
            --reload)
                reload="--reload"
                shift
                ;;
            --debug)
                debug="--debug"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "服务器配置:"
    log_info "  地址: $host"
    log_info "  端口: $port"
    log_info "  重载: ${reload:-否}"
    log_info "  调试: ${debug:-否}"
    
    echo
    log_success "系统启动完成！"
    log_info "请在浏览器中访问: http://$host:$port"
    log_info "按 Ctrl+C 停止服务器"
    echo
    
    # 启动Python服务器
    exec $PYTHON_CMD start_server.py --host "$host" --port "$port" $reload $debug
}

# 主函数
main() {
    echo "=================================================="
    echo "    树莓派衰减器控制系统启动脚本"
    echo "=================================================="
    echo
    
    # 检查Python
    if ! check_python; then
        exit 1
    fi
    
    # 检查虚拟环境
    check_venv
    
    # 检查依赖
    if ! check_dependencies; then
        exit 1
    fi
    
    # 检查串口权限
    check_serial_permissions
    
    # 创建示例文件
    create_sample_frequency_file
    
    echo
    log_info "系统检查完成，准备启动服务器..."
    sleep 2
    
    # 启动服务器
    start_server "$@"
}

# 信号处理
trap 'log_info "收到中断信号，正在关闭..."; exit 0' INT TERM

# 运行主函数
main "$@"