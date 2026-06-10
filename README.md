# 当直スケジューラ

FastAPI + React で構築された当直/宿直シフトスケジューラです。

## 機能

- 指定された年月のシフトを自動生成
- 医師ごとのシフト不可日を設定可能（日直/夜勤）
- シフト間隔の最小・最大日数を指定可能
- 生成されたシフト表を CSV 形式でダウンロード
- **アンケート機能**: 共有URLで医師から入れない日の希望を収集し、管理画面で集計・シフト作成に反映

## 技術スタック

| 層 | 技術 |
|----|------|
| フロントエンド | React 18 + Vite + react-router-dom |
| バックエンド | FastAPI + Uvicorn |
| スケジューリング | pandas + jpholiday |
| データ永続化 | SQLite (アンケート保存) |

## 環境構築

Python 3.11 以上と Node.js が必要です。

### 1. リポジトリのクローン

```bash
git clone https://github.com/Osakana7777777/oncall_app.git
cd oncall_app
```

### 2. Python 依存関係のインストール

```bash
uv venv -p 3.11
source .venv/bin/activate  # Windows の場合は .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 3. フロントエンドのビルド

```bash
cd frontend
npm install
npm run build
cd ..
```

## 起動方法

```bash
uv run uvicorn oncall_app.oncall_app:app --reload
```

ブラウザで [http://localhost:8000](http://localhost:8000) にアクセスしてください。

## 使用方法

### A. 管理者が直接シフトを作成

1. 年・月・医師名（カンマ区切り）・シフト間隔を入力して「カレンダー表示」をクリック
2. カレンダーで医師ごとに入れない日の日直/夜勤をクリックして選択
3. 「スケジュール作成」をクリックするとシフト表が生成される
4. 生成されたシフト表は CSV でダウンロード可能

### B. 医師にアンケートを配布して集約する

1. トップ画面から「アンケート管理画面へ」→ タイトル・年月・医師名を入力してアンケートを作成
2. 一覧の「URLコピー」で共有URL (`/survey/<id>`) を取得し、医師に配布
3. 各医師が自分の名前を選び、入れない「昼/夜」をタップして送信（後から上書き可）
4. 管理画面の「集計」で回答カレンダーを確認 → 「この結果でシフト作成」で自動生成に反映

## API エンドポイント

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET | `/` | React SPA を返す | - |
| POST | `/api/calendar` | カレンダーデータを JSON で返す | - |
| POST | `/api/schedule` | シフト表を生成して JSON で返す | - |
| GET | `/csv?tok=<token>` | シフト表を CSV でダウンロード (リンクは発行から 1 時間有効) | - |
| POST | `/api/surveys` | アンケートを作成 | 管理 |
| GET | `/api/surveys` | アンケート一覧 | 管理 |
| GET | `/api/surveys/{id}` | アンケート情報 (医師・カレンダー) | - |
| DELETE | `/api/surveys/{id}` | アンケート削除 | 管理 |
| POST | `/api/surveys/{id}/responses` | 医師の回答を送信 (再送で上書き) | - |
| GET | `/api/surveys/{id}/responses/{doctor}` | ある医師の回答を取得 | - |
| GET | `/api/surveys/{id}/results` | 集計結果を取得 | 管理 |

「管理」の付いたエンドポイントは、環境変数 `ADMIN_TOKEN` が設定されている場合に `X-Admin-Token` ヘッダによる認証が必要になります（未設定の場合は認証なしで動作します）。

## セキュリティ (管理画面の保護)

アンケートには医師名や勤務不可日といった個人情報が含まれるため、公開サーバで運用する場合は必ず管理トークンを設定してください。

```bash
# トークンの生成例
openssl rand -hex 24
```

環境変数 `ADMIN_TOKEN` に生成した値を設定すると、管理画面 (`/admin`) を開いた際にトークン入力画面が表示されます。入力したトークンはブラウザの sessionStorage に保持されます。医師向けのアンケート回答ページ (`/survey/<id>`) は共有 URL で使うため認証不要のままです。

## Railway へのデプロイ

[Railway](https://railway.app) を使ってワンコマンドでデプロイできます。

```bash
railway login
railway init
railway up
```

デプロイ後は Railway ダッシュボードの **Settings → Networking → Generate Domain** で公開 URL を発行してください。

`railway.toml` にはビルドコマンドと起動コマンドのみが定義されています。GitHub 連携でプロジェクトを作成した場合は、Railway が対象ブランチへのプッシュを検知して自動ビルド・デプロイを実行します（設定は Railway ダッシュボードの **Settings → Source** にあります）。`railway up` による手動デプロイ運用の場合、プッシュしただけでは自動デプロイされません。

### アンケートデータの永続化

アンケートの保存先はデフォルトで `./data/survey.db` (SQLite) です。Railway のコンテナファイルシステムは再起動で消えるため、本番運用ではボリュームをマウントしてください。

1. Railway ダッシュボードで **Volumes → New Volume** を作成し、マウントパスを `/data` に設定
2. **Variables** で `SURVEY_DB_PATH=/data/survey.db` を追加
3. 次回のデプロイ以降、アンケートデータが永続化されます

### 管理トークンの設定（公開運用では必須）

Railway ダッシュボードの **Variables** で `ADMIN_TOKEN` にランダムな文字列（`openssl rand -hex 24` などで生成）を設定してください。未設定のままだと管理画面・アンケートデータに誰でもアクセスできます。

## テスト

```bash
pip install pytest httpx
pytest tests/ -v
```

50 件のテスト（ユニットテスト・統合テスト・セキュリティテスト）が含まれています。

## 開発者

Jinsei Shiraishi

## ライセンス

MIT ライセンス。詳細は [LICENSE](LICENSE) を参照してください。
