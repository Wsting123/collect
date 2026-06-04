#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import time
import datetime
import os
from ipv_data_source import ipv_data_source

class PhilipsMonitorManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.devices = []
        self.config = self.load_config()
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
    
    def load_config(self):
        """加载配置文件"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def initialize_devices(self):
        """初始化设备连接"""
        for device_config in self.config:
            if device_config["DeviceType"] == "Philips2":
                for bed in device_config["BedAdtList"]:
                    ip = bed["DeviceIP"]
                    port = bed["DevicePort"]
                    bed_no = bed["HisBedNO"]
                    device = {
                        "ip": ip,
                        "port": port,
                        "bed_no": bed_no,
                        "instance": None,
                        "is_connected": False
                    }
                    self.devices.append(device)
    
    def connect_all_devices(self):
        """连接所有设备"""
        for device in self.devices:
            try:
                self._log(f"正在连接设备: {device['ip']} (床位: {device['bed_no']})")
                device["instance"] = ipv_data_source(device["ip"])
                device["instance"].start_client()
                
                # 等待设备初始化
                time.sleep(5)
                
                # 检查连接状态，最多重试3次
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    if device["instance"].check_client_is_working_correctly():
                        device["is_connected"] = True
                        self._log(f"设备 {device['ip']} 连接成功")
                        break
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            self._log(f"设备 {device['ip']} 连接中，正在重试 ({retry_count}/{max_retries})...")
                            time.sleep(3)
                        else:
                            device["is_connected"] = False
                            self._log(f"设备 {device['ip']} 连接失败: 未收到响应")
            except Exception as e:
                device["is_connected"] = False
                self._log(f"连接设备 {device['ip']} 失败: {str(e)}")
    
    def collect_data(self, duration=60):
        """采集体征数据"""
        start_time = time.time()
        while time.time() - start_time < duration:
            for device in self.devices:
                if device["is_connected"]:
                    try:
                        vital_signs = device["instance"].get_vital_signs()
                        patient_data = device["instance"].get_patient_data()
                        self._log_vital_signs(device, vital_signs)
                        self._log_patient_data(device, patient_data)
                    except Exception as e:
                        self._log(f"获取设备 {device['ip']} 数据失败: {str(e)}")
            time.sleep(10)  # 每10秒采集一次数据
    
    def _log(self, message):
        """记录日志"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        log_file = os.path.join(self.log_dir, f"philips-monitor.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + "\n")
    
    def _log_vital_signs(self, device, vital_signs):
        """记录体征数据"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        log_file = os.path.join(self.log_dir, f"vital_signs_{device['ip'].replace('.', '_')}.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] 床位: {device['bed_no']}\n")
            for item in vital_signs:
                f.write(f"  {item[0]}: {item[1]}\n")
            f.write("\n")
    
    def _log_patient_data(self, device, patient_data):
        """记录患者数据"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        log_file = os.path.join(self.log_dir, f"patient_data_{device['ip'].replace('.', '_')}.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] 床位: {device['bed_no']}\n")
            for item in patient_data:
                f.write(f"  {item[0]}: {item[1]}\n")
            f.write("\n")
    
    def disconnect_all_devices(self):
        """断开所有设备连接"""
        for device in self.devices:
            if device["is_connected"] and device["instance"]:
                try:
                    device["instance"].halt_client()
                    device["is_connected"] = False
                    self._log(f"设备 {device['ip']} 断开连接")
                except Exception as e:
                    self._log(f"断开设备 {device['ip']} 连接失败: {str(e)}")

def main():
    config_file = "deviceSetting.json"
    manager = PhilipsMonitorManager(config_file)
    manager.initialize_devices()
    
    try:
        manager.connect_all_devices()
        manager.collect_data(duration=30000)  # 采集500分钟数据
    finally:
        manager.disconnect_all_devices()

if __name__ == "__main__":
    main()
