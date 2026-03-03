# core/pose_engine.py
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import List, Tuple, Optional
import os

# ====================== 模型路径 ======================
def _get_model_path():
    """获取 MediaPipe 模型路径（models/pose_landmarker_heavy.task）"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(project_root, "models", "pose_landmarker_heavy.task")
    return path if os.path.exists(path) else None

_model_path = _get_model_path()
BaseOptions = python.BaseOptions
PoseLandmarker = vision.PoseLandmarker
PoseLandmarkerOptions = vision.PoseLandmarkerOptions
RunningMode = vision.RunningMode

if _model_path:
    _options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=_model_path),
        running_mode=RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
else:
    _options = PoseLandmarkerOptions(
        base_options=BaseOptions(),
        running_mode=RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

pose_landmarker = PoseLandmarker.create_from_options(_options)

# MediaPipe 关键点映射（MediaPipe 33点）
# MediaPipe Pose 关键点索引：
# 11: LEFT_SHOULDER, 12: RIGHT_SHOULDER
# 23: LEFT_HIP, 24: RIGHT_HIP
# 25: LEFT_KNEE, 26: RIGHT_KNEE
# 27: LEFT_ANKLE, 28: RIGHT_ANKLE
# 29: LEFT_HEEL, 30: RIGHT_HEEL
# 32: LEFT_FOOT_INDEX, 31: RIGHT_FOOT_INDEX

L_SHOULDER = 11
R_SHOULDER = 12
L_HIP = 23
R_HIP = 24
L_KNEE = 25
R_KNEE = 26
L_ANKLE = 27
R_ANKLE = 28
L_TOE = 32  # LEFT_FOOT_INDEX
R_TOE = 31  # RIGHT_FOOT_INDEX
L_HEEL = 29
R_HEEL = 30


def detect_pose(frame: np.ndarray) -> List[Tuple[float, float]]:
    """
    使用 MediaPipe 检测视频帧中的人体姿态关键点
    
    Args:
        frame: BGR 格式的视频帧
        
    Returns:
        关键点列表，格式为 [(x, y), ...]，共 33 个关键点
        如果检测失败，返回全为零的关键点
    """
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = frame.shape[:2]

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
    results = pose_landmarker.detect(mp_image)

    keypoints = [(0.0, 0.0)] * 33

    if results.pose_landmarks and len(results.pose_landmarks) > 0:
        landmarks = results.pose_landmarks[0]
        for i, landmark in enumerate(landmarks):
            x = landmark.x * w
            y = landmark.y * h
            if landmark.visibility < 0.3:
                x, y = 0.0, 0.0
            keypoints[i] = (x, y)

    return keypoints


def get_keypoints(keypoints: List[Tuple[float, float]], frame_width: int, frame_height: int) -> List[Tuple[float, float]]:
    """
    获取关键点坐标（MediaPipe 版本）
    
    Args:
        keypoints: MediaPipe 检测的关键点列表
        frame_width: 帧宽度
        frame_height: 帧高度
        
    Returns:
        关键点列表，保持原样返回
    """
    # MediaPipe 已经返回像素坐标，直接返回
    return keypoints


def project_pt(knee, hip, ankle):
    """将膝盖点投影到髋-踝连线上（用于后视膝力线分析）"""
    ap = np.array(knee) - np.array(hip)
    ab = np.array(ankle) - np.array(hip)
    dot = np.dot(ap, ab)
    norm_ab = np.dot(ab, ab)
    d = dot / norm_ab if norm_ab > 1e-6 else 0
    proj = np.array(hip) + d * ab
    return tuple(map(int, proj))


def calculate_angle(p1, p2, p3):
    """计算三点夹角（度）"""
    a = np.array(p1)
    b = np.array(p2)
    c = np.array(p3)
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return np.degrees(np.acos(np.clip(cosine, -1.0, 1.0)))


def analyze_leg_metrics(hip, knee, ankle, heel, is_left):
    """
    后视分析：计算膝内/外翻 + 踝内/外翻
    返回 dict 或 None
    """
    try:
        # 膝内/外翻偏移计算
        if abs(ankle[1] - hip[1]) < 1e-6:
            return None
        lx = hip[0] + (ankle[0] - hip[0]) * (knee[1] - hip[1]) / (ankle[1] - hip[1])
        offset = knee[0] - lx

        v_hk = np.array(knee) - np.array(hip)
        v_ka = np.array(ankle) - np.array(knee)
        knee_angle = np.degrees(np.acos(np.clip(
            np.dot(v_hk, v_ka) / (np.linalg.norm(v_hk) * np.linalg.norm(v_ka) + 1e-6),
            -1.0, 1.0
        )))

        knee_type = ("膝内翻(O型)" if offset < 0 else "膝外翻(X型)") if is_left else \
                    ("膝内翻(O型)" if offset > 0 else "膝外翻(X型)")

        # 踝内/外翻
        ankle_offset = heel[0] - ankle[0]
        v_ak = np.array(ankle) - np.array(knee)
        v_ah = np.array(heel) - np.array(ankle)
        ankle_angle = np.degrees(np.acos(np.clip(
            np.dot(v_ak, v_ah) / (np.linalg.norm(v_ak) * np.linalg.norm(v_ah) + 1e-6),
            -1.0, 1.0
        )))

        ankle_type = ("足内翻(旋后)" if (ankle_offset < 0 if is_left else ankle_offset > 0) else "足外翻(旋前)")

        return {
            "kt": knee_type,
            "ka": abs(knee_angle),
            "at": ankle_type,
            "aa": abs(ankle_angle)
        }
    except Exception:
        return None


# ====================== 后视专用绘图函数 ======================
def draw_back_view_annotations(frame, keypoints):
    """在帧上绘制后视所需的骨架线、投影线、科技感圆点"""
    k = keypoints

    # 上身骨架（白色粗线）
    pairs = [(L_SHOULDER, R_SHOULDER), (L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP), (L_HIP, R_HIP)]
    for p1, p2 in pairs:
        if k[p1][0] > 10 and k[p2][0] > 10:
            cv2.line(frame, tuple(map(int, k[p1])), tuple(map(int, k[p2])), (255, 255, 255), 4, cv2.LINE_AA)

    # 双腿主线（白色更粗）
    for side, color in [("L", (255, 255, 0)), ("R", (0, 255, 255))]:
        hip_idx = L_HIP if side == "L" else R_HIP
        knee_idx = L_KNEE if side == "L" else R_KNEE
        ankle_idx = L_ANKLE if side == "L" else R_ANKLE

        hip, knee, ankle = k[hip_idx], k[knee_idx], k[ankle_idx]
        if hip[0] > 10:
            cv2.line(frame, tuple(map(int, hip)), tuple(map(int, knee)), (255, 255, 255), 6, cv2.LINE_AA)
            cv2.line(frame, tuple(map(int, knee)), tuple(map(int, ankle)), (255, 255, 255), 6, cv2.LINE_AA)

            # 膝盖投影线（黄色）
            proj = project_pt(knee, hip, ankle)
            cv2.line(frame, tuple(map(int, knee)), proj, (255, 255, 0), 4, cv2.LINE_AA)

    # 关键点高亮圆圈
    highlight_pts = [L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE, L_HEEL, R_HEEL]
    for i in highlight_pts:
        if k[i][0] > 10:
            cv2.circle(frame, tuple(map(int, k[i])), 6, (0, 255, 255), -1)      # 内圈青色
            cv2.circle(frame, tuple(map(int, k[i])), 8, (255, 255, 255), 2)     # 外圈白色
