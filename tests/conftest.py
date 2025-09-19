import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from serial_attenuator import FrequencyCompensator, SerialAttenuator, MultiAttenuatorController


@pytest.fixture
def sample_frequency_data():
    """提供测试用的频率补偿数据"""
    return {
        "1000": 0.5,
        "2000": 1.0,
        "3000": 1.5,
        "4000": 2.0,
        "5000": 2.5
    }


@pytest.fixture
def temp_json_file(sample_frequency_data):
    """创建临时JSON文件用于测试"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_frequency_data, f)
        temp_file = f.name
    
    yield temp_file
    
    # 清理临时文件
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_serial():
    """模拟串口对象"""
    mock = Mock()
    mock.is_open = True
    mock.port = 'COM1'
    mock.baudrate = 9600
    mock.write.return_value = None
    mock.read.return_value = b'OK\r\n'
    mock.readline.return_value = b'OK\r\n'
    mock.close.return_value = None
    # 设置 in_waiting 为 PropertyMock，这样可以设置 side_effect
    from unittest.mock import PropertyMock
    type(mock).in_waiting = PropertyMock(return_value=0)
    return mock


@pytest.fixture
def frequency_compensator(temp_json_file):
    """创建FrequencyCompensator实例"""
    return FrequencyCompensator(temp_json_file)


@pytest.fixture
def mock_serial_attenuator(mock_serial):
    """创建模拟的SerialAttenuator实例"""
    with patch('serial.Serial', return_value=mock_serial):
        attenuator = SerialAttenuator('COM1')
        attenuator.serial_conn = mock_serial
        attenuator.is_connected = True
        # 确保 lock 属性存在
        import threading
        attenuator.lock = threading.Lock()
        return attenuator


@pytest.fixture
def sample_config():
    """提供测试用的配置数据"""
    return {
        "frequency": {
            "json_file": "1.json"
        },
        "serial": {
            "baudrate": 9600,
            "timeout": 1.0
        }
    }


@pytest.fixture
def temp_config_file(sample_config):
    """创建临时配置文件用于测试"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_config, f)
        temp_file = f.name
    
    yield temp_file
    
    # 清理临时文件
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_controller(temp_json_file):
    """创建模拟的MultiAttenuatorController实例"""
    with patch('serial.Serial'):
        controller = MultiAttenuatorController(temp_json_file)
        return controller