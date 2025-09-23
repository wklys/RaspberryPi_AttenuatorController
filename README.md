# WCS衰减器控制系统 v1.1.1

基于FastAPI的多路衰减器控制系统，提供现代化Web界面进行远程控制和管理。由测升科技（上海）责任有限公司开发。

## 功能特性

- 🔌 **多设备管理**: 支持同时控制多个串口衰减器设备
- 📡 **频率补偿**: 基于JSON配置文件的频率-损耗自动补偿
- 🎛️ **实时控制**: 单独或批量设置衰减值，支持0-90dB范围
- 🌐 **现代Web界面**: 响应式设计，支持移动端访问
- 📊 **状态监控**: 实时显示设备连接状态和参数
- 📝 **操作日志**: 完整的操作记录和系统日志
- ⚡ **高性能**: 异步处理，支持并发操作

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│   FastAPI       │◄──►│  Serial Devices │
│                 │    │   Web Server    │    │   (Attenuators) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        │                        │                        │
   ┌─────────┐            ┌─────────────┐         ┌─────────────┐
   │ Static  │            │ Frequency   │         │   Device    │
   │ Files   │            │ Compensation│         │  Management │
   └─────────┘            └─────────────┘         └─────────────┘
```

## 快速开始

### 环境要求
- Python 3.8+
- Windows/Linux/macOS
- 串口设备访问权限

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd AttCtrl
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置设备**
   - 连接串口衰减器设备
   - 确保串口权限正确配置

4. **启动服务**
   ```bash
   python web_server.py
   ```

5. **访问界面**
   打开浏览器访问: `http://localhost:8000`

## 使用指南

### 设备连接
1. 点击"扫描串口"查找可用设备
2. 选择要连接的串口
3. 点击"连接设备"建立连接

### 频率设置
1. 在频率输入框中输入工作频率(MHz)
2. 点击"设置频率"应用设置
3. 系统自动根据补偿文件调整损耗

### 衰减控制
- **批量设置**: 同时设置所有设备的衰减值
- **单独控制**: 针对特定设备设置衰减值
- **快速设置**: 使用预设按钮快速设置常用值

## API接口

### 设备管理
- `GET /api/scan_ports` - 扫描可用串口
- `POST /api/connect` - 连接设备
- `POST /api/disconnect` - 断开所有连接
- `GET /api/devices` - 获取设备状态列表
- `GET /api/devices/ids` - 获取设备ID列表

### 衰减控制
- `POST /api/set_attenuation` - 批量设置衰减值
- `GET /api/get_attenuation` - 获取所有设备衰减值
- `POST /api/attenuators/set` - 设置单个设备衰减值
- `GET /api/attenuators/{device_id}` - 获取单个设备状态
- `GET /api/get_attenuation_range` - 获取衰减值范围
- `GET /api/get_min_attenuation` - 获取最小衰减值

### 频率管理
- `POST /api/set_frequency` - 设置工作频率
- `GET /api/get_frequency` - 获取当前频率

### 系统状态
- `GET /api/status` - 获取系统运行状态

## 配置文件

### config.json
```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "serial": {
        "baudrate": 9600,
        "timeout": 2.0
    },
    "frequency": {
        "json_file": "1.json",
        "default_frequency": 1000.0
    }
}
```

### 频率补偿文件
补偿文件位于 `compensation_files/` 目录，格式为JSON：
```json
{
    "frequency_compensation": {
        "1000.0": 2.5,
        "2000.0": 3.2,
        "5000.0": 4.1
    }
}
```

## 项目结构

```
AttCtrl/
├── web_server.py              # FastAPI主服务器
├── serial_attenuator.py       # 串口设备控制模块
├── start_server.py           # 启动脚本
├── config.json              # 系统配置
├── requirements.txt         # Python依赖
├── compensation_files/      # 频率补偿数据
│   ├── 1.json
│   ├── 2.json
│   └── ...
├── static/                 # 静态资源
│   ├── css/
│   │   ├── bootstrap.min.css
│   │   ├── bootstrap-icons.css
│   │   └── style.css
│   ├── js/
│   │   ├── app.js
│   │   └── bootstrap.bundle.min.js
│   ├── fonts/
│   └── favicon.svg
├── templates/             # HTML模板
│   └── index.html
└── tests/                # 测试文件
    ├── test_serial_attenuator.py
    ├── test_web_server.py
    └── ...
```

## 开发说明

### 运行测试
```bash
pytest tests/
```

### 开发模式启动
```bash
uvicorn web_server:app --reload --host 0.0.0.0 --port 8000
```

### 添加新设备支持
1. 在 `serial_attenuator.py` 中扩展设备类
2. 更新通信协议处理
3. 添加相应的测试用例

## 故障排除

### 常见问题

1. **串口权限错误**
   - Windows: 检查设备管理器中的COM端口
   - Linux: 添加用户到dialout组 `sudo usermod -a -G dialout $USER`

2. **端口被占用**
   ```bash
   # 查找占用进程
   netstat -ano | findstr :8000
   # 或使用其他端口启动
   python web_server.py --port 8080
   ```

3. **设备连接失败**
   - 检查串口线缆连接
   - 确认设备电源状态
   - 验证波特率设置

4. **频率补偿不生效**
   - 检查补偿文件格式
   - 确认频率值在补偿范围内
   - 查看系统日志获取详细信息

### 日志查看
```bash
# 查看应用日志
tail -f attenuator_control.log

# 启用调试模式
python web_server.py --log-level debug
```

## 版本历史

### v1.1.1 (当前版本)
- 优化定时器间隔，减少系统负载
- 添加网页版本号显示
- 修复favicon显示问题
- 改进错误处理和日志记录

### v1.1.0
- 添加单设备控制API
- 优化前端界面响应速度
- 增强设备状态监控

### v1.0.0
- 初始版本发布
- 基础的多设备控制功能
- Web界面和API接口

## 技术支持

如遇到问题或需要技术支持，请：
1. 查看本文档的故障排除部分
2. 检查系统日志文件
3. 联系开发团队获取帮助（1073494339@qq.com 黄工）
