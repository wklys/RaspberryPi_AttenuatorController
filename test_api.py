#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API端点
"""

import requests
import json

def test_api_endpoints():
    """测试API端点"""
    base_url = "http://192.168.137.195:8000"
    
    print("=== 测试API端点 ===")
    
    # 测试获取频率
    try:
        response = requests.get(f"{base_url}/api/get_frequency")
        print(f"获取频率: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"当前频率: {data}")
    except Exception as e:
        print(f"获取频率失败: {e}")
    
    # 测试获取最小衰减值
    try:
        response = requests.get(f"{base_url}/api/get_min_attenuation")
        print(f"获取最小衰减值: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"最小衰减值: {data}")
        else:
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"获取最小衰减值失败: {e}")
    
    # 测试获取衰减值范围
    try:
        response = requests.get(f"{base_url}/api/get_attenuation_range")
        print(f"获取衰减值范围: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"衰减值范围: {data}")
        else:
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"获取衰减值范围失败: {e}")
    
    # 测试设置衰减值（应该失败，因为没有连接设备）
    try:
        response = requests.post(
            f"{base_url}/api/set_attenuation",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"value": 0.5})
        )
        print(f"设置衰减值: {response.status_code}")
        if response.status_code != 200:
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"设置衰减值失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_api_endpoints()