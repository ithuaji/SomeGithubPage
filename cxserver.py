from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import csv
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, supports_credentials=False) # 确保允许跨域请求

# --- 数据库配置 ---
DB_HOST = 'localhost'  # MySQL 服务运行在本机
DB_USER = 'root'       # MySQL 用户名
DB_PASSWORD = 'Your_new_password47'  # 您刚刚设置的密码
DB_NAME = 'device_management_db'     # 您创建的数据库名
DB_PORT = 3306         # MySQL 默认端口

# --- 工具函数 ---
def get_db_connection():
    """获取数据库连接"""
    print(f"🔧 正在连接数据库: {DB_HOST}:{DB_PORT}, database: {DB_NAME}, user: {DB_USER}")
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ 数据库连接成功")
        return connection
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        raise e

def get_status_color(status):
    """根据状态返回颜色类，用于前端显示"""
    print(f"🎨 获取状态颜色: status={status}")
    color_map = {
        "今日已经完成": "status-completed",
        "密码错误": "status-error",
        "账号不存在": "status-error",
        "网络异常": "status-error",
        "设备故障": "status-error",
        "手机没电": "status-warning",
        "部署异常": "status-warning",
        "NPS联结异常": "status-warning",
        "账号被其他人登录": "status-warning",
        "时间不够": "status-warning",
        None: "status-uncompleted",
        "": "status-uncompleted"
    }
    color = color_map.get(status, "status-other") # 默认颜色
    print(f"🎨 状态 '{status}' 对应颜色类: {color}")
    return color

# --- API路由 ---

@app.route('/api/device', methods=['POST', 'OPTIONS'])
def get_device_info():
    """客户端查询设备信息的API"""
    print(f"🔍 收到设备查询请求: method={request.method}")
    if request.method == 'OPTIONS':
        print("🔄 处理预检请求 (OPTIONS)")
        return '', 200

    data = request.get_json(silent=True)
    print(f"📥 接收到的JSON数据: {data}")
    device_id = data.get('model_id') if data else None
    print(f"🆔 设备编号: {device_id}")
    if not device_id:
        print("❌ 错误: 缺少设备编号")
        return jsonify({"error": "缺少设备编号"}), 400

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            print(f"🔍 执行SQL查询: SELECT * FROM device_records WHERE 设备编号 = '{device_id}'")
            # 查询指定设备编号的所有记录
            sql = "SELECT * FROM device_records WHERE 设备编号 = %s ORDER BY id ASC"
            cursor.execute(sql, (str(device_id),))
            records = cursor.fetchall()
            print(f"📊 查询到 {len(records)} 条记录")
    except Exception as e:
        print(f"❌ 查询数据库出错: {e}")
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        connection.close()
        print("🔒 数据库连接已关闭")

    if records:
        # 为每条记录添加颜色类
        print("🎨 为查询结果添加颜色类")
        for record in records:
            record['status_color'] = get_status_color(record['status'])
        print(f"✅ 返回 {len(records)} 条记录给客户端")
        return jsonify(records)
    else:
        print(f"❌ 未找到设备编号为 '{device_id}' 的记录")
        return jsonify({"error": f"未找到设备编号为 '{device_id}' 的记录"}), 404


@app.route('/api/mark_completed', methods=['POST', 'OPTIONS'])
def mark_completed():
    """客户端标记账号密码已复制，状态为'今日已经完成'的API"""
    print(f"📝 收到标记完成请求: method={request.method}")
    if request.method == 'OPTIONS':
        print("🔄 处理预检请求 (OPTIONS)")
        return '', 200

    data = request.get_json(silent=True)
    print(f"📥 接收到的JSON数据: {data}")
    record_id = data.get('record_id')
    print(f"🆔 记录ID: {record_id}")
    if not record_id:
        print("❌ 错误: 缺少记录ID")
        return jsonify({"error": "缺少记录ID"}), 400

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            print(f"🔍 检查记录 {record_id} 是否已有状态")
            # 检查该记录是否已经有状态，防止重复标记
            sql_check = "SELECT status FROM device_records WHERE id = %s"
            cursor.execute(sql_check, (record_id,))
            result = cursor.fetchone()
            print(f"🔍 检查结果: {result}")
            if result and result['status']:
                 # 如果已有状态，可以选择返回错误或更新状态
                 # 这里我们选择更新状态为完成
                 print(f"⚠️ 记录 {record_id} 已有状态 '{result['status']}', 将更新为'今日已经完成'")
                 pass # 继续执行更新

            print(f"🔄 更新记录 {record_id} 的状态为 '今日已经完成'")
            # 更新记录状态为'今日已经完成'
            sql_update = "UPDATE device_records SET status = %s WHERE id = %s"
            cursor.execute(sql_update, ("今日已经完成", record_id))
            connection.commit()
            print(f"✅ 记录 {record_id} 状态更新成功")
    except Exception as e:
        print(f"❌ 更新数据库状态出错: {e}")
        connection.rollback()
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        connection.close()
        print("🔒 数据库连接已关闭")

    return jsonify({"message": "状态更新成功"})


@app.route('/api/mark_status', methods=['POST', 'OPTIONS'])
def mark_status():
    """客户端标记异常状态的API"""
    print(f"⚠️ 收到标记异常状态请求: method={request.method}")
    if request.method == 'OPTIONS':
        print("🔄 处理预检请求 (OPTIONS)")
        return '', 200

    data = request.get_json(silent=True)
    print(f"📥 接收到的JSON数据: {data}")
    record_id = data.get('record_id')
    status = data.get('status')
    valid_statuses = ["密码错误", "账号不存在", "网络异常", "设备故障", "手机没电", "部署异常", "NPS联结异常", "账号被其他人登录", "时间不够"]
    print(f"🆔 记录ID: {record_id}, 状态: {status}")

    if not record_id or not status or status not in valid_statuses:
        print(f"❌ 错误: 缺少记录ID或无效状态 (record_id={record_id}, status={status}, valid_statuses={valid_statuses})")
        return jsonify({"error": "缺少记录ID或无效状态"}), 400

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            print(f"🔄 更新记录 {record_id} 的状态为 '{status}'")
            sql_update = "UPDATE device_records SET status = %s WHERE id = %s"
            cursor.execute(sql_update, (status, record_id))
            connection.commit()
            print(f"✅ 记录 {record_id} 状态更新为 '{status}' 成功")
    except Exception as e:
        print(f"❌ 更新数据库状态出错: {e}")
        connection.rollback()
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        connection.close()
        print("🔒 数据库连接已关闭")

    return jsonify({"message": "状态更新成功"})


@app.route('/api/clear_status', methods=['POST', 'OPTIONS'])
def clear_status():
    """管理端清除所有状态的API (需要二次确认)"""
    print(f"🧹 收到清除状态请求: method={request.method}")
    if request.method == 'OPTIONS':
        print("🔄 处理预检请求 (OPTIONS)")
        return '', 200

    data = request.get_json(silent=True)
    print(f"📥 接收到的JSON数据: {data}")
    confirmation = data.get('confirmation')
    print(f"📝 二次确认信息: {confirmation}")

    if confirmation != "确认清除":
         print(f"❌ 错误: 清除操作需要输入 '确认清除' 进行二次确认, 实际输入: '{confirmation}'")
         return jsonify({"error": "清除操作需要输入 '确认清除' 进行二次确认"}), 400

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            print("🔄 执行清除所有状态的SQL")
            # 将所有记录的status字段设为NULL
            sql_update = "UPDATE device_records SET status = NULL"
            cursor.execute(sql_update)
            rows_affected = cursor.rowcount
            connection.commit()
            print(f"✅ 成功清除 {rows_affected} 条记录的状态")
    except Exception as e:
        print(f"❌ 清除数据库状态出错: {e}")
        connection.rollback()
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        connection.close()
        print("🔒 数据库连接已关闭")

    return jsonify({"message": f"成功清除 {rows_affected} 条记录的状态"})


@app.route('/api/import_csv', methods=['POST', 'OPTIONS'])
def import_csv():
    """管理端通过CSV文件导入数据的API"""
    print(f"📁 收到CSV导入请求: method={request.method}")
    if request.method == 'OPTIONS':
        print("🔄 处理预检请求 (OPTIONS)")
        return '', 200

    print(f"📥 检查上传的文件...")
    if 'file' not in request.files:
        print("❌ 错误: 没有文件")
        return jsonify({"error": "没有文件"}), 400

    file = request.files['file']
    print(f"📄 上传的文件名: {file.filename}")
    if file.filename == '':
        print("❌ 错误: 没有选择文件")
        return jsonify({"error": "没有选择文件"}), 400

    if not file.filename.lower().endswith('.csv'):
        print("❌ 错误: 文件类型错误，请上传CSV文件")
        return jsonify({"error": "文件类型错误，请上传CSV文件"}), 400

    try:
        print("📄 正在读取CSV内容...")
        # 读取CSV内容
        content = file.stream.read().decode("utf-8-sig") # .decode("utf-8-sig") 去除BOM
        lines = content.splitlines()
        reader = csv.reader(lines)
        print(f"📄 CSV内容行数: {len(lines)}")

        # 获取列名 (第一行)
        header = next(reader, None)
        print(f"📋 CSV列头: {header}")
        if not header:
            print("❌ 错误: CSV文件为空")
            return jsonify({"error": "CSV文件为空"}), 400

        expected_header = ["录入编号", "设备编号", "账号", "密码", "学校", "备注", "每次", "总", "day", "时段", "起始", "结束", "status"]
        if header != expected_header:
            print(f"⚠️ CSV列头不匹配。期望: {expected_header}, 实际: {header}")
            # 可以选择严格匹配或尝试按顺序处理，这里按顺序处理前13列
            # 但为了健壮性，最好要求格式一致
            # 此处简化处理，假设顺序一致
            print("⚠️ 继续处理，按顺序匹配列...")
            pass # 继续处理


        connection = get_db_connection()
        with connection.cursor() as cursor:
            inserted_count = 0
            print("🔄 开始逐行处理CSV数据...")
            for i, row in enumerate(reader, start=2):  # 从第2行开始计数
                print(f"🔄 处理第 {i} 行数据: {row}")
                if len(row) < 13: # 至少需要13列
                    print(f"⚠️ 跳过格式不正确的行 {i}: {row} (列数: {len(row)})")
                    continue

                # 按顺序提取字段
                录入编号, 设备编号, 账号, 密码, 学校, 备注, 每次, 总, day, 时段, 起始, 结束, status = row[:13]
                print(f"🔍 提取字段 - 录入编号: {录入编号}, 设备编号: {设备编号}, 账号: {账号}, 密码: {密码}")

                # 处理可能的空字符串，将其设为NULL
                录入编号 = 录入编号 if 录入编号.strip() else None
                设备编号 = 设备编号 if 设备编号.strip() else None
                账号 = 账号 if 账号.strip() else None
                密码 = 密码 if 密码.strip() else None
                学校 = 学校 if 学校.strip() else None
                备注 = 备注 if 备注.strip() else None
                每次 = 每次 if 每次.strip() else None
                总 = 总 if 总.strip() else None
                day = day if day.strip() else None
                时段 = 时段 if 时段.strip() else None
                起始 = 起始 if 起始.strip() else None
                结束 = 结束 if 结束.strip() else None
                status = status if status.strip() else None # 状态可以为空，代表未完成

                print(f"🔄 插入数据库 - 录入编号: {录入编号}, 设备编号: {设备编号}, 账号: {账号}, 状态: {status}")

                # 插入数据库
                sql_insert = """
                INSERT INTO device_records (录入编号, 设备编号, 账号, 密码, 学校, 备注, 每次, 总, day, 时段, 起始, 结束, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert, (录入编号, 设备编号, 账号, 密码, 学校, 备注, 每次, 总, day, 时段, 起始, 结束, status))
                inserted_count += 1
                print(f"✅ 第 {i} 行数据插入成功, 当前已插入: {inserted_count}")

            connection.commit()
            print(f"💾 所有数据提交到数据库，共插入 {inserted_count} 条记录")
    except Exception as e:
        print(f"❌ 导入CSV出错: {e}")
        connection.rollback()
        return jsonify({"error": f"导入失败: {str(e)}"}), 500
    finally:
        connection.close()
        print("🔒 数据库连接已关闭")

    return jsonify({"message": f"成功导入 {inserted_count} 条记录"})

# ... (之前的代码) ...
# ... (保留您现有的所有代码，包括 get_stats 函数)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """管理端获取统计信息的API"""
    print("📊 收到统计信息请求")
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            print("🔍 统计今日异常数量")
            # 统计今日异常 (status不为NULL且不为'今日已经完成')
            sql_error = """
            SELECT COUNT(*) as count FROM device_records
            WHERE status IS NOT NULL AND status != '今日已经完成'
            """
            cursor.execute(sql_error)
            error_count = cursor.fetchone()['count']
            print(f"📊 今日异常数量: {error_count}")

            print("🔍 统计今日未完成数量")
            # 统计今日未完成 (status为NULL)
            sql_uncompleted = """
            SELECT COUNT(*) as count FROM device_records
            WHERE status IS NULL
            """
            cursor.execute(sql_uncompleted)
            uncompleted_count = cursor.fetchone()['count']
            print(f"📊 今日未完成数量: {uncompleted_count}")

    except Exception as e:
        print(f"❌ 获取统计信息出错: {e}")
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        connection.close()
        print("🔒 数据库连接已关闭")

    print(f"✅ 返回统计信息: 异常={error_count}, 未完成={uncompleted_count}")
    return jsonify({
        "today_error_count": error_count,
        "today_uncompleted_count": uncompleted_count
    })

# --- 新增API：获取详细异常统计 ---
@app.route('/api/detailed_stats', methods=['GET'])
def get_detailed_stats():
    """管理端获取详细异常统计信息的API"""
    print("📊 收到详细统计信息请求")
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 查询所有非完成状态的记录
            print("🔍 查询所有非完成状态的记录")
            sql_detailed = """
            SELECT 账号, status FROM device_records
            WHERE status IS NOT NULL AND status != '今日已经完成'
            """
            cursor.execute(sql_detailed)
            error_records = cursor.fetchall()
            print(f"📊 查询到 {len(error_records)} 条异常记录")

            # 查询所有未完成的记录
            print("🔍 查询所有未完成的记录")
            sql_uncompleted_detailed = """
            SELECT 账号 FROM device_records
            WHERE status IS NULL
            """
            cursor.execute(sql_uncompleted_detailed)
            uncompleted_records = cursor.fetchall()
            print(f"📊 查询到 {len(uncompleted_records)} 条未完成记录")

    except Exception as e:
        print(f"❌ 获取详细统计信息出错: {e}")
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        connection.close()
        print("🔒 数据库连接已关闭")

    # 统计异常类型
    status_counts = {}
    status_details = {}
    for record in error_records:
        status = record['status']
        account = record['账号']
        if status not in status_counts:
            status_counts[status] = 0
            status_details[status] = []
        status_counts[status] += 1
        status_details[status].append(account)

    # 统计未完成
    uncompleted_count = len(uncompleted_records)
    uncompleted_accounts = [record['账号'] for record in uncompleted_records]

    # 构造返回数据
    detailed_stats = {
        "total_error_count": len(error_records),
        "error_types": status_counts,
        "error_details": status_details,
        "uncompleted_count": uncompleted_count,
        "uncompleted_details": uncompleted_accounts
    }

    print(f"✅ 返回详细统计信息: {detailed_stats}")
    return jsonify(detailed_stats)

# ... (保留 __main__ 部分)
# ... (app.run 之前的代码) ...
if __name__ == '__main__':
    print("🚀 启动服务器: http://127.0.0.1:5233")
    app.run(host='0.0.0.0', port=5233, debug=True)
