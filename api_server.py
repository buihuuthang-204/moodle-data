import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import joblib  # type: ignore
import warnings
import requests  # type: ignore
import shap  # type: ignore
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
import subprocess

# === Logging chuyên nghiệp ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('EWS')

# Suppress sklearn version mismatch warning khi load .pkl tu Colab
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
from google import genai  # SDK moi (thay the google.generativeai da deprecated)
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # type: ignore
from dotenv import load_dotenv  # type: ignore
from pymongo import MongoClient  # type: ignore

# Load config
load_dotenv()

app = Flask(__name__)
CORS(app)

# ═══ CONFIG ═══
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ai_client = None
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "your_email@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "your_app_password")
SPEEDSMS_API_TOKEN = os.getenv("SPEEDSMS_API_TOKEN", "")

# ═══ MONGODB ═══
MONGO_URI = os.getenv("MONGO_URI", "")
db = None
if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        db = mongo_client['ews_pro']
        logger.info('[MongoDB] Ket noi thanh cong!')
    except Exception as e:
        logger.warning(f'[MongoDB] Khong ket noi duoc: {e}')
        logger.info('[MongoDB] Se dung fallback JSON file.')

# ═══ ML MODEL ═══
ml_model = None
if os.path.exists('student_risk_model.pkl'):
    try:
        ml_model = joblib.load('student_risk_model.pkl')
        acc = ml_model.get('accuracy', 0)
        logger.info(f'[ML] Model loaded: RF Accuracy={acc:.4f}')
    except Exception as e:
        logger.error(f'[ML] Loi khi load model: {e}')
else:
    logger.warning('[ML] Chua co file student_risk_model.pkl. Dashboard se dung rule-based scoring.')


# ═══ HELPER: Flatten Nested Array → Dict phẳng cho ML ═══
def flatten_student_doc(doc):
    """Chuyen 1 document MongoDB (Nested Array) thanh dict phang de phuc vu ML model."""
    flat = {}
    if 'weeks' in doc and 'totals' in doc:
        for w in doc['weeks']:
            wk = w.get('week', 0)
            for k, v in w.items():
                if k != 'week':
                    flat[f"{k}_w{wk}"] = v
        for k, v in doc['totals'].items():
            flat[k] = v
    else:
        flat = {k: v for k, v in doc.items() if k not in ('_id',)}
    return flat


def predict_student_risk(doc):
    """Du doan risk score tu ML model cho 1 sinh vien. Tra ve None neu khong predict duoc."""
    if ml_model is None:
        return None
    try:
        features = ml_model['features']
        scaler = ml_model['scaler']
        model = ml_model['model']

        flat_data = flatten_student_doc(doc)
        df_input = pd.DataFrame([flat_data])

        for f in features:
            if f not in df_input.columns:
                df_input[f] = 0
        df_input = df_input[features]

        X_scaled = scaler.transform(df_input)
        proba = model.predict_proba(X_scaled)[0]
        risk_prob = float(proba[1]) * 100 if len(proba) > 1 else 0.0
        return round(risk_prob, 1)  # type: ignore
    except Exception:
        return None


def format_student_for_dashboard(doc):
    """Chuyen 1 document MongoDB thanh format ma Dashboard can."""
    s = {
        "mssv": str(doc.get('mssv') or doc.get('student_id') or ''),
        "name": doc.get('name') or doc.get('full_name') or '',
        "course": doc.get('course', ''),
        "class": doc.get('class', ''),
    }

    if 'totals' in doc and 'weeks' in doc:
        # Nested format (từ sync_sheet_to_mongo với cấu trúc weeks/totals)
        totals = doc['totals']
        s['score'] = totals.get('total_weekly_score', 0)
        s['login'] = totals.get('total_login_count', 0)
        s['video'] = totals.get('total_video_views', 0)
        s['doc'] = totals.get('total_document_reads', 0)
        s['disc'] = totals.get('total_discussion', 0)
        s['session'] = totals.get('total_session_duration', 0)
        s['duration'] = totals.get('total_assignment_duration_mins', 0)

        weeks_sorted = sorted(doc['weeks'], key=lambda x: x.get('week', 0))
        s['w'] = [w.get('weekly_score', 0) for w in weeks_sorted]
        s['total_assignments'] = [w.get('total_assignments', 0) for w in weeks_sorted]
        s['assignment_attempt'] = [w.get('assignment_attempt', 0) for w in weeks_sorted]
    elif 'score' in doc and 'w' in doc:
        # Dashboard-ready format (đã có sẵn các field ngắn từ generate_dashboard_data.py)
        for key in ('score', 'login', 'video', 'doc', 'disc', 'session', 'duration', 'w',
                     'total_assignments', 'assignment_attempt'):
            if key in doc:
                s[key] = doc[key]
    elif 'total_weekly_score' in doc:
        # Flat format (từ generate_dashboard_data.py / Google Sheets import trực tiếp)
        s['score'] = doc.get('total_weekly_score', 0)
        s['login'] = doc.get('total_login_count', 0)
        s['video'] = doc.get('total_video_views', 0)
        s['doc'] = doc.get('total_document_reads', 0)
        s['disc'] = doc.get('total_discussion', 0)
        s['session'] = doc.get('total_session_duration', 0)
        s['duration'] = doc.get('total_assignment_duration_mins', 0)
        s['w'] = [
            doc.get('weekly_score_w1', 0),
            doc.get('weekly_score_w2', 0),
            doc.get('weekly_score_w3', 0),
            doc.get('weekly_score_w4', 0),
        ]
        s['total_assignments'] = [
            doc.get('total_assignments_w1', 0),
            doc.get('total_assignments_w2', 0),
            doc.get('total_assignments_w3', 0),
            doc.get('total_assignments_w4', 0),
        ]
        s['assignment_attempt'] = [
            doc.get('assignment_attempt_w1', 0),
            doc.get('assignment_attempt_w2', 0),
            doc.get('assignment_attempt_w3', 0),
            doc.get('assignment_attempt_w4', 0),
        ]
    else:
        s.update(doc)

    s['ai_risk_score'] = predict_student_risk(doc)
    return s


# ═══ HOMEPAGE ═══
@app.route('/')
def index():
    """Phục vụ file dashboard.html (Frontend chính)."""
    return send_from_directory('.', 'dashboard.html')

# ═══ API: STUDENTS ═══
@app.route('/api/students', methods=['GET'])
def get_students():
    """Lay danh sach sinh vien tu MongoDB hoac fallback JSON."""
    if db is not None:
        raw_students = list(db.students.find({}, {'_id': 0}))
        return jsonify([format_student_for_dashboard(doc) for doc in raw_students])
    else:
        try:
            with open('students_data.json', 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except Exception:
            return jsonify([])


@app.route('/api/students/import', methods=['POST'])
def import_students():
    """Import students_data.json vao MongoDB."""
    if db is None:
        return jsonify({"error": "MongoDB chua duoc cau hinh"}), 500
    try:
        with open('students_data.json', 'r', encoding='utf-8') as f:
            students = json.load(f)
        db.students.delete_many({})
        if students:
            db.students.insert_many(students)
        return jsonify({"success": True, "count": len(students)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══ API: INTERVENTIONS ═══
@app.route('/api/interventions', methods=['GET'])
def get_interventions():
    """Lay lich su can thiep cua 1 SV."""
    mssv = request.args.get('mssv', '')
    if db is None:
        return jsonify([])
    records = list(db.interventions.find({'mssv': mssv}, {'_id': 0}).sort('timestamp', -1))
    return jsonify(records)


@app.route('/api/interventions', methods=['POST'])
def save_intervention():
    """Luu 1 hanh dong can thiep."""
    if db is None:
        return jsonify({"warning": "MongoDB chua cau hinh, khong luu duoc."})
    data = request.json
    data['timestamp'] = datetime.utcnow().isoformat()
    db.interventions.insert_one(data)
    return jsonify({"success": True})


# ═══ API: ML PREDICT ═══
@app.route('/api/predict', methods=['POST'])
def predict_risk():
    """Du doan muc do rui ro cua 1 sinh vien bang ML model."""
    if ml_model is None:
        return jsonify({"error": "Chua co model. Chay Train_Model_Colab.py tren Colab truoc."}), 500

    data = request.json
    try:
        features = ml_model['features']
        scaler = ml_model['scaler']
        model = ml_model['model']

        df_input = pd.DataFrame([data])
        for f in features:
            if f not in df_input.columns:
                df_input[f] = 0
        df_input = df_input[features]

        X_scaled = scaler.transform(df_input)
        prediction = int(model.predict(X_scaled)[0])
        proba = model.predict_proba(X_scaled)[0]

        return jsonify({
            "prediction": prediction,
            "label": "Co nguy co" if prediction == 1 else "An toan",
            "probability": {
                "an_toan": float(np.round(proba[0], 4)),
                "co_nguy_co": float(np.round(proba[1], 4)) if len(proba) > 1 else 0.0
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══ API: EXPLAINABLE AI (XAI) ═══
@app.route('/api/explain/<mssv>', methods=['GET'])
def explain_student(mssv):
    """Sử dụng SHAP để giải thích lý do vì sao một sinh viên có nguy cơ rớt môn (XAI)."""
    if db is None or ml_model is None:
        return jsonify({"error": "Chưa kết nối DB hoặc mô hình ML"}), 500
    
    doc = db.students.find_one({"mssv": mssv})
    if not doc:
        return jsonify({"error": "Không tìm thấy sinh viên"}), 404
        
    try:
        features = ml_model['features']
        scaler = ml_model['scaler']
        model = ml_model['model']

        flat_data = flatten_student_doc(doc)
        df_input = pd.DataFrame([flat_data])

        for f in features:
            if f not in df_input.columns:
                df_input[f] = 0
        df_input = df_input[features]

        X_scaled = scaler.transform(df_input)
        
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_scaled)
        
        # Với Random Forest (phân loại nhị phân), shape trả về thường là list của 2 array (class 0 và class 1).
        sv = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
        
        feature_impacts = [{"feature": f, "impact": float(v)} for f, v in zip(features, sv)]
        # Chọn top thay đổi tích cực dẫn đến nguy cơ (impact > 0)
        feature_impacts.sort(key=lambda x: x['impact'], reverse=True)
        top_3 = [x for x in feature_impacts if x['impact'] > 0][:3]
        
        # Generate friendly names for UI
        translate = {
            "total_login_count": "Ít truy cập Moodle",
            "total_weekly_score": "Điểm bài tập thấp",
            "total_document_reads": "Lười đọc tài liệu",
            "total_assignment_duration_mins": "Làm bài quá nhanh hoặc chậm",
            "active_days_w1": "Ít học trong tuần 1"
        }
        for f in top_3:
            f['friendly_name'] = translate.get(f['feature'], str(f['feature']).replace('_', ' ').title())

        return jsonify({
            "mssv": mssv,
            "top_factors": top_3
        })
    except Exception as e:
        logger.error(f"[XAI] Lỗi khi giải thích SHAP: {e}")
        return jsonify({"error": str(e)}), 500


# ═══ API: GEMINI AI ═══
@app.route('/api/generate-ai', methods=['POST'])
def generate_ai():
    if not GEMINI_API_KEY or ai_client is None:
        return jsonify({"error": "Chua cau hinh GEMINI_API_KEY trong file .env"}), 500

    data = request.json
    student = data.get('student', {})

    prompt = f"""
    Ban la mot Co van hoc tap tai Dai hoc. Hay viet 2 doan tin nhan canh bao hoc vu cho sinh vien dua tren thong tin sau:
    - Ten: {student.get('name')}
    - MSSV: {student.get('mssv')}
    - Mon hoc: {student.get('course')}
    - Muc do rui ro rot mon: {student.get('riskPct')}%
    - Ly do chinh: {student.get('issue')}
    - Diem trung binh tuan: {student.get('score')}
    - So lan dang nhap he thong trong thang: {student.get('login')}

    Yeu cau:
    1. Mot email chi tiet, lich su, neu ro van de han che o tren, canh bao muc do rui ro, va yeu cau sinh vien phan hoi hoac gap mat de giai quyet. (Khoang 150 chu).
    2. Mot tin nhan SMS KHONG DAU, cuc ky ngan gon (duoi 160 ky tu) de bao dong cho sinh vien kiem tra Email gap hoac lien he co van.

    Tra ve dinh dang JSON chinh xac nhu sau:
    {{
        "email_content": "noi dung email o day...",
        "sms_content": "noi dung sms khong dau o day..."
    }}
    Chi tra ve JSON, khong them van ban du thua.
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text = response.text
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        result = json.loads(text.strip())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══ API: EMAIL ═══
@app.route('/api/send-email', methods=['POST'])
def send_email():
    if GMAIL_APP_PASSWORD == "your_app_password":
        return jsonify({"error": "Chua cau hinh GMAIL_APP_PASSWORD"}), 500

    data = request.json
    to_email = data.get('to')
    subject = data.get('subject')
    body = data.get('body')

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Co van hoc tap EWS <{GMAIL_ADDRESS}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return jsonify({"success": True, "message": "Email sent successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══ API: SMS ═══
@app.route('/api/send-sms', methods=['POST'])
def send_sms():
    if not SPEEDSMS_API_TOKEN:
        return jsonify({"warning": "Chua cau hinh API SMS. Gia lap SMS thanh cong."})

    data = request.json
    phone = data.get('to', '')
    if phone.startswith('0'):
        phone = '84' + phone[1:]
    content = data.get('body')

    try:
        url = "https://api.speedsms.vn/index.php/sms/send"
        auth = (SPEEDSMS_API_TOKEN, "x")
        payload = {
            "to": [phone],
            "content": content,
            "sms_type": 2,
            "brandname": "Notify"
        }
        r = requests.post(url, json=payload, auth=auth)
        res_data = r.json()
        if res_data.get('status') == 'success':
            return jsonify({"success": True})
        else:
            return jsonify({"error": res_data.get('message')}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══ API: ĐĂNG NHẬP (Backend Authentication) ═══
VALID_USERS = {
    'admin': {'password': 'ews2024', 'role': 'Admin Hệ thống'},
    'advisor': {'password': '123456', 'role': 'Cố vấn Học tập'},
    'gv': {'password': 'gv2024', 'role': 'Giảng viên'},
}

@app.route('/api/login', methods=['POST'])
def api_login():
    """Xác thực đăng nhập từ phía server."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    user = VALID_USERS.get(username)
    if user and user['password'] == password:
        logger.info(f'[Auth] Đăng nhập thành công: {username}')
        return jsonify({
            "success": True,
            "username": username,
            "role": user['role'],
        })
    else:
        logger.warning(f'[Auth] Đăng nhập thất bại: {username}')
        return jsonify({"success": False, "error": "Sai tên đăng nhập hoặc mật khẩu"}), 401


# ═══ API: HEALTH CHECK ═══
@app.route('/api/status', methods=['GET'])
def api_status():
    """Kiem tra trang thai cac dich vu."""
    return jsonify({
        "gemini": bool(GEMINI_API_KEY),
        "email": GMAIL_APP_PASSWORD != "your_app_password",
        "sms": bool(SPEEDSMS_API_TOKEN),
        "mongodb": db is not None,
        "ml_model": ml_model is not None,
        "ml_accuracy": ml_model.get('accuracy') if ml_model else None
    })


# ═══ ETL SCHEDULER ═══
def run_etl_job():
    """Tự động hoá pipeline kéo dữ liệu hàng ngày (Yêu cầu đánh giá luận văn)."""
    logger.info("[Scheduler] Bắt đầu tự động hoá ETL Pipeline...")
    try:
        subprocess.run(["python", "etl_moodle_warehouse.py"], check=False)
        subprocess.run(["python", "sync_sheet_to_mongo.py"], check=False)
        logger.info("[Scheduler] Tự động hoá ETL hoàn tất.")
    except Exception as e:
        logger.error(f"[Scheduler] Lỗi khi chạy ETL tự động: {e}")

# Khai báo Background Scheduler (chạy mỗi đêm lúc 1H sáng)
scheduler = BackgroundScheduler()
scheduler.add_job(func=run_etl_job, trigger="cron", hour=1, minute=0)
scheduler.start()


if __name__ == '__main__':
    logger.info('=' * 50)
    logger.info('EWS Pro API Server')
    logger.info('=' * 50)
    logger.info(f"  Gemini AI : {'OK' if GEMINI_API_KEY else 'CHUA CAU HINH'}")
    logger.info(f"  Email     : {'OK' if GMAIL_APP_PASSWORD != 'your_app_password' else 'CHUA CAU HINH'}")
    logger.info(f"  SMS       : {'OK' if SPEEDSMS_API_TOKEN else 'CHUA CAU HINH'}")
    logger.info(f"  MongoDB   : {'OK' if db is not None else 'CHUA CAU HINH (dung JSON fallback)'}")
    logger.info(f"  ML Model  : {'OK' if ml_model is not None else 'CHUA CO (dung rule-based)'}")
    logger.info('=' * 50)
    logger.info('APIs: /api/students, /api/predict, /api/generate-ai, /api/send-email, /api/send-sms, /api/status')
    logger.info('Dang chay tai http://0.0.0.0:5000 (Cho phep truy cap mang LAN)')
    app.run(host='0.0.0.0', port=5000, debug=True)
