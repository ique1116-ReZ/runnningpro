# manager/analysis_manager.py
import cv2
import numpy as np
import os
import platform
from datetime import datetime

# 正确导入所有函数和关键点常量
from core.pose_engine import (
    detect_pose,
    get_keypoints,
    draw_back_view_annotations,
    analyze_leg_metrics,
    L_SHOULDER, R_SHOULDER,
    L_HIP, R_HIP,
    L_KNEE, R_KNEE,
    L_ANKLE, R_ANKLE,
    L_TOE, R_TOE,
    L_HEEL, R_HEEL
)

from core.diagnosis_engine import (
    median_or_zero,
    most_common_or_na,
    generate_back_advice,
    generate_back_issue_assessment,
)

from config.paths import get_temp_path


# ==================== 跨平台视频编码器 ====================
def get_video_fourcc():
    """获取跨平台的视频编码器FourCC码"""
    system = platform.system()
    # 尝试不同的编码器，优先使用跨平台兼容的
    if system == "Darwin":  # macOS
        return cv2.VideoWriter_fourcc(*'avc1')
    elif system == "Windows":
        return cv2.VideoWriter_fourcc(*'mp4v')
    else:  # Linux
        return cv2.VideoWriter_fourcc(*'h264')


# ==================== 后视处理 ====================
def process_back_view(video_path: str, progress_callback=None):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("无法打开后视视频")

    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    output_path = get_temp_path("relab_back") + ".mp4"
    writer = cv2.VideoWriter(output_path, get_video_fourcc(), fps, (fw, fh))

    stats = {"L": [], "R": []}
    pel = {"L": [], "R": []}
    cache = {"L": [], "R": []}
    back_kin = {
        "pelvic_all": [],
        "trunk_lateral_angles": [],
        "hip_mid_x": [],
        "hip_width_px": [],
        "step_width_pct": [],
        "cross_step_frames": 0,
        "valid_step_frames": 0,
        "left_fpa": [],
        "right_fpa": [],
    }
    support_segments = []
    current_support = None
    support_start_frame = 0

    best_frame = None
    best_keypoint_count = 0
    frame_id = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 使用 MediaPipe 检测姿态
        keypoints = detect_pose(frame)

        draw_back_view_annotations(frame, keypoints)

        visible_count = sum(1 for pt in keypoints if pt[0] > 10)
        if visible_count > best_keypoint_count:
            best_keypoint_count = visible_count
            best_frame = frame.copy()

        # 支持腿判断
        is_left_support = (keypoints[L_ANKLE][1] > keypoints[R_ANKLE][1] + 15 and keypoints[L_ANKLE][1] > fh * 0.6)
        is_right_support = (keypoints[R_ANKLE][1] > keypoints[L_ANKLE][1] + 15 and keypoints[R_ANKLE][1] > fh * 0.6)

        # 骨盆下垂
        if keypoints[L_HIP][0] > 10 and keypoints[R_HIP][0] > 10:
            pelvic_angle = abs(np.degrees(np.atan2(keypoints[L_HIP][1] - keypoints[R_HIP][1],
                                                  abs(keypoints[L_HIP][0] - keypoints[R_HIP][0]))))
            back_kin["pelvic_all"].append(pelvic_angle)
            if is_left_support:
                pel["L"].append(pelvic_angle)
            if is_right_support:
                pel["R"].append(pelvic_angle)

        current_side = "L" if is_left_support else ("R" if is_right_support else None)
        if current_side != current_support:
            if current_support in ("L", "R") and frame_id > support_start_frame:
                support_segments.append({
                    "side": current_support,
                    "frames": frame_id - support_start_frame
                })
            if current_side in ("L", "R"):
                support_start_frame = frame_id
            current_support = current_side

        # 躯干侧倾、重心横向摆动
        if keypoints[L_HIP][0] > 10 and keypoints[R_HIP][0] > 10:
            hip_mid_x = (keypoints[L_HIP][0] + keypoints[R_HIP][0]) / 2.0
            hip_mid_y = (keypoints[L_HIP][1] + keypoints[R_HIP][1]) / 2.0
            hip_width = abs(keypoints[L_HIP][0] - keypoints[R_HIP][0])
            if hip_width > 5:
                back_kin["hip_mid_x"].append(hip_mid_x)
                back_kin["hip_width_px"].append(hip_width)

            if keypoints[L_SHOULDER][0] > 10 and keypoints[R_SHOULDER][0] > 10:
                shoulder_mid_x = (keypoints[L_SHOULDER][0] + keypoints[R_SHOULDER][0]) / 2.0
                shoulder_mid_y = (keypoints[L_SHOULDER][1] + keypoints[R_SHOULDER][1]) / 2.0
                trunk_lateral_angle = abs(np.degrees(np.atan2(
                    shoulder_mid_x - hip_mid_x,
                    abs(shoulder_mid_y - hip_mid_y) + 1e-6
                )))
                back_kin["trunk_lateral_angles"].append(trunk_lateral_angle)

            # 步宽和交叉步（相对骨盆宽度归一化）
            if keypoints[L_HEEL][0] > 10 and keypoints[R_HEEL][0] > 10 and hip_width > 5:
                step_width = abs(keypoints[L_HEEL][0] - keypoints[R_HEEL][0])
                back_kin["step_width_pct"].append(step_width / hip_width * 100.0)
                back_kin["valid_step_frames"] += 1
                left_cross = keypoints[L_HEEL][0] > hip_mid_x
                right_cross = keypoints[R_HEEL][0] < hip_mid_x
                if left_cross or right_cross:
                    back_kin["cross_step_frames"] += 1

        # 足尖朝向（后视近似：跟点->足尖在画面横向偏转）
        if keypoints[L_HEEL][0] > 10 and keypoints[L_TOE][0] > 10:
            l_dx = keypoints[L_TOE][0] - keypoints[L_HEEL][0]
            l_dy = keypoints[L_TOE][1] - keypoints[L_HEEL][1]
            l_mag = abs(np.degrees(np.atan2(abs(l_dx), abs(l_dy) + 1e-6)))
            back_kin["left_fpa"].append(l_mag if l_dx < 0 else -l_mag)
        if keypoints[R_HEEL][0] > 10 and keypoints[R_TOE][0] > 10:
            r_dx = keypoints[R_TOE][0] - keypoints[R_HEEL][0]
            r_dy = keypoints[R_TOE][1] - keypoints[R_HEEL][1]
            r_mag = abs(np.degrees(np.atan2(abs(r_dx), abs(r_dy) + 1e-6)))
            back_kin["right_fpa"].append(r_mag if r_dx > 0 else -r_mag)

        if current_side:
            hip_idx = L_HIP if current_side == "L" else R_HIP
            knee_idx = L_KNEE if current_side == "L" else R_KNEE
            ankle_idx = L_ANKLE if current_side == "L" else R_ANKLE
            heel_idx = L_HEEL if current_side == "L" else R_HEEL

            pts = (keypoints[hip_idx], keypoints[knee_idx], keypoints[ankle_idx], keypoints[heel_idx])
            result = analyze_leg_metrics(*pts, current_side == "L")
            if result:
                cache[current_side].append(result)
        else:
            for side in ["L", "R"]:
                if len(cache[side]) > 5:
                    sorted_cache = sorted(cache[side], key=lambda x: x["ka"])
                    mid_start = int(len(sorted_cache) * 0.25)
                    mid_end = int(len(sorted_cache) * 0.75)
                    stats[side].extend(sorted_cache[mid_start:mid_end])
                cache[side].clear()

        writer.write(frame)
        frame_id += 1
        if progress_callback and frame_id % 10 == 0:
            progress_callback(frame_id / total_frames)

    # 视频结束后，处理最后一段尚未刷入的缓存，避免尾段样本丢失
    if current_support in ("L", "R") and frame_id > support_start_frame:
        support_segments.append({
            "side": current_support,
            "frames": frame_id - support_start_frame
        })

    for side in ["L", "R"]:
        if len(cache[side]) > 5:
            sorted_cache = sorted(cache[side], key=lambda x: x["ka"])
            mid_start = int(len(sorted_cache) * 0.25)
            mid_end = int(len(sorted_cache) * 0.75)
            stats[side].extend(sorted_cache[mid_start:mid_end])
        cache[side].clear()

    cap.release()
    writer.release()

    snapshot_path = None
    if best_frame is not None:
        snapshot_path = get_temp_path("back_snapshot") + ".jpg"
        cv2.imwrite(snapshot_path, best_frame)

    lp_avg = np.mean(pel["L"]) if pel["L"] else 0.0
    rp_avg = np.mean(pel["R"]) if pel["R"] else 0.0
    knee_l = median_or_zero(stats["L"], "ka")
    knee_r = median_or_zero(stats["R"], "ka")
    ankle_l = median_or_zero(stats["L"], "aa")
    ankle_r = median_or_zero(stats["R"], "aa")

    pelvic_asymmetry = abs(lp_avg - rp_avg)
    knee_asymmetry = abs(knee_l - knee_r)
    ankle_asymmetry = abs(ankle_l - ankle_r)

    pelvic_variability = float(np.std(back_kin["pelvic_all"])) if back_kin["pelvic_all"] else 0.0
    trunk_lateral_mean = float(np.mean(back_kin["trunk_lateral_angles"])) if back_kin["trunk_lateral_angles"] else 0.0
    trunk_lateral_variability = float(np.std(back_kin["trunk_lateral_angles"])) if back_kin["trunk_lateral_angles"] else 0.0
    step_width_mean = float(np.mean(back_kin["step_width_pct"])) if back_kin["step_width_pct"] else 0.0
    cross_step_ratio = (
        back_kin["cross_step_frames"] / back_kin["valid_step_frames"] * 100.0
        if back_kin["valid_step_frames"] > 0 else 0.0
    )
    hip_sway_pct = 0.0
    if back_kin["hip_mid_x"] and back_kin["hip_width_px"]:
        mean_hip_width = float(np.mean(back_kin["hip_width_px"]))
        if mean_hip_width > 1e-6:
            hip_sway_pct = float(np.std(back_kin["hip_mid_x"]) / mean_hip_width * 100.0)

    left_fpa_mean = float(np.mean(back_kin["left_fpa"])) if back_kin["left_fpa"] else 0.0
    right_fpa_mean = float(np.mean(back_kin["right_fpa"])) if back_kin["right_fpa"] else 0.0

    valid_segments = [s for s in support_segments if s["frames"] >= 2]
    l_support_ms = 0.0
    r_support_ms = 0.0
    cadence_spm = 0.0
    support_time_variability = 0.0
    if fps and fps > 0 and valid_segments:
        left_support_times = [seg["frames"] / fps for seg in valid_segments if seg["side"] == "L"]
        right_support_times = [seg["frames"] / fps for seg in valid_segments if seg["side"] == "R"]
        if left_support_times:
            l_support_ms = float(np.mean(left_support_times) * 1000.0)
        if right_support_times:
            r_support_ms = float(np.mean(right_support_times) * 1000.0)
        seg_times = np.array([seg["frames"] / fps for seg in valid_segments], dtype=float)
        if seg_times.size > 0:
            duration_s = frame_id / fps if frame_id > 0 else 0.0
            if duration_s > 0:
                cadence_spm = float(seg_times.size / duration_s * 60.0)
            if seg_times.mean() > 1e-6:
                support_time_variability = float(seg_times.std() / seg_times.mean() * 100.0)

    extra_metrics = {
        "pelvic_asymmetry": pelvic_asymmetry,
        "knee_asymmetry": knee_asymmetry,
        "ankle_asymmetry": ankle_asymmetry,
        "pelvic_variability": pelvic_variability,
        "trunk_lateral_mean": trunk_lateral_mean,
        "trunk_lateral_variability": trunk_lateral_variability,
        "step_width_mean": step_width_mean,
        "cross_step_ratio": cross_step_ratio,
        "hip_sway_pct": hip_sway_pct,
        "left_fpa_mean": left_fpa_mean,
        "right_fpa_mean": right_fpa_mean,
        "left_support_time_ms": l_support_ms,
        "right_support_time_ms": r_support_ms,
        "support_time_asymmetry_ms": abs(l_support_ms - r_support_ms),
        "cadence_spm": cadence_spm,
        "support_time_variability": support_time_variability,
        "support_segments": len(valid_segments),
    }
    issue_assessment = generate_back_issue_assessment({
        "pelvic_left": lp_avg,
        "pelvic_right": rp_avg,
        "knee_left_angle": knee_l,
        "knee_right_angle": knee_r,
        "ankle_left_angle": ankle_l,
        "ankle_right_angle": ankle_r,
        **extra_metrics,
    })

    report_data = {
        "pelvic_left": round(lp_avg, 1),
        "pelvic_right": round(rp_avg, 1),
        "knee_left_angle": round(knee_l, 1),
        "knee_right_angle": round(knee_r, 1),
        "knee_left_type": most_common_or_na(stats["L"], "kt"),
        "knee_right_type": most_common_or_na(stats["R"], "kt"),
        "ankle_left_angle": round(ankle_l, 1),
        "ankle_right_angle": round(ankle_r, 1),
        "ankle_left_type": most_common_or_na(stats["L"], "at"),
        "ankle_right_type": most_common_or_na(stats["R"], "at"),
        "pelvic_asymmetry": round(pelvic_asymmetry, 1),
        "knee_asymmetry": round(knee_asymmetry, 1),
        "ankle_asymmetry": round(ankle_asymmetry, 1),
        "pelvic_variability": round(pelvic_variability, 1),
        "trunk_lateral_mean": round(trunk_lateral_mean, 1),
        "trunk_lateral_variability": round(trunk_lateral_variability, 1),
        "step_width_mean": round(step_width_mean, 1),
        "cross_step_ratio": round(cross_step_ratio, 1),
        "hip_sway_pct": round(hip_sway_pct, 1),
        "left_fpa_mean": round(left_fpa_mean, 1),
        "right_fpa_mean": round(right_fpa_mean, 1),
        "left_support_time_ms": round(l_support_ms, 1),
        "right_support_time_ms": round(r_support_ms, 1),
        "support_time_asymmetry_ms": round(abs(l_support_ms - r_support_ms), 1),
        "cadence_spm": round(cadence_spm, 1),
        "support_time_variability": round(support_time_variability, 1),
        "support_segments": len(valid_segments),
        "issue_assessment": issue_assessment,
        "advice": generate_back_advice(
            lp_avg, rp_avg, knee_l, knee_r, ankle_l, ankle_r, extra_metrics=extra_metrics
        )
    }

    return output_path, snapshot_path, report_data
