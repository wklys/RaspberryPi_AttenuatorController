# 测试文档

本项目包含完整的测试套件，用于验证衰减器控制系统的各个功能模块。

## 测试结构

```
tests/
├── __init__.py                          # 测试包初始化
├── conftest.py                          # 测试配置和共享fixtures
├── test_frequency_compensator.py        # 频率补偿器测试
├── test_serial_attenuator.py           # 串口衰减器测试
├── test_multi_attenuator_controller.py  # 多设备控制器测试
├── test_web_server.py                   # Web API接口测试
└── test_config.py                       # 配置文件加载测试
```

## 安装测试依赖

```bash
pip install -r requirements.txt
```

测试依赖包括：
- `pytest`: 测试框架
- `pytest-cov`: 代码覆盖率
- `pytest-mock`: 模拟对象
- `httpx`: HTTP客户端（用于API测试）

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定测试文件
```bash
pytest tests/test_frequency_compensator.py
pytest tests/test_serial_attenuator.py
pytest tests/test_multi_attenuator_controller.py
pytest tests/test_web_server.py
pytest tests/test_config.py
```

### 运行特定测试类或方法
```bash
# 运行特定测试类
pytest tests/test_frequency_compensator.py::TestFrequencyCompensator

# 运行特定测试方法
pytest tests/test_frequency_compensator.py::TestFrequencyCompensator::test_init_with_valid_file
```

### 使用标记运行测试
```bash
# 运行单元测试
pytest -m unit

# 运行API测试
pytest -m api

# 运行串口相关测试
pytest -m serial

# 排除慢速测试
pytest -m "not slow"
```

### 详细输出
```bash
# 显示详细输出
pytest -v

# 显示测试覆盖率
pytest --cov

# 生成HTML覆盖率报告
pytest --cov --cov-report=html
```

## 测试覆盖的功能

### 1. FrequencyCompensator 测试
- 初始化和文件加载
- 频率补偿计算
- 线性插值算法
- 边界条件处理
- 异常情况处理

### 2. SerialAttenuator 测试
- 串口连接和通信
- 衰减值设置和获取
- 频率设置
- 设备状态查询
- 命令发送和响应解析
- 异常处理

### 3. MultiAttenuatorController 测试
- 多设备管理
- 串口扫描和连接
- 批量操作
- 设备状态监控
- 配置文件管理
- 序列号映射

### 4. Web API 测试
- 所有REST API端点
- 请求参数验证
- 响应格式验证
- 错误处理
- 异常情况处理

### 5. 配置管理测试
- 配置文件加载
- JSON格式验证
- 错误处理
- 边界条件

## 测试数据和模拟

测试使用以下模拟策略：

1. **串口模拟**: 使用 `unittest.mock` 模拟串口通信
2. **文件系统模拟**: 使用临时文件进行测试
3. **HTTP客户端**: 使用 `TestClient` 进行API测试
4. **共享Fixtures**: 在 `conftest.py` 中定义可重用的测试数据

## 持续集成

测试配置支持持续集成环境：

```bash
# CI环境运行
pytest --cov --cov-report=xml --junitxml=test-results.xml
```

## 测试最佳实践

1. **隔离性**: 每个测试都是独立的，不依赖其他测试
2. **可重复性**: 测试结果在任何环境下都应该一致
3. **快速执行**: 大部分测试使用模拟对象，执行速度快
4. **全面覆盖**: 覆盖正常流程、边界条件和异常情况
5. **清晰命名**: 测试方法名称清楚描述测试内容

## 故障排除

### 常见问题

1. **导入错误**: 确保在项目根目录运行测试
2. **依赖缺失**: 运行 `pip install -r requirements.txt`
3. **权限问题**: 确保有临时文件创建权限

### 调试测试

```bash
# 在测试失败时进入调试器
pytest --pdb

# 显示详细的失败信息
pytest --tb=long

# 只运行失败的测试
pytest --lf
```
