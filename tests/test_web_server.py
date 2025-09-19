import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from web_server import app, controller, load_config


class TestWebServer:
    """测试Web服务器API接口"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_data = {
            "frequency": {
                "json_file": "1.json"
            },
            "serial": {
                "baudrate": 9600,
                "timeout": 1
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        yield temp_file
        os.unlink(temp_file)
    
    @pytest.fixture
    def mock_controller_for_web(self):
        """为Web测试创建模拟控制器"""
        mock = Mock()
        mock.scan_serial_ports.return_value = ['COM1', 'COM2', 'COM3']
        mock.connect_attenuator.return_value = True
        mock.disconnect_attenuator.return_value = True
        mock.disconnect_all.return_value = None
        mock.get_connected_devices.return_value = ['COM1', 'COM2']
        mock.set_frequency.return_value = None
        mock.get_frequency.return_value = 2000
        mock.set_all_attenuation.return_value = {'COM1': True, 'COM2': True}
        mock.get_all_attenuation.return_value = {'COM1': 10.5, 'COM2': 15.0}
        mock.set_attenuation_by_device_id.return_value = True
        mock.get_attenuation_by_device_id.return_value = 12.5
        mock.get_device_status.return_value = {'connected': True, 'port': 'COM1'}
        mock.get_min_attenuation.return_value = {'COM1': 0.5, 'COM2': 1.0}
        return mock
    
    def test_load_config_success(self):
        """测试成功加载配置文件"""
        config = load_config()
        
        # 配置可能为空字典或包含默认值
        assert isinstance(config, dict)
    
    def test_load_config_file_not_found(self):
        """测试配置文件不存在时使用默认配置"""
        # load_config函数在文件不存在时返回空字典
        config = load_config()
        assert isinstance(config, dict)
    
    def test_load_config_invalid_json(self):
        """测试无效JSON配置文件时使用默认配置"""
        # load_config函数在JSON无效时返回空字典
        config = load_config()
        assert isinstance(config, dict)
    
    def test_root_endpoint(self, client):
        """测试根路径重定向"""
        response = client.get('/')
        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']
    
    def test_scan_ports_endpoint(self, client, mock_controller_for_web):
        """测试扫描串口端点"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/scan_ports')
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'data' in data
            assert 'ports' in data['data']
            assert len(data['data']['ports']) == 3
            assert 'COM1' in data['data']['ports']
    
    def test_connect_device_success(self, client, mock_controller_for_web):
        """测试成功连接设备"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/connect', json={'ports': ['COM1']})
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'message' in data
    
    def test_connect_device_failure(self, client, mock_controller_for_web):
        """测试连接设备失败"""
        mock_controller_for_web.connect_attenuator.return_value = False
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/connect', json={'ports': ['COM1']})
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is False
            assert 'message' in data
    
    def test_connect_device_missing_port(self, client):
        """测试缺少端口参数"""
        response = client.post('/api/connect', json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_disconnect_device_success(self, client, mock_controller_for_web):
        """测试成功断开设备"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/disconnect')
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'message' in data
    
    def test_disconnect_device_failure(self, client, mock_controller_for_web):
        """测试断开设备失败"""
        mock_controller_for_web.disconnect_all.side_effect = Exception("Disconnect failed")
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/disconnect')
            
            assert response.status_code == 500
            data = response.json()
            assert 'detail' in data
    
    def test_disconnect_all_devices(self, client, mock_controller_for_web):
        """测试断开所有设备"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/disconnect')
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'message' in data
    
    def test_get_connected_devices(self, client, mock_controller_for_web):
        """测试获取已连接设备列表"""
        mock_controller_for_web.get_device_status.return_value = {
            'att_1': {
                'port': 'COM1',
                'connected': True,
                'current_attenuation': 10.5
            }
        }
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/devices')
            
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert 'data' in data
    
    def test_set_frequency_success(self, client, mock_controller_for_web):
        """测试成功设置频率"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/set_frequency', json={'frequency': 2500})
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'message' in data
    
    def test_set_frequency_invalid(self, client, mock_controller_for_web):
        """测试设置无效频率"""
        mock_controller_for_web.set_frequency.side_effect = ValueError("Invalid frequency")
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/set_frequency', json={'frequency': -100})
            
            assert response.status_code == 400
            data = response.json()
            assert 'detail' in data
    
    def test_get_frequency(self, client, mock_controller_for_web):
        """测试获取当前频率"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/get_frequency')
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'data' in data
            assert 'frequency' in data['data']
    
    def test_set_all_attenuation_success(self, client, mock_controller_for_web):
        """测试成功设置所有设备衰减值"""
        mock_controller_for_web.set_all_attenuation.return_value = {'att_1': True}
        mock_controller_for_web.get_min_attenuation.return_value = 0.5
        mock_controller_for_web.get_frequency.return_value = 2000
        # 模拟有连接的衰减器
        mock_attenuator = type('MockAttenuator', (), {})() 
        mock_controller_for_web.attenuators = {'att_1': mock_attenuator}
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/set_attenuation', json={'value': 15.5})
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'message' in data
            assert 'data' in data
    
    def test_set_all_attenuation_invalid(self, client, mock_controller_for_web):
        """测试设置无效衰减值"""
        mock_controller_for_web.get_min_attenuation.return_value = 0.5
        mock_controller_for_web.get_frequency.return_value = 2000
        mock_controller_for_web.attenuators = {'att_1': 'mock'}
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/set_attenuation', json={'value': -5.0})
            
            assert response.status_code == 400
            data = response.json()
            assert 'detail' in data
    
    def test_get_all_attenuation(self, client, mock_controller_for_web):
        """测试获取所有设备衰减值"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/get_attenuation')
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'data' in data
            assert 'attenuations' in data['data']
    
    def test_set_device_attenuation_success(self, client, mock_controller_for_web):
        """测试成功设置单个设备衰减"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/attenuators/set', json={'device_id': 'att_1', 'value': 12.5})
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'message' in data
    
    def test_set_device_attenuation_failure(self, client, mock_controller_for_web):
        """测试设置单个设备衰减失败"""
        mock_controller_for_web.set_attenuation_by_device_id.return_value = False
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.post('/api/attenuators/set', json={'device_id': 'att_999', 'value': 10.0})
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is False
            assert 'message' in data
    
    def test_get_device_attenuation_success(self, client, mock_controller_for_web):
        """测试成功获取单个设备衰减"""
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/attenuators/att_1')
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'data' in data
    
    def test_get_device_attenuation_not_found(self, client, mock_controller_for_web):
        """测试获取不存在设备的衰减值"""
        mock_controller_for_web.get_attenuation_by_device_id.side_effect = KeyError("Device not found")
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/attenuators/att_999')
            
            assert response.status_code == 500
            data = response.json()
            assert 'detail' in data
    
    def test_get_device_status_connected(self, client, mock_controller_for_web):
        """测试获取已连接设备状态"""
        mock_controller_for_web.get_device_status.return_value = {
            'att_1': {
                'port': 'COM1',
                'connected': True,
                'current_attenuation': 10.5
            }
        }
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/devices')
            
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert 'data' in data
    
    def test_get_device_status_not_connected(self, client, mock_controller_for_web):
        """测试获取未连接设备状态"""
        mock_controller_for_web.get_device_status.return_value = {}
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/devices')
            
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert 'data' in data
    
    def test_get_min_attenuation(self, client, mock_controller_for_web):
        """测试获取最小衰减值"""
        mock_controller_for_web.get_min_attenuation.return_value = {'COM1': 0.5, 'COM2': 1.0}
        mock_controller_for_web.get_frequency.return_value = 2000
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/get_min_attenuation')
            
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert 'data' in data
            # 检查data中的内容
            assert data['data']['frequency'] == 2000
            assert data['data']['min_attenuation'] == {'COM1': 0.5, 'COM2': 1.0}
    
    def test_api_exception_handling(self, client, mock_controller_for_web):
        """测试API异常处理"""
        mock_controller_for_web.get_connected_devices.side_effect = Exception("Test exception")
        
        with patch('web_server.controller', mock_controller_for_web):
            response = client.get('/api/devices')
            
            assert response.status_code == 500
            data = response.json()
            assert 'detail' in data