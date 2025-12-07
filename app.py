#!/usr/bin/env python3
"""
VE-System API Server v4
虛擾地球系統 API 伺服器
新增：用戶系統、進度追蹤、學習分析
"""

import os
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, g

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# 資料庫目錄
DB_DIR = os.environ.get('DATABASE_DIR', './data')
USER_DB = os.path.join(DB_DIR, 'users.db')

# ============ CORS 設定 ============
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Token')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ============ 資料庫工具 ============
def get_db(db_name):
    db_path = os.path.join(DB_DIR, f'{db_name}.db')
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_db():
    conn = sqlite3.connect(USER_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_user_db():
    """初始化用戶資料庫"""
    conn = get_user_db()
    cur = conn.cursor()
    
    # 用戶表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            avatar TEXT DEFAULT '🧙',
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 500,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            settings TEXT DEFAULT '{}'
        )
    ''')
    
    # 令牌表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 答題記錄
    cur.execute('''
        CREATE TABLE IF NOT EXISTS answer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            subject TEXT,
            is_correct INTEGER NOT NULL,
            answer_given TEXT,
            correct_answer TEXT,
            time_spent INTEGER,
            answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 學習進度
    cur.execute('''
        CREATE TABLE IF NOT EXISTS learning_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            concept_id INTEGER,
            mastery_level REAL DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            last_studied TEXT,
            next_review TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, subject, concept_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 遊戲進度
    cur.execute('''
        CREATE TABLE IF NOT EXISTS game_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            scenario_id TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            completed_at TEXT,
            UNIQUE(user_id, scenario_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 成就解鎖
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            achievement_id TEXT NOT NULL,
            unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, achievement_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 徽章收集
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_id TEXT NOT NULL,
            earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, badge_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 每日統計
    cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            questions_answered INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            exp_gained INTEGER DEFAULT 0,
            gold_gained INTEGER DEFAULT 0,
            time_spent INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# 初始化
init_user_db()

# ============ 密碼工具 ============
def hash_password(password):
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"

def verify_password(password, password_hash):
    try:
        salt, hash_value = password_hash.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == hash_value
    except:
        return False

def generate_token():
    return secrets.token_urlsafe(32)

# ============ 認證裝飾器 ============
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': '需要登入', 'code': 'AUTH_REQUIRED'}), 401
        
        conn = get_user_db()
        cur = conn.cursor()
        cur.execute('''
            SELECT t.user_id, u.* FROM tokens t
            JOIN users u ON t.user_id = u.id
            WHERE t.token = ? AND t.expires_at > ?
        ''', (token, datetime.now().isoformat()))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': '令牌無效或已過期', 'code': 'INVALID_TOKEN'}), 401
        
        g.user = dict(row)
        g.user_id = row['id']
        return f(*args, **kwargs)
    return decorated

def optional_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        g.user = None
        g.user_id = None
        
        if token:
            conn = get_user_db()
            cur = conn.cursor()
            cur.execute('''
                SELECT t.user_id, u.* FROM tokens t
                JOIN users u ON t.user_id = u.id
                WHERE t.token = ? AND t.expires_at > ?
            ''', (token, datetime.now().isoformat()))
            row = cur.fetchone()
            conn.close()
            if row:
                g.user = dict(row)
                g.user_id = row['id']
        
        return f(*args, **kwargs)
    return decorated

# ============ 健康檢查 ============
@app.route('/')
def index():
    return jsonify({
        'name': 'VE-System API',
        'version': '4.0.0',
        'status': 'running',
        'features': ['user_system', 'progress_tracking', 'analytics'],
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
    
    # 檢查用戶資料庫
    try:
        conn = get_user_db()
        conn.execute("SELECT 1")
        conn.close()
        status['users'] = 'ok'
    except:
        status['users'] = 'error'
        all_ok = False
    
    return jsonify({
        'status': 'ready' if all_ok else 'partial',
        'databases': status,
        'timestamp': datetime.now().isoformat()
    }), 200 if all_ok else 503

# ============ 用戶系統 API ============

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """用戶註冊"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip() or None
    display_name = data.get('display_name', '').strip() or username
    
    # 驗證
    if not username or len(username) < 3:
        return jsonify({'error': '用戶名至少3個字元', 'code': 'INVALID_USERNAME'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': '密碼至少6個字元', 'code': 'INVALID_PASSWORD'}), 400
    
    conn = get_user_db()
    cur = conn.cursor()
    
    # 檢查重複
    cur.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cur.fetchone():
        conn.close()
        return jsonify({'error': '用戶名已被使用', 'code': 'USERNAME_EXISTS'}), 400
    
    if email:
        cur.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cur.fetchone():
            conn.close()
            return jsonify({'error': 'Email已被使用', 'code': 'EMAIL_EXISTS'}), 400
    
    # 建立用戶
    password_hash = hash_password(password)
    cur.execute('''
        INSERT INTO users (username, email, password_hash, display_name)
        VALUES (?, ?, ?, ?)
    ''', (username, email, password_hash, display_name))
    user_id = cur.lastrowid
    
    # 建立令牌
    token = generate_token()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    cur.execute('INSERT INTO tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
                (user_id, token, expires_at))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '註冊成功',
        'token': token,
        'user': {
            'id': user_id,
            'username': username,
            'display_name': display_name,
            'level': 1,
            'exp': 0,
            'gold': 500
        }
    }), 201

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """用戶登入"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': '請輸入用戶名和密碼', 'code': 'MISSING_CREDENTIALS'}), 400
    
    conn = get_user_db()
    cur = conn.cursor()
    
    cur.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username))
    user = cur.fetchone()
    
    if not user or not verify_password(password, user['password_hash']):
        conn.close()
        return jsonify({'error': '用戶名或密碼錯誤', 'code': 'INVALID_CREDENTIALS'}), 401
    
    # 建立新令牌
    token = generate_token()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    cur.execute('INSERT INTO tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
                (user['id'], token, expires_at))
    
    # 更新最後登入
    cur.execute('UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now().isoformat(), user['id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '登入成功',
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'display_name': user['display_name'],
            'avatar': user['avatar'],
            'level': user['level'],
            'exp': user['exp'],
            'gold': user['gold'],
            'hp': user['hp'],
            'max_hp': user['max_hp']
        }
    })

@app.route('/api/v1/auth/logout', methods=['POST'])
@require_auth
def logout():
    """登出"""
    token = request.headers.get('X-Token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    conn = get_user_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM tokens WHERE token = ?', (token,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '已登出'})

@app.route('/api/v1/user/profile', methods=['GET'])
@require_auth
def get_profile():
    """取得用戶資料"""
    user = g.user
    
    conn = get_user_db()
    cur = conn.cursor()
    
    # 統計
    cur.execute('''
        SELECT 
            COUNT(*) as total_answers,
            SUM(is_correct) as correct_count,
            MAX(answered_at) as last_answer
        FROM answer_history WHERE user_id = ?
    ''', (g.user_id,))
    stats = dict(cur.fetchone())
    
    # 今日統計
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute('SELECT * FROM daily_stats WHERE user_id = ? AND date = ?', (g.user_id, today))
    today_stats = cur.fetchone()
    
    # 成就數
    cur.execute('SELECT COUNT(*) FROM user_achievements WHERE user_id = ?', (g.user_id,))
    achievement_count = cur.fetchone()[0]
    
    # 徽章數
    cur.execute('SELECT COUNT(*) FROM user_badges WHERE user_id = ?', (g.user_id,))
    badge_count = cur.fetchone()[0]
    
    conn.close()
    
    accuracy = round(stats['correct_count'] / stats['total_answers'] * 100, 1) if stats['total_answers'] else 0
    
    return jsonify({
        'user': {
            'id': user['id'],
            'username': user['username'],
            'display_name': user['display_name'],
            'avatar': user['avatar'],
            'level': user['level'],
            'exp': user['exp'],
            'exp_to_next': (user['level'] * 300) - (user['exp'] % 300),
            'gold': user['gold'],
            'hp': user['hp'],
            'max_hp': user['max_hp'],
            'created_at': user['created_at']
        },
        'stats': {
            'total_answers': stats['total_answers'] or 0,
            'correct_count': stats['correct_count'] or 0,
            'accuracy': accuracy,
            'achievement_count': achievement_count,
            'badge_count': badge_count
        },
        'today': dict(today_stats) if today_stats else {
            'questions_answered': 0,
            'correct_count': 0,
            'exp_gained': 0,
            'streak_count': 0
        }
    })

@app.route('/api/v1/user/profile', methods=['PUT'])
@require_auth
def update_profile():
    """更新用戶資料"""
    data = request.get_json() or {}
    
    allowed_fields = ['display_name', 'avatar', 'settings']
    updates = []
    values = []
    
    for field in allowed_fields:
        if field in data:
            updates.append(f'{field} = ?')
            values.append(json.dumps(data[field]) if field == 'settings' else data[field])
    
    if not updates:
        return jsonify({'error': '沒有可更新的欄位'}), 400
    
    values.append(g.user_id)
    
    conn = get_user_db()
    cur = conn.cursor()
    cur.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', values)
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '已更新'})

# ============ 進度追蹤 API ============

@app.route('/api/v1/progress/answer', methods=['POST'])
@optional_auth
def record_answer():
    """記錄答題"""
    data = request.get_json() or {}
    question_id = data.get('question_id')
    subject = data.get('subject')
    is_correct = data.get('is_correct', False)
    answer_given = data.get('answer_given')
    correct_answer = data.get('correct_answer')
    time_spent = data.get('time_spent', 0)
    
    if not question_id:
        return jsonify({'error': '缺少 question_id'}), 400
    
    result = {
        'recorded': False,
        'exp_gained': 0,
        'gold_gained': 0,
        'level_up': False
    }
    
    if g.user_id:
        conn = get_user_db()
        cur = conn.cursor()
        
        # 記錄答題
        cur.execute('''
            INSERT INTO answer_history 
            (user_id, question_id, subject, is_correct, answer_given, correct_answer, time_spent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (g.user_id, question_id, subject, 1 if is_correct else 0, answer_given, correct_answer, time_spent))
        
        # 計算獎勵
        exp_gain = 20 if is_correct else 5
        gold_gain = 10 if is_correct else 0
        
        # 更新用戶
        cur.execute('SELECT level, exp FROM users WHERE id = ?', (g.user_id,))
        user = cur.fetchone()
        new_exp = user['exp'] + exp_gain
        new_level = (new_exp // 300) + 1
        level_up = new_level > user['level']
        
        cur.execute('UPDATE users SET exp = ?, level = ?, gold = gold + ? WHERE id = ?',
                    (new_exp, new_level, gold_gain, g.user_id))
        
        # 更新每日統計
        today = datetime.now().strftime('%Y-%m-%d')
        cur.execute('''
            INSERT INTO daily_stats (user_id, date, questions_answered, correct_count, exp_gained, gold_gained)
            VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                questions_answered = questions_answered + 1,
                correct_count = correct_count + ?,
                exp_gained = exp_gained + ?,
                gold_gained = gold_gained + ?
        ''', (g.user_id, today, 1 if is_correct else 0, exp_gain, gold_gain,
              1 if is_correct else 0, exp_gain, gold_gain))
        
        # 更新學習進度
        if subject:
            cur.execute('''
                INSERT INTO learning_progress (user_id, subject, attempts, correct_count, last_studied)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(user_id, subject, concept_id) DO UPDATE SET
                    attempts = attempts + 1,
                    correct_count = correct_count + ?,
                    last_studied = ?,
                    mastery_level = CAST(correct_count + ? AS REAL) / (attempts + 1) * 100
            ''', (g.user_id, subject, 1 if is_correct else 0, datetime.now().isoformat(),
                  1 if is_correct else 0, datetime.now().isoformat(), 1 if is_correct else 0))
        
        conn.commit()
        conn.close()
        
        result = {
            'recorded': True,
            'exp_gained': exp_gain,
            'gold_gained': gold_gain,
            'new_exp': new_exp,
            'new_level': new_level,
            'level_up': level_up
        }
    
    return jsonify(result)

@app.route('/api/v1/progress/game', methods=['POST'])
@optional_auth
def record_game_progress():
    """記錄遊戲進度"""
    data = request.get_json() or {}
    scenario_id = data.get('scenario_id')
    completed = data.get('completed', False)
    score = data.get('score', 0)
    
    if not scenario_id:
        return jsonify({'error': '缺少 scenario_id'}), 400
    
    if g.user_id:
        conn = get_user_db()
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO game_progress (user_id, scenario_id, completed, score, completed_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, scenario_id) DO UPDATE SET
                completed = MAX(completed, ?),
                score = MAX(score, ?),
                completed_at = CASE WHEN ? > completed THEN ? ELSE completed_at END
        ''', (g.user_id, scenario_id, 1 if completed else 0, score, 
              datetime.now().isoformat() if completed else None,
              1 if completed else 0, score, 1 if completed else 0, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'recorded': True})
    
    return jsonify({'success': True, 'recorded': False, 'message': '未登入，進度未保存'})

@app.route('/api/v1/progress/history', methods=['GET'])
@require_auth
def get_answer_history():
    """取得答題歷史"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    subject = request.args.get('subject')
    
    conn = get_user_db()
    cur = conn.cursor()
    
    if subject:
        cur.execute('''
            SELECT * FROM answer_history 
            WHERE user_id = ? AND subject = ?
            ORDER BY answered_at DESC LIMIT ? OFFSET ?
        ''', (g.user_id, subject, limit, offset))
    else:
        cur.execute('''
            SELECT * FROM answer_history 
            WHERE user_id = ?
            ORDER BY answered_at DESC LIMIT ? OFFSET ?
        ''', (g.user_id, limit, offset))
    
    history = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    return jsonify({'history': history, 'count': len(history)})

# ============ 學習分析 API ============

@app.route('/api/v1/analytics/overview', methods=['GET'])
@require_auth
def get_analytics_overview():
    """學習分析總覽"""
    conn = get_user_db()
    cur = conn.cursor()
    
    # 各科統計
    cur.execute('''
        SELECT 
            subject,
            COUNT(*) as total,
            SUM(is_correct) as correct,
            ROUND(CAST(SUM(is_correct) AS REAL) / COUNT(*) * 100, 1) as accuracy
        FROM answer_history 
        WHERE user_id = ?
        GROUP BY subject
    ''', (g.user_id,))
    by_subject = [dict(row) for row in cur.fetchall()]
    
    # 每日趨勢 (最近7天)
    cur.execute('''
        SELECT 
            date,
            questions_answered,
            correct_count,
            exp_gained,
            max_streak
        FROM daily_stats 
        WHERE user_id = ?
        ORDER BY date DESC LIMIT 7
    ''', (g.user_id,))
    daily_trend = [dict(row) for row in cur.fetchall()]
    
    # 弱點分析 (正確率最低的科目)
    cur.execute('''
        SELECT 
            subject,
            COUNT(*) as total,
            SUM(is_correct) as correct,
            ROUND(CAST(SUM(is_correct) AS REAL) / COUNT(*) * 100, 1) as accuracy
        FROM answer_history 
        WHERE user_id = ?
        GROUP BY subject
        HAVING total >= 5
        ORDER BY accuracy ASC
        LIMIT 3
    ''', (g.user_id,))
    weak_subjects = [dict(row) for row in cur.fetchall()]
    
    # 學習時間分布
    cur.execute('''
        SELECT 
            strftime('%H', answered_at) as hour,
            COUNT(*) as count
        FROM answer_history 
        WHERE user_id = ?
        GROUP BY hour
        ORDER BY hour
    ''', (g.user_id,))
    hourly_dist = [dict(row) for row in cur.fetchall()]
    
    # 連勝記錄
    cur.execute('SELECT MAX(max_streak) as best_streak FROM daily_stats WHERE user_id = ?', (g.user_id,))
    best_streak = cur.fetchone()['best_streak'] or 0
    
    conn.close()
    
    return jsonify({
        'by_subject': by_subject,
        'daily_trend': daily_trend,
        'weak_subjects': weak_subjects,
        'hourly_distribution': hourly_dist,
        'best_streak': best_streak
    })

@app.route('/api/v1/analytics/subject/<subject>', methods=['GET'])
@require_auth
def get_subject_analytics(subject):
    """單科目分析"""
    conn = get_user_db()
    cur = conn.cursor()
    
    # 基本統計
    cur.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(is_correct) as correct,
            ROUND(CAST(SUM(is_correct) AS REAL) / COUNT(*) * 100, 1) as accuracy,
            AVG(time_spent) as avg_time
        FROM answer_history 
        WHERE user_id = ? AND subject = ?
    ''', (g.user_id, subject))
    stats = dict(cur.fetchone())
    
    # 最近答題
    cur.execute('''
        SELECT question_id, is_correct, answered_at
        FROM answer_history 
        WHERE user_id = ? AND subject = ?
        ORDER BY answered_at DESC LIMIT 20
    ''', (g.user_id, subject))
    recent = [dict(row) for row in cur.fetchall()]
    
    # 錯題
    cur.execute('''
        SELECT question_id, answer_given, correct_answer, answered_at
        FROM answer_history 
        WHERE user_id = ? AND subject = ? AND is_correct = 0
        ORDER BY answered_at DESC LIMIT 10
    ''', (g.user_id, subject))
    wrong_answers = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return jsonify({
        'subject': subject,
        'stats': stats,
        'recent': recent,
        'wrong_answers': wrong_answers
    })

@app.route('/api/v1/analytics/recommendations', methods=['GET'])
@require_auth
def get_recommendations():
    """學習推薦"""
    conn = get_user_db()
    cur = conn.cursor()
    
    # 找出弱點科目
    cur.execute('''
        SELECT 
            subject,
            ROUND(CAST(SUM(is_correct) AS REAL) / COUNT(*) * 100, 1) as accuracy
        FROM answer_history 
        WHERE user_id = ?
        GROUP BY subject
        HAVING COUNT(*) >= 3
        ORDER BY accuracy ASC
        LIMIT 3
    ''', (g.user_id,))
    weak = [dict(row) for row in cur.fetchall()]
    
    # 找出需要複習的 (超過3天沒練習)
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    cur.execute('''
        SELECT subject, last_studied, mastery_level
        FROM learning_progress
        WHERE user_id = ? AND last_studied < ?
        ORDER BY mastery_level ASC
        LIMIT 5
    ''', (g.user_id, three_days_ago))
    need_review = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    recommendations = []
    
    for w in weak:
        recommendations.append({
            'type': 'weak_subject',
            'subject': w['subject'],
            'accuracy': w['accuracy'],
            'message': f"你在{w['subject']}的正確率只有{w['accuracy']}%，建議多加練習"
        })
    
    for r in need_review:
        recommendations.append({
            'type': 'review',
            'subject': r['subject'],
            'last_studied': r['last_studied'],
            'message': f"你已經{3}天沒有練習{r['subject']}了，記得複習哦"
        })
    
    return jsonify({'recommendations': recommendations})

# ============ 排行榜 API ============

@app.route('/api/v1/leaderboard', methods=['GET'])
def get_leaderboard():
    """排行榜"""
    board_type = request.args.get('type', 'exp')  # exp, accuracy, streak
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_user_db()
    cur = conn.cursor()
    
    if board_type == 'exp':
        cur.execute('''
            SELECT id, username, display_name, avatar, level, exp
            FROM users ORDER BY exp DESC LIMIT ?
        ''', (limit,))
    elif board_type == 'accuracy':
        cur.execute('''
            SELECT u.id, u.username, u.display_name, u.avatar, u.level,
                   ROUND(CAST(SUM(ah.is_correct) AS REAL) / COUNT(*) * 100, 1) as accuracy
            FROM users u
            JOIN answer_history ah ON u.id = ah.user_id
            GROUP BY u.id
            HAVING COUNT(*) >= 10
            ORDER BY accuracy DESC
            LIMIT ?
        ''', (limit,))
    else:  # streak
        cur.execute('''
            SELECT u.id, u.username, u.display_name, u.avatar, u.level,
                   MAX(ds.max_streak) as best_streak
            FROM users u
            JOIN daily_stats ds ON u.id = ds.user_id
            GROUP BY u.id
            ORDER BY best_streak DESC
            LIMIT ?
        ''', (limit,))
    
    rankings = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    # 加入排名
    for i, r in enumerate(rankings):
        r['rank'] = i + 1
    
    return jsonify({'type': board_type, 'rankings': rankings})

# ============ 原有 API (保持相容) ============

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
                table_count = len(tables)
                record_count = 0
                for (table,) in tables:
                    try:
                        count = cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                        record_count += count
                    except:
                        pass
                db_stats[db_name] = {'tables': table_count, 'records': record_count, 'status': 'ok'}
                total_tables += table_count
                total_records += record_count
                conn.close()
            except Exception as e:
                db_stats[db_name] = {'status': 'error', 'error': str(e)}
        else:
            db_stats[db_name] = {'status': 'not found'}
    
    return jsonify({
        'total_databases': len([d for d in db_stats.values() if d.get('status') == 'ok']),
        'total_tables': total_tables,
        'total_records': total_records,
        'databases': db_stats,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/v1/db/<db_name>/tables')
def list_tables(db_name):
    conn = get_db(db_name)
    if not conn:
        return jsonify({'error': f'資料庫 {db_name} 不存在'}), 404
    
    cur = conn.cursor()
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    
    result = []
    for (table,) in tables:
        try:
            count = cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            result.append({'name': table, 'count': count})
        except:
            result.append({'name': table, 'count': -1})
    
    conn.close()
    return jsonify({'database': db_name, 'tables': result, 'count': len(result)})

@app.route('/api/v1/db/<db_name>/table/<table_name>')
def query_table(db_name, table_name):
    conn = get_db(db_name)
    if not conn:
        return jsonify({'error': f'資料庫 {db_name} 不存在'}), 404
    
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    cur = conn.cursor()
    try:
        cur.execute(f'SELECT * FROM "{table_name}" LIMIT ? OFFSET ?', (limit, offset))
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        total = cur.fetchone()[0]
        
        conn.close()
        return jsonify({'table': table_name, 'data': data, 'count': len(data), 'total': total})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400

# 教育系統 API
@app.route('/api/v1/education/questions')
def get_questions():
    limit = request.args.get('limit', 10, type=int)
    subject = request.args.get('subject')
    
    conn = get_db('education')
    if not conn:
        return jsonify({'error': '教育資料庫不存在'}), 404
    
    cur = conn.cursor()
    
    # 只回傳有有效選項的選擇題
    base_query = '''
        SELECT * FROM exam_questions 
        WHERE options IS NOT NULL 
          AND options != '' 
          AND options != '[]'
          AND length(options) > 10
    '''
    
    if subject and subject != 'all':
        cur.execute(base_query + ' AND subject_id LIKE ? ORDER BY RANDOM() LIMIT ?', 
                    (f'%{subject}%', limit * 2))
    else:
        cur.execute(base_query + ' ORDER BY RANDOM() LIMIT ?', (limit * 2,))
    
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    questions = []
    
    for row in rows:
        q = dict(zip(columns, row))
        if isinstance(q.get('options'), str):
            try:
                opts = json.loads(q['options'])
                if isinstance(opts, list) and len(opts) >= 2:
                    q['options'] = opts
                    questions.append(q)
            except:
                pass
        elif isinstance(q.get('options'), list) and len(q['options']) >= 2:
            questions.append(q)
        
        if len(questions) >= limit:
            break
    
    conn.close()
    return jsonify({'questions': questions, 'count': len(questions)})

@app.route('/api/v1/education/check', methods=['POST'])
@optional_auth
def check_answer():
    data = request.get_json() or {}
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    if not question_id or not answer:
        return jsonify({'error': '缺少必要參數'}), 400
    
    conn = get_db('education')
    if not conn:
        return jsonify({'error': '教育資料庫不存在'}), 404
    
    cur = conn.cursor()
    cur.execute('SELECT answer, explanation, subject_id FROM exam_questions WHERE question_id = ?', (question_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': '題目不存在'}), 404
    
    correct_answer = row[0]
    explanation = row[1]
    subject = row[2]
    is_correct = answer.upper() == correct_answer.upper()
    
    # 自動記錄 (如果已登入)
    if g.user_id:
        record_data = {
            'question_id': question_id,
            'subject': subject,
            'is_correct': is_correct,
            'answer_given': answer,
            'correct_answer': correct_answer
        }
        with app.test_request_context(json=record_data):
            g.user_id = g.user_id
            record_answer()
    
    return jsonify({
        'correct': is_correct,
        'correct_answer': correct_answer,
        'explanation': explanation
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
