# テンプレートの概要

## 何を解決するのか

エンジニア3人が1人1案件で開発し、それぞれの流儀で作った結果、お互いのツールを保守できなくなっている。
これを、人間同士のレビューを増やさずに解消する。

## どう解決するのか

1. **書く時点でそろえる**:全員が使う Claude Code に、同じチームルール(`AGENTS.md`)と、ツールごとの業務文脈(`README.md`)を自動で読ませる
2. **MR のときに確かめる**:CI(lint・test)と AIレビュー(PR-Agent)が、同じ `AGENTS.md` を基準にチェックする
3. **人が見るのは危ない変更だけ**:本番データ更新・DB構造変更・外部接続のときだけ、チーフもレビューする

成功の基準は「AIレビューが動いていること」ではなく、**担当外のツールの軽微な改修を、作者に聞かずにこなせたか**。

## 資料

| 資料 | 内容 | 読む人 |
|---|---|---|
| [ROLLOUT.md](ROLLOUT.md) | 導入手順(最初に一度だけ) | 推進担当・チーフ・ツール作者 |
| [OPERATIONS.md](OPERATIONS.md) | 改修の流れ、新しいツールの作り方、ルールの変え方 | エンジニア全員 |

## ファイルの役割

| ファイル | 役割 | 読むもの |
|---|---|---|
| `AGENTS.md` | チーム共通ルール。正本はこのテンプレートにあり、各ツールには写しを置く | Claude Code・AIレビュー・人 |
| `README.md` | ツールごとの業務文脈(なぜ・誰が・入出力・障害時)。ツールごとに書く | Claude Code・AIレビュー・人 |
| `CLAUDE.md` | 上の2つを Claude Code に読み込ませる | Claude Code |
| `.claude/settings.json` | 編集後の自動整形、実データ(`.env`・`data/`・`output/`)の読み取り禁止 | Claude Code |
| `.claude/hooks/` | 自動整形の処理 | Claude Code |
| `.claude/skills/` | `/self-review`・`/update-context`・`/handover` | Claude Code |
| `.gitlab-ci.yml` | lint・test・AIレビューの実行 | GitLab |
| `.pr_agent.toml` | AIレビューの方針(日本語、指摘は3件まで、保守性を重視) | AIレビュー |
| `.gitlab/merge_request_templates/Default.md` | MR の説明欄のひな形(高リスク変更のチェック欄つき) | 人 |
| `pyproject.toml`・`requirements*.txt` | ruff・pytest の設定、使うライブラリ | 人・CI |
| `app/`・`tests/` | ツールの構成の見本。新しいツールでは実際の処理に置き換える | 人・Claude Code |
| `admin/` | main ブランチの一括保護、ルールの一括配布を行う管理用スクリプト。テンプレートにだけ置く | 推進担当 |
| `docs/` | この資料。テンプレートにだけ置く | 人 |

## この版でやっていないこと(必要になったら追加する)

- MR のコメントに `/review` と書いて再レビューさせる(PR-Agent を Webhook サーバーとして常駐させる必要がある)
- 高リスク変更の自動判定(変更したファイルの場所で、承認者を自動で決める)
- シークレット(パスワード等)の混入を検出する CI ジョブ
- VBA・Access のソース管理(`.xlsm`・`.accdb` は Git で差分が取れないため、モジュールを書き出す運用が別に必要)
