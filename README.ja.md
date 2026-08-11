# 👁️ Claude Vision — Claude に「目」を与える

> **ネイティブの画像理解能力を持たない LLM に視覚を追加**：スクリーンショット、UI 再現、OCR、画像比較、ハードウェア写真認識 — すべて豆包（Doubao）ビジョンモデル（火山エンジン Ark）で自動処理。

「モデルが画像を見られない」という苦い経験から、「画像をアップロードすれば即分析」まで磨き上げた完全なソリューション。

---

## 🚀 30秒で再現：他のエージェント向けクイックスタート・プロンプト

> これを任意のエージェント（Claude / ChatGPT / その他）に貼り付けるだけで、この視覚機能をすぐに学習できます：

```
あなたは私の視覚分析アシスタントです。この環境のモデルは画像を直接見られない可能性があります：
1. `vision_doubao.py` スクリプトで豆包ビジョンモデル（火山エンジン Ark）を呼び出して画像を分析
2. キー解決の順序：環境変数 ARK_API_KEY → 1Password op CLI（OP_REF参照）→ エラー
3. ユーザーが画像/スクリーンショット/PDFをアップロードしたら → 自動分析。「見ましょうか？」と聞かない、「unsupported file」と報告しない
4. 画像は uploads ディレクトリにある。bashで探す（ls /sessions/*/mnt/uploads/）
5. モード選択：UIスクショ=A（再現）；バグUI=B；エラーログ=C；文字/表=D；実物写真=E；画像比較=compare
6. 大きな画像は先に1280pxへ縮小（2.1-proの深い思考は大画像でタイムアウト）；webpはJPEGへ変換；PDFは先に画像へ変換
7. 実行前にプロキシを解除：unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy
8. デフォルトは doubao-seed-2-1-pro（品質優先）。バッチは --model doubao-seed-2-0-mini

使い方：
  python3 vision_doubao.py <画像> A "指示"   # UI再現
  python3 vision_doubao.py <画像> B          # 問題特定
  python3 vision_doubao.py <画像> C          # エラーログ抽出
  python3 vision_doubao.py <画像> D          # OCR
  python3 vision_doubao.py <画像> E "指示"   # 一般的な説明
  python3 vision_doubao.py compare a b "指示"  # 画像比較
```

**上のプロンプトをコピー + `vision_doubao.py` をダウンロードすれば、完全な視覚分析機能を手に入れられます。**

---

## 💡 なぜ作ったのか

### 問題：モデルが画像を見られない

この環境のモデル（Haiku 4.5）には**信頼できる組み込みの画像理解機能がありません**。ユーザーが画像をアップロードするたびに、モデルはこう表示します：

> `[Unsupported Image]` / "I can't see the image"

画像を使う作業（UIデザイン、ハードウェア開発、ドキュメントOCR）には致命的です。

### 解決策：外部ビジョンレイヤー

モデルに目がないなら、**外部の目**を与えましょう — **豆包ビジョンモデル**（火山エンジン Ark API）を呼んで画像を見せ、テキストで返してもらいます。

```
ユーザーが画像をアップロード → Claudeスクリプトが豆包ビジョンを呼ぶ → 構造化テキストが返る → Claudeが理解して返信
```

---

## 📚 開発の軌跡（学んだ教訓）

| 日付 | 段階 | 重要な決定 / 落とし穴 |
|------|------|---------------------|
| 2026-08-08 | **Qwen時代** | Qwen3-VL-flash を DashScope API 経由でビジョンレイヤーに。OCR/ログ抽出は正確 |
| 2026-08-08 | **幻覚を発見** | Qwen3-VL-flash は**画像比較で幻覚** — 存在しない差分を捏造。結果は「検証チェックリスト」としてのみ使用可能 |
| 2026-08-10 | **豆包に切り替え** | ユーザーが切り替えを決定。doubao-seed-1.6-vision vs 2.0-mini vs **2.1-pro** を評価 |
| 2026-08-10 | **デュアルモデル決定** | 2.1-pro（品質優先、深い思考）をメイン + 2-0-mini（バッチ速度）をフォールバック |
| 2026-08-11 | **1Password統合** | キー管理：手動貼り付け → op CLI自動取得 → スキルにトークンを埋め込み、どのセッションでも使用可能 |
| 2026-08-11 | **GitHub公開** | コードを一般化（ハードコード削除）、monah-studio/claude-vision にプッシュ |

### 主な落とし穴チェックリスト

1. **Qwen3-VL-flash の画像比較幻覚** → 豆包 2.1-pro に切り替え（深い思考で安定）
2. **大画像 + 深い思考でタイムアウト** → スクリプトが >2048px を自動縮小。先に1280pxへ縮小推奨
3. **webp が拒否される** → JPEGへ変換（PIL convert RGB）
4. **サンドボックスのプロキシが異常なIPv6** → 実行前に必ず `unset ...proxy...`。しないとHTTPライブラリがクラッシュ
5. **`op read` タイトルに空白/括弧があると解析失敗** → 常にアイテムIDを使用
6. **スキルのbase64破損** → 再生成時にデコード整合性を検証

---

## ✨ 最終ソリューション

### アーキテクチャ

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  画像アップロード │ ──▶ │    Claude Agent   │ ──▶ │ 豆包ビジョン       │
│ (uploads dir) │     │ (ネイティブ視覚なし)│     │ 2.1-pro (Ark API)│
└─────────────┘     └──────────────────┘     └──────────────────┘
                           │  ▲
                           ▼  │
                    ┌──────────────────┐
                    │ 1Password キー    │
                    │ (op CLI 自動)     │
                    └──────────────────┘
```

### コア機能

| 機能 | 説明 |
|------|------|
| 🖼️ **5つの認識モード** | UI再現 / 問題特定 / ログ抽出 / OCR / 一般的な説明 |
| 🔄 **画像比較** | 実際の差分を検出、幻覚を防止 |
| 📦 **自動縮小** | >2048px 自動リサイズ、過大なAPIリクエストを回避 |
| 🔑 **自動キー取得** | 環境変数 → 1Password op → 明確なエラー。ハードコードしない |
| 🚀 **デュアルモデル** | 品質優先（深い思考）+ バッチ速度（低遅延） |
| 🪶 **サードパーティ依存なし** | 純Python標準ライブラリ + Pillow |

### 技術スタック

- **ビジョンモデル**: Doubao Seed 2.1 Pro（`doubao-seed-2-1-pro-260628`）/ 2.0 Mini
- **API**: 火山エンジン Ark（OpenAI互換）
- **認証情報**: 1Password CLI（`op`）+ Service Accountトークン
- **言語**: Python 3.8+（urllib + Pillow）

---

## 🚀 クイックスタート

### 1. 依存関係をインストール

```bash
pip install Pillow
```

### 2. APIキーを設定（どちらか）

```bash
# 方法1：環境変数
export ARK_API_KEY="ark-..."

# 方法2：1Password（推奨）
# op read "op://Claude Code/Ark API Key (豆包视觉)/credential"
```

### 3. 最初の画像を分析

```bash
python3 vision_doubao.py your_image.png E "この画像を説明してください"
```

---

## 📖 ユーザーガイド

### モード一覧

| モード | 用途 | 例 |
|--------|------|-----|
| `A` | **UIピクセル再現**：レイアウト/座標/色/フォント | `vision_doubao.py ui.png A "ページを再現"` |
| `B` | **問題特定**：UIバグ/ずれ/重なり | `vision_doubao.py bug.png B` |
| `C` | **エラーログ抽出**：エラー/スタックを原文まま | `vision_doubao.py error.png C` |
| `D` | **OCR**：テキストを原文まま抽出 | `vision_doubao.py doc.png D` |
| `E` | **一般的な説明**：実物/シーン/写真 | `vision_doubao.py photo.jpg E` |
| `compare` | **画像比較**：実際の差分を検出 | `vision_doubao.py compare a.png b.png` |

### モデル切り替え

```bash
# 品質優先（デフォルト）
python3 vision_doubao.py img.png E

# バッチ速度
python3 vision_doubao.py img.png D --model doubao-seed-2-0-mini-260428

# 環境変数
export ARK_MODEL="doubao-seed-2-0-mini-260428"
```

### 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `ARK_API_KEY` | — | 火山エンジンArkキー（最優先） |
| `ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` | APIエンドポイント |
| `ARK_MODEL` | `doubao-seed-2-1-pro-260628` | デフォルトモデル |
| `OP_REF` | `op://Claude Code/Ark API Key (豆包视觉)/credential` | 1Password参照 |

---

## 🔁 自動化ワークフロー

### UIピクセル再現ループ

```
デザイン → 豆包ビジョンA分析 → HTML/CSS作成 → スクリーンショット → compare画像比較 → 修正 → 一致
```

### アップロード時の自動分析

Claudeのメモリルールを設定すると、**ユーザーが画像をアップロード → エージェントが自動分析**、手動トリガー不要：
- uploadsディレクトリを自動検索
- モードを自動選択（迷ったらE）
- 自動縮小/形式変換
- 結果を直接表示

---

## ⚠️ トラブルシューティング

| 問題 | 解決策 |
|------|--------|
| 大画像でタイムアウト | 先に1280pxへ縮小 |
| webp拒否 | JPEGへ変換 |
| プロキシエラー `Invalid port` | `unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy` |
| 401キー無効 | 火山エンジンコンソールのキー/残高を確認 |
| 429レート制限 | 後でリトライ |
| 403権限なし | モデルを切り替え |

---

## 📚 リファレンス

全モデル、プラットフォーム、依存関係、ライセンスは [REFERENCES.md](REFERENCES.md) を参照。

- **ビジョンモデル**: [豆包 Seed（火山エンジン Ark）](https://www.volcengine.com/product/ark)
- **APIプラットフォーム**: [火山エンジン](https://www.volcengine.com/) · [Arkドキュメント](https://www.volcengine.com/docs/82379)
- **認証情報**: [1Password Developer](https://developer.1password.com/)
- **依存関係**: [Pillow](https://python-pillow.org/) · [Python](https://www.python.org/)

---

## 🤝 謝辞

「モデルが画像を見られない」という実際の痛点から生まれ、何度も反復を重ねて磨かれました。強力なビジョン理解を提供する豆包Seed、安全な認証情報管理を提供する1Passwordに感謝します。

---

## 📄 ライセンス

MIT — [LICENSE](LICENSE) を参照。自由に使用・変更・共有できます。
