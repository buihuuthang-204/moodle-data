# -*- coding: utf-8 -*-
"""
Unit Tests cho Hệ thống EWS Pro
Chạy: python -m pytest tests/ -v
"""
import sys
import os
import json
import pytest

# Thêm thư mục gốc vào path để import được các module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# TEST 1: Hàm flatten_student_doc (api_server.py)
# ============================================================
class TestFlattenStudentDoc:
    """Test chuyển document MongoDB (Nested Array) → dict phẳng cho ML."""

    def test_nested_format(self):
        """Test với dữ liệu dạng Nested Array (chuẩn từ MongoDB)."""
        from api_server import flatten_student_doc
        doc = {
            'mssv': '122000001',
            'name': 'Nguyễn Văn A',
            'weeks': [
                {'week': 1, 'login_count': 5, 'weekly_score': 10},
                {'week': 2, 'login_count': 3, 'weekly_score': 8},
            ],
            'totals': {
                'total_login_count': 8,
                'total_weekly_score': 18,
            }
        }
        result = flatten_student_doc(doc)
        assert result['login_count_w1'] == 5
        assert result['weekly_score_w2'] == 8
        assert result['total_login_count'] == 8
        assert 'mssv' not in result  # mssv không nằm trong flat dict

    def test_flat_format(self):
        """Test với dữ liệu đã phẳng sẵn (fallback JSON)."""
        from api_server import flatten_student_doc
        doc = {'mssv': '122000002', 'score': 50, 'login': 10, '_id': 'abc123'}
        result = flatten_student_doc(doc)
        assert result['score'] == 50
        assert result['login'] == 10
        assert '_id' not in result  # _id bị loại bỏ

    def test_empty_doc(self):
        """Test với document rỗng."""
        from api_server import flatten_student_doc
        result = flatten_student_doc({})
        assert isinstance(result, dict)


# ============================================================
# TEST 2: Hàm build_student_doc (sync_sheet_to_mongo.py)
# ============================================================
class TestBuildStudentDoc:
    """Test chuyển 1 dòng Google Sheet → document MongoDB."""

    def test_basic_conversion(self):
        """Test chuyển đổi cơ bản với dữ liệu mẫu."""
        from sync_sheet_to_mongo import build_student_doc
        row = {
            'MSSV': '122000010',
            'Ho_Ten': 'Trần Thị B',
            'Email': 'b@test.com',
            'login_count_w1': 5,
            'login_count_w2': 3,
            'login_count_w3': 4,
            'login_count_w4': 2,
            'weekly_score_w1': 10,
            'weekly_score_w2': 8,
            'weekly_score_w3': 9,
            'weekly_score_w4': 7,
            'total_login_count': 14,
            'total_weekly_score': 34,
        }
        docs = build_student_doc(row)
        assert isinstance(docs, list)
        assert len(docs) == 2  # Mỗi SV học 2 khóa
        assert docs[0]['mssv'] == '122000010'
        assert docs[0]['name'] == 'Trần Thị B'
        assert docs[0]['course'] == 'Nhập môn Lập trình C++'
        assert docs[1]['course'] == 'English for Information Technology'
        assert len(docs[0]['weeks']) == 4
        assert docs[0]['weeks'][0]['week'] == 1

    def test_both_courses(self):
        """Test: Mọi SV đều xuất hiện ở 2 khóa."""
        from sync_sheet_to_mongo import build_student_doc
        row = {'MSSV': '122000011', 'Ho_Ten': 'Test'}
        docs = build_student_doc(row)
        courses = [d['course'] for d in docs]
        assert 'Nhập môn Lập trình C++' in courses
        assert 'English for Information Technology' in courses


# ============================================================
# TEST 3: Hàm to_num (sync_sheet_to_mongo.py)
# ============================================================
class TestToNum:
    """Test chuyển giá trị về số."""

    def test_integer(self):
        from sync_sheet_to_mongo import to_num
        assert to_num(5) == 5
        assert to_num('10') == 10

    def test_float(self):
        from sync_sheet_to_mongo import to_num
        assert to_num('3.14') == 3.14

    def test_invalid(self):
        from sync_sheet_to_mongo import to_num
        assert to_num('abc') == 0
        assert to_num(None) == 0
        assert to_num('') == 0


# ============================================================
# TEST 4: Hàm generate_dashboard_data (logic cơ bản)
# ============================================================
class TestGenerateDashboard:
    """Test logic phân chia khóa học trong generate_dashboard_data."""

    def test_course_assignment(self):
        """MSSV chẵn → C++, MSSV lẻ → English."""
        even = int('122000010') % 2  # 0 → C++
        odd = int('122000011') % 2   # 1 → English
        assert even == 0
        assert odd == 1


# ============================================================
# TEST 5: API Server endpoints (Flask test client)
# ============================================================
class TestAPIEndpoints:
    """Test các endpoint API cơ bản."""

    @pytest.fixture
    def client(self):
        from api_server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_status_endpoint(self, client):
        """Test /api/status trả về JSON hợp lệ."""
        rv = client.get('/api/status')
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert 'gemini' in data
        assert 'mongodb' in data
        assert 'ml_model' in data

    def test_students_endpoint(self, client):
        """Test /api/students trả về danh sách."""
        rv = client.get('/api/students')
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert isinstance(data, list)

    def test_predict_without_model(self, client):
        """Test /api/predict khi chưa có model → trả lỗi hoặc kết quả."""
        rv = client.post('/api/predict',
                        data=json.dumps({'total_login_count': 10}),
                        content_type='application/json')
        # Có thể 200 (nếu có model) hoặc 500 (nếu chưa có model)
        assert rv.status_code in [200, 500]

    def test_homepage_serves_dashboard(self, client):
        """Test route / trả về file dashboard.html."""
        rv = client.get('/')
        assert rv.status_code == 200
        # Kiểm tra response chứa nội dung HTML của dashboard
        html = rv.data.decode('utf-8')
        assert 'EWS Pro' in html
        assert 'loginScreen' in html

    def test_login_success(self, client):
        """Test /api/login với tài khoản hợp lệ."""
        rv = client.post('/api/login',
                        data=json.dumps({'username': 'admin', 'password': 'ews2024'}),
                        content_type='application/json')
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data['success'] is True
        assert data['role'] == 'Admin Hệ thống'

    def test_login_fail(self, client):
        """Test /api/login với mật khẩu sai → 401."""
        rv = client.post('/api/login',
                        data=json.dumps({'username': 'admin', 'password': 'wrongpass'}),
                        content_type='application/json')
        assert rv.status_code == 401
        data = json.loads(rv.data)
        assert data['success'] is False


# ============================================================
# TEST 6: XAI Explainable AI API
# ============================================================
class TestXAIExplain:
    """Test API giải thích XAI cho sinh viên."""

    @pytest.fixture
    def client(self):
        from api_server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_explain_invalid_mssv(self, client):
        """Test /api/explain/<mssv> với MSSV không tồn tại."""
        rv = client.get('/api/explain/000000000')
        # 404 (không tìm thấy SV) hoặc 500 (chưa kết nối DB)
        assert rv.status_code in [404, 500]

    def test_explain_returns_json(self, client):
        """Test /api/explain trả về JSON schema đúng (nếu có DB)."""
        rv = client.get('/api/explain/122000001')
        data = json.loads(rv.data)
        if rv.status_code == 200:
            assert 'mssv' in data
            assert 'top_factors' in data
            assert isinstance(data['top_factors'], list)
        else:
            # Chấp nhận lỗi nếu DB/Model chưa sẵn sàng
            assert 'error' in data


# ============================================================
# TEST 7: ETL Scheduler Configuration
# ============================================================
class TestScheduler:
    """Test cấu hình APScheduler ETL tự động."""

    def test_scheduler_imported(self):
        """Test APScheduler đã được import và khởi tạo."""
        from api_server import scheduler
        assert scheduler is not None
        assert scheduler.running is True

    def test_etl_job_registered(self):
        """Test job run_etl_job đã được đăng ký trong scheduler."""
        from api_server import scheduler
        jobs = scheduler.get_jobs()
        job_names = [j.name for j in jobs]
        assert 'run_etl_job' in job_names

    def test_run_etl_job_callable(self):
        """Test hàm run_etl_job có thể gọi được."""
        from api_server import run_etl_job
        assert callable(run_etl_job)
