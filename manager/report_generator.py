# manager/report_generator.py
import base64
import html
import os

from core.diagnosis_engine import get_ankle_status, get_knee_status


def generate_html_report(
    back_data,
    nickname,
    task_id,
    back_snapshot=None,
    height_cm=None,
    weight_kg=None,
    science_advice="",
    shoe_recommendations=None,
):
    """生成仅后视的完整 HTML 报告，返回 HTML 字符串。"""

    def image_to_base64(path):
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except OSError:
            return None

    back_snapshot_b64 = image_to_base64(back_snapshot)
    nickname_safe = html.escape(str(nickname or "客户"))

    def make_badge(text, color_hex):
        return (
            f'<span style="background-color: {color_hex}; color: white; '
            f'padding: 3px 10px; border-radius: 4px; font-size: 12px;">{text}</span>'
        )

    def get_status(angle, status_func):
        text, color = status_func(angle)
        return text, make_badge(text, color)

    # 后视数据
    pelvic_left = back_data.get("pelvic_left", 0)
    pelvic_right = back_data.get("pelvic_right", 0)
    knee_left_angle = back_data.get("knee_left_angle", 0)
    knee_right_angle = back_data.get("knee_right_angle", 0)
    knee_left_type = back_data.get("knee_left_type", "N/A")
    knee_right_type = back_data.get("knee_right_type", "N/A")
    ankle_left_angle = back_data.get("ankle_left_angle", 0)
    ankle_right_angle = back_data.get("ankle_right_angle", 0)
    ankle_left_type = back_data.get("ankle_left_type", "N/A")
    ankle_right_type = back_data.get("ankle_right_type", "N/A")
    pelvic_asymmetry = back_data.get("pelvic_asymmetry", 0)
    knee_asymmetry = back_data.get("knee_asymmetry", 0)
    ankle_asymmetry = back_data.get("ankle_asymmetry", 0)
    trunk_lateral_mean = back_data.get("trunk_lateral_mean", 0)
    trunk_lateral_variability = back_data.get("trunk_lateral_variability", 0)
    step_width_mean = back_data.get("step_width_mean", 0)
    cross_step_ratio = back_data.get("cross_step_ratio", 0)
    hip_sway_pct = back_data.get("hip_sway_pct", 0)
    left_fpa_mean = back_data.get("left_fpa_mean", 0)
    right_fpa_mean = back_data.get("right_fpa_mean", 0)
    left_support_time_ms = back_data.get("left_support_time_ms", 0)
    right_support_time_ms = back_data.get("right_support_time_ms", 0)
    support_time_asymmetry_ms = back_data.get("support_time_asymmetry_ms", 0)
    cadence_spm = back_data.get("cadence_spm", 0)
    support_time_variability = back_data.get("support_time_variability", 0)

    _, lk_badge = get_status(knee_left_angle, get_knee_status)
    _, rk_badge = get_status(knee_right_angle, get_knee_status)
    _, la_badge = get_status(ankle_left_angle, get_ankle_status)
    _, ra_badge = get_status(ankle_right_angle, get_ankle_status)

    issue_assessment = back_data.get("issue_assessment", [])
    all_advice = back_data.get("advice", [])
    if not science_advice:
        science_advice = "本次科学建议暂不可用，请稍后重试。"
    science_advice_safe = html.escape(str(science_advice))

    shoe_recommendations = shoe_recommendations or []
    shoe_items = []
    for item in shoe_recommendations[:3]:
        text = html.escape(str(item).strip())
        if text:
            shoe_items.append(f"<li>{text}</li>")
    if not shoe_items:
        shoe_items = ["<li>建议选择稳定支撑与中高缓震均衡的日常训练鞋，并根据训练强度进行双鞋轮换。</li>"]
    shoe_html = "".join(shoe_items)

    detail_advice_html = "".join([f"<li>{item}</li>" for item in all_advice])
    if not detail_advice_html:
        detail_advice_html = "<li>• 当前未识别到明显异常，建议定期复测并维持力量与稳定性训练。</li>"

    status_color = {"正常": "#10b981", "提示关注": "#f59e0b", "建议干预": "#ef4444"}
    issue_rows = []
    for item in issue_assessment:
        color = status_color.get(item.get("status", "正常"), "#10b981")
        issue_rows.append(
            f"""
            <div class="issue-item">
                <div class="issue-head">
                    <span class="issue-metric">{item.get("metric", "-")}</span>
                    <span class="issue-badge" style="background:{color};">{item.get("status", "正常")}</span>
                </div>
                <div class="issue-line"><span>当前值:</span><span>{item.get("current", "-")}</span></div>
                <div class="issue-line"><span>参考区间:</span><span>{item.get("normal_range", "-")}</span></div>
                <div class="issue-text"><strong>可能问题:</strong> {item.get("issue", "-")}</div>
                <div class="issue-text"><strong>对应建议:</strong> {item.get("suggestion", "-")}</div>
            </div>
            """
        )
    issue_html = "".join(issue_rows) if issue_rows else "<p>暂无问题评估数据。</p>"

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReLab 跑姿分析报告 - {nickname_safe}</title>
    <style>
        body {{ background-color: #05070a; color: #cbd5e1; font-family: 'Segoe UI', sans-serif; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1080px; margin: 0 auto; background: #0d1117; padding: 28px; border-radius: 16px; border: 1px solid #30363d; }}
        h1 {{ color: #ffffff; text-align: center; }}
        .section {{ margin: 25px 0; padding: 20px; background: #161b22; border-radius: 10px; }}
        .section-title {{ color: #00ffff; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 15px; font-size: 18px; }}
        .data-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #21262d; }}
        .data-row:last-child {{ border-bottom: none; }}
        .label {{ color: #94a3b8; }}
        .value {{ color: #ffffff; font-weight: bold; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 10px 0; border-bottom: 1px solid #21262d; line-height: 1.8; }}
        li:last-child {{ border-bottom: none; }}
        .footer {{ text-align: center; color: #475569; font-size: 12px; margin-top: 30px; }}
        .two-col {{ display: flex; gap: 20px; }}
        .two-col .card {{ flex: 1; background: #1a1f26; padding: 15px; border-radius: 8px; }}
        .issue-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .issue-item {{ background: #1a1f26; border-radius: 8px; padding: 12px; border: 1px solid #2b313b; }}
        .issue-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .issue-metric {{ color: #e2e8f0; font-weight: bold; }}
        .issue-badge {{ color: #fff; font-size: 12px; padding: 2px 8px; border-radius: 12px; }}
        .issue-line {{ display: flex; justify-content: space-between; color: #94a3b8; font-size: 13px; padding: 2px 0; }}
        .issue-text {{ color: #cbd5e1; font-size: 13px; margin-top: 6px; }}
        .top-grid {{ display: grid; grid-template-columns: 1.1fr 1fr; gap: 16px; margin-top: 10px; }}
        .profile-card {{ background: linear-gradient(160deg, #112232 0%, #0f1722 65%); border: 1px solid #1f3142; border-radius: 12px; padding: 18px; }}
        .profile-title {{ color: #dbeafe; font-size: 20px; font-weight: 700; margin-bottom: 8px; }}
        .profile-line {{ display: flex; justify-content: space-between; border-bottom: 1px dashed #27435d; padding: 8px 0; }}
        .profile-line:last-child {{ border-bottom: none; }}
        .shot-card {{ background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 10px; }}
        .shot-card img {{ width: 100%; border-radius: 8px; border: 2px solid #00ffff; display: block; }}
        .llm-advice {{ background: linear-gradient(180deg, #0d2a22 0%, #11231e 100%); border: 1px solid #1f4d3f; border-radius: 10px; padding: 14px; color: #d1fae5; }}
        .shoe-box {{ margin-top: 12px; background: #1a1f26; border: 1px solid #2b313b; border-radius: 10px; padding: 12px; }}
        .shoe-title {{ color: #fde68a; font-weight: 700; margin-bottom: 6px; }}
        @media (max-width: 900px) {{
            .two-col {{ flex-direction: column; }}
            .issue-grid {{ grid-template-columns: 1fr; }}
            .top-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>ReLab 跑姿分析报告</h1>
        <p style="text-align: center; color: #94a3b8;">客户: {nickname_safe} | 报告编号: {task_id}</p>

        <div class="top-grid">
            <div class="profile-card">
                <div class="profile-title">跑者信息</div>
                <div class="profile-line"><span class="label">昵称</span><span class="value">{nickname_safe}</span></div>
                <div class="profile-line"><span class="label">身高</span><span class="value">{f"{round(float(height_cm), 1)} cm" if height_cm else "未填写"}</span></div>
                <div class="profile-line"><span class="label">体重</span><span class="value">{f"{round(float(weight_kg), 1)} kg" if weight_kg else "未填写"}</span></div>
                <div class="profile-line"><span class="label">分析视角</span><span class="value">后视</span></div>
            </div>
            <div class="shot-card">
                {f'<img src="data:image/jpeg;base64,{back_snapshot_b64}" alt="后视骨骼标记截图" />' if back_snapshot_b64 else '<div style="color:#64748b; text-align:center; padding:40px 10px;">后视截图不可用</div>'}
            </div>
        </div>

        <div class="section">
            <div class="section-title">一、后视步态力线分析 (Rear View)</div>

            <div class="two-col">
                <div class="card">
                    <div class="data-row">
                        <span class="label">左支撑侧骨盆下垂:</span>
                        <span class="value">{pelvic_left}°</span>
                    </div>
                    <div class="data-row">
                        <span class="label">右支撑侧骨盆下垂:</span>
                        <span class="value">{pelvic_right}°</span>
                    </div>
                </div>
                <div class="card">
                    <div class="data-row">
                        <span class="label">左膝 ({knee_left_type}):</span>
                        <span class="value">{knee_left_angle}° {lk_badge}</span>
                    </div>
                    <div class="data-row">
                        <span class="label">右膝 ({knee_right_type}):</span>
                        <span class="value">{knee_right_angle}° {rk_badge}</span>
                    </div>
                </div>
            </div>

            <div style="margin-top: 15px;">
                <div class="data-row">
                    <span class="label">左踝 ({ankle_left_type}):</span>
                    <span class="value">{ankle_left_angle}° {la_badge}</span>
                </div>
                <div class="data-row">
                    <span class="label">右踝 ({ankle_right_type}):</span>
                    <span class="value">{ankle_right_angle}° {ra_badge}</span>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">二、后视扩展稳定性与对称性 (Rear+)</div>
            <div class="two-col">
                <div class="card">
                    <div class="data-row"><span class="label">骨盆左右差:</span><span class="value">{pelvic_asymmetry}°</span></div>
                    <div class="data-row"><span class="label">膝力线左右差:</span><span class="value">{knee_asymmetry}°</span></div>
                    <div class="data-row"><span class="label">踝力线左右差:</span><span class="value">{ankle_asymmetry}°</span></div>
                    <div class="data-row"><span class="label">躯干侧倾均值:</span><span class="value">{trunk_lateral_mean}°</span></div>
                    <div class="data-row"><span class="label">躯干侧倾波动:</span><span class="value">{trunk_lateral_variability}°</span></div>
                </div>
                <div class="card">
                    <div class="data-row"><span class="label">步宽(相对髋宽):</span><span class="value">{step_width_mean}%</span></div>
                    <div class="data-row"><span class="label">交叉步比例:</span><span class="value">{cross_step_ratio}%</span></div>
                    <div class="data-row"><span class="label">重心横摆(相对髋宽):</span><span class="value">{hip_sway_pct}%</span></div>
                    <div class="data-row"><span class="label">左足进展角:</span><span class="value">{left_fpa_mean}°</span></div>
                    <div class="data-row"><span class="label">右足进展角:</span><span class="value">{right_fpa_mean}°</span></div>
                </div>
            </div>
            <div style="margin-top: 15px;">
                <div class="data-row"><span class="label">左支撑时间:</span><span class="value">{left_support_time_ms} ms</span></div>
                <div class="data-row"><span class="label">右支撑时间:</span><span class="value">{right_support_time_ms} ms</span></div>
                <div class="data-row"><span class="label">支撑时间左右差:</span><span class="value">{support_time_asymmetry_ms} ms</span></div>
                <div class="data-row"><span class="label">估算步频:</span><span class="value">{cadence_spm} spm</span></div>
                <div class="data-row"><span class="label">支撑时间波动:</span><span class="value">{support_time_variability}%</span></div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">三、问题评估与对应建议 (Rear View)</div>
            <div class="issue-grid">{issue_html}</div>
        </div>

        <div class="section">
            <div class="section-title">四、科学建议</div>
            <div class="llm-advice">{science_advice_safe}</div>
            <div class="shoe-box">
                <div class="shoe-title">跑鞋推荐 Top3</div>
                <ul style="margin-top:6px;">{shoe_html}</ul>
            </div>
            <ul style="margin-top:12px;">{detail_advice_html}</ul>
        </div>

        <div class="footer">
            Generated by ReLab API V4.0
        </div>
    </div>
</body>
</html>
"""
    return html_content
