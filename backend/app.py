# backend/app.py
"""
ReLab 跑姿分析后端 API 服务
基于 Flask，提供视频分析接口
仅接收后视视频，生成后视分析报告
"""

import os
import re
import sys
import time
import uuid
from datetime import datetime

from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载环境变量配置文件
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# 导入分析模块
from manager.analysis_manager import process_back_view
from manager.report_generator import generate_html_report
from manager.llm_advisor import generate_llm_outputs

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = "/tmp/relab_uploads"
REPORT_FOLDER = "/tmp/relab_reports"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["REPORT_FOLDER"] = REPORT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 最大 100MB

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_task_id():
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def safe_nickname_for_filename(nickname):
    """清理昵称以便用于文件名"""
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', nickname)
    return safe[:20]


def parse_optional_positive_float(value):
    """解析可选的正浮点数参数"""
    if not value:
        return None
    try:
        f = float(value)
        return f if f > 0 else None
    except ValueError:
        return None

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = "/tmp/relab_uploads"
REPORT_FOLDER = "/tmp/relab_reports"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["REPORT_FOLDER"] = REPORT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 最大 100MB

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_task_id():
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def safe_nickname_for_filename(nickname: str) -> str:
    """仅用于文件名，避免路径穿越和非法字符。"""
    raw = (nickname or "客户").strip()
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]", "_", raw)
    cleaned = cleaned.strip("._-")
    return cleaned[:50] or "客户"


def parse_optional_positive_float(raw_value):
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


# ==================== 首页 ====================
@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ReLab 跑姿分析 API</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #00ffff; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>ReLab 跑姿分析 API</h1>
        <p>版本: 4.0 (MediaPipe)</p>

        <h2>接口列表</h2>

        <div class="endpoint">
            <h3>POST /api/analyze</h3>
            <p>上传后视视频进行分析</p>
            <p><strong>参数:</strong></p>
            <ul>
                <li><code>back_video</code> - 后视视频文件 (必填)</li>
                <li><code>nickname</code> - 客户昵称 (可选)</li>
                <li><code>height_cm</code> - 身高(cm) (可选)</li>
                <li><code>weight_kg</code> - 体重(kg) (可选)</li>
            </ul>
            <p><strong>返回:</strong> JSON 数据 + HTML 报告 URL</p>
        </div>

        <div class="endpoint">
            <h3>GET /api/status</h3>
            <p>获取服务状态</p>
        </div>

        <div class="endpoint">
            <h3>GET /api/report/&lt;task_id&gt;</h3>
            <p>获取 HTML 报告</p>
        </div>
    </body>
    </html>
    """


# ==================== 状态接口 ====================
@app.route("/api/status")
def status():
    return jsonify(
        {
            "status": "running",
            "version": "4.0",
            "model": "MediaPipe",
            "timestamp": datetime.now().isoformat(),
        }
    )


# ==================== 分析接口（仅后视） ====================
@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    接收后视视频，分析后生成完整报告
    """
    back_path = None
    back_output = None
    back_snapshot = None

    # 检查视频文件
    back_video = request.files.get("back_video")
    nickname = request.form.get("nickname", "客户")
    height_cm = parse_optional_positive_float(request.form.get("height_cm"))
    weight_kg = parse_optional_positive_float(request.form.get("weight_kg"))

    # 验证文件
    if not back_video or back_video.filename == "":
        return jsonify({"error": "请上传后视视频 (back_video)"}), 400

    if not allowed_file(back_video.filename):
        return jsonify({"error": "后视视频格式不支持"}), 400

    # 生成任务ID
    task_id = generate_task_id()

    # 保存上传的视频
    back_filename = f"{task_id}_back_{secure_filename(back_video.filename)}"
    back_path = os.path.join(app.config["UPLOAD_FOLDER"], back_filename)

    back_video.save(back_path)

    try:
        total_start = time.time()

        # ===== 1. 分析后视 =====
        print(f"[{task_id}] 开始分析后视视频...")
        back_start = time.time()
        back_output, back_snapshot, back_data = process_back_view(back_path)
        back_elapsed = time.time() - back_start
        print(f"[{task_id}] 后视分析完成，耗时: {back_elapsed:.2f}秒")

        total_elapsed = time.time() - total_start

        # ===== 2. 基于后视分析结果调用大模型建议 =====
        llm_outputs = generate_llm_outputs(back_data, nickname, height_cm=height_cm, weight_kg=weight_kg)
        science_advice = llm_outputs.get("science_advice", "")
        shoe_recommendations = llm_outputs.get("shoe_recommendations", [])

        # ===== 2. 生成完整 HTML 报告 =====
        print(f"[{task_id}] 生成完整报告...")
        html_report = generate_html_report(
            back_data,
            nickname,
            task_id,
            back_snapshot=back_snapshot,
            height_cm=height_cm,
            weight_kg=weight_kg,
            science_advice=science_advice,
            shoe_recommendations=shoe_recommendations,
        )

        # 保存报告
        safe_name = safe_nickname_for_filename(nickname)
        report_filename = f"报告_{safe_name}_{task_id}.html"
        report_path = os.path.join(app.config["REPORT_FOLDER"], report_filename)
        with open(report_path, "w", encoding="utf-8") as report_file:
            report_file.write(html_report)

        all_advice = back_data.get("advice", [])

        # 返回结果
        result = {
            "success": True,
            "task_id": task_id,
            "nickname": nickname,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "back_data": back_data,
            "back_elapsed": round(back_elapsed, 2),
            "total_elapsed": round(total_elapsed, 2),
            "all_advice": all_advice,
            "science_advice": science_advice,
            "shoe_recommendations": shoe_recommendations,
            "report_url": f"/api/report/{task_id}",
        }

        print(f"[{task_id}] 分析完成，总耗时: {total_elapsed:.2f}秒")
        return jsonify(result)

    except Exception as exc:
        import traceback

        error_msg = str(exc)
        traceback_msg = traceback.format_exc()
        print(f"[{task_id}] 分析失败: {error_msg}")
        print(traceback_msg)
        return jsonify({"success": False, "error": error_msg}), 500

    finally:
        # 清理上传和分析过程中的临时文件
        for temp_path in [back_path, back_output, back_snapshot]:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


# ==================== 报告下载接口 ====================
@app.route("/api/report/<task_id>")
def get_report(task_id):
    """获取分析报告"""
    for filename in os.listdir(app.config["REPORT_FOLDER"]):
        if task_id in filename:
            report_path = os.path.join(app.config["REPORT_FOLDER"], filename)
            return send_file(report_path, mimetype="text/html")

    return jsonify({"error": "报告不存在"}), 404


# ==================== 健康检查 ====================
@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    # 启动服务
    app.run(host="0.0.0.0", port=5000, debug=False)
