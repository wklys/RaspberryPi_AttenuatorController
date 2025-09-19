import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from serial_attenuator import MultiAttenuatorController, SerialAttenuator
import serial


class TestMultiAttenuatorController:
    """测试MultiAttenuatorController类的功能"""
    
    def test_init_with_valid_file(self, temp_json_file):
        """测试使用有效补偿文件初始化"""
        with patch('serial.Serial'):
            controller = MultiAttenuatorController(temp_json_file)
            assert controller.default_compensation_file == temp_json_file
            assert len(controller.attenuators) == 0
            assert controller.current_frequency == 1000
    
    def test_init_with_invalid_file(self):
        """测试使用无效补偿文件初始化"""
        # MultiAttenuatorController不会在初始化时验证文件存在性
        controller = MultiAttenuatorController("nonexistent.json")
        assert controller.default_compensation_file == "nonexistent.json"
    
    def test_scan_serial_ports(self, mock_controller):
        """测试扫描串口"""
        mock_ports = [Mock(), Mock(), Mock()]
        mock_ports[0].device = '/dev/ttyACM0'
        mock_ports[0].serial_number = 'SN001'
        mock_ports[0].description = 'ACM Device 1'
        mock_ports[0].manufacturer = 'Test Manufacturer'
        
        mock_ports[1].device = '/dev/ttyACM1'
        mock_ports[1].serial_number = 'SN002'
        mock_ports[1].description = 'ACM Device 2'
        mock_ports[1].manufacturer = 'Test Manufacturer'
        
        # 这个设备不包含ACM，应该被过滤掉
        mock_ports[2].device = '/dev/ttyUSB0'
        mock_ports[2].serial_number = 'SN003'
        
        with patch('serial.tools.list_ports.comports', return_value=mock_ports):
            ports = mock_controller.scan_serial_ports()
            
            assert len(ports) == 2
            assert '/dev/ttyACM0' in ports
            assert '/dev/ttyACM1' in ports
            assert '/dev/ttyUSB0' not in ports
            assert hasattr(mock_controller, 'device_info')
            assert '/dev/ttyACM0' in mock_controller.device_info
    
    def test_connect_attenuator_success(self, mock_controller):
        """测试成功连接衰减器"""
        mock_serial = Mock()
        mock_serial.is_open = True
        
        with patch('serial.Serial', return_value=mock_serial), \
             patch.object(mock_controller, '_get_device_serial', return_value='SN001'), \
             patch.object(mock_controller, '_get_compensation_file_for_device', return_value='1.json'):
            result = mock_controller.connect_attenuator('COM1', 'device1')
            
            assert result is True
            assert 'device1' in mock_controller.attenuators
            assert isinstance(mock_controller.attenuators['device1'], SerialAttenuator)
            assert mock_controller.device_port_mapping['device1'] == 'COM1'
            assert mock_controller.device_serial_mapping['device1'] == 'SN001'
    
    def test_connect_attenuator_failure(self, mock_controller):
        """测试连接衰减器失败"""
        with patch('serial.Serial', side_effect=serial.SerialException("Connection failed")):
            result = mock_controller.connect_attenuator('COM999', 'device999')
            
            assert result is False
            assert 'device999' not in mock_controller.attenuators
    
    def test_connect_attenuator_already_connected(self, mock_controller):
        """测试连接已连接的衰减器"""
        # 先连接一次
        mock_serial = Mock()
        mock_serial.is_open = True
        
        with patch('serial.Serial', return_value=mock_serial), \
             patch.object(mock_controller, '_get_device_serial', return_value='SN001'), \
             patch.object(mock_controller, '_get_compensation_file_for_device', return_value='1.json'):
            mock_controller.connect_attenuator('COM1', 'device1')
            
            # 再次连接同一个设备ID（会覆盖之前的连接）
            result = mock_controller.connect_attenuator('COM1', 'device1')
            
            assert result is True  # 应该返回成功，因为可以重新连接
    
    def test_disconnect_all_success(self, mock_controller):
        """测试成功断开所有衰减器连接"""
        # 先连接多个设备
        mock_serial1 = Mock()
        mock_serial1.is_open = True
        mock_serial2 = Mock()
        mock_serial2.is_open = True
        
        with patch('serial.Serial', side_effect=[mock_serial1, mock_serial2]):
            mock_controller.connect_attenuator('COM1', 'device1')
            mock_controller.connect_attenuator('COM2', 'device2')
            
            # 断开所有连接
            mock_controller.disconnect_all()
            
            assert len(mock_controller.attenuators) == 0
            assert len(mock_controller.compensators) == 0
    
    def test_disconnect_all_no_devices(self, mock_controller):
        """测试断开连接时没有设备"""
        # 直接调用disconnect_all，不应该出错
        mock_controller.disconnect_all()
        
        assert len(mock_controller.attenuators) == 0
    
    def test_disconnect_all(self, mock_controller):
        """测试断开所有连接"""
        # 连接多个设备
        mock_serials = {}
        ports = ['COM1', 'COM2', 'COM3']
        for i, port in enumerate(ports):
            mock_serial = Mock()
            mock_serial.is_open = True
            mock_serials[port] = mock_serial
            
            with patch('serial.Serial', return_value=mock_serial):
                mock_controller.connect_attenuator(port, f'device{i+1}')
        
        # 断开所有连接
        mock_controller.disconnect_all()
        
        assert len(mock_controller.attenuators) == 0
        for mock_serial in mock_serials.values():
            mock_serial.close.assert_called_once()
    
    def test_set_frequency_all_devices(self, mock_controller):
        """测试设置所有设备的频率"""
        # 连接多个设备
        for i, port in enumerate(['COM1', 'COM2']):
            mock_serial = Mock()
            mock_serial.is_open = True
            
            with patch('serial.Serial', return_value=mock_serial):
                mock_controller.connect_attenuator(port, f'device{i+1}')
        
        # 设置频率
        mock_controller.set_frequency(2500)
        
        assert mock_controller.current_frequency == 2500
        # 验证所有补偿器的频率都被设置
        for compensator in mock_controller.compensators.values():
            assert compensator.current_frequency == 2500
    
    def test_set_frequency_invalid(self, mock_controller):
        """测试设置无效频率"""
        # set_frequency方法不会验证频率值，只是简单设置
        mock_controller.set_frequency(-100)
        assert mock_controller.get_frequency() == -100
    
    def test_get_frequency(self, mock_controller):
        """测试获取当前频率"""
        mock_controller.set_frequency(3000)
        
        frequency = mock_controller.get_frequency()
        
        assert frequency == 3000
    
    def test_set_all_attenuation_success(self, mock_controller):
        """测试成功设置所有设备的衰减值"""
        # 连接设备并模拟成功响应
        mock_serials = []
        for i, port in enumerate(['COM1', 'COM2']):
            mock_serial = Mock()
            mock_serial.is_open = True
            mock_serial.readline.return_value = b'OK\r\n'
            mock_serials.append(mock_serial)
            
            with patch('serial.Serial', return_value=mock_serial), \
                 patch.object(mock_controller, '_get_device_serial', return_value=f'SN00{i+1}'), \
                 patch.object(mock_controller, '_get_compensation_file_for_device', return_value='1.json'):
                mock_controller.connect_attenuator(port, f'device{i+1}')
        
        # 模拟set_attenuation方法返回True
        for device_id in mock_controller.attenuators:
            mock_controller.attenuators[device_id].set_attenuation = Mock(return_value=True)
        
        # 设置衰减值
        results = mock_controller.set_all_attenuation(15.0)
        
        assert len(results) == 2
        assert all(results.values())  # 所有设备都应该返回True
    
    def test_set_all_attenuation_no_devices(self, mock_controller):
        """测试在没有连接设备时设置衰减值"""
        results = mock_controller.set_all_attenuation(10.0)
        
        assert len(results) == 0
    
    def test_get_all_attenuation_success(self, mock_controller):
        """测试成功获取所有设备的衰减值"""
        # 连接设备并模拟响应
        mock_serials = []
        for i, port in enumerate(['COM1', 'COM2']):
            mock_serial = Mock()
            mock_serial.is_open = True
            mock_serial.readline.return_value = f'ATT {10.5 + i * 4.5}\r\n'.encode()
            mock_serials.append(mock_serial)
            
            with patch('serial.Serial', return_value=mock_serial):
                mock_controller.connect_attenuator(port, f'device{i+1}')
        
        # 获取衰减值
        results = mock_controller.get_all_attenuation()
        
        assert len(results) == 2
        assert 'device1' in results
        assert 'device2' in results
    
    def test_set_attenuation_by_device_id_success(self, mock_controller):
        """测试成功设置指定设备的衰减值"""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.readline.return_value = b'OK\r\n'
        
        with patch('serial.Serial', return_value=mock_serial), \
             patch.object(mock_controller, '_get_device_serial', return_value='SN001'), \
             patch.object(mock_controller, '_get_compensation_file_for_device', return_value='1.json'):
            mock_controller.connect_attenuator('COM1', 'device1')
            
            # 模拟set_attenuation方法返回True
            mock_controller.attenuators['device1'].set_attenuation = Mock(return_value=True)
        
        result = mock_controller.set_attenuation_by_device_id('device1', 12.5)
        
        assert result is True
    
    def test_set_attenuation_by_device_id_not_found(self, mock_controller):
        """测试设置不存在设备的衰减值"""
        result = mock_controller.set_attenuation_by_device_id('nonexistent_device', 10.0)
        
        assert result is False
    
    def test_get_attenuation_by_device_id_success(self, mock_controller):
        """测试通过设备ID成功获取衰减值"""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.readline.return_value = b'18.5\r\n'
        
        with patch('serial.Serial', return_value=mock_serial), \
             patch.object(mock_controller, '_get_device_serial', return_value='SN001'), \
             patch.object(mock_controller, '_get_compensation_file_for_device', return_value='1.json'):
            mock_controller.connect_attenuator('COM1', 'device1')
            
            # 模拟read_attenuation方法返回18.5
            mock_controller.attenuators['device1'].read_attenuation = Mock(return_value=18.5)
            # 模拟补偿器的补偿方法返回相同值（无补偿）
            mock_controller.compensators['device1'].compensate_attenuation_for_reading = Mock(return_value=18.5)
            
            result = mock_controller.get_attenuation_by_device_id('device1')
            
            assert result == 18.5
    
    def test_get_attenuation_by_device_id_not_found(self, mock_controller):
        """测试获取不存在设备的衰减值"""
        attenuation = mock_controller.get_attenuation_by_device_id('nonexistent_device')
        
        assert attenuation is None
    
    def test_get_connected_devices(self, mock_controller):
        """测试获取已连接设备列表"""
        # 连接多个设备
        ports = ['COM1', 'COM2', 'COM3']
        device_ids = ['device1', 'device2', 'device3']
        
        for i, port in enumerate(ports):
            mock_serial = Mock()
            mock_serial.is_open = True
            
            with patch('serial.Serial', return_value=mock_serial):
                mock_controller.connect_attenuator(port, device_ids[i])
        
        connected = mock_controller.get_connected_devices()
        
        assert len(connected) == 3
        assert set(connected) == set(device_ids)
    
    def test_get_device_status_connected(self, mock_controller):
        """测试获取已连接设备的状态"""
        mock_serial = Mock()
        mock_serial.is_open = True
        
        with patch('serial.Serial', return_value=mock_serial):
            mock_controller.connect_attenuator('COM1', 'device1')
        
        status = mock_controller.get_device_status()
        
        assert 'device1' in status
        assert status['device1']['connected'] is True
        assert status['device1']['port'] == 'COM1'
    
    def test_get_device_status_no_devices(self, mock_controller):
        """测试获取设备状态时没有连接设备"""
        status = mock_controller.get_device_status()
        
        assert status == {}
    
    def test_get_min_attenuation_success(self, mock_controller):
        """测试成功获取最小衰减值"""
        # 连接设备
        mock_serial = Mock()
        mock_serial.is_open = True
        
        with patch('serial.Serial', return_value=mock_serial):
            mock_controller.connect_attenuator('COM1', 'device1')
        
        # 模拟补偿器返回最小衰减值
        with patch.object(mock_controller.compensators['device1'], 'get_current_min_attenuation', return_value=1.0):
            result = mock_controller.get_min_attenuation()
        
        assert result == 1.0
    
    def test_get_min_attenuation_at_frequency_success(self, mock_controller):
        """测试成功获取指定频率下的最小衰减值"""
        mock_serial = Mock()
        mock_serial.is_open = True
        
        with patch('serial.Serial', return_value=mock_serial):
            mock_controller.connect_attenuator('COM1', 'device1')
        
        # 模拟补偿器返回指定频率的最小衰减值
        with patch.object(mock_controller.compensators['device1'], 'get_min_attenuation_at_frequency', return_value=0.8):
            result = mock_controller.get_min_attenuation_at_frequency(2000)
        
        assert result == 0.8
    
    def test_load_serial_mapping_file_exists(self, mock_controller):
        """测试加载存在的序列号映射文件"""
        mapping_data = {
            "serial_to_compensation_mapping": {
                "SN001": "device1.json",
                "SN002": "device2.json"
            }
        }
        
        # 清空现有的映射数据
        mock_controller.serial_to_compensation = {}
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(mapping_data))):
            mock_controller._load_serial_mapping()
        
        assert mock_controller.serial_to_compensation == mapping_data["serial_to_compensation_mapping"]
    
    def test_load_serial_mapping_file_not_exists(self, mock_controller):
        """测试加载不存在的序列号映射文件"""
        with patch('os.path.exists', return_value=False):
            mock_controller._load_serial_mapping()
            
            assert mock_controller.serial_to_compensation == {}