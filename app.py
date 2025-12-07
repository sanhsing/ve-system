#!/usr/bin/env python3
"""
VE-System API Server
虛擾地球系統 API 伺服器
"""

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# 資料庫目錄
DB_DIR = os.environ.get('DATABASE_DIR', './data')

# ============ CORS 設定 ============
@app.after_request
def after_request(response):
    """允許跨域請求"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def get_db(db_name):
    """取得資料庫連線"""
    db_path = os.path.join(DB_DIR, f'{db_name}.db')
    if not os.path.exists(db_path):
        return None
    return sqlite3.connect(db_path)

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
    """檢查資料庫是否就緒"""
    dbs = ['meta', 've', 'trade', 'education', 'business', 
           'clarity', 'corpus', 'taoist', 'work']
    
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
    """系統狀態總覽"""
    dbs = ['meta', 've', 'trade', 'education', 'business', 
           'clarity', 'corpus', 'taoist', 'work']
    
    db_stats = {}
    total_tables = 0
    total_records = 0
    
    for db_name in dbs:
        conn = get_db(db_name)
        if conn:
            try:
                cur = conn.cursor()
                tables = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                
                records = 0
                for t in tables:
                    try:
                        records += cur.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
                    except:
                        pass
                
                db_stats[db_name] = {
                    'tables': len(tables),
                    'records': records
                }
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
        'totals': {
            'databases': len(dbs),
            'tables': total_tables,
            'records': total_records
        },
        'timestamp': datetime.now().isoformat()
    })

# ============ 資料庫 API ============

@app.route('/api/v1/db/<db_name>/tables')
def list_tables(db_name):
    """列出資料庫的所有表"""
    conn = get_db(db_name)
    if not conn:
        return jsonify({'error': f'Database {db_name} not found'}), 404
    
    try:
        cur = conn.cursor()
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        
        return jsonify({
            'database': db_name,
            'tables': [t[0] for t in tables],
            'count': len(tables)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/db/<db_name>/table/<table_name>')
def query_table(db_name, table_name):
    """查詢表資料"""
    conn = get_db(db_name)
    if not conn:
        return jsonify({'error': f'Database {db_name} not found'}), 404
    
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    try:
        cur = conn.cursor()
        
        # 取得欄位
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cur.fetchall()]
        
        # 取得資料
        cur.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
        rows = cur.fetchall()
        
        # 取得總數
        total = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'database': db_name,
            'table': table_name,
            'columns': columns,
            'data': [dict(zip(columns, row)) for row in rows],
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 北斗七星 API ============

@app.route('/api/v1/qixing')
def qixing_status():
    """北斗七星協作體系狀態"""
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

# ============ 教育系統 API ============

@app.route('/api/v1/education/questions')
def get_questions():
    """取得題庫"""
    conn = get_db('education')
    if not conn:
        return jsonify({'error': 'Education database not found'}), 404
    
    subject = request.args.get('subject', None)
    limit = request.args.get('limit', 10, type=int)
    
    try:
        cur = conn.cursor()
        
        if subject:
            cur.execute(
                "SELECT * FROM exam_questions WHERE subject = ? ORDER BY RANDOM() LIMIT ?",
                (subject, limit)
            )
        else:
            cur.execute(
                "SELECT * FROM exam_questions ORDER BY RANDOM() LIMIT ?",
                (limit,)
            )
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        conn.close()
        
        questions = []
        for row in rows:
            q = dict(zip(columns, row))
            # 解析 options JSON
            if 'options' in q and q['options']:
                try:
                    q['options'] = json.loads(q['options'])
                except:
                    pass
            questions.append(q)
        
        return jsonify({
            'questions': questions,
            'count': len(questions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/education/check', methods=['POST'])
def check_answer():
    """檢查答案"""
    data = request.get_json()
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    conn = get_db('education')
    if not conn:
        return jsonify({'error': 'Education database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT answer, explanation FROM exam_questions WHERE question_id = ?",
            (question_id,)
        )
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Question not found'}), 404
        
        correct_answer, explanation = row
        is_correct = (answer == correct_answer)
        
        return jsonify({
            'correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': explanation,
            'your_answer': answer
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 交易系統 API ============

@app.route('/api/v1/trade/strategies')
def get_strategies():
    """取得策略列表"""
    conn = get_db('trade')
    if not conn:
        return jsonify({'error': 'Trade database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM trading_strategies LIMIT 20")
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        conn.close()
        
        return jsonify({
            'strategies': [dict(zip(columns, row)) for row in rows],
            'count': len(rows)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/trade/indicators')
def get_indicators():
    """取得技術指標"""
    conn = get_db('trade')
    if not conn:
        return jsonify({'error': 'Trade database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM technical_indicators")
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        conn.close()
        
        return jsonify({
            'indicators': [dict(zip(columns, row)) for row in rows],
            'count': len(rows)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 虛擬地球 API ============

@app.route('/api/v1/ve/quests')
def get_quests():
    """取得任務列表"""
    conn = get_db('ve')
    if not conn:
        return jsonify({'error': 'VE database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM quest_rewards ORDER BY quest_id")
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        conn.close()
        
        return jsonify({
            'quests': [dict(zip(columns, row)) for row in rows],
            'count': len(rows)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/ve/npcs')
def get_npcs():
    """取得 NPC 列表"""
    conn = get_db('ve')
    if not conn:
        return jsonify({'error': 'VE database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM npc_dialogues")
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        conn.close()
        
        return jsonify({
            'npcs': [dict(zip(columns, row)) for row in rows],
            'count': len(rows)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/ve/shop')
def get_shop():
    """取得商店物品"""
    conn = get_db('ve')
    if not conn:
        return jsonify({'error': 'VE database not found'}), 404
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM shop_items")
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        conn.close()
        
        return jsonify({
            'items': [dict(zip(columns, row)) for row in rows],
            'count': len(rows)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ 啟動 ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('APP_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
