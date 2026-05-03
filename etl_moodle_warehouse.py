import mysql.connector
import sqlite3
import pandas as pd
import time

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'moodle'
}

# Bảng Delta (Dữ liệu log tăng dần mỗi ngày, chỉ hút log mới)
DELTA_TABLES = {
    'mdl_logstore_standard_log': 'timecreated',
    'mdl_quiz_attempts': 'timestart',
    'mdl_assign_submission': 'timecreated',
    'mdl_assign_grades': 'timemodified',
    'mdl_quiz_grades': 'timemodified'
}

# Bảng Dimension (Bảng thông tin danh mục dung lượng nhỏ, đồng bộ toàn bộ mỗi ngày)
DIM_TABLES = [
    'mdl_user',
    'mdl_course',
    'mdl_enrol',
    'mdl_user_enrolments',
    'mdl_assign'
]

def run_etl():
    print("🚀 KHỞI ĐỘNG HỆ THỐNG MOODLE ETL PIPELINE...")
    print("=" * 50)
    
    # Kết nối Source (Moodle MySQL Prod DB)
    try:
        source_conn = mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Lỗi kết nối Moodle DB: {e}")
        return

    # Kết nối Target (Data Warehouse lưu vĩnh viễn - Local SQLite)
    target_conn = sqlite3.connect("moodle_warehouse.db")
    
    # -------------------------------------------------------------
    # 1. TRÍCH XUẤT (EXTRACT) & TẢI (LOAD) BẢNG DELTA
    # Hút log nối đuôi, không lấy trùng, giữ lại lịch sử rác bị Moodle dọn
    # -------------------------------------------------------------
    for table, time_col in DELTA_TABLES.items():
        print(f"\n🔄 [DELTA LOAD] Đang quét bảng log: {table}...")
        
        # Lấy mốc thời gian lớn nhất (Mới nhất) đã lưu trong Warehouse
        try:
            max_val_df = pd.read_sql(f"SELECT MAX({time_col}) as max_time FROM {table}", target_conn)
            max_time = max_val_df['max_time'].iloc[0]
            if pd.isna(max_time):
                max_time = 0
        except:
            max_time = 0 # Bảng chưa tồn tại lần chạy đầu
            
        print(f"   => Mốc sự kiện cuối lưu trữ: {max_time}")
        
        # Hút dữ liệu từ MySQL MỚI HƠN mốc này
        query = f"SELECT * FROM {table} WHERE {time_col} > {max_time}"
        new_data = pd.read_sql(query, source_conn)
        
        if len(new_data) > 0:
            # Lưu vĩnh viễn vào SQLite bằng cách dán thêm (append)
            # Ngay cả khi MySQL Prod DB bị dọn dẹp (truncate), SQLite vẫn còn dữ liệu cũ.
            new_data.to_sql(table, target_conn, if_exists='append', index=False)
            print(f"   ✅ Đã hút thành công {len(new_data)} dòng log mới vào Warehouse.")
        else:
            print(f"   ⚡ Không có tương tác mới nào phát sinh.")

    # -------------------------------------------------------------
    # 2. TRÍCH XUẤT (EXTRACT) & TẢI (LOAD) BẢNG DIMENSION
    # -------------------------------------------------------------
    for table in DIM_TABLES:
        print(f"\n🔄 [FULL LOAD] Đang đồng bộ danh mục: {table}...")
        query = f"SELECT * FROM {table}"
        dim_data = pd.read_sql(query, source_conn)
        
        # Ghi đè cấu trúc cũ bằng cấu trúc mới
        dim_data.to_sql(table, target_conn, if_exists='replace', index=False)
        print(f"   ✅ Đã đồng bộ {len(dim_data)} records.")

    source_conn.close()
    target_conn.close()
    print("\n" + "=" * 50)
    print("🎉 HOÀN TẤT MOODLE DAILY ETL! Log đã đóng băng vĩnh viễn ở máy chủ của bạn.")

if __name__ == "__main__":
    run_etl()
