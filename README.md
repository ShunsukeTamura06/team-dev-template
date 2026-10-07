# team-dev-template

業務ツールを開発するチーム(各ツールを1人ずつ担当し、全員が Claude Code を使う)のための、チーム標準の一式です。
目的は、**担当者以外でも、どのツールも保守できる状態を保つこと**です。

## 何が入っているか

| 仕組み | 中身 | 効く場所 |
|---|---|---|
| Claude Code のプラグイン `team` | チーム共通ルールの読み込み、実データを読ませない保護、編集後の自動整形、`/team:...` のスキル | 各自の PC |
| 共通 CI | 変更したファイルの書式チェック、テスト、社内 LLM による AI レビュー | 社内 GitLab の各ツールの MR |
| 新しいツールのひな形 | README の型、構成、CI の参照 | 新しいツール |
| 管理スクリプト | main ブランチの保護設定 | 推進担当の PC |

チーム共通のものは、すべてこのリポジトリにだけ置きます。各ツールのリポジトリは、ここを参照するだけです。
ルールを変えるときは、このリポジトリを1か所変えれば、全員の Claude Code と全ツールの CI に反映されます。

## 文書

| 文書 | 読む人 | 内容 |
|---|---|---|
| [docs/ROLLOUT.md](docs/ROLLOUT.md) | 推進担当・全員 | 導入時に1回だけ行う作業 |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 全員 | 日々の開発と、ルールなどを変えるときの作業 |
| [docs/DESIGN.md](docs/DESIGN.md) | 推進担当・チーフ | 何をどこに置くか、何が変わったら誰が何をするかの一覧 |
| [plugins/team/rules.md](plugins/team/rules.md) | 全員 | チーム共通ルール(正本) |

## スキル(Claude Code で入力する)

| 入力 | いつ使うか |
|---|---|
| `/team:setup` | 自分の PC の初期設定(最初に1回。警告が出たときも) |
| `/team:new-tool` | 新しいツールをひな形から作る |
| `/team:adopt` | 既存のツールをチーム標準に乗せる |
| `/team:self-review` | MR を作る前に、CI と同じ確認をする |
| `/team:update-context` | README(業務文脈)を書く・更新する |
| `/team:handover` | 担当を引き継ぐための説明を作る |

## フォルダ構成

```
.claude-plugin/marketplace.json   Claude Code のマーケットプレイスの定義
plugins/team/                     プラグイン本体
  rules.md                        チーム共通ルール(正本)
  ruff.toml / tool-versions.txt   書式チェックの設定と、ruff・pytest のバージョン
  protected-paths.txt             Claude Code に読み書きさせないパス
  hooks/ scripts/                 起動時・編集前後に動く処理
  skills/                         /team:... のスキル
  templates/tool/                 新しいツールのひな形
ci/python-tool.yml                全ツール共通の CI(各ツールから include される)
pr-agent/pr_agent.toml            AI レビューの設定
admin/gitlab_admin.py             main ブランチの保護設定
tests/                            このリポジトリ自身のテスト
```

## このリポジトリを変更するとき

変更は MR で行い、チーフが承認します。MR では CI が `tests/` を実行し、全ツールを壊す変更を防ぎます。
手元で確認する場合:

```
pip install -r plugins/team/tool-versions.txt pyyaml
python -m pytest tests
```
