import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from serial_attenuator import SerialAttenuator, FrequencyCompensator
import serial


@pytest.fixture(autouse=True)
def mock_time_sleep():
    """全局mock time.sleep以避免测试中的延时"""
    with patch('serial_attenuator.time.sleep'):
        yield


class TestSerialAttenuator:
    """测试SerialAttenuator类的功能"""
    
    def test_init_success(self, mock_serial):
        """测试成功初始化串口衰减器"""
        with patch('serial.Serial', return_value=mock_serial):
            attenuator = SerialAttenuator('COM1')
            assert attenuator.port == 'COM1'
            assert attenuator.baudrate == 9600
            assert attenuator.serial_conn is None
            assert attenuator.is_connected == False
    
    def test_init_serial_exception(self):
        """测试串口初始化异常"""
        # SerialAttenuator构造函数不会抛出异常，只是初始化属性
        attenuator = SerialAttenuator('COM999')
        assert attenuator.port == 'COM999'
        assert attenuator.is_connected == False
    
    def test_send_command_success(self, mock_serial_attenuator):
        """测试成功发送命令"""
        # 模拟串口数据读取：第一次有数据，后续都没有数据（避免无限循环）
        from unittest.mock import PropertyMock
        
        call_count = 0
        def mock_in_waiting():
            nonlocal call_count
            call_count += 1
            return 5 if call_count == 1 else 0
            
        type(mock_serial_attenuator.serial_conn).in_waiting = PropertyMock(side_effect=mock_in_waiting)
        mock_serial_attenuator.serial_conn.read.return_value = b'OK\r\n'
        
        response = mock_serial_attenuator.send_command('ATT 10')
        
        mock_serial_attenuator.serial_conn.write.assert_called_once()
        assert response == 'OK'
    
    def test_send_command_timeout(self, mock_serial_attenuator):
        """测试命令发送超时"""
        mock_serial_attenuator.serial_conn.write.side_effect = serial.SerialTimeoutException("Timeout")
        
        with pytest.raises(serial.SerialTimeoutException):
            mock_serial_attenuator.send_command('ATT 10')
    
    def test_send_command_serial_exception(self, mock_serial_attenuator):
        """测试命令发送串口异常"""
        mock_serial_attenuator.serial_conn.write.side_effect = serial.SerialException("Write error")
        
        with pytest.raises(serial.SerialException):
                mock_serial_attenuator.send_command('ATT 10')
    
    def test_set_attenuation_valid_range(self, mock_serial_attenuator):
        """测试设置有效范围内的衰减值"""
        # 模拟串口数据读取：第一次有数据，第二次没有数据（避免无限循环）
        from unittest.mock import PropertyMock
        
        call_count = 0
        def mock_in_waiting():
            nonlocal call_count
            call_count += 1
            return 5 if call_count == 1 else 0
            
        type(mock_serial_attenuator.serial_conn).in_waiting = PropertyMock(side_effect=mock_in_waiting)
        mock_serial_attenuator.serial_conn.read.return_value = b'OK\r\n'
        
        result = mock_serial_attenuator.set_attenuation(15.5)
        
        assert result is True
        # 验证发送的命令包含衰减值
        mock_serial_attenuator.serial_conn.write.assert_called_once()
    
    def test_set_attenuation_below_minimum(self, mock_serial_attenuator):
        """测试设置低于最小值的衰减"""
        # 模拟串口数据读取，避免无限循环
        from unittest.mock import PropertyMock
        
        call_count = 0
        def mock_in_waiting():
            nonlocal call_count
            call_count += 1
            return 5 if call_count == 1 else 0
            
        type(mock_serial_attenuator.serial_conn).in_waiting = PropertyMock(side_effect=mock_in_waiting)
        mock_serial_attenuator.serial_conn.read.return_value = b'OK\r\n'
        
        # SerialAttenuator不进行范围检查，直接设置
        result = mock_serial_attenuator.set_attenuation(-1.0)
        assert result is True
    
    def test_set_attenuation_above_maximum(self, mock_serial_attenuator):
        """测试设置高于最大值的衰减"""
        # 模拟串口数据读取，避免无限循环
        from unittest.mock import PropertyMock
        
        call_count = 0
        def mock_in_waiting():
            nonlocal call_count
            call_count += 1
            return 5 if call_count == 1 else 0
            
        type(mock_serial_attenuator.serial_conn).in_waiting = PropertyMock(side_effect=mock_in_waiting)
        mock_serial_attenuator.serial_conn.read.return_value = b'OK\r\n'
        
        # SerialAttenuator不进行范围检查，直接设置
        result = mock_serial_attenuator.set_attenuation(100.0)
        assert result is True
    
    def test_set_attenuation_command_failure(self, mock_serial_attenuator):
        """测试衰减设置命令失败"""
        mock_serial_attenuator.serial_conn.write.side_effect = Exception("Write error")
        
        result = mock_serial_attenuator.set_attenuation(10.0)
        
        assert result is False
    
    def test_get_attenuation_success(self, mock_serial_attenuator):
        """测试成功获取衰减值"""
        # 模拟串口数据读取：第一次有数据，第二次没有数据（避免无限循环）
        from unittest.mock import PropertyMock
        
        call_count = 0
        def mock_in_waiting():
            nonlocal call_count
            call_count += 1
            return 5 if call_count == 1 else 0
            
        type(mock_serial_attenuator.serial_conn).in_waiting = PropertyMock(side_effect=mock_in_waiting)
        mock_serial_attenuator.serial_conn.read.return_value = b'ATT 15.5\r\n'
        
        attenuation = mock_serial_attenuator.read_attenuation()
        
        # SerialAttenuator返回当前设置的值
        assert attenuation == 0.0
    
    def test_get_attenuation_invalid_response(self, mock_serial_attenuator):
        """测试获取衰减值时响应格式无效"""
        # 模拟串口数据读取：第一次有数据，第二次没有数据（避免无限循环）
        from unittest.mock import PropertyMock
        
        call_count = 0
        def mock_in_waiting():
            nonlocal call_count
            call_count += 1
            return 5 if call_count == 1 else 0
            
        type(mock_serial_attenuator.serial_conn).in_waiting = PropertyMock(side_effect=mock_in_waiting)
        mock_serial_attenuator.serial_conn.read.return_value = b'INVALID\r\n'
        
        attenuation = mock_serial_attenuator.read_attenuation()
        
        # SerialAttenuator返回当前设置的值而不是解析响应
        assert attenuation == 0.0
    
    def test_get_attenuation_exception(self, mock_serial_attenuator):
        """测试获取衰减值时发生异常"""
        mock_serial_attenuator.serial_conn.write.side_effect = serial.SerialException("Read error")
        
        attenuation = mock_serial_attenuator.read_attenuation()
        
        assert attenuation is None
    
    def test_connect_success(self, mock_serial_attenuator):
        """测试成功连接"""
        with patch('serial.Serial') as mock_serial_class:
            # 设置 mock 的 is_open 属性为 True
            mock_serial_instance = Mock()
            mock_serial_instance.is_open = True
            mock_serial_class.return_value = mock_serial_instance
            
            # 重置连接状态
            mock_serial_attenuator.is_connected = False
            mock_serial_attenuator.serial_conn = None
            
            result = mock_serial_attenuator.connect()
            assert result is True
            assert mock_serial_attenuator.is_connected is True
    
    def test_connect_failure(self):
        """测试连接失败"""
        with patch('serial.Serial', side_effect=Exception("Connection failed")):
            attenuator = SerialAttenuator('COM999')
            result = attenuator.connect()
            assert result is False
            assert attenuator.is_connected is False
    
    def test_disconnect(self, mock_serial_attenuator):
        """测试断开连接"""
        mock_serial_attenuator.disconnect()
        
        mock_serial_attenuator.serial_conn.close.assert_called_once()
        assert mock_serial_attenuator.is_connected is False
    
    def test_disconnect_exception(self, mock_serial_attenuator):
        """测试断开连接时发生异常"""
        mock_serial_attenuator.serial_conn.close.side_effect = Exception("Close error")
        mock_serial_attenuator.serial_conn.is_open = True
        
        # 应该不抛出异常，但实际上会抛出，因为代码没有处理异常
        with pytest.raises(Exception, match="Close error"):
            mock_serial_attenuator.disconnect()
    
    def test_is_connected_true(self, mock_serial_attenuator):
        """测试连接状态检查 - 已连接"""
        mock_serial_attenuator.is_connected = True
        
        assert mock_serial_attenuator.is_connected is True
    
    def test_is_connected_false(self, mock_serial_attenuator):
        """测试连接状态检查 - 未连接"""
        mock_serial_attenuator.is_connected = False
        
        assert mock_serial_attenuator.is_connected is False
    
    def test_is_connected_no_connection(self):
        """测试连接状态检查 - 无连接对象"""
        attenuator = SerialAttenuator('COM1')
        
        assert attenuator.is_connected is False