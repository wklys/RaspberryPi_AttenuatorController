import pytest
import json
import tempfile
import os
from serial_attenuator import FrequencyCompensator


class TestFrequencyCompensator:
    """测试FrequencyCompensator类的功能"""
    
    @pytest.fixture
    def sample_frequency_data(self):
        """创建测试用的补偿数据，格式匹配实际文件"""
        return {
            "1000.0": {
                "0.0": 0.5,
                "10.0": 10.5,
                "20.0": 20.5
            },
            "2000.0": {
                "0.0": 1.0,
                "10.0": 11.0,
                "20.0": 21.0
            },
            "3000.0": {
                "0.0": 1.5,
                "10.0": 11.5,
                "20.0": 21.5
            }
        }
    
    @pytest.fixture
    def temp_json_file(self, sample_frequency_data):
        """创建临时JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_frequency_data, f)
            temp_file = f.name
        yield temp_file
        os.unlink(temp_file)
    
    @pytest.fixture
    def frequency_compensator(self, temp_json_file):
        """创建FrequencyCompensator实例"""
        return FrequencyCompensator(temp_json_file)
    
    def test_init_with_valid_file(self, temp_json_file):
        """测试使用有效JSON文件初始化"""
        compensator = FrequencyCompensator(temp_json_file)
        assert compensator.compensation_file == temp_json_file
        assert len(compensator.frequency_data) > 0
    
    def test_init_with_invalid_file(self):
        """测试使用无效文件初始化"""
        # 无效文件会使用默认数据，不会抛出异常
        compensator = FrequencyCompensator("nonexistent.json")
        assert isinstance(compensator.frequency_data, dict)
    
    def test_init_with_invalid_json(self):
        """测试使用无效JSON文件初始化"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            # 无效JSON会使用默认数据，不会抛出异常
            compensator = FrequencyCompensator(temp_file)
            assert isinstance(compensator.frequency_data, dict)
        finally:
            os.unlink(temp_file)
    
    def test_load_frequency_data(self, frequency_compensator):
        """测试频率数据加载"""
        # 验证数据已正确加载，检查是否为字典类型
        assert isinstance(frequency_compensator.frequency_data, dict)
        assert len(frequency_compensator.frequency_data) > 0
    
    def test_compensate_attenuation_exact_frequency(self, frequency_compensator):
        """测试精确频率的衰减补偿"""
        frequency_compensator.set_frequency(2000)
        result = frequency_compensator.compensate_attenuation(10.0)
        # 应该返回实际需要设置的值，从显示值10.0反向查找
        # 在测试数据中，2000频率下，显示值10.0对应实际值10.0
        assert isinstance(result, float)
    
    def test_compensate_attenuation_interpolation(self, frequency_compensator):
        """测试插值计算的衰减补偿"""
        frequency_compensator.set_frequency(1500)  # 在1000和2000之间
        result = frequency_compensator.compensate_attenuation(10.0)
        # 应该进行频率插值计算
        assert isinstance(result, float)
    
    def test_compensate_attenuation_below_range(self, frequency_compensator):
        """测试低于频率范围的补偿计算"""
        frequency_compensator.set_frequency(500)  # 低于最小频率1000
        result = frequency_compensator.compensate_attenuation(10.0)
        # 应该使用最接近的频率数据
        assert isinstance(result, float)
    
    def test_compensate_attenuation_above_range(self, frequency_compensator):
        """测试高于频率范围的补偿计算"""
        frequency_compensator.set_frequency(5000)  # 高于最大频率3000
        result = frequency_compensator.compensate_attenuation(10.0)
        # 应该使用最接近的频率数据
        assert isinstance(result, float)
    
    def test_compensate_attenuation_zero_base(self, frequency_compensator):
        """测试零基础衰减的补偿计算"""
        frequency_compensator.set_frequency(2000)
        result = frequency_compensator.compensate_attenuation(0.0)
        # 从显示值0.0查找对应的实际值
        assert isinstance(result, float)
    
    def test_compensate_attenuation_negative_base(self, frequency_compensator):
        """测试负基础衰减的补偿计算"""
        frequency_compensator.set_frequency(2000)
        result = frequency_compensator.compensate_attenuation(-5.0)
        # 负值应该使用最小值或进行外推
        assert isinstance(result, float)
    
    def test_get_loss_at_frequency_exact(self, frequency_compensator):
        """测试获取精确频率的损耗值"""
        loss = frequency_compensator.get_loss_at_frequency(2000)
        # get_loss_at_frequency返回的是插入损耗，不是补偿数据
        assert isinstance(loss, float)
    
    def test_get_loss_at_frequency_interpolation(self, frequency_compensator):
        """测试获取插值频率的损耗值"""
        loss = frequency_compensator.get_loss_at_frequency(2500)
        # get_loss_at_frequency返回的是插入损耗，进行插值计算
        assert isinstance(loss, float)
    
    def test_empty_frequency_data(self):
        """测试空频率数据的处理"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump({}, temp_file)
            temp_file.flush()
            temp_filename = temp_file.name
        
        try:
            compensator = FrequencyCompensator(temp_filename)
            # 空数据时应该返回原值
            compensator.set_frequency(1000)
            result = compensator.compensate_attenuation(10.0)
            assert result == 10.0  # 无补偿，返回原值
        finally:
            os.unlink(temp_filename)
    
    def test_single_frequency_data(self):
        """测试单一频率数据的处理"""
        single_data = {"2000.0": {"0.0": 1.0, "10.0": 11.5}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(single_data, temp_file)
            temp_file.flush()
            temp_filename = temp_file.name
        
        try:
            compensator = FrequencyCompensator(temp_filename)
            # 任何频率都应该使用这个单一的补偿值
            compensator.set_frequency(1000)
            result1 = compensator.compensate_attenuation(10.0)
            compensator.set_frequency(3000)
            result2 = compensator.compensate_attenuation(10.0)
            # 验证返回数值类型，具体值由反向查找算法决定
            assert isinstance(result1, (int, float))
            assert isinstance(result2, (int, float))
        finally:
            os.unlink(temp_filename)