#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树莓派串口衰减器控制器
通过串口控制多个衰减器设备
"""

import serial
import serial.tools.list_ports
import time
import threading
import logging
import os
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FrequencyCompensator:
    """频率补偿器 - 处理频率相关的插入损耗补偿"""
    
    def __init__(self, excel_file: str = "frequency_loss1.xlsx"):
        self.excel_file = excel_file
        self.frequency_data = {}
        self.current_frequency = 1000.0  # 默认频率 1000MHz
        self.last_modified_time = 0  # 记录文件最后修改时间
        self.load_frequency_data()
    
    def load_frequency_data(self):
        """从Excel文件加载频率-损耗数据"""
        try:
            # 检查文件是否存在
            if not os.path.exists(self.excel_file):
                logger.warning(f"频率数据文件 {self.excel_file} 不存在，使用默认数据")
                self._use_default_data()
                return
            
            # 更新文件修改时间
            self.last_modified_time = os.path.getmtime(self.excel_file)
            
            df = pd.read_excel(self.excel_file)
            # 假设第一列是频率(MHz)，第二列是插入损耗(dB)
            self.frequency_data.clear()  # 清空旧数据
            for _, row in df.iterrows():
                frequency = float(row.iloc[0])  # 第一列：频率
                loss = float(row.iloc[1])       # 第二列：插入损耗
                self.frequency_data[frequency] = loss
            
            logger.info(f"成功加载 {len(self.frequency_data)} 个频率点的损耗数据")
            
        except Exception as e:
            logger.error(f"加载频率数据失败: {e}")
            self._use_default_data()
    
    def _use_default_data(self):
        """使用默认频率数据"""
        self.frequency_data = {
            50: -2.9,
            1004: -5.05,
            1998: -6.08,
            3031: -7.14,
            4025: -8.12,
            5019: -9.16,
            6013: -11.55,
            7006: -11.99,
            8000: -13.88
        }
        logger.info("使用默认频率数据")
    
    def check_and_reload_if_modified(self):
        """检查文件是否被修改，如果是则重新加载"""
        try:
            if not os.path.exists(self.excel_file):
                return False
            
            current_modified_time = os.path.getmtime(self.excel_file)
            if current_modified_time > self.last_modified_time:
                logger.info(f"检测到频率数据文件 {self.excel_file} 已更新，重新加载数据")
                self.load_frequency_data()
                return True
            return False
        except Exception as e:
            logger.error(f"检查文件修改时间失败: {e}")
            return False
    
    def get_loss_at_frequency(self, frequency: float) -> float:
        """获取指定频率的插入损耗（线性插值）"""
        # 检查文件是否被修改，如果是则重新加载
        self.check_and_reload_if_modified()
        
        if frequency in self.frequency_data:
            return self.frequency_data[frequency]
        
        # 线性插值
        frequencies = sorted(self.frequency_data.keys())
        
        if not frequencies:  # 如果没有数据
            logger.warning("没有频率数据，返回默认插入损耗 0.0dB")
            return 0.0
        
        if frequency < frequencies[0]:
            return self.frequency_data[frequencies[0]]
        if frequency > frequencies[-1]:
            return self.frequency_data[frequencies[-1]]
        
        # 找到相邻的两个频率点
        for i in range(len(frequencies) - 1):
            f1, f2 = frequencies[i], frequencies[i + 1]
            if f1 <= frequency <= f2:
                loss1 = self.frequency_data[f1]
                loss2 = self.frequency_data[f2]
                # 线性插值
                ratio = (frequency - f1) / (f2 - f1)
                return loss1 + ratio * (loss2 - loss1)
        
        return 0.0
    
    def compensate_attenuation(self, target_attenuation: float) -> float:
        """
        计算补偿后的实际衰减值
        目标衰减值 + 插入损耗 = 实际衰减值
        """
        loss = self.get_loss_at_frequency(self.current_frequency)
        # 插入损耗是负值，实际衰减 = 目标衰减 + 插入损耗
        actual_attenuation = target_attenuation + loss
        return round(actual_attenuation, 2)
    
    def compensate_attenuation_for_reading(self, actual_attenuation: float) -> float:
        """
        计算读取时显示给用户的衰减值
        显示衰减值 = 实际衰减值 - 插入损耗
        """
        loss = self.get_loss_at_frequency(self.current_frequency)
        # 显示衰减值 = 实际衰减值 - 插入损耗
        display_attenuation = actual_attenuation - loss
        return round(display_attenuation, 2)
    
    def set_frequency(self, frequency: float):
        """设置当前工作频率"""
        self.current_frequency = frequency
        logger.info(f"设置工作频率为: {frequency} MHz")
    
    def get_frequency(self) -> float:
        """获取当前工作频率"""
        return self.current_frequency
    
    def get_min_attenuation_at_frequency(self, frequency: float) -> float:
        """
        获取指定频率下的最小衰减值
        最小衰减值 = 插入损耗补偿的绝对值
        """
        loss = self.get_loss_at_frequency(frequency)
        # 插入损耗是负值，取绝对值作为最小衰减值
        min_attenuation = abs(loss)
        return round(min_attenuation, 2)
    
    def get_current_min_attenuation(self) -> float:
        """获取当前频率下的最小衰减值"""
        return self.get_min_attenuation_at_frequency(self.current_frequency)


class SerialAttenuator:
    """串口衰减器控制器"""
    
    def __init__(self, port: str, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self.lock = threading.Lock()
        self.current_attenuation = 0.0  # 存储设备实际设置的衰减值（未补偿）
        
    def connect(self) -> bool:
        """连接串口设备"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2.0
            )
            
            if self.serial_conn.is_open:
                self.is_connected = True
                logger.info(f"成功连接到串口设备: {self.port}")
                return True
            else:
                logger.error(f"无法打开串口: {self.port}")
                return False
                
        except Exception as e:
            logger.error(f"连接串口设备失败: {e}")
            return False
    
    def disconnect(self):
        """断开串口连接"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.is_connected = False
            logger.info(f"已断开串口连接: {self.port}")
    
    def send_command(self, command: str) -> str:
        """发送命令并接收响应"""
        if not self.is_connected or not self.serial_conn:
            raise Exception("串口未连接")
        
        with self.lock:
            try:
                # 发送命令（添加回车换行符）
                cmd_bytes = (command + '\r\n').encode('ascii')
                self.serial_conn.write(cmd_bytes)
                
                # 等待设备处理
                time.sleep(0.5)
                
                # 读取响应
                response = ""
                while self.serial_conn.in_waiting > 0:
                    response += self.serial_conn.read(self.serial_conn.in_waiting).decode('ascii', errors='ignore')
                    time.sleep(0.1)
                
                return response.strip()
                
            except Exception as e:
                logger.error(f"发送命令失败: {e}")
                raise
    
    def set_attenuation(self, value: float) -> bool:
        """设置衰减值"""
        try:
            # 格式: att-xxx.xx
            command = f"att-{value:06.2f}"
            response = self.send_command(command)
            
            # 简化响应检查，只要没有异常就认为成功
            self.current_attenuation = value
            logger.info(f"设置衰减值: {value}dB, 响应: {response}")
            return True
                
        except Exception as e:
            logger.error(f"设置衰减值异常: {e}")
            return False
    
    def read_attenuation(self) -> Optional[float]:
        """读取当前衰减值"""
        try:
            response = self.send_command("READ")
            
            # 解析响应，提取衰减值
            # 假设响应格式包含衰减值信息
            if response:
                # 这里需要根据实际设备响应格式来解析
                # 暂时返回当前设置的值
                return self.current_attenuation
            else:
                logger.error("读取衰减值失败: 无响应")
                return None
                
        except Exception as e:
            logger.error(f"读取衰减值异常: {e}")
            return None


class MultiAttenuatorController:
    """多衰减器控制器"""
    
    def __init__(self, excel_file: str = "frequency_loss1.xlsx"):
        self.attenuators: Dict[str, SerialAttenuator] = {}
        self.compensator = FrequencyCompensator(excel_file)
        self.available_ports = []
        
    def scan_serial_ports(self) -> List[str]:
        """扫描可用的串口设备"""
        ports = []
        try:
            for port in serial.tools.list_ports.comports():
                # 只添加ACM设备
                if 'ACM' in port.device:
                    ports.append(port.device)
            
            self.available_ports = ports
            logger.info(f"发现 {len(ports)} 个ACM串口设备: {ports}")
            return ports
            
        except Exception as e:
            logger.error(f"扫描串口设备失败: {e}")
            return []
    
    def connect_attenuator(self, port: str, device_id: str = None) -> bool:
        """连接单个衰减器"""
        if device_id is None:
            device_id = f"att_{len(self.attenuators) + 1}"
        
        try:
            # 判断是否为USB虚拟串口（STM32F4）
            baudrate = 9600  # 默认TTL串口波特率
            if "USB" in port.upper() or "ACM" in port.upper():
                baudrate = 115200  # USB虚拟串口通常使用更高波特率
            
            attenuator = SerialAttenuator(port, baudrate)
            
            if attenuator.connect():
                self.attenuators[device_id] = attenuator
                logger.info(f"成功连接衰减器 {device_id} 到端口 {port}")
                return True
            else:
                logger.error(f"连接衰减器失败: {port}")
                return False
                
        except Exception as e:
            logger.error(f"连接衰减器异常: {e}")
            return False
    
    def disconnect_all(self):
        """断开所有衰减器连接"""
        for device_id, attenuator in self.attenuators.items():
            attenuator.disconnect()
            logger.info(f"断开衰减器 {device_id}")
        
        self.attenuators.clear()
    
    def set_all_attenuation(self, target_value: float) -> Dict[str, bool]:
        """批量设置所有衰减器的衰减值"""
        results = {}
        
        # 计算补偿后的实际衰减值
        actual_value = self.compensator.compensate_attenuation(target_value)
        
        logger.info(f"目标衰减值: {target_value}dB, 补偿后实际值: {actual_value}dB")
        
        for device_id, attenuator in self.attenuators.items():
            try:
                success = attenuator.set_attenuation(actual_value)
                results[device_id] = success
                
                if success:
                    logger.info(f"设备 {device_id} 设置成功")
                else:
                    logger.error(f"设备 {device_id} 设置失败")
                    
            except Exception as e:
                logger.error(f"设备 {device_id} 设置异常: {e}")
                results[device_id] = False
        
        return results
    
    def get_all_attenuation(self) -> Dict[str, Optional[float]]:
        """获取所有衰减器的当前衰减值"""
        results = {}
        
        for device_id, attenuator in self.attenuators.items():
            try:
                # 从设备读取实际设置的衰减值
                actual_value = attenuator.read_attenuation()
                if actual_value is not None:
                    # actual_value是设备实际设置的值（已补偿），需要转换回目标值
                    target_value = self.compensator.compensate_attenuation_for_reading(actual_value)
                    results[device_id] = target_value
                    logger.info(f"设备 {device_id}: 实际值 {actual_value}dB -> 目标值 {target_value}dB")
                else:
                    results[device_id] = None
                
            except Exception as e:
                logger.error(f"读取设备 {device_id} 衰减值异常: {e}")
                results[device_id] = None
        
        return results
    
    def set_frequency(self, frequency: float):
        """设置工作频率"""
        self.compensator.set_frequency(frequency)
    
    def get_frequency(self) -> float:
        """获取当前工作频率"""
        return self.compensator.get_frequency()
    
    def get_connected_devices(self) -> List[str]:
        """获取已连接的设备列表"""
        return list(self.attenuators.keys())
    
    def get_device_status(self) -> Dict[str, Dict]:
        """获取所有设备状态"""
        status = {}
        
        for device_id, attenuator in self.attenuators.items():
            # 获取实际设置的衰减值
            actual_value = attenuator.current_attenuation
            # 转换为目标值（显示值）
            display_value = None
            if actual_value is not None:
                display_value = self.compensator.compensate_attenuation_for_reading(actual_value)
            
            status[device_id] = {
                "port": attenuator.port,
                "connected": attenuator.is_connected,
                "current_attenuation": display_value
            }
        
        return status
    
    def get_min_attenuation(self) -> float:
        """获取当前频率下的最小衰减值"""
        return self.compensator.get_current_min_attenuation()
    
    def get_min_attenuation_at_frequency(self, frequency: float) -> float:
        """获取指定频率下的最小衰减值"""
        return self.compensator.get_min_attenuation_at_frequency(frequency)
    
    def get_insertion_loss(self, frequency: float = None) -> float:
        """获取插入损耗值"""
        if frequency is None:
            frequency = self.compensator.get_frequency()
        return self.compensator.get_loss_at_frequency(frequency)
    
    def reload_frequency_data(self):
        """重新加载频率数据"""
        self.compensator.load_frequency_data()


if __name__ == "__main__":
    # 测试代码
    controller = MultiAttenuatorController()
    
    # 扫描串口
    ports = controller.scan_serial_ports()
    print(f"可用串口: {ports}")
    
    # 连接第一个串口（如果存在）
    if ports:
        success = controller.connect_attenuator(ports[0], "test_device")
        if success:
            print("连接成功")
            
            # 设置频率
            controller.set_frequency(2000)
            
            # 设置衰减值
            results = controller.set_all_attenuation(10.0)
            print(f"设置结果: {results}")
            
            # 读取衰减值
            values = controller.get_all_attenuation()
            print(f"当前衰减值: {values}")
            
            # 断开连接
            controller.disconnect_all()
        else:
            print("连接失败")
    else:
        print("未发现可用串口")