#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WCS串口衰减器控制器
通过串口控制多个衰减器设备
"""

import serial
import serial.tools.list_ports
import time
import threading
import logging
import os
import json
from typing import List, Dict, Optional, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FrequencyCompensator:
    """频率补偿器 - 处理频率相关的插入损耗补偿"""

    def __init__(self, compensation_file: str = "1.json"):
        # 如果文件名不包含路径，则添加compensation_files文件夹路径
        if not os.path.dirname(compensation_file):
            self.compensation_file = os.path.join("compensation_files", compensation_file)
        else:
            self.compensation_file = compensation_file
        self.frequency_data = {}
        self.current_frequency = 1000.0  # 默认频率 1000MHz
        self.last_modified_time = 0  # 记录文件最后修改时间
        self.load_frequency_data()

    def load_frequency_data(self):
        """从补偿文件加载频率-损耗数据，支持JSON格式"""
        try:
            # 检查文件是否存在
            if not os.path.exists(self.compensation_file):
                logger.warning(f"补偿数据文件 {self.compensation_file} 不存在，使用默认数据")
                self._use_default_data()
                return

            # 更新文件修改时间
            self.last_modified_time = os.path.getmtime(self.compensation_file)

            # 根据文件扩展名选择加载方式
            if self.compensation_file.endswith('.json'):
                self._load_json_data()
            else:
                logger.warning(f"不支持的文件格式: {self.compensation_file}，仅支持JSON格式，使用默认数据")
                self._use_default_data()

        except Exception as e:
            logger.error(f"加载补偿数据失败: {e}")
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

    def _load_json_data(self):
        """从JSON文件加载补偿数据"""
        with open(self.compensation_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        self.frequency_data.clear()
        
        # JSON格式: {"频率": {"实际衰减值": "显示衰减值", ...}, ...}
        for freq_str, attenuation_map in json_data.items():
            frequency = float(freq_str)
            # 将衰减值映射转换为插入损耗数据
            # 插入损耗 = 显示衰减值 - 实际衰减值
            for actual_str, display_value in attenuation_map.items():
                actual_value = float(actual_str)
                display_value = float(display_value)
                # 计算插入损耗（负值）
                insertion_loss = display_value - actual_value
                
                # 存储频率对应的插入损耗（使用实际衰减值0作为基准）
                if actual_value == 0.0:
                    self.frequency_data[frequency] = insertion_loss
                    break
        
        # 如果没有找到0dB的基准点，使用第一个数据点
        if not self.frequency_data:
            for freq_str, attenuation_map in json_data.items():
                frequency = float(freq_str)
                first_actual = list(attenuation_map.keys())[0]
                first_display = list(attenuation_map.values())[0]
                insertion_loss = float(first_display) - float(first_actual)
                self.frequency_data[frequency] = insertion_loss
        
        logger.info(f"成功从JSON加载 {len(self.frequency_data)} 个频率点的补偿数据")
    

    
    def check_and_reload_if_modified(self):
        """检查文件是否被修改，如果是则重新加载"""
        try:
            if not os.path.exists(self.compensation_file):
                return False

            current_modified_time = os.path.getmtime(self.compensation_file)
            if current_modified_time > self.last_modified_time:
                logger.info(f"检测到补偿数据文件 {self.compensation_file} 已更新，重新加载数据")
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
        根据用户输入的目标衰减值（显示值），查表获取实际需要设置的衰减值
        输入：用户想要的衰减值（显示值）
        输出：衰减器实际需要设置的衰减值
        """
        # 重新加载原始JSON数据进行查表（不依赖frequency_data进行早期检查）
        with open(self.compensation_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 查找当前频率的数据
        freq_str = str(self.current_frequency)
        if freq_str not in json_data:
            # 尝试其他格式
            freq_str = str(int(self.current_frequency))
            if freq_str not in json_data:
                # 查找最接近的频率
                available_freqs = [float(f) for f in json_data.keys()]
                if not available_freqs:
                    logger.warning(f"补偿文件中没有任何频率数据，使用原始值")
                    return target_attenuation
                
                closest_freq = min(available_freqs, key=lambda x: abs(x - self.current_frequency))
                freq_str = str(closest_freq)
                logger.warning(f"频率 {self.current_frequency} MHz 不在补偿数据中，使用最近频率 {closest_freq} MHz 的补偿数据")
        
        freq_data = json_data[freq_str]
        
        # 首先检查是否有精确匹配
        for actual_str, display_val in freq_data.items():
            if abs(display_val - target_attenuation) < 0.01:  # 精确匹配（误差小于0.01dB）
                actual_value = float(actual_str)
                logger.debug(f"精确匹配：目标显示值 {target_attenuation} -> 实际设置值 {actual_value}")
                return actual_value
        
        # 如果没有精确匹配，使用线性插值
        actual_values = [float(k) for k in freq_data.keys()]
        display_values = [float(v) for v in freq_data.values()]
        
        # 按显示值排序
        sorted_pairs = sorted(zip(display_values, actual_values))
        sorted_display = [pair[0] for pair in sorted_pairs]
        sorted_actual = [pair[1] for pair in sorted_pairs]
        
        # 检查目标值是否在范围内
        if target_attenuation < min(sorted_display):
            logger.warning(f"目标显示值 {target_attenuation} 小于最小值 {min(sorted_display)}，使用最小值对应的实际值")
            return sorted_actual[0]
        elif target_attenuation > max(sorted_display):
            logger.warning(f"目标显示值 {target_attenuation} 大于最大值 {max(sorted_display)}，使用最大值对应的实际值")
            return sorted_actual[-1]
        
        # 线性插值
        import numpy as np
        interpolated_actual = np.interp(target_attenuation, sorted_display, sorted_actual)
        logger.debug(f"线性插值：目标显示值 {target_attenuation} -> 实际设置值 {interpolated_actual:.2f}")
        return round(interpolated_actual, 2)

    def compensate_attenuation_for_reading(self, actual_attenuation: float) -> float:
        """
        根据衰减器实际设置的衰减值，查表获取显示给用户的衰减值
        输入：衰减器实际设置的衰减值
        输出：显示给用户的衰减值
        """
        # 重新加载原始JSON数据进行查表（不依赖frequency_data进行早期检查）
        with open(self.compensation_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 查找当前频率的数据
        freq_str = str(self.current_frequency)
        if freq_str not in json_data:
            # 尝试其他格式
            freq_str = str(int(self.current_frequency))
            if freq_str not in json_data:
                # 查找最接近的频率
                available_freqs = [float(f) for f in json_data.keys()]
                if not available_freqs:
                    logger.warning(f"补偿文件中没有任何频率数据，使用原始值")
                    return actual_attenuation
                
                closest_freq = min(available_freqs, key=lambda x: abs(x - self.current_frequency))
                freq_str = str(closest_freq)
                logger.warning(f"频率 {self.current_frequency} MHz 不在补偿数据中，使用最近频率 {closest_freq} MHz 的补偿数据")
        
        freq_data = json_data[freq_str]
        
        # 首先检查是否有精确匹配
        for actual_str, display_val in freq_data.items():
            if abs(float(actual_str) - actual_attenuation) < 0.01:  # 精确匹配（误差小于0.01dB）
                logger.debug(f"精确匹配：实际设置值 {actual_attenuation} -> 显示值 {display_val}")
                return display_val
        
        # 如果没有精确匹配，使用线性插值
        actual_values = [float(k) for k in freq_data.keys()]
        display_values = [float(v) for v in freq_data.values()]
        
        # 按实际值排序
        sorted_pairs = sorted(zip(actual_values, display_values))
        sorted_actual = [pair[0] for pair in sorted_pairs]
        sorted_display = [pair[1] for pair in sorted_pairs]
        
        # 检查目标值是否在范围内
        if actual_attenuation < min(sorted_actual):
            logger.warning(f"实际设置值 {actual_attenuation} 小于最小值 {min(sorted_actual)}，使用最小值对应的显示值")
            return sorted_display[0]
        elif actual_attenuation > max(sorted_actual):
            logger.warning(f"实际设置值 {actual_attenuation} 大于最大值 {max(sorted_actual)}，使用最大值对应的显示值")
            return sorted_display[-1]
        
        # 线性插值
        import numpy as np
        interpolated_display = np.interp(actual_attenuation, sorted_actual, sorted_display)
        logger.debug(f"线性插值：实际设置值 {actual_attenuation} -> 显示值 {interpolated_display:.2f}")
        return round(interpolated_display, 2)

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

    def __init__(self, default_compensation_file: str = "1.json"):
        self.attenuators: Dict[str, SerialAttenuator] = {}
        self.compensators: Dict[str, FrequencyCompensator] = {}  # 每个设备对应一个补偿器
        self.device_port_mapping: Dict[str, str] = {}  # 设备ID到端口的映射
        self.device_serial_mapping: Dict[str, str] = {}  # 设备ID到序列号的映射
        self.serial_to_compensation: Dict[str, str] = {}  # 序列号到补偿文件的映射
        self.default_compensation_file = default_compensation_file
        self.available_ports = []
        self.current_frequency = 1000.0  # 全局频率设置
        self._load_serial_mapping()

    def _load_serial_mapping(self):
        """加载设备序列号到补偿文件的映射配置"""
        try:
            mapping_file = "device_serial_mapping.json"
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.serial_to_compensation = config.get("serial_to_compensation_mapping", {})
                    logger.info(f"加载设备序列号映射配置: {len(self.serial_to_compensation)} 个设备")
            else:
                logger.warning(f"序列号映射配置文件 {mapping_file} 不存在，将使用默认端口映射")
                self.serial_to_compensation = {}
        except Exception as e:
            logger.error(f"加载序列号映射配置失败: {e}")
            self.serial_to_compensation = {}

    def scan_serial_ports(self) -> List[str]:
        """扫描可用的串口设备并获取序列号信息"""
        ports = []
        device_info = {}
        try:
            for port in serial.tools.list_ports.comports():
                # 只添加ACM设备
                if 'ACM' in port.device:
                    ports.append(port.device)
                    # 获取设备序列号
                    serial_number = getattr(port, 'serial_number', None) or 'unknown'
                    device_info[port.device] = {
                        'serial_number': serial_number,
                        'description': getattr(port, 'description', ''),
                        'manufacturer': getattr(port, 'manufacturer', '')
                    }
                    logger.info(f"发现设备: {port.device}, 序列号: {serial_number}")

            self.available_ports = ports
            self.device_info = device_info
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
                self.device_port_mapping[device_id] = port
                
                # 获取设备序列号并记录映射关系
                device_serial = self._get_device_serial(port)
                self.device_serial_mapping[device_id] = device_serial
                
                # 为每个设备分配对应的补偿文件（优先使用序列号映射）
                compensation_file = self._get_compensation_file_for_device(port, device_serial)
                compensator = FrequencyCompensator(compensation_file)
                compensator.set_frequency(self.current_frequency)
                self.compensators[device_id] = compensator
                
                logger.info(f"成功连接衰减器 {device_id} 到端口 {port}，序列号: {device_serial}，使用补偿文件: {compensation_file}")
                return True
            else:
                logger.error(f"连接衰减器失败: {port}")
                return False

        except Exception as e:
            logger.error(f"连接衰减器异常: {e}")
            return False
    
    def _get_device_serial(self, port: str) -> str:
        """获取指定端口设备的序列号"""
        try:
            if hasattr(self, 'device_info') and port in self.device_info:
                return self.device_info[port]['serial_number']
            else:
                # 如果没有预先扫描的信息，尝试重新获取
                for port_info in serial.tools.list_ports.comports():
                    if port_info.device == port:
                        return getattr(port_info, 'serial_number', None) or 'unknown'
                return 'unknown'
        except Exception as e:
            logger.error(f"获取设备序列号失败: {e}")
            return 'unknown'
    
    def _get_compensation_file_for_device(self, port: str, device_serial: str) -> str:
        """根据设备序列号或端口获取对应的补偿文件"""
        # 优先使用序列号映射
        if device_serial in self.serial_to_compensation:
            compensation_file = self.serial_to_compensation[device_serial]
            logger.info(f"使用序列号映射: {device_serial} -> {compensation_file}")
            
            # 检查文件是否存在
            if os.path.exists(compensation_file):
                return compensation_file
            else:
                logger.warning(f"序列号映射的补偿文件 {compensation_file} 不存在，回退到端口映射")
        
        # 回退到原有的端口映射逻辑
        return self._get_compensation_file_for_port(port)
    
    def _get_compensation_file_for_port(self, port: str) -> str:
        """根据COM口获取对应的补偿文件"""
        # 提取端口号，例如从 /dev/ttyACM0 提取 0，从 COM3 提取 3
        import re
        
        # 匹配ACM端口号
        acm_match = re.search(r'ACM(\d+)', port)
        if acm_match:
            port_num = int(acm_match.group(1))
            # acm0->1.json, acm1->2.json, acm2->3.json, acm3->4.json
            compensation_file = f"{port_num + 1}.json"
            compensation_file_path = os.path.join("compensation_files", compensation_file)
            
            # 检查文件是否存在
            if os.path.exists(compensation_file_path):
                return compensation_file
            else:
                logger.warning(f"补偿文件 {compensation_file_path} 不存在，使用默认文件")
                return self.default_compensation_file
        
        # 匹配COM端口号
        com_match = re.search(r'COM(\d+)', port, re.IGNORECASE)
        if com_match:
            port_num = int(com_match.group(1))
            compensation_file = f"{port_num}.json"
            compensation_file_path = os.path.join("compensation_files", compensation_file)
            
            if os.path.exists(compensation_file_path):
                return compensation_file
            else:
                logger.warning(f"补偿文件 {compensation_file_path} 不存在，使用默认文件")
                return self.default_compensation_file
        
        # 如果无法识别端口格式，使用默认文件
        logger.warning(f"无法识别端口格式 {port}，使用默认补偿文件")
        return self.default_compensation_file

    def disconnect_all(self):
        """断开所有衰减器连接"""
        for device_id, attenuator in self.attenuators.items():
            try:
                attenuator.disconnect()
                logger.info(f"断开衰减器 {device_id} 连接")
            except Exception as e:
                logger.error(f"断开衰减器 {device_id} 连接失败: {e}")
        
        self.attenuators.clear()
        self.compensators.clear()
        self.device_port_mapping.clear()

    def set_all_attenuation(self, target_value: float) -> Dict[str, bool]:
        """批量设置所有衰减器的衰减值，每个设备使用自己的补偿器"""
        results = {}
        
        if not self.attenuators:
            logger.warning("没有连接的衰减器")
            return results
        
        logger.info(f"批量设置衰减值: 目标值={target_value}dB (频率={self.current_frequency}MHz)")
        
        for device_id, attenuator in self.attenuators.items():
            try:
                # 每个设备使用自己的补偿器
                compensator = self.compensators.get(device_id)
                if compensator is None:
                    logger.error(f"设备 {device_id} 没有对应的补偿器")
                    results[device_id] = False
                    continue
                
                # 使用设备专用的频率补偿计算实际衰减值
                actual_value = compensator.compensate_attenuation(target_value)
                
                success = attenuator.set_attenuation(actual_value)
                results[device_id] = success
                
                if success:
                    logger.info(f"设备 {device_id} 设置成功: 目标值={target_value}dB, 实际值={actual_value}dB")
                else:
                    logger.error(f"设备 {device_id} 设置失败")
                    
            except Exception as e:
                logger.error(f"设备 {device_id} 设置异常: {e}")
                results[device_id] = False
        
        return results

    def get_all_attenuation(self) -> Dict[str, Optional[float]]:
        """获取所有衰减器的当前衰减值，每个设备使用自己的补偿器"""
        results = {}

        for device_id, attenuator in self.attenuators.items():
            try:
                # 从设备读取实际设置的衰减值
                actual_value = attenuator.read_attenuation()
                if actual_value is not None:
                    # 每个设备使用自己的补偿器
                    compensator = self.compensators.get(device_id)
                    if compensator is None:
                        logger.error(f"设备 {device_id} 没有对应的补偿器")
                        results[device_id] = None
                        continue
                    
                    # actual_value是设备实际设置的值（已补偿），需要转换回目标值
                    target_value = compensator.compensate_attenuation_for_reading(actual_value)
                    results[device_id] = target_value
                    logger.info(f"设备 {device_id}: 实际值 {actual_value}dB -> 目标值 {target_value}dB")
                else:
                    results[device_id] = None

            except Exception as e:
                logger.error(f"读取设备 {device_id} 衰减值异常: {e}")
                results[device_id] = None

        return results

    def set_attenuation_by_device_id(self, device_id: str, target_value: float) -> bool:
        """
        设置指定设备的衰减值（新增方法）
        :param device_id: 设备ID（如 "att_1"）
        :param target_value: 目标衰减值（用户输入的原始值，未补偿）
        :return: 设置是否成功
        """
        # 校验设备是否存在
        if device_id not in self.attenuators:
            logger.error(f"设备 {device_id} 不存在")
            return False

        # 获取设备专用的补偿器
        compensator = self.compensators.get(device_id)
        if compensator is None:
            logger.error(f"设备 {device_id} 没有对应的补偿器")
            return False

        # 获取当前频率下的最小衰减值（用于校验）
        min_attenuation = compensator.get_current_min_attenuation()

        # 校验目标值是否在有效范围（用户输入的是未补偿值）
        if not (min_attenuation <= target_value <= 90.0):
            logger.error(f"衰减值 {target_value} 超出范围（当前最小 {min_attenuation}dB）")
            return False

        try:
            # 获取对应设备的串口控制器
            attenuator = self.attenuators[device_id]

            # 计算补偿后的实际衰减值（关键逻辑）
            actual_value = compensator.compensate_attenuation(target_value)

            # 调用串口设备设置方法
            success = attenuator.set_attenuation(actual_value)

            if success:
                logger.info(f"设备 {device_id} 设置成功：目标 {target_value}dB → 实际 {actual_value}dB")
            else:
                logger.error(f"设备 {device_id} 设置失败")

            return success

        except Exception as e:
            logger.error(f"设备 {device_id} 设置异常: {e}")
            return False

    def get_attenuation_by_device_id(self, device_id: str) -> Optional[float]:
        """
        获取指定设备的当前衰减值（新增方法）
        :param device_id: 设备ID
        :return: 用户可见的衰减值（未补偿值）
        """
        # 校验设备是否存在
        if device_id not in self.attenuators:
            logger.error(f"设备 {device_id} 不存在")
            return None

        # 获取设备专用的补偿器
        compensator = self.compensators.get(device_id)
        if compensator is None:
            logger.error(f"设备 {device_id} 没有对应的补偿器")
            return None

        try:
            attenuator = self.attenuators[device_id]

            # 从串口设备读取实际设置的衰减值（已补偿值）
            actual_value = attenuator.read_attenuation()

            if actual_value is None:
                logger.error(f"设备 {device_id} 读取失败（无响应）")
                return None

            # 转换为用户可见的未补偿值（关键逻辑）
            display_value = compensator.compensate_attenuation_for_reading(actual_value)
            logger.info(f"设备 {device_id} 读取成功：实际 {actual_value}dB → 显示 {display_value}dB")

            return display_value

        except Exception as e:
            logger.error(f"设备 {device_id} 读取异常: {e}")
            return None

    def set_frequency(self, frequency: float):
        """设置工作频率，同步更新所有补偿器"""
        self.current_frequency = frequency
        
        # 更新所有设备的补偿器频率
        for device_id, compensator in self.compensators.items():
            compensator.set_frequency(frequency)
            logger.info(f"设备 {device_id} 补偿器频率已更新为: {frequency} MHz")
        
        logger.info(f"全局工作频率设置为: {frequency} MHz")

    def get_frequency(self) -> float:
        """获取当前工作频率"""
        return self.current_frequency

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
                # 获取设备专用的补偿器
                if device_id in self.compensators:
                    compensator = self.compensators[device_id]
                    display_value = compensator.compensate_attenuation_for_reading(actual_value)
                else:
                    logger.error(f"设备 {device_id} 的补偿器不存在")
                    display_value = actual_value  # 如果没有补偿器，直接使用实际值

            status[device_id] = {
                "port": attenuator.port,
                "connected": attenuator.is_connected,
                "current_attenuation": display_value
            }

        return status

    def get_min_attenuation(self) -> float:
        """获取当前频率下的最小衰减值（取所有设备中的最大值）"""
        if not self.compensators:
            return 0.0
        
        # 取所有设备补偿器中的最大最小衰减值，确保所有设备都能正常工作
        min_attenuations = [comp.get_current_min_attenuation() for comp in self.compensators.values()]
        return max(min_attenuations) if min_attenuations else 0.0

    def get_min_attenuation_at_frequency(self, frequency: float) -> float:
        """获取指定频率下的最小衰减值（取所有设备中的最大值）"""
        if not self.compensators:
            return 0.0
        
        min_attenuations = [comp.get_min_attenuation_at_frequency(frequency) for comp in self.compensators.values()]
        return max(min_attenuations) if min_attenuations else 0.0

    def get_insertion_loss(self, frequency: float = None, device_id: str = None) -> float:
        """获取插入损耗"""
        if frequency is None:
            frequency = self.current_frequency
        
        if device_id and device_id in self.compensators:
            # 获取指定设备的插入损耗
            return self.compensators[device_id].get_loss_at_frequency(frequency)
        elif self.compensators:
            # 获取第一个设备的插入损耗作为默认值
            first_compensator = next(iter(self.compensators.values()))
            return first_compensator.get_loss_at_frequency(frequency)
        else:
            return 0.0

    def reload_frequency_data(self):
        """重新加载所有设备的频率数据"""
        for device_id, compensator in self.compensators.items():
            compensator.load_frequency_data()
            logger.info(f"设备 {device_id} 补偿数据已重新加载")
    
    def get_device_compensation_info(self, device_id: str) -> Dict:
        """获取指定设备的补偿信息"""
        if device_id not in self.compensators:
            return {}
        
        compensator = self.compensators[device_id]
        port = self.device_port_mapping.get(device_id, "未知")
        serial_number = self.device_serial_mapping.get(device_id, "未知")
        
        return {
            "device_id": device_id,
            "port": port,
            "serial_number": serial_number,
            "compensation_file": compensator.compensation_file,
            "current_frequency": compensator.get_frequency(),
            "min_attenuation": compensator.get_current_min_attenuation(),
            "insertion_loss": compensator.get_loss_at_frequency(compensator.get_frequency())
        }
    
    def get_all_device_serials(self) -> Dict[str, Dict]:
        """获取所有设备的序列号和绑定信息"""
        result = {}
        for device_id in self.attenuators.keys():
            port = self.device_port_mapping.get(device_id, "unknown")
            serial_number = self.device_serial_mapping.get(device_id, "unknown")
            compensation_file = self.compensators[device_id].compensation_file if device_id in self.compensators else "unknown"
            
            result[device_id] = {
                "port": port,
                "serial_number": serial_number,
                "compensation_file": compensation_file,
                "is_serial_mapped": serial_number in self.serial_to_compensation
            }
        return result
    
    def add_serial_mapping(self, serial_number: str, compensation_file: str) -> bool:
        """添加新的序列号到补偿文件的映射"""
        try:
            self.serial_to_compensation[serial_number] = compensation_file
            
            # 保存到配置文件
            mapping_file = "device_serial_mapping.json"
            config = {
                "serial_to_compensation_mapping": self.serial_to_compensation,
                "description": "设备序列号到补偿文件的映射配置",
                "note": "请将实际的设备序列号添加到此配置文件中"
            }
            
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"添加序列号映射: {serial_number} -> {compensation_file}")
            return True
        except Exception as e:
            logger.error(f"添加序列号映射失败: {e}")
            return False


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