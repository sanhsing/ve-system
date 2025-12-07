# VE-System 虛擾地球系統

## 快速部署 (Render)

1. Fork 或上傳此 repo 到 GitHub
2. 登入 [Render](https://render.com)
3. New → Web Service → 連結 GitHub repo
4. 自動偵測 `render.yaml` 配置
5. Deploy!

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /` | 系統資訊 |
| `GET /health` | 健康檢查 |
| `GET /health/ready` | 就緒檢查 (含DB狀態) |
| `GET /api/v1/status` | 系統狀態總覽 |
| `GET /api/v1/qixing` | 北斗七星狀態 |
| `GET /api/v1/db/<db>/tables` | 列出資料表 |
| `GET /api/v1/db/<db>/table/<table>` | 查詢資料 |

## 資料庫 (9庫)

- meta.db - 元資料
- ve.db - 虛擬地球
- trade.db - 交易系統
- education.db - 教育系統
- business.db - 商業運營
- clarity.db - 清晰化
- corpus.db - 語料庫
- taoist.db - 道家哲學
- work.db - 工作流程

## 系統成熟度

整體: 90.7% (產品級)
