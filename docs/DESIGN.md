# 設計:何を、どこに置き、変わったときに誰が何をするか

## 1. 設計の原則

**チーム全体で共通のものは、このリポジトリ(以下「中央リポジトリ」)にだけ置く。各ツールのリポジトリには写さない。**

写すと、ルールを1行変えるたびに全リポジトリへの反映作業が発生し、いずれ反映漏れで食い違う。
そこで、各ツールと各自の PC は中央リポジトリを「参照」する作りにしている。

| 参照する側 | 参照のしかた | 反映のタイミング |
|---|---|---|
| 各自の PC の Claude Code | 中央リポジトリをプラグインのマーケットプレイスとして登録し、プラグイン `team` を入れる。自動更新を有効にする | Claude Code の起動後しばらくして取り込み、**次の起動から**有効 |
| 各ツールの CI | `.gitlab-ci.yml` で、中央リポジトリの `ci/python-tool.yml` を `include` する | **次のパイプラインから** |
| AI レビュー(PR-Agent) | CI が実行のたびに、中央リポジトリから `rules.md` と `pr_agent.toml` を取得する | **次のパイプラインから** |

## 2. 層の構成(上ほど優先)

| 層 | 置き場所 | 誰が書くか | 何を書くか |
|---|---|---|---|
| ツール固有 | 各ツールの `README.md`「このツール固有のルール」 | ツールの担当者 | そのツールだけの例外・業務ルール |
| チーム共通 | 中央リポジトリ `plugins/team/rules.md` | チーフが承認 | 全ツールに共通の書き方 |
| 個人 | 各自の PC の `~/.claude/CLAUDE.md` | 本人 | 口調・説明の詳しさなど、本人の好みだけ |

- 個人の好みはコードの品質に影響させない(チームの書き方に関わることは個人の CLAUDE.md に書かない)
- AI レビューは「ツール固有 + チーム共通」だけを見る。個人の層はレビューに影響しない

## 3. ファイルの置き場所

### 中央リポジトリ(このリポジトリ)

| ファイル | 役割 | 使う側 |
|---|---|---|
| `plugins/team/rules.md` | チーム共通ルールの正本 | Claude Code(フック)・AI レビュー(CI) |
| `plugins/team/ruff.toml` | 書式チェックの設定 | Claude Code(編集後の自動整形・self-review)・CI |
| `plugins/team/tool-versions.txt` | ruff・pytest のバージョン | 各自の PC(`/team:setup`)・CI |
| `plugins/team/protected-paths.txt` | Claude Code に読み書きさせないパス(`.env`・`data/`・`output/`) | Claude Code(フック) |
| `plugins/team/hooks/` と `scripts/` | セッション開始時のルール読み込み、パスの保護、編集後の整形 | Claude Code |
| `plugins/team/skills/` | `/team:setup`・`self-review`・`update-context`・`handover`・`new-tool`・`adopt` | Claude Code |
| `plugins/team/templates/tool/` | 新しいツールのひな形 | `/team:new-tool`・`/team:adopt` |
| `ci/python-tool.yml` | 全ツール共通の CI(lint・test・ai_review) | 各ツールの CI |
| `pr-agent/pr_agent.toml` | AI レビューの方針(言語・指摘数など) | CI |
| `admin/gitlab_admin.py` | main ブランチの保護設定 | 推進担当 |
| `tests/` | 上記が壊れていないかのテスト | 中央リポジトリの CI |

### 各ツールのリポジトリに置くもの(これだけ)

| ファイル | 中身 | 中央の変更で書き換えが要るか |
|---|---|---|
| `.gitlab-ci.yml` | `include` の3行だけ | 要らない |
| `CLAUDE.md` | `@README.md` の1行(と、そのツール専用の Claude への注意) | 要らない |
| `README.md` | そのツールの業務文脈・固有ルール | 要らない(ツール固有の情報なので) |
| `.gitlab/merge_request_templates/Default.md` | MR の説明のひな形 | 原則要らない(※) |
| `.gitignore`・`.gitattributes`・`.env.example` | Git とツールの設定 | 要らない |

※ GitLab は MR のひな形を各リポジトリから読む(グループ共通にするには有料版が必要)。中身は変わりにくい項目だけにしてある。変えたくなった場合は、変更後のひな形を `templates/tool/` に入れ、各ツールは次に触るときに `/team:adopt` で取り込めばよい(全ツール一斉に直す必要はない)。

**各ツールに置かないもの**:チーム共通ルール、ruff の設定、AI レビューの設定、Claude Code の設定(`.claude/settings.json`)。

## 4. 変更の一覧:何が起こり、誰が何をするか

「各ツールでの作業」が「なし」になることを、設計の目標にしている。

### よく起こる変更

| 変更 | 頻度の目安 | 変えるファイル | 誰が | 各ツールでの作業 | 反映 |
|---|---|---|---|---|---|
| チーム共通ルールの追加・変更・削除 | 月に数回 | `plugins/team/rules.md` | 誰でも MR、チーフが承認 | なし | PC:次の起動 / AI レビュー:次の MR |
| ツール固有のルール・業務背景 | 随時 | 各ツールの `README.md` | 担当者(`/team:update-context`) | そのツールだけ | 次の起動・次の MR |
| 個人の好み | 随時 | 本人の `~/.claude/CLAUDE.md` | 本人 | なし | 次の起動 |
| AI レビューの方針(指摘数・観点) | 月に1回程度 | `pr-agent/pr_agent.toml`(観点は `rules.md` の「AI レビュアーへ」) | チーフ | なし | 次の MR |
| スキルの追加・改善 | 随時 | `plugins/team/skills/<名前>/SKILL.md` | 誰でも MR | なし | 次の起動 |
| 新しいツールを作る | 随時 | (新しいリポジトリ) | 担当者が `/team:new-tool`、推進担当が保護設定 | そのツールだけ | — |

### ときどき起こる変更

| 変更 | 変えるもの | 誰が | 各ツールでの作業 |
|---|---|---|---|
| ruff のルール変更 | `plugins/team/ruff.toml` | チーフ | なし。CI は MR で変更したファイルだけを確認するので、既存コードが一斉に CI 失敗することはない |
| ruff・pytest のバージョン更新 | `plugins/team/tool-versions.txt` | チーフ | なし。各自の PC は次の起動時に警告が出るので `/team:setup` を実行 |
| 読ませないパスの追加 | `plugins/team/protected-paths.txt` | チーフ | なし |
| CI のジョブの追加・変更 | `ci/python-tool.yml` | チーフ | なし |
| LLM のモデル・接続先の変更 | GitLab グループの CI 変数 `AI_REVIEW_*` | 推進担当 | なし |
| トークンの更新(有効期限切れ) | グループアクセストークンを作り直し、CI 変数 `TEAM_BOT_TOKEN` を更新 | 推進担当 | なし |
| PR-Agent・Python のイメージの変更 | `ci/python-tool.yml` の `TEAM_PR_AGENT_IMAGE`・`TEAM_PYTHON_IMAGE` | 推進担当 | なし |
| 既存ツールを標準に乗せる | (そのツール) | 担当者が `/team:adopt`(以前の方式で写した設定の削除も含む)、推進担当が保護設定 | そのツールだけ |
| ツールの廃止 | GitLab でプロジェクトをアーカイブ | 推進担当 | — |
| メンバーの参加 | 本人の PC で `docs/ROLLOUT.md` 段階4を実施。GitLab グループに追加 | 本人・推進担当 | なし |
| メンバーの離任 | GitLab グループから外す。担当ツールは `/team:handover` で引き継ぐ | 推進担当・担当者 | なし |

### まれに起こる変更

| 変更 | 対応 | 各ツールでの作業 |
|---|---|---|
| 中央リポジトリの移動・名前変更 | GitLab のリダイレクトが効く間に、CI 変数 `TEAM_STANDARDS_PROJECT` を更新。各自は `claude plugin marketplace remove team-dev` → 新しい URL で段階4をやり直す | なし |
| Python 以外の言語のツールを扱う | `ci/` に別の CI 定義(例 `ci/vba-tool.yml`)を足し、そのツールの `.gitlab-ci.yml` の `file:` を変える | そのツールだけ |
| ルールの方針をツールの種類で分けたい | `rules.md` に「〇〇のツールでは」と書く。分量が増えたら、スキルにして必要なときだけ読ませる | なし |

### 変更を取り消したいとき

中央リポジトリで、その変更の MR を GitLab の「Revert(元に戻す)」ボタンで取り消す。取り消しも通常の変更と同じ経路で全員に届く。

## 5. 中央リポジトリを守る仕組み

中央リポジトリの変更は全ツールに即座に効くため、次で守っている。

- **main ブランチの保護**:中央リポジトリ自体も `admin/gitlab_admin.py protect --merge-level maintainer` で保護し、MR 経由でしか変えられず、マージできるのはチーフ(と推進担当)だけにする
- **中央リポジトリの CI**(`.gitlab-ci.yml`):フック・CI スクリプト・管理スクリプトのテスト、ファイル同士の整合性(名前の食い違い・存在しないファイルの参照・ルールの長さ)を確認する
- **ルールの長さの上限**:`rules.md` は 8,000 文字未満(テストで確認)。Claude Code のフックが渡せる文脈は 10,000 文字までのため。ルールは10項目前後に保ち、足したら削れるものがないかも考える

## 6. 既知の制約

- 自動更新は「起動後しばらくして取り込み、次の起動から有効」。急ぐときは、各自が Claude Code で `/plugin marketplace update team-dev` → `/reload-plugins` を実行する
- 読ませないパスの保護は、Claude Code がファイルやフォルダを指定して読み書き・検索する操作(Read・Edit・Write・Grep・Glob)に効く。Bash のコマンド(`cat` など)や、範囲を指定しないリポジトリ全体の検索までは止められない。最終的な防御は `.gitignore` と運用である
- 各ツールのプロジェクトは対象グループの中に置く(グループの CI 変数を使うため)
- 社内の方針で Claude Code の自動更新が止められている(環境変数 `DISABLE_AUTOUPDATER` が設定されている)PC では、プラグインの自動更新も止まる。その場合は環境変数 `FORCE_AUTOUPDATE_PLUGINS=1` を追加で設定する
- 各ツールの `.claude/settings.json` でプラグインを有効にする方法も Claude Code にはあるが、リポジトリを信頼する操作の後でしか働かず、URL を各リポジトリに書くことになるため採用していない
