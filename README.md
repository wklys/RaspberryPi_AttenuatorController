# WCS衰减器控制系统

基于树莓派的串口衰减器控制系统，提供Web界面进行远程控制。

## 功能特性

- 🔌 **串口设备管理**: 自动扫描和连接多个串口衰减器设备
- 📡 **频率补偿**: 基于Excel文件的频率-损耗补偿功能
- 🎛️ **批量控制**: 同时控制多个衰减器设备
- 🌐 **Web界面**: 现代化的响应式Web控制界面
- 📊 **实时监控**: 设备状态和参数实时显示
- 📝 **操作日志**: 详细的操作记录和系统日志

## 系统要求

### 硬件要求
- 树莓派 4B/5 (推荐)
- USB转串口模块或直接串口连接
- 支持的衰减器设备

### 软件要求
- Python 3.8+
- 现代Web浏览器

## 安装部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd AttCtrl
```

### 2. 创建虚拟环境 (推荐)
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置串口权限
```bash
# 将用户添加到dialout组
sudo usermod -a -G dialout $USER

# 重新登录或重启系统使权限生效
```

### 5. 准备频率补偿文件
将包含频率-损耗数据的Excel文件命名为 `frequency_loss.xlsx` 并放在项目根目录。

Excel文件格式:
- 第一列: 频率 (MHz)
- 第二列: 插入损耗 (dB，通常为负值)

示例:
```
频率(MHz) | 插入损耗(dB)
---------|------------
10       | -1.86
18       | -1.86
26       | -1.95
...      | ...
```

## 启动系统

### 方法1: 使用启动脚本 (推荐)
```bash
# 给脚本执行权限
chmod +x start_server.sh

# 启动系统
./start_server.sh

# 自定义参数启动
./start_server.sh --host 0.0.0.0 --port 8000 --debug
```

### 方法2: 直接使用Python
```bash
python3 start_server.py --host 0.0.0.0 --port 8000
```

### 方法3: 开发模式
```bash
python3 web_server.py --reload --debug
```

## 使用说明

### 1. 访问Web界面
启动系统后，在浏览器中访问:
```
http://树莓派IP地址:8000
```

### 2. 连接设备
1. 点击"扫描串口"按钮查找可用设备
2. 选择要连接的串口设备
3. 点击"连接设备"建立连接

### 3. 设置频率
1. 在频率设置区域输入工作频率 (MHz)
2. 点击"设置频率"应用设置
3. 系统会根据频率自动进行损耗补偿

### 4. 控制衰减值
1. 输入目标衰减值 (0-90 dB)
2. 点击"批量设置衰减值"同时设置所有设备
3. 使用快速设置按钮快速设置常用值

### 5. 监控状态
- 设备状态表格显示所有连接设备的实时状态
- 操作日志记录所有操作和系统事件

## 串口通信协议

### 设置衰减值
```
发送: att-XX.XX\r\n
响应: attOK
```

### 读取衰减值
```
发送: READ\r\n
响应: (设备相关格式)
```

### 通信参数
- **TTL串口**: 波特率 9600
- **USB虚拟串口**: 自动检测波特率
- **超时**: 2秒

## API接口

系统提供RESTful API接口:

### 设备管理
- `GET /api/scan_ports` - 扫描串口设备
- `POST /api/connect` - 连接设备
- `POST /api/disconnect` - 断开连接
- `GET /api/devices` - 获取设备状态

### 频率控制
- `POST /api/set_frequency` - 设置工作频率
- `GET /api/get_frequency` - 获取当前频率

### 衰减控制
- `POST /api/set_attenuation` - 设置衰减值
- `GET /api/get_attenuation` - 获取衰减值

### 系统状态
- `GET /api/status` - 获取系统状态

## 配置文件

`config.json` 包含系统配置参数:

```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "serial": {
        "default_baudrate": 9600,
        "timeout": 2.0
    },
    "frequency": {
        "default_frequency": 1000.0,
        "excel_file": "frequency_loss.xlsx"
    },
    "attenuation": {
        "min_value": 0.0,
        "max_value": 90.0
    }
}
```

## 系统服务

### 创建systemd服务
```bash
sudo nano /etc/systemd/system/attenuator-control.service
```

服务文件内容:
```ini
[Unit]
Description=Raspberry Pi Attenuator Control System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/AttCtrl
ExecStart=/home/pi/AttCtrl/venv/bin/python start_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable attenuator-control.service
sudo systemctl start attenuator-control.service
```

## 故障排除

### 常见问题

1. **串口权限问题**
   ```bash
   # 检查用户组
   groups
   
   # 添加到dialout组
   sudo usermod -a -G dialout $USER
   ```

2. **端口被占用**
   ```bash
   # 查找占用端口的进程
   sudo lsof -i :8000
   
   # 或使用其他端口
   ./start_server.sh --port 8080
   ```

3. **依赖包问题**
   ```bash
   # 重新安装依赖
   pip install -r requirements.txt --force-reinstall
   ```

4. **串口设备未找到**
   ```bash
   # 列出串口设备
   ls /dev/tty*
   
   # 检查USB设备
   lsusb
   ```

### 日志查看
```bash
# 查看系统日志
tail -f attenuator_control.log

# 查看systemd服务日志
sudo journalctl -u attenuator-control.service -f
```

## 开发说明

### 项目结构
```
AttCtrl/
├── serial_attenuator.py    # 串口控制核心模块
├── web_server.py          # FastAPI Web服务器
├── start_server.py        # 启动脚本
├── config.json           # 配置文件
├── requirements.txt      # Python依赖
├── templates/           # HTML模板
│   └── index.html
├── static/             # 静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── README.md
```

### 扩展开发
1. 修改 `serial_attenuator.py` 添加新的设备支持
2. 在 `web_server.py` 中添加新的API接口
3. 更新前端 `app.js` 添加新功能
4. 修改 `config.json` 添加新配置项

## 许可证

本项目采用 MIT 许可证。

## 技术支持

如有问题或建议，请联系开发团队。