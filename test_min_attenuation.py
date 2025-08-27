#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试最小衰减值功能
"""

from serial_attenuator import FrequencyCompensator

def test_min_attenuation():
    """测试最小衰减值计算"""
    print("=== 测试最小衰减值功能 ===")
    
    # 创建频率补偿器
    compensator = FrequencyCompensator()
    
    # 显示加载的数据
    print(f"加载的频率数据点数: {len(compensator.frequency_data)}")
    
    # 测试几个频率点
    test_frequencies = [10, 1000, 2000, 3000, 5000, 8000]
    
    for freq in test_frequencies:
        compensator.set_frequency(freq)
        loss = compensator.get_loss_at_frequency(freq)
        min_att = compensator.get_current_min_attenuation()
        
        print(f"频率: {freq}MHz, 插入损耗: {loss}dB, 最小衰减值: {min_att}dB")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_min_attenuation()