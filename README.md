# 当直スケジューラ

FastAPI + React で構築された当直/宿直シフトスケジューラです。

## 機能

- 指定された年月のシフトを自動生成
- 医師ごとのシフト不可日を設定可能（日直/夜勤）
- シフト間隔の最小・最大日数を指定可能
- 生成されたシフト表を CSV 形式でダウンロード

## 技術スタック

| 層 | 技術 |
|----|------|
| フロントエンド | React 18 + Vite + react-router-dom |
| バックエンド | FastAPI + Uvicorn |
| スケジューリング | pandas + jpholiday |

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
uvicorn oncall_app.oncall_app:app --reload
```

ブラウザで [http://localhost:8000](http://localhost:8000) にアクセスしてください。

## 使用方法

1. 年・月・医師名（カンマ区切り）・シフト間隔を入力して「カレンダー表示」をクリック
2. カレンダーで医師ごとに入れない日の日直/夜勤をクリックして選択
3. 「スケジュール作成」をクリックするとシフト表が生成される
4. 生成されたシフト表は CSV でダウンロード可能

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | React SPA を返す |
| POST | `/api/calendar` | カレンダーデータを JSON で返す |
| POST | `/api/schedule` | シフト表を生成して JSON で返す |
| GET | `/csv?tok=<token>` | シフト表を CSV でダウンロード |

## テスト

```bash
pip install pytest httpx
pytest tests/ -v
```

33 件のテスト（ユニットテスト・統合テスト）が含まれています。

## 開発者

Jinsei Shiraishi

## ライセンス

MIT ライセンス。詳細は [LICENSE](LICENSE) を参照してください。
