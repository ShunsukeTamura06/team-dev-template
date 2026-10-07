---
name: self-review
description: MR を作る前に、変更内容をチーム共通ルールとツールの README に照らしてセルフレビューする。「MR前に確認して」「セルフレビューして」と言われたとき、または MR を作る前に使う。
---

# MR 前セルフレビュー

CI と同じ基準で確認する。ruff の設定はチーム共通のもの(`${CLAUDE_PLUGIN_ROOT}/ruff.toml`)を使う。

1. 変更を把握する
   - `git fetch origin` を実行し、`git diff origin/main...HEAD` と `git status` で変更を把握する(未コミットの変更も含める)
2. CI と同じチェックを実行する。対象は main から変更した `.py` ファイルだけ(CI も変更ファイルだけを見る)
   - `ruff format --check --config "${CLAUDE_PLUGIN_ROOT}/ruff.toml" <変更した.pyファイル>`
   - `ruff check --config "${CLAUDE_PLUGIN_ROOT}/ruff.toml" <変更した.pyファイル>`
   - `python -m pytest -q`(テストが1つも無い場合は、失敗ではなく「テストなし」と報告する)
   - 失敗があれば先に直す
3. 差分を、チーム共通ルール(セッション開始時に読み込み済み)と README の「このツール固有のルール」に照らして確認し、次の形式で報告する

```
## セルフレビュー結果

### ルール違反(直すべき)
- [ルール番号] ファイル:行 — 内容と直し方

### 担当者以外が読んで迷いそうな箇所
- ファイル:行 — 何が分かりにくいか

### README の更新漏れ
- 仕様・設定値・入出力の変更に対して、README(業務背景/入力/出力/環境変数/用語集)の更新が必要か

### 人間のレビューが必要な変更か
- 本番データ更新 / DB 構造変更 / 外部システム接続 / 削除処理 の該当有無
```

4. 「直すべき」がある場合は、修正してよいかユーザーに確認してから直す
5. 最後に、MR の説明文の下書きを `.gitlab/merge_request_templates/Default.md` の形式で作る
