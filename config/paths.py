# config/paths.py
import os
import platform
import tempfile
from datetime import datetime
from pathlib import Path


# ====================== 常量 ======================
# MediaPipe 关键点索引（保持不变）
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_TOE, R_TOE = 32, 31
L_HEEL, R_HEEL = 30, 29


# ====================== OS 工具 ======================
def open_file_or_folder(path: str):
    """跨平台打开文件或文件夹"""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            os.system(f"open '{path}'")
        else:
            os.system(f"xdg-open '{path}'")
    except Exception as e:
        print(f"打开失败: {e}")

def get_temp_path(prefix: str):
    return os.path.join(tempfile.gettempdir(), f"{prefix}_{int(datetime.now().timestamp())}.tmp")
