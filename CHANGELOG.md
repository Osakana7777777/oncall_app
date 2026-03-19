## [1.0.0] - 2026-03-19

### 追加
- React + Vite による SPA フロントエンドを新規構築
- `react-router-dom` でクライアントサイドルーティング（IndexPage / CalendarPage / SchedulePage）
- `pytest` によるテストスイートを追加（ユニットテスト 21 件・統合テスト 12 件、計 33 件）

### 変更
- FastAPI のルートを HTML 返却から JSON API に変更
  - `POST /calendar` → `POST /api/calendar`
  - `POST /schedule` → `POST /api/schedule`
- `GET /`・`/calendar`・`/schedule` で React の `index.html` を配信

### 修正
- `datetime.date` オブジェクトが JSON シリアライズできないバグを修正

### 削除
- Jinja2 テンプレート（`templates.py`）を削除
- `jinja2` 依存を削除

---

## [0.2.1] - 2025-06-19

### 変更
- 機能ごとにファイルを分割
