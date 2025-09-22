#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WCS衰减器控制Web服务器
使用FastAPI提供RESTful API和Web界面
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import logging
import asyncio
import json
from pathlib import Path

from serial_attenuator import MultiAttenuatorController

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 读取配置文件
def load_config():
    """加载配置文件"""
    config_file = Path(__file__).parent / "config.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        return {}


# 加载配置
config = load_config()
json_file = config.get("frequency", {}).get("json_file", "1.json")

# 创建FastAPI应用
app = FastAPI(
    title="WCS衰减器控制系统",
    description="通过Web界面控制多个串口衰减器设备",
    version="1.0.0"
)

# 挂载静态文件 - 使用绝对路径
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 模板引擎 - 使用绝对路径
templates = Jinja2Templates(directory=str(templates_dir))

# 全局控制器实例
controller = MultiAttenuatorController(json_file)


# Pydantic模型
class AttenuationAndIdRequest(BaseModel):
    device_id: str
    value: float


class AttenuationRequest(BaseModel):
    value: float


class FrequencyRequest(BaseModel):
    frequency: float


class ConnectRequest(BaseModel):
    ports: List[str]


class DeviceResponse(BaseModel):
    device_id: str
    port: str
    connected: bool
    current_attenuation: Optional[float] = None


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


# 新增单设备设置请求模型（如果已有可复用）
class SingleAttenuationSetRequest(BaseModel):
    device_id: str  # 设备ID（如 "att_1"）
    value: float  # 目标衰减值（用户输入的原始值）


class DeviceIdListResponse(BaseModel):
    """设备ID列表响应模型"""
    device_ids: List[str]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/scan_ports")
async def scan_ports():
    """扫描可用串口"""
    try:
        ports = controller.scan_serial_ports()
        return ApiResponse(
            success=True,
            message=f"发现 {len(ports)} 个串口设备",
            data={"ports": ports}
        )
    except Exception as e:
        logger.error(f"扫描串口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connect")
async def connect_devices(request: ConnectRequest):
    """连接衰减器设备"""
    try:
        # 先断开所有现有连接
        controller.disconnect_all()

        results = {}
        connected_count = 0

        for i, port in enumerate(request.ports):
            device_id = f"attenuator_{i + 1}"
            success = controller.connect_attenuator(port, device_id)
            results[device_id] = {
                "port": port,
                "connected": success
            }
            if success:
                connected_count += 1

        return ApiResponse(
            success=connected_count > 0,
            message=f"成功连接 {connected_count}/{len(request.ports)} 个设备",
            data={"devices": results}
        )

    except Exception as e:
        logger.error(f"连接设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/disconnect")
async def disconnect_all():
    """断开所有设备连接"""
    try:
        controller.disconnect_all()
        return ApiResponse(
            success=True,
            message="已断开所有设备连接"
        )
    except Exception as e:
        logger.error(f"断开连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices")
async def get_devices():
    """获取设备状态"""
    try:
        status = controller.get_device_status()
        devices = []

        for device_id, info in status.items():
            devices.append(DeviceResponse(
                device_id=device_id,
                port=info["port"],
                connected=info["connected"],
                current_attenuation=info["current_attenuation"]
            ))

        return ApiResponse(
            success=True,
            message=f"获取到 {len(devices)} 个设备信息",
            data={"devices": [device.dict() for device in devices]}
        )

    except Exception as e:
        logger.error(f"获取设备状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/set_attenuation")
async def set_attenuation(request: AttenuationRequest):
    """批量设置衰减值"""
    try:
        if not controller.attenuators:
            raise HTTPException(status_code=400, detail="没有连接的设备")

        # 获取当前频率下的最小衰减值
        min_attenuation = controller.get_min_attenuation()

        # 验证衰减值范围（使用动态最小值）
        if not (min_attenuation <= request.value <= 90.0):
            raise HTTPException(
                status_code=400,
                detail=f"衰减值必须在{min_attenuation}-90dB范围内（当前频率{controller.get_frequency()}MHz的最小值为{min_attenuation}dB）"
            )

        results = controller.set_all_attenuation(request.value)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        return ApiResponse(
            success=success_count > 0,
            message=f"成功设置 {success_count}/{total_count} 个设备",
            data={
                "target_value": request.value,
                "results": results,
                "min_attenuation": min_attenuation
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置衰减值失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_attenuation")
async def get_attenuation():
    """获取所有设备的衰减值"""
    try:
        if not controller.attenuators:
            raise HTTPException(status_code=400, detail="没有连接的设备")

        values = controller.get_all_attenuation()

        return ApiResponse(
            success=True,
            message="获取衰减值成功",
            data={"attenuations": values}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取衰减值失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/attenuators/set", response_model=ApiResponse)
async def set_single_attenuation(request: SingleAttenuationSetRequest):
    """
    设置指定衰减器的衰减值（用户接口）
    """
    try:
        # 参数基础校验
        if not (0 <= request.value <= 90):
            raise HTTPException(
                status_code=400,
                detail="衰减值必须在0-90dB范围内"
            )

        # 调用控制器设置单设备
        success = controller.set_attenuation_by_device_id(
            device_id=request.device_id,
            target_value=request.value
        )

        # 初始化响应数据
        response_data = {
            "device_id": request.device_id,
            "target_value": request.value,
            "current_value": None
        }

        if success:
            response_data["message"] = f"设备 {request.device_id} 设置成功"

            # 获取实际显示值（需根据硬件反馈修正）
            current_value = controller.get_attenuation_by_device_id(request.device_id)
            if current_value is not None:
                response_data["current_value"] = current_value
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"设备 {request.device_id} 无响应"
                )
        else:
            response_data["message"] = f"设备 {request.device_id} 设置失败"

        # 统一返回结构
        return ApiResponse(
            success=success,
            message=response_data["message"],
            data=response_data
        )

    except HTTPException as e:
        return ApiResponse(
            success=False,
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        logger.error(f"单设备设置接口异常: {e}")
        return ApiResponse(
            success=False,
            message="服务器内部错误",
            code=500
        )


@app.get("/api/attenuators/{device_id}", response_model=ApiResponse)
async def get_single_attenuation(device_id: str):
    """
    获取指定衰减器的当前衰减值（用户接口）
    """
    try:
        current_value = controller.get_attenuation_by_device_id(device_id)

        if current_value is None:
            if device_id not in controller.attenuators:
                raise HTTPException(
                    status_code=404,
                    detail=f"设备 {device_id} 未连接"
                )
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"设备 {device_id} 无响应"
                )

        return ApiResponse(
            success=True,
            message=f"获取设备 {device_id} 衰减值成功",
            data={"device_id": device_id, "current_attenuation": current_value}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"单设备查询接口异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices/ids", response_model=ApiResponse)
async def get_all_device_ids():
    """
    获取所有已连接设备的ID列表（新增接口）
    """
    try:
        # 调用控制器获取设备ID列表
        device_ids = controller.get_connected_devices()

        return ApiResponse(
            success=True,
            message=f"获取到 {len(device_ids)} 个设备ID",
            data={"device_ids": device_ids}
        )

    except Exception as e:
        logger.error(f"获取设备ID列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/set_frequency")
async def set_frequency(request: FrequencyRequest):
    """设置工作频率"""
    try:
        # 验证频率范围
        if not (1 <= request.frequency <= 8000):
            raise HTTPException(status_code=400, detail="频率必须在1-8000MHz范围内")

        controller.set_frequency(request.frequency)

        return ApiResponse(
            success=True,
            message=f"设置频率成功: {request.frequency}MHz",
            data={"frequency": request.frequency}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置频率失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_frequency")
async def get_frequency():
    """获取当前工作频率"""
    try:
        frequency = controller.get_frequency()

        return ApiResponse(
            success=True,
            message="获取频率成功",
            data={"frequency": frequency}
        )

    except Exception as e:
        logger.error(f"获取频率失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_min_attenuation")
async def get_min_attenuation():
    """获取当前频率下的最小衰减值"""
    try:
        min_attenuation = controller.get_min_attenuation()
        frequency = controller.get_frequency()

        return ApiResponse(
            success=True,
            message="获取最小衰减值成功",
            data={
                "min_attenuation": min_attenuation,
                "frequency": frequency
            }
        )

    except Exception as e:
        logger.error(f"获取最小衰减值失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_attenuation_range")
async def get_attenuation_range():
    """获取当前频率下的衰减值范围"""
    try:
        min_attenuation = controller.get_min_attenuation()
        frequency = controller.get_frequency()

        return ApiResponse(
            success=True,
            message="获取衰减值范围成功",
            data={
                "min_attenuation": min_attenuation,
                "max_attenuation": 90.0,
                "frequency": frequency,
                "range_text": f"{min_attenuation} - 90.0 dB"
            }
        )

    except Exception as e:
        logger.error(f"获取衰减值范围失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_system_status():
    """获取系统状态"""
    try:
        connected_devices = controller.get_connected_devices()
        current_frequency = controller.get_frequency()

        return ApiResponse(
            success=True,
            message="获取系统状态成功",
            data={
                "connected_devices": len(connected_devices),
                "device_list": connected_devices,
                "current_frequency": current_frequency,
                "available_ports": controller.available_ports
            }
        )

    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("WCS衰减器控制系统启动")

    # 自动扫描串口
    try:
        ports = controller.scan_serial_ports()
        logger.info(f"启动时发现 {len(ports)} 个串口设备")
    except Exception as e:
        logger.error(f"启动时扫描串口失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("正在关闭系统...")

    try:
        controller.disconnect_all()
        logger.info("已断开所有设备连接")
    except Exception as e:
        logger.error(f"关闭时断开连接失败: {e}")


# 异常处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "message": "接口不存在"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "服务器内部错误"}
    )


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="衰减器控制Web服务器")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")

    args = parser.parse_args()

    logger.info(f"启动Web服务器: http://{args.host}:{args.port}")

    uvicorn.run(
        "web_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()