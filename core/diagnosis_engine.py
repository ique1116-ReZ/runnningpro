# core/diagnosis_engine.py
import numpy as np
from collections import Counter
from typing import List, Dict, Optional

# ====================== 风险等级判断 ======================
def get_knee_status(angle: float):
    """膝关节力线偏移角度风险判断（后视）"""
    if angle < 5:
        return "正常", "#10b981"
    elif 5 <= angle <= 10:
        return "提示关注", "#f59e0b"
    else:
        return "建议干预", "#ef4444"


def get_ankle_status(angle: float):
    """踝关节偏转角度风险判断（后视）"""
    if angle < 10:
        return "正常", "#10b981"
    elif 10 <= angle <= 20:
        return "提示关注", "#f59e0b"
    else:
        return "建议干预", "#ef4444"


# ====================== 统计辅助函数 ======================
def median_or_zero(data_list, key):
    """安全取中位数"""
    if not data_list:
        return 0.0
    values = [item[key] for item in data_list]
    return float(np.median(values))


def most_common_or_na(data_list, key):
    """安全取最常见项"""
    if not data_list:
        return "N/A"
    values = [item[key] for item in data_list]
    return Counter(values).most_common(1)[0][0]


# ====================== 后视诊断建议生成（专业版） ======================
def generate_back_advice(pelvic_l: float, pelvic_r: float,
                         knee_l_angle: float, knee_r_angle: float,
                         ankle_l_angle: float, ankle_r_angle: float,
                         extra_metrics: Optional[Dict[str, float]] = None) -> List[str]:
    """
    根据后视统计数据生成专业改善建议列表。
    覆盖：骨盆稳定度、膝关节力线、足踝力线；正常/轻度/中度/重度/左右不对称。
    """
    advice: List[str] = []

    # ----- 1. 骨盆稳定度 (Pelvic Stability) -----
    pelvic_max = max(pelvic_l, pelvic_r)
    pelvic_diff = abs(pelvic_l - pelvic_r)
    if pelvic_max <= 3:
        advice.append("• 【骨盆稳定度】当前单腿支撑期骨盆控制良好（<3°），建议维持核心与臀中肌常规训练。")
    elif pelvic_max <= 5:
        advice.append("• 【骨盆稳定度】骨盆下垂处于临界（3–5°），建议加强臀中肌力量：侧卧抬腿、贝壳式、单腿站立平衡；跑步时注意收腹、避免骨盆侧倾。")
    elif pelvic_max <= 10:
        advice.append("• 【骨盆稳定度】存在明显骨盆下垂（5–10°），与臀中肌无力、髂胫束紧张相关。建议：臀中肌强化（弹力带侧向行走、单腿蹲）、髋外展拉伸；跑量循序渐进，避免突然加量。")
    else:
        advice.append("• 【骨盆稳定度】骨盆下垂较重（>10°），建议在专业康复或运动医学指导下进行臀中肌与核心稳定性评估，必要时结合步态训练与跑姿纠正。")
    if pelvic_diff > 3 and pelvic_max > 3:
        advice.append("• 【骨盆对称性】左右支撑侧骨盆下垂不对称，提示可能存在单侧臀中肌薄弱或代偿。建议双侧均衡训练，弱侧可适当增加组数或负荷。")

    # ----- 2. 膝关节力线 (Knee Alignment) -----
    knee_max = max(knee_l_angle, knee_r_angle)
    knee_diff = abs(knee_l_angle - knee_r_angle)
    if knee_max < 5:
        advice.append("• 【膝关节力线】膝内/外翻角度在正常范围，髌股关节负荷可控。建议继续保持股四头肌与腘绳肌均衡发展，避免膝内扣落地。")
    elif knee_max <= 10:
        advice.append("• 【膝关节力线】存在轻度膝偏移（5–10°），建议：强化股四头肌内侧头（终末伸膝、浅蹲静蹲）、改善髌骨轨迹；落地时保持膝盖与第二趾方向一致，避免内扣或外撇。")
    elif knee_max <= 15:
        advice.append("• 【膝关节力线】膝偏移达中度（10–15°），与Q角增大、足弓塌陷或髋控制不足有关。建议：足弓与髋外展强化、落地时刻意控制膝朝向；可考虑具有支撑/稳定型的跑鞋，并逐步增加力量训练比例。")
    else:
        advice.append("• 【膝关节力线】膝偏移角度较大（>15°），长期可能增加髌股疼痛与半月板应力。建议在康复或运动医学指导下进行下肢力线评估，结合力量、拉伸与跑姿纠正综合干预。")
    if knee_diff > 5 and knee_max >= 5:
        advice.append("• 【膝对称性】左右膝力线不对称，需注意单侧代偿与损伤风险。建议双侧均衡训练，弱侧可增加单腿稳定性与力量练习。")

    # ----- 3. 足踝力线 (Ankle Alignment) -----
    ankle_max = max(ankle_l_angle, ankle_r_angle)
    ankle_diff = abs(ankle_l_angle - ankle_r_angle)
    if ankle_max < 10:
        advice.append("• 【足踝力线】踝关节偏转在正常范围，足弓与距下关节控制良好。建议维持小腿三头肌与胫骨后肌力量，避免过度旋前落地。")
    elif ankle_max <= 20:
        advice.append("• 【足踝力线】存在轻度足踝偏转（10–20°），可能与足弓塌陷或旋前有关。建议：足弓抓地，短足练习、胫骨后肌强化；可考虑具有内侧支撑或适度稳定型的跑鞋。")
    elif ankle_max <= 30:
        advice.append("• 【足踝力线】足踝偏转达中度（20–30°），提示过度旋前或足弓支撑不足。建议：足弓与小腿后群强化、步态周期中控制距下关节；跑鞋选择稳定型或控制型，必要时在专业人员指导下使用矫形垫。")
    else:
        advice.append("• 【足踝力线】足踝偏转较大（>30°），建议在康复或足踝专科评估距下关节活动度、足弓形态及下肢力线，结合矫形与力量训练综合干预。")
    if ankle_diff > 8 and ankle_max >= 10:
        advice.append("• 【踝对称性】左右足踝力线不对称，可能加重单侧负荷。建议双侧足弓与小腿训练，并检查是否存在单侧代偿或旧伤。")

    # ----- 4. 后视扩展指标 (Stability & Symmetry) -----
    if extra_metrics:
        pelvic_var = float(extra_metrics.get("pelvic_variability", 0.0))
        trunk_lat = float(extra_metrics.get("trunk_lateral_mean", 0.0))
        trunk_var = float(extra_metrics.get("trunk_lateral_variability", 0.0))
        cross_step_ratio = float(extra_metrics.get("cross_step_ratio", 0.0))
        step_width_mean = float(extra_metrics.get("step_width_mean", 0.0))
        hip_sway_pct = float(extra_metrics.get("hip_sway_pct", 0.0))
        fpa_l = float(extra_metrics.get("left_fpa_mean", 0.0))
        fpa_r = float(extra_metrics.get("right_fpa_mean", 0.0))
        support_asym_ms = float(extra_metrics.get("support_time_asymmetry_ms", 0.0))
        support_var = float(extra_metrics.get("support_time_variability", 0.0))

        if pelvic_var > 2.0:
            advice.append("• 【骨盆稳定性】骨盆下垂波动较大（跨步间一致性不足），提示疲劳后控制易下降。建议降低单次跑量峰值，加入单腿稳定与节律控制训练。")

        if trunk_lat > 6 or trunk_var > 2.5:
            advice.append("• 【躯干侧倾控制】存在明显躯干侧倾/波动，可能增加髋外展肌与腰背代偿负荷。建议加强核心抗侧屈训练（侧桥、行走负重）与臀中肌控制。")

        if hip_sway_pct > 8:
            advice.append("• 【重心横向摆动】跑步中左右摆动偏大，提示前进方向效率下降。建议提高步频并减小横向摆动，强化骨盆-核心协同控制。")

        if cross_step_ratio >= 20 or (step_width_mean > 0 and step_width_mean < 60):
            advice.append("• 【步宽与落点】存在步宽偏窄或交叉步倾向，可能提升髂胫束与膝外侧负荷。建议保持落点接近髋宽，避免脚落到身体中线内侧。")

        if abs(fpa_l) > 12 or abs(fpa_r) > 12:
            advice.append("• 【足尖朝向】足尖进展角偏大，提示足部控制或髋旋转控制需优化。建议结合髋外旋/内旋控制与足弓稳定训练，逐步校正内八/外八代偿。")

        if support_asym_ms > 40:
            advice.append("• 【支撑时间对称性】左右支撑时间差异较大，提示可能存在单侧保护或旧伤代偿。建议弱侧增加单腿力量与平衡训练，并监测疼痛反馈。")

        if support_var > 25:
            advice.append("• 【节律稳定性】步态支撑时间波动偏大，跑步节律稳定性一般。建议用节拍器进行步频训练，优先稳定动作质量再逐步提速。")

    return advice


# ====================== 未来扩展：标准化风险标签 ======================
def extract_back_risks(pelvic_l: float, pelvic_r: float,
                       knee_l_angle: float, knee_r_angle: float,
                       ankle_l_angle: float, ankle_r_angle: float) -> List[str]:
    """
    返回标准化风险标签列表（供后续 recommendation_engine 使用）
    """
    risks = []
    if pelvic_l > 5 or pelvic_r > 5:
        risks.append("pelvic_drop")
    if knee_l_angle > 5 or knee_r_angle > 5:
        risks.append("knee_misalignment")
    if ankle_l_angle > 10 or ankle_r_angle > 10:
        risks.append("overpronation")
    return risks


def generate_back_issue_assessment(metrics: Dict[str, float]) -> List[Dict[str, str]]:
    """
    基于后视指标按预设标准区间输出结构化问题评估：
    - metric: 指标名称
    - current: 当前值
    - normal_range: 参考区间
    - status: 正常 / 提示关注 / 建议干预
    - issue: 可能问题
    - suggestion: 对应建议
    """

    def _fmt(value: float, unit: str) -> str:
        return f"{round(float(value), 1)}{unit}"

    def _status(ok: bool, warn: bool) -> str:
        if ok:
            return "正常"
        if warn:
            return "提示关注"
        return "建议干预"

    data = [
        {
            "metric": "骨盆下垂（左/右最大值）",
            "value": max(metrics.get("pelvic_left", 0.0), metrics.get("pelvic_right", 0.0)),
            "unit": "°",
            "normal": "<=5°",
            "ok": 5.0,
            "warn": 8.0,
            "issue_warn": "骨盆控制偏弱",
            "issue_bad": "骨盆稳定不足（Trendelenburg风险）",
            "advice_warn": "加强臀中肌与核心稳定训练，先控量后提强度。",
            "advice_bad": "建议康复评估并进行单腿稳定与步态纠正训练。",
        },
        {
            "metric": "骨盆左右差",
            "value": metrics.get("pelvic_asymmetry", 0.0),
            "unit": "°",
            "normal": "<=3°",
            "ok": 3.0,
            "warn": 5.0,
            "issue_warn": "存在轻度单侧代偿",
            "issue_bad": "左右代偿明显",
            "advice_warn": "弱侧增加单腿力量和平衡训练。",
            "advice_bad": "建议排查旧伤侧并做双侧不对称专项干预。",
        },
        {
            "metric": "膝力线（左/右最大值）",
            "value": max(metrics.get("knee_left_angle", 0.0), metrics.get("knee_right_angle", 0.0)),
            "unit": "°",
            "normal": "<=10°",
            "ok": 10.0,
            "warn": 15.0,
            "issue_warn": "膝力线偏移",
            "issue_bad": "膝内扣/外撇风险较高",
            "advice_warn": "强化髋外展与股四头肌控制，保持膝盖对准第二趾。",
            "advice_bad": "建议进行下肢力线评估并进行动作重建。",
        },
        {
            "metric": "踝力线（左/右最大值）",
            "value": max(metrics.get("ankle_left_angle", 0.0), metrics.get("ankle_right_angle", 0.0)),
            "unit": "°",
            "normal": "<=20°",
            "ok": 20.0,
            "warn": 30.0,
            "issue_warn": "足踝旋前/旋后偏大",
            "issue_bad": "足踝力线异常明显",
            "advice_warn": "加强足弓与小腿后群训练，关注跑鞋支撑性。",
            "advice_bad": "建议进行足踝专科评估，必要时结合矫形策略。",
        },
        {
            "metric": "躯干侧倾均值",
            "value": metrics.get("trunk_lateral_mean", 0.0),
            "unit": "°",
            "normal": "<=6°",
            "ok": 6.0,
            "warn": 8.0,
            "issue_warn": "躯干侧倾偏大",
            "issue_bad": "躯干控制不足",
            "advice_warn": "增加抗侧屈核心训练与跑中姿态提醒。",
            "advice_bad": "建议降低训练强度并进行核心-骨盆协同重建。",
        },
        {
            "metric": "交叉步比例",
            "value": metrics.get("cross_step_ratio", 0.0),
            "unit": "%",
            "normal": "<20%",
            "ok": 20.0,
            "warn": 35.0,
            "issue_warn": "存在交叉步倾向",
            "issue_bad": "交叉步明显，外侧链负荷升高",
            "advice_warn": "保持落点接近髋宽，避免脚落中线内侧。",
            "advice_bad": "建议用节拍器与地面标线做步宽重建训练。",
        },
        {
            "metric": "重心横摆（相对髋宽）",
            "value": metrics.get("hip_sway_pct", 0.0),
            "unit": "%",
            "normal": "<=8%",
            "ok": 8.0,
            "warn": 12.0,
            "issue_warn": "横向摆动偏大",
            "issue_bad": "横向控制较差",
            "advice_warn": "提高步频并减少横向位移。",
            "advice_bad": "建议先做稳定性周期，再逐步恢复速度训练。",
        },
        {
            "metric": "足进展角（左右绝对值最大）",
            "value": max(abs(metrics.get("left_fpa_mean", 0.0)), abs(metrics.get("right_fpa_mean", 0.0))),
            "unit": "°",
            "normal": "<=12°",
            "ok": 12.0,
            "warn": 18.0,
            "issue_warn": "内八/外八倾向",
            "issue_bad": "足尖朝向代偿明显",
            "advice_warn": "加入髋旋转控制与足弓稳定训练。",
            "advice_bad": "建议进行髋-足联动评估，分阶段纠正足尖轨迹。",
        },
        {
            "metric": "支撑时间左右差",
            "value": metrics.get("support_time_asymmetry_ms", 0.0),
            "unit": "ms",
            "normal": "<=40ms",
            "ok": 40.0,
            "warn": 60.0,
            "issue_warn": "左右支撑时间不对称",
            "issue_bad": "单侧保护/代偿可能性高",
            "advice_warn": "弱侧增加单腿离心与稳定训练。",
            "advice_bad": "建议结合疼痛史做负荷管理与康复介入。",
        },
        {
            "metric": "支撑时间波动",
            "value": metrics.get("support_time_variability", 0.0),
            "unit": "%",
            "normal": "<=25%",
            "ok": 25.0,
            "warn": 35.0,
            "issue_warn": "节律稳定性一般",
            "issue_bad": "节律波动较大",
            "advice_warn": "用节拍器稳定步频后再提速。",
            "advice_bad": "建议先做低速节律重建，避免疲劳状态硬顶配速。",
        },
    ]

    result: List[Dict[str, str]] = []
    for item in data:
        value = float(item["value"])
        ok = value <= float(item["ok"])
        warn = value <= float(item["warn"])
        status = _status(ok, warn)
        issue = "未见明显异常"
        suggestion = "维持现有训练，定期复测。"
        if status == "提示关注":
            issue = item["issue_warn"]
            suggestion = item["advice_warn"]
        elif status == "建议干预":
            issue = item["issue_bad"]
            suggestion = item["advice_bad"]

        result.append({
            "metric": item["metric"],
            "current": _fmt(value, item["unit"]),
            "normal_range": item["normal"],
            "status": status,
            "issue": issue,
            "suggestion": suggestion,
        })

    return result
