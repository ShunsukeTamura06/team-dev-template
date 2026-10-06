# テンプレート利用ガイド

## このテンプレートの狙い

3人がそれぞれの流儀で作り、お互いにメンテできない状態を解消する。
人間同士のレビューは増やさず、次の2つで揃える。

1. **書く時点で揃える**: 全員が使う Claude Code に、同じルール(AGENTS.md)と業務文脈(README)を読ませる
2. **MR時に確認する**: CI(ruff・pytest)とAIレビュー(PR-Agent)が、同じルールでチェックする

成功の基準は「AIレビューが動いていること」ではなく、**担当者以外が、そのツールの軽微な改修を自力でこなせたか**。

## 中身

| ファイル | 役割 | 読む人 |
|---|---|---|
| `AGENTS.md` | チーム開発ルール v1 | Claude Code / PR-Agent / 人 |
| `README.md` | ツールの業務文脈(なぜ・誰が・入出力・障害時) | Claude Code / PR-Agent / 人 |
| `CLAUDE.md` | 上の2つを Claude Code に読み込ませる | Claude Code |
| `.claude/settings.json` | 編集後の自動整形(hook)、実データの読み取り禁止 | Claude Code |
| `.claude/skills/` | `/self-review` `/update-context` `/handover` | Claude Code |
| `.gitlab-ci.yml` | lint・test・AIレビュー | GitLab |
| `.pr_agent.toml` | AIレビューの方針(日本語、指摘は3件まで 等) | PR-Agent |
| `.gitlab/merge_request_templates/` | MRの説明テンプレート(高リスク変更のチェック欄) | 人 |
| `app/` `tests/` | 構成の見本(入口・I/O・業務ロジック・設定の分離) | 置き換えて使う |

## 使い始める

### 新しいツールを作るとき

1. このリポジトリをコピーして新しいGitLabプロジェクトを作る(GitLabの「プロジェクトテンプレート」機能が使える環境ならそれに登録すると楽)
2. Claude Code を起動し、作りたいものを伝える。最初に README の「目的」「業務背景」を一緒に埋める
3. `app/` のサンプルを実際の処理に置き換える

### 既存のツールに導入するとき

1. `AGENTS.md` `CLAUDE.md` `.claude/` `.gitlab-ci.yml` `.pr_agent.toml` `.gitlab/` をコピーする
2. Claude Code で `/update-context` を実行し、READMEの業務文脈を作る(作者が質問に答える。1ツール15分程度)
3. 構成(`app/` の分け方)は、改修のついでに少しずつ寄せればよい。一度に直さない

## GitLab 側の初期設定(最初に一度だけ)

1. **mainブランチの保護**: Settings → Repository → Protected branches で、main への push を「No one」、merge を「Developers + Maintainers」にする
2. **パイプライン必須**: Settings → Merge requests で「Pipelines must succeed」をオンにする(AIレビューは `allow_failure` なので止まらない)
3. **AIレビュー用のトークン**: グループアクセストークン(ロール: Developer、スコープ: `api`)を発行する
4. **CI/CD変数**: グループの Settings → CI/CD → Variables に以下を登録する(グループに置けば全リポジトリで共有できる)

| 変数名 | 内容 | 設定 |
|---|---|---|
| `AI_REVIEW_GITLAB_TOKEN` | 3. のトークン | Masked |
| `AI_REVIEW_API_BASE` | 社内LLM API のURL(例: `https://llm.example.local/v1`) | |
| `AI_REVIEW_API_KEY` | 社内LLM API のキー | Masked |
| `AI_REVIEW_MODEL` | モデル名。**`openai/` を先頭に付ける**(例: `openai/claude-sonnet`) | |
| `AI_REVIEW_MAX_TOKENS` | モデルの最大入力トークン数(省略時 128000) | 任意 |

※ 変数を「Protected」にすると、保護されていないブランチのMRで読めなくなるので付けない。

## 日々の流れ

1. ブランチを切る → Claude Code で開発(ルールは自動で読み込まれる)
2. MR前に `/self-review`
3. MRを作る → CI と AIレビューのコメントを確認し、必要なら直す
4. 自分で merge する
5. MRテンプレートの「高リスク」に該当する場合だけ、チーフにもレビューを依頼する

## 育て方(運用しながら改善する)

- **AIの指摘が的外れ・多すぎる** → AGENTS.md の「AIレビュアーへ」か `.pr_agent.toml` を直す
- **AIが見逃した問題を人が見つけた** → AGENTS.md にルールを1つ足す。以降のすべての開発・レビューに効く
- **担当外のツールを触って困った** → 困ったことを README か AGENTS.md に足す
- ルールの変更は、それ自体をMRにする(誰が・なぜ変えたかが残る)
- 月に1回程度、AGENTS.md を見直し、守られていない・意味のないルールを削る。**10項目前後を保つ**

## 導入前に確認すること

- [ ] **内部統制**: 本番で使うツールの変更に「作成者以外の承認」が求められていないか(EUC管理・システムリスク管理の規程)。求められる場合は、GitLabの承認ルールで承認者1名を必須にし、承認者はAIレビュー結果を前提に概要を確認する運用にする
- [ ] **社内LLM APIの利用範囲**: ソースコードをLLM APIに送ってよいか(コードに顧客情報等が含まれないことは AGENTS.md ルール3で担保)
- [ ] **Dockerイメージ**: Runner から Docker Hub に出られるか。出られない場合は `python` と `pragent/pr-agent` を社内レジストリにミラーし、`.gitlab-ci.yml` の `PYTHON_IMAGE` / `PR_AGENT_IMAGE` を差し替える
- [ ] **pip**: Runner から PyPI に出られるか。出られない場合は CI変数 `PIP_INDEX_URL` に社内ミラーを設定する
- [ ] **証明書**: 社内LLM API が社内CAの証明書を使っている場合、PR-Agentのコンテナで `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` の設定が必要になることがある
- [ ] **Pythonのコマンド名**: hook は `python` で起動する。`python3` しか無い環境では `.claude/settings.json` の `"command"` を書き換える
- [ ] **ruff**: hook は ruff が入っていないと何もしない。開発PCでも `pip install -r requirements-dev.txt` を済ませておく

## この版でやっていないこと(必要になったら追加)

- MRコメントで `/review` と書いて再レビューさせる(PR-Agent を Webhook サーバーとして常駐させる必要がある)
- 高リスク変更の自動判定(CODEOWNERS やパスごとの承認ルール)
- シークレット検出のCIジョブ
- VBA / Access のソース管理(`.xlsm` `.accdb` はGitで差分が取れないため、モジュールのエクスポート運用が必要)
