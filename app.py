#!/usr/bin/env python3
"""
VE-System API Server v3
虛擾地球系統 API 伺服器
修正教育系統科目對應
"""

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

DB_DIR = os.environ.get('DATABASE_DIR', './data')

# ============ CORS ============
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def get_db(db_name):
    db_path = os.path.join(DB_DIR, f'{db_name}.db')
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# ============ 健康檢查 ============

@app.route('/')
def index():
    return jsonify({
        'name': 'VE-System API',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
@app.route('/health/live')
def health_live():
    return jsonify({'status': 'alive', 'timestamp': datetime.now().isoformat()})

@app.route('/health/ready')
def health_ready():
    dbs = ['meta', 've', 'trade', 'education', 'business', 'clarity', 'corpus', 'taoist', 'work']
    status = {}
    all_ok = True
    
    for db in dbs:
        db_path = os.path.join(DB_DIR, f'{db}.db')
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
                status[db] = 'ok'
            except Exception as e:
                status[db] = f'error: {e}'
                all_ok = False
        else:
            status[db] = 'not found'
            all_ok = False
    
    return jsonify({
        'status': 'ready' if all_ok else 'partial',
        'databases': status,
        'timestamp': datetime.now().isoformat()
    }), 200 if all_ok else 503

# ============ 系統狀態 ============

@app.route('/api/v1/status')
def system_status():
    dbs = ['meta', 've', 'trade', 'education', 'business', 'clarity', 'corpus', 'taoist', 'work']
    
    db_stats = {}
    total_tables = 0
    total_records = 0
    
    for db_name in dbs:
        conn = get_db(db_name)
        if conn:
            try:
                cur = conn.cursor()
                tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                
                records = 0
                for t in tables:
                    try:
                        records += cur.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
                    except:
                        pass
                
                db_stats[db_name] = {'tables': len(tables), 'records': records}
                total_tables += len(tables)
                total_records += records
                conn.close()
            except Exception as e:
                db_stats[db_name] = {'error': str(e)}
        else:
            db_stats[db_name] = {'status': 'not found'}
    
    return jsonify({
        'system': 'VE-System',
        'version': '1.0.0',
        'maturity': '90.7%',
        'databases': db_stats,
        'totals': {'databases': len(dbs), 'tables': total_tables, 'records': total_records},
        'timestamp': datetime.now().isoformat()
    })

# ============ 資料庫 API ============

@app.route('/api/v1/db/<db_name>/tables')
def list_tables(db_name):
    conn = get_db(db_name)
    if not conn:
        return jsonify({'error': f'Database {db_name} not found'}), 404
    
    try:
        cur = conn.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        conn.close()
        return jsonify({'database': db_name, 'tables': [t[0] for t in tables], 'count': len(tables)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/db/<db_name>/table/<table_name>')
def query_table(db_name, table_name):
    conn = get_db(db_name)
    if not conn:
        return jsonify({'error': f'Database {db_name} not found'}), 404
    
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info([{table_name}])")
        columns = [col[1] for col in cur.fetchall()]
        
        cur.execute(f"SELECT * FROM [{table_name}] LIMIT ? OFFSET ?", (limit, offset))
        rows = cur.fetchall()
        
        total = cur.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
        conn.close()
        
        return jsonify({
            'database': db_name,
            'table': table_name,
            'columns': columns,
            'data': [dict(row) for row in rows],
            'pagination': {'limit': limit, 'offset': offset, 'total': total}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 北斗七星 ============

@app.route('/api/v1/qixing')
def qixing_status():
    stars = [
        {'id': 1, 'name': '光蘊', 'role': '願景守護', 'status': 'active'},
        {'id': 2, 'name': '織明', 'role': '結構編織', 'status': 'active'},
        {'id': 3, 'name': '理樞', 'role': '邏輯核心', 'status': 'active'},
        {'id': 4, 'name': '澄書', 'role': '文檔沉澱', 'status': 'active'},
        {'id': 5, 'name': '流祇', 'role': '流程優化', 'status': 'active'},
        {'id': 6, 'name': '星殼', 'role': '界面呈現', 'status': 'active'},
        {'id': 7, 'name': '璃語', 'role': '溝通橋樑', 'status': 'active'},
    ]
    
    return jsonify({
        'system': '北斗七星協作體系',
        'stars': stars,
        'alignment': '99.7%',
        'timestamp': datetime.now().isoformat()
    })

# ============ 教育系統 API (修正版) ============

# 科目 ID 對應表
SUBJECT_MAP = {
    'all': None,
    '數學': ['SUBJ_MATH_A', 'SUBJ_MATH'],
    '國文': ['SUBJ_CHI_A', 'SUBJ_CHINESE'],
    '英文': ['SUBJ_ENG_A', 'SUBJ_ENGLISH'],
    '理化': ['SUBJ_SCI_A', 'SUBJ_PHYSICS', 'SUBJ_CHEMISTRY'],
    '社會': ['SUBJ_SOC_A', 'SUBJ_HISTORY', 'SUBJ_GEOGRAPHY'],
    '自然': ['SUBJ_SCI_A', 'SUBJ_BIO'],
    '科技': ['SUBJ_TECH_A'],
    '藝術': ['SUBJ_ART_A'],
    '體育': ['SUBJ_PE_A'],
    '生活': ['SUBJ_LIFE_A'],
}

SUBJECT_NAMES = {
    'SUBJ_MATH_A': '數學', 'SUBJ_MATH': '數學',
    'SUBJ_CHI_A': '國文', 'SUBJ_CHINESE': '國文',
    'SUBJ_ENG_A': '英文', 'SUBJ_ENGLISH': '英文',
    'SUBJ_SCI_A': '自然', 'SUBJ_PHYSICS': '物理', 'SUBJ_CHEMISTRY': '化學',
    'SUBJ_SOC_A': '社會', 'SUBJ_HISTORY': '歷史', 'SUBJ_GEOGRAPHY': '地理',
    'SUBJ_TECH_A': '科技', 'SUBJ_ART_A': '藝術', 
    'SUBJ_PE_A': '體育', 'SUBJ_LIFE_A': '生活',
}

@app.route('/api/v1/education/subjects')
def get_subjects():
    """取得可用科目列表"""
    conn = get_db('education')
    if not conn:
        return jsonify({'error': 'Education database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT subject_id, COUNT(*) as count FROM exam_questions GROUP BY subject_id")
        rows = cur.fetchall()
        conn.close()
        
        subjects = []
        for row in rows:
            sid = row['subject_id']
            subjects.append({
                'id': sid,
                'name': SUBJECT_NAMES.get(sid, sid),
                'count': row['count']
            })
        
        return jsonify({'subjects': subjects, 'count': len(subjects)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/education/questions')
def get_questions():
    """取得題庫（支援科目篩選）"""
    conn = get_db('education')
    if not conn:
        return jsonify({'error': 'Education database not found'}), 404
    
    subject = request.args.get('subject', 'all')
    limit = request.args.get('limit', 10, type=int)
    difficulty = request.args.get('difficulty', None, type=int)
    
    try:
        cur = conn.cursor()
        
        # 建立查詢
        query = "SELECT * FROM exam_questions WHERE 1=1"
        params = []
        
        # 科目篩選
        if subject != 'all' and subject in SUBJECT_MAP:
            subject_ids = SUBJECT_MAP[subject]
            if subject_ids:
                placeholders = ','.join(['?' for _ in subject_ids])
                query += f" AND subject_id IN ({placeholders})"
                params.extend(subject_ids)
        
        # 難度篩選
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)
        
        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        
        questions = []
        for row in rows:
            q = dict(row)
            # 轉換科目 ID 為中文名稱
            q['subject'] = SUBJECT_NAMES.get(q.get('subject_id', ''), q.get('subject_id', '未分類'))
            # 解析 options
            if q.get('options'):
                try:
                    q['options'] = json.loads(q['options'])
                except:
                    pass
            questions.append(q)
        
        return jsonify({'questions': questions, 'count': len(questions)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/education/check', methods=['POST', 'OPTIONS'])
def check_answer():
    """檢查答案"""
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    conn = get_db('education')
    if not conn:
        return jsonify({'error': 'Education database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT answer, explanation FROM exam_questions WHERE question_id = ?", (question_id,))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Question not found'}), 404
        
        correct_answer = row['answer']
        explanation = row['explanation']
        is_correct = (answer == correct_answer)
        
        return jsonify({
            'correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': explanation,
            'your_answer': answer
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 交易系統 ============

@app.route('/api/v1/trade/strategies')
def get_strategies():
    conn = get_db('trade')
    if not conn:
        return jsonify({'error': 'Trade database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM trading_strategies LIMIT 20")
        rows = cur.fetchall()
        conn.close()
        return jsonify({'strategies': [dict(row) for row in rows], 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/trade/indicators')
def get_indicators():
    conn = get_db('trade')
    if not conn:
        return jsonify({'error': 'Trade database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM technical_indicators")
        rows = cur.fetchall()
        conn.close()
        return jsonify({'indicators': [dict(row) for row in rows], 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 虛擬地球 ============

@app.route('/api/v1/ve/quests')
def get_quests():
    conn = get_db('ve')
    if not conn:
        return jsonify({'error': 'VE database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM quest_rewards ORDER BY quest_id")
        rows = cur.fetchall()
        conn.close()
        return jsonify({'quests': [dict(row) for row in rows], 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/ve/npcs')
def get_npcs():
    conn = get_db('ve')
    if not conn:
        return jsonify({'error': 'VE database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM npc_dialogues")
        rows = cur.fetchall()
        conn.close()
        return jsonify({'npcs': [dict(row) for row in rows], 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/ve/shop')
def get_shop():
    conn = get_db('ve')
    if not conn:
        return jsonify({'error': 'VE database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM shop_items")
        rows = cur.fetchall()
        conn.close()
        return jsonify({'items': [dict(row) for row in rows], 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/ve/regions')
def get_regions():
    """取得區域列表"""
    conn = get_db('ve')
    if not conn:
        return jsonify({'error': 'VE database not found'}), 404
    
    try:
        cur = conn.cursor()
        # 嘗試多個可能的表名
        for table in ['regions', 'game_regions', 'e18k_regions']:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                if rows:
                    conn.close()
                    return jsonify({'regions': [dict(row) for row in rows], 'count': len(rows)})
            except:
                pass
        
        # 如果沒有找到，返回預設區域
        conn.close()
        default_regions = [
            {'region_id': 'R001', 'name': '新手村', 'description': '所有冒險者的起點', 'level_required': 1},
            {'region_id': 'R002', 'name': '詐騙森林', 'description': '充滿投資陷阱的危險區域', 'level_required': 3},
            {'region_id': 'R003', 'name': '釣魚海灘', 'description': '網路釣魚盛行的沿海地帶', 'level_required': 5},
            {'region_id': 'R004', 'name': '假客服山谷', 'description': '假冒客服橫行的山區', 'level_required': 7},
            {'region_id': 'R005', 'name': '愛情詐騙城', 'description': '感情騙子的大本營', 'level_required': 10},
        ]
        return jsonify({'regions': default_regions, 'count': len(default_regions)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/ve/scenarios')
def get_scenarios():
    """取得防詐情境題"""
    conn = get_db('ve')
    if not conn:
        # 返回預設情境
        default_scenarios = [
            {
                'id': 'S001',
                'title': '神秘的投資機會',
                'description': '你收到一則訊息：「獨家內線！保證報酬率50%！只限今天！」',
                'options': [
                    {'id': 'A', 'text': '立即投資，把握機會', 'correct': False, 'feedback': '這是典型的投資詐騙手法！保證高報酬都是騙局。'},
                    {'id': 'B', 'text': '先查證對方身份和公司背景', 'correct': True, 'feedback': '正確！投資前務必查證，合法投資不會保證報酬。'},
                    {'id': 'C', 'text': '詢問朋友意見', 'correct': False, 'feedback': '朋友可能也被騙，應該向專業機構查證。'},
                    {'id': 'D', 'text': '小額投資試試看', 'correct': False, 'feedback': '詐騙集團會讓你先嚐甜頭，之後騙更多！'}
                ],
                'exp_reward': 50,
                'gold_reward': 30
            },
            {
                'id': 'S002',
                'title': '假冒銀行來電',
                'description': '自稱銀行人員來電說你的帳戶有異常，要求提供密碼進行「安全驗證」。',
                'options': [
                    {'id': 'A', 'text': '配合提供密碼，保護帳戶安全', 'correct': False, 'feedback': '銀行絕不會要求密碼！這是詐騙！'},
                    {'id': 'B', 'text': '掛斷電話，自行撥打銀行客服確認', 'correct': True, 'feedback': '正確！永遠自己撥打官方電話確認，不要回撥來電號碼。'},
                    {'id': 'C', 'text': '請對方證明身份', 'correct': False, 'feedback': '詐騙集團可以偽造任何證明，這樣做沒有用。'},
                    {'id': 'D', 'text': '提供一半密碼試探', 'correct': False, 'feedback': '任何密碼資訊都不能提供！'}
                ],
                'exp_reward': 60,
                'gold_reward': 40
            },
            {
                'id': 'S003',
                'title': '中獎通知',
                'description': '你收到簡訊說抽中了iPhone 15，只要付500元運費就能領取。',
                'options': [
                    {'id': 'A', 'text': '付款領獎，500元換iPhone超划算', 'correct': False, 'feedback': '這是「預付費詐騙」！真正的抽獎不會要你先付錢。'},
                    {'id': 'B', 'text': '確認是否真的有參加過這個抽獎', 'correct': True, 'feedback': '正確！沒參加過的抽獎不可能中獎，這是詐騙。'},
                    {'id': 'C', 'text': '請朋友幫忙付款', 'correct': False, 'feedback': '這樣會害朋友一起被騙！'},
                    {'id': 'D', 'text': '回覆詢問更多細節', 'correct': False, 'feedback': '回覆會讓對方知道這是有效號碼，可能收到更多詐騙訊息。'}
                ],
                'exp_reward': 55,
                'gold_reward': 35
            },
            {
                'id': 'S004',
                'title': '網路購物陷阱',
                'description': '你在社群網站看到名牌包只要原價的1/10，賣家說是「員工內購價」。',
                'options': [
                    {'id': 'A', 'text': '立即下單，這麼便宜不買可惜', 'correct': False, 'feedback': '價格過低通常是詐騙或仿冒品！'},
                    {'id': 'B', 'text': '要求使用第三方支付平台交易', 'correct': True, 'feedback': '正確！使用有保障的支付方式，不要私下轉帳。'},
                    {'id': 'C', 'text': '先付一半訂金', 'correct': False, 'feedback': '付了訂金就拿不回來了！'},
                    {'id': 'D', 'text': '請賣家提供更多照片', 'correct': False, 'feedback': '照片可以從網路上偷來的，不能證明什麼。'}
                ],
                'exp_reward': 50,
                'gold_reward': 30
            },
            {
                'id': 'S005',
                'title': '交友軟體的曖昧對象',
                'description': '交友軟體上認識一個月的對象突然說家人生病需要借錢。',
                'options': [
                    {'id': 'A', 'text': '立即借錢，畢竟是關心的人', 'correct': False, 'feedback': '這是「殺豬盤」愛情詐騙的典型手法！'},
                    {'id': 'B', 'text': '要求視訊通話確認真實身份', 'correct': True, 'feedback': '正確！愛情詐騙者通常會拒絕視訊。還要注意可能是AI換臉。'},
                    {'id': 'C', 'text': '借一小筆金額表示心意', 'correct': False, 'feedback': '一旦借了就會有第二次、第三次...'},
                    {'id': 'D', 'text': '請對方提供醫療證明', 'correct': False, 'feedback': '詐騙集團可以偽造任何文件。'}
                ],
                'exp_reward': 70,
                'gold_reward': 50
            }
        ]
        return jsonify({'scenarios': default_scenarios, 'count': len(default_scenarios)})
    
    try:
        cur = conn.cursor()
        # 嘗試查詢情境表
        for table in ['scenarios', 'fraud_scenarios', 'e18k_scenarios', 'game_scenarios']:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                if rows:
                    conn.close()
                    return jsonify({'scenarios': [dict(row) for row in rows], 'count': len(rows)})
            except:
                pass
        conn.close()
        
        # 返回預設情境
        return jsonify({'scenarios': default_scenarios, 'count': len(default_scenarios)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 啟動 ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('APP_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
