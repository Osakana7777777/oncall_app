## [1.3.0] - 2026-04-21

### 追加
- 集計画面にシフト間隔（最小・最大）の編集欄を追加
  - アンケート作成時の設定値で初期表示
  - シフト生成に失敗した場合、エラーをインライン表示し「間隔を変更して再試行」できるように
  - アンケート回答データは保持したまま何度でも再生成可能

---

## [1.2.0] - 2026-04-17

### 追加
- アンケート機能: 医師ごとに入れない日直/夜勤を事前申告できる仕組み
  - 管理画面 (`/admin`) でアンケートを作成し、共有URLを発行
  - 公開アンケートページ (`/survey/:id`) で医師が名前を選び、入れない昼/夜をタップ送信（再送で上書き可）
  - 集計画面 (`/admin/results/:id`) で回答状況をカレンダー表示し、そのままシフト自動生成に反映
- SQLite による永続化レイヤー (`oncall_app/db.py`) を追加（`SURVEY_DB_PATH` 環境変数で保存先変更可）
- アンケート関連 API エンドポイントを追加
  - `POST/GET/DELETE /api/surveys`
  - `GET /api/surveys/{id}` (医師一覧 + カレンダー)
  - `POST /api/surveys/{id}/responses` (回答送信)
  - `GET /api/surveys/{id}/responses/{doctor}` (回答取得)
  - `GET /api/surveys/{id}/results` (集計結果)

### 変更
- SPA ルーティングをキャッチオール化し、`/admin`・`/survey/:id` などの新ルートに対応
- トップ画面に管理画面へのリンクを追加

### ドキュメント
- README にアンケート機能の使い方、API 一覧、Railway ボリューム設定手順を追記

---

## [1.1.0] - 2026-03-28

### 変更
- カレンダーのシフト選択 UI を刷新（セル内に昼/夜ボタン配置）

---

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
