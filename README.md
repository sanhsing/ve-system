# VE-System v4 部署包

## 後端 API

### 部署到 Render
1. Fork 或上傳到 GitHub
2. 在 Render 建立 Web Service
3. 連接 GitHub repo
4. 自動部署

### 本地測試
```bash
pip install -r requirements.txt
python app.py
```

### API 端點

**認證**
- POST /api/v1/auth/register - 註冊
- POST /api/v1/auth/login - 登入
- POST /api/v1/auth/logout - 登出

**用戶**
- GET /api/v1/user/profile - 個人資料
- PUT /api/v1/user/profile - 更新資料

**進度**
- POST /api/v1/progress/answer - 記錄答題
- POST /api/v1/progress/game - 記錄遊戲
- GET /api/v1/progress/history - 答題歷史

**分析**
- GET /api/v1/analytics/overview - 學習分析
- GET /api/v1/analytics/subject/<s> - 單科分析
- GET /api/v1/analytics/recommendations - 推薦

**排行榜**
- GET /api/v1/leaderboard?type=exp|accuracy|streak

## 前端

### 部署到 GitHub Pages
1. 將 index.html 推送到 gh-pages 分支
2. 啟用 GitHub Pages

### 功能
- 用戶註冊/登入
- localStorage 本地持久化
- 學習分析儀表板 (Recharts)
- 知識測驗系統
- 防詐情境遊戲
