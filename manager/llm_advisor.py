import json
import os
import urllib.request
from typing import Any, Dict, List, Optional


def _truncate_chars(text: str, limit: int = 150) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。；、 ") + "。"


def _truncate_list(items: List[str], limit: int = 3, item_limit: int = 80) -> List[str]:
    out: List[str] = []
    for item in items[:limit]:
        text = (item or "").strip()
        if not text:
            continue
        out.append(_truncate_chars(text, item_limit))
    return out


def _ensure_top3_with_reason(items: List[str]) -> List[str]:
    base = [
        "推荐：稳定支撑训练鞋；理由：有助于控制内扣与横向摆动，适合需要步态稳定的人群。",
        "推荐：中高缓震慢跑鞋；理由：可降低日常训练冲击，提升长距离舒适性。",
        "推荐：轻量节奏训练鞋；理由：在姿态稳定前提下兼顾推进效率，适合提速课表。",
    ]
    clean = _truncate_list(items, limit=3, item_limit=100)
    if len(clean) >= 3:
        return clean[:3]
    return clean + base[len(clean):3]


def _fallback_outputs(back_data: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = back_data.get("issue_assessment", []) or []
    bad = [i for i in issues if i.get("status") == "建议干预"]
    warn = [i for i in issues if i.get("status") == "提示关注"]

    focus = bad[:2] if bad else warn[:2]
    if not focus:
        return {
            "science_advice": "本次后视跑姿整体稳定，建议保持当前训练节奏，每周2次臀中肌与核心稳定训练，并每4-6周复测关键指标。",
            "shoe_recommendations": _ensure_top3_with_reason([
                "建议选择日常缓震训练鞋，关注中底缓震均衡与舒适鞋楦。",
                "若周跑量较大，可搭配一双稳定支撑型慢跑鞋轮换使用。",
            ]),
        }

    parts = [f"{item.get('metric', '')}{item.get('current', '')}" for item in focus]
    text = "本次后视评估重点关注" + "、".join(parts) + "。建议先做步宽与骨盆稳定控制训练，弱侧增加单腿力量和平衡训练，近期循序增量并在2-4周复测。"
    shoe = [
        "优先考虑稳定支撑型训练鞋，降低过度内扣与横摆带来的负荷。",
        "可搭配中高缓震日常跑鞋，减少训练期冲击累积。",
    ]
    return {
        "science_advice": _truncate_chars(text, 150),
        "shoe_recommendations": _ensure_top3_with_reason(shoe),
    }


def _build_summary(back_data: Dict[str, Any], nickname: str, height_cm: Optional[float], weight_kg: Optional[float]) -> Dict[str, Any]:
    issues = back_data.get("issue_assessment", []) or []
    focus = [i for i in issues if i.get("status") in ("提示关注", "建议干预")]
    return {
        "nickname": nickname,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "metrics": {
            "pelvic_left": back_data.get("pelvic_left", 0),
            "pelvic_right": back_data.get("pelvic_right", 0),
            "knee_left_angle": back_data.get("knee_left_angle", 0),
            "knee_right_angle": back_data.get("knee_right_angle", 0),
            "ankle_left_angle": back_data.get("ankle_left_angle", 0),
            "ankle_right_angle": back_data.get("ankle_right_angle", 0),
            "cross_step_ratio": back_data.get("cross_step_ratio", 0),
            "hip_sway_pct": back_data.get("hip_sway_pct", 0),
            "support_time_asymmetry_ms": back_data.get("support_time_asymmetry_ms", 0),
            "support_time_variability": back_data.get("support_time_variability", 0),
        },
        "focus_issues": focus[:6],
    }


def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception as e:
        import traceback
        print(f"[LLM Error] {e}")
        traceback.print_exc()
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception as e:
        import traceback
        print(f"[LLM Error] {e}")
        traceback.print_exc()
        return None


def generate_llm_outputs(
    back_data: Dict[str, Any],
    nickname: str,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    调用大模型生成科学建议与跑鞋推荐；若未配置 API 或调用失败，返回规则兜底结果。
    环境变量:
      RELAB_LLM_API_KEY
      RELAB_LLM_MODEL (默认 deepseek-chat)
      RELAB_LLM_API_URL (默认 DeepSeek Chat Completions)
    """
    api_key = os.getenv("RELAB_LLM_API_KEY", "").strip()
    model = os.getenv("RELAB_LLM_MODEL", "deepseek-chat").strip()
    api_url = os.getenv("RELAB_LLM_API_URL", "https://api.deepseek.com/chat/completions").strip()

    summary = _build_summary(back_data, nickname, height_cm, weight_kg)
    if not api_key:
        return _fallback_outputs(back_data)

    system_prompt = (
        "你是运动康复跑姿教练与跑鞋顾问。请基于输入指标给出个性化建议，严格输出 JSON，格式为："
        '{"science_advice":"...","shoe_recommendations":["...","..."]}。'
        "要求："
        "1) science_advice 为中文单段，不超过150字；"
        "2) shoe_recommendations 必须给出3条（Top3），每条必须同时包含“推荐：”和“理由：”；"
        "3) 不编造未给出的数据，不输出 JSON 以外任何文本。"
    )

    user_prompt = "以下是后视跑姿分析结果(JSON)：\n" + json.dumps(summary, ensure_ascii=False)
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        data = json.loads(raw)
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        parsed = _extract_json_block(content)
        if not parsed:
            return _fallback_outputs(back_data)

        science_advice = _truncate_chars(str(parsed.get("science_advice", "")).strip(), 150)
        shoes_raw = parsed.get("shoe_recommendations", [])
        shoes = []
        if isinstance(shoes_raw, list):
            shoes = [str(x).strip() for x in shoes_raw if str(x).strip()]
        shoes = _ensure_top3_with_reason(shoes)

        if not science_advice:
            return _fallback_outputs(back_data)
        if not shoes:
            shoes = _ensure_top3_with_reason(
                _fallback_outputs(back_data).get("shoe_recommendations", [])
            )

        return {
            "science_advice": science_advice,
            "shoe_recommendations": shoes,
        }
    except Exception as e:
        import traceback
        print(f"[LLM Error] {e}")
        traceback.print_exc()
        return _fallback_outputs(back_data)
