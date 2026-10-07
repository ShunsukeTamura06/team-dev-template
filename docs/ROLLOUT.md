# 導入手順書

このテンプレートを社内に導入するための手順書です。最初に一度だけ行います。
導入後の日々の使い方は [OPERATIONS.md](OPERATIONS.md) を参照してください。

## 登場する人(役割)

1人が複数の役割を兼ねても構いません。手順を始める前に、それぞれ誰が担当するかを決めてください。

| 役割 | やること | 必要なGitLab権限 |
|---|---|---|
| **推進担当** | 導入全体を進める。事前確認、テンプレートの持ち込み、動作確認 | グループの Owner |
| **チーフ** | チーム共通ルール(AGENTS.md)の内容を決める | グループの Maintainer 以上 |
| **ツール作者** | 自分が担当するツールにテンプレートを入れる | 担当ツールのプロジェクトの Maintainer 以上 |
| **エンジニア全員** | 自分のPCの Claude Code の設定を整える | — |

「グループ」とは、各ツールのGitLabプロジェクトをまとめているGitLabのグループのことです。
ツールのプロジェクトが1つのグループにまとまっていない場合は、先に1つのグループへ移すと、以降の設定が一度で済みます。

## 全体の流れ

| 段階 | 内容 | 担当 |
|---|---|---|
| 0 | 事前確認 | 推進担当 |
| 1 | テンプレートを社内GitLabに置く | 推進担当 |
| 2 | 共通ルール v1 を決める | チーフ |
| 3 | GitLabグループを設定する | 推進担当 |
| 4 | 1つのツールで試す | ツール作者・推進担当 |
| 5 | 残りのツールに広げる | 各ツール作者・推進担当 |
| 6 | 各自のPCを整える | エンジニア全員 |

---

## 段階0 事前確認

**推進担当が**、次の4点を確認します。答えによって後の手順が変わるので、必ず先に行ってください。

### 0-1 作成者以外の承認が必要か

- **誰に聞くか**:EUC管理・システムリスク管理の規程を所管する部署
- **何を聞くか**:「担当部署で開発している業務ツールの変更を本番に反映するとき、作成者以外の承認が必要か」
- **答えが「必要」の場合**:段階3の後に、各ツールのプロジェクトで「承認者1名を必須」にする設定を追加します(GitLab の Settings → Merge requests → Merge request approvals)。承認者は、AIレビューの結果を見たうえで概要を確認して承認します。

### 0-2 ソースコードを社内LLM APIに送ってよいか

- **誰に聞くか**:社内LLM APIを管理している部署
- **何を聞くか**:「業務ツールのソースコード(顧客情報は含まない)を、自動レビューのためにLLM APIへ送ってよいか」
- **答えが「不可」の場合**:AIレビューは使えません。段階3の CI変数を登録せず、`.gitlab-ci.yml` の `ai_review` ジョブを削除して導入します(ルールの統一と lint・test は有効です)。

### 0-3 GitLab の Runner が使えるか

- **誰に聞くか**:社内GitLabの管理者(インフラ担当)
- **何を聞くか**:
  1. 対象グループのプロジェクトで使える Runner があり、その種類(executor)が **docker** か
  2. その Runner から次の3つに接続できるか:Docker Hub(イメージの取得)、PyPI(Pythonライブラリの取得)、社内LLM API
- **Docker Hub に出られない場合**:管理者に `python:3.12-slim` と `pragent/pr-agent:latest` を社内のコンテナレジストリへ登録してもらいます。登録先のイメージ名を控えておき、段階1-4で使います。
- **PyPI に出られない場合**:社内のPyPIミラーのURLを控えておき、段階3-3で CI変数 `PIP_INDEX_URL` として登録します。

### 0-4 社内PCの Python のバージョン

- **誰に聞くか**:エンジニア全員(自分のPCで `python --version` を実行してもらう)
- **使い道**:CIで使う Python のバージョンを、社内PCとそろえます。社内PCの Python が 3.12 ではない場合は、段階1-4でテンプレートの設定を書き換えます。

---

## 段階1 テンプレートを社内GitLabに置く

**推進担当が**行います。

### 1-1 テンプレートを社内に持ち込む

1. **推進担当が**、社外のPCで https://github.com/ShunsukeTamura06/team-dev-template を開き、緑色の **Code** ボタン → **Download ZIP** でダウンロードする
2. **推進担当が**、社内の外部ファイル持ち込み手順(申請など)に従って、ZIP を社内PCへ移す
3. **推進担当が**、社内PCで ZIP を展開する。展開したフォルダ名を `team-dev-template` にする

### 1-2 社内GitLabにプロジェクトを作る

1. **推進担当が**、ブラウザで社内GitLabを開き、ツールのプロジェクトがあるグループを開く
2. **推進担当が**、画面右上の **New project(新規プロジェクト)** → **Create blank project(空のプロジェクトを作成)** を選ぶ
3. **推進担当が**、次のとおり入力して **Create project** を押す
   - Project name:`team-dev-template`
   - Visibility Level:**Private**
   - **Initialize repository with a README のチェックを外す**(外さないと、次の手順の push が失敗します)

### 1-3 テンプレートを push する

**推進担当が**、社内PCで `team-dev-template` フォルダを開いたターミナルから、次を実行します。
`<プロジェクトのURL>` は、1-2で作ったプロジェクトの画面の **Code → Clone with HTTPS** に表示される URL です。

```
git init -b main
git add .
git commit -m "テンプレートを追加"
git remote add origin <プロジェクトのURL>
git push -u origin main
```

**確認**:**推進担当が**、ブラウザでプロジェクトを再読み込みし、`AGENTS.md` などのファイルが表示されることを確認します。

### 1-4 社内環境に合わせて書き換える(必要な場合のみ)

段階0の答えによって、**推進担当が**次のファイルを書き換え、commit して push します。

| 段階0の答え | 書き換えるファイル | 書き換える内容 |
|---|---|---|
| Docker Hub に出られない | `.gitlab-ci.yml` | `PYTHON_IMAGE` と `PR_AGENT_IMAGE` を社内レジストリのイメージ名にする |
| 社内PCの Python が 3.12 ではない | `.gitlab-ci.yml` | `PYTHON_IMAGE` を `python:<バージョン>-slim` にする |
| 社内PCの Python が 3.11 より古い | `pyproject.toml` | `target-version` を `"py310"` などそのバージョンにする |
| LLM APIへの送信が不可 | `.gitlab-ci.yml` | `ai_review:` から最後の行までを削除する |

---

## 段階2 共通ルール v1 を決める

**チーフが**行います。段階4より前に終わらせてください(ツールに配るのは、この時点の AGENTS.md です)。

1. **チーフが**、エンジニア全員から、各自が今使っている `CLAUDE.md` / `AGENTS.md`(各ツールのリポジトリにあるもの、自分のPCの `~/.claude/CLAUDE.md` の両方)を集める
2. **チーフが**、集めた内容のうち「チーム全員が守るべき書き方のルール」を選び、テンプレートの `AGENTS.md` に反映する
   - **ルールは合計10個前後に抑えます**。多すぎると、AIレビューの指摘が増えて読まれなくなります
   - そのツールだけの情報(業務の理由・入出力など)は、ここには入れません。段階4で各ツールの README に移します
3. **チーフが**、変更を `team-dev-template` プロジェクトへの MR として出し、エンジニア全員に内容を確認してもらってからマージする

---

## 段階3 GitLabグループを設定する

**推進担当が**行います。グループの Owner 権限が必要です。

### 3-1 AIレビュー用のトークンを作る

1. **推進担当が**、GitLabでツールのグループを開き、左のサイドバーで **Settings(設定)→ Access tokens(アクセストークン)** を開く
2. **推進担当が**、**Add new token(新しいトークンを追加)** を押し、次のとおり入力して **Create group access token** を押す
   - Token name:`ai-review`
   - Expiration date:1年後の日付(上限は通常1年)
   - Select a role:**Developer**
   - Select scopes:**api** にチェック
3. **推進担当が**、画面に表示されたトークンをコピーし、3-3 で使う。**この画面を閉じると二度と表示されません**
4. **推進担当が**、有効期限の1か月前に予定表へ「ai-review トークンの更新」を登録する(期限が切れると AIレビューが止まります)

### 3-2 社内LLM APIの情報をそろえる

**推進担当が**、社内LLM APIの管理部署から次の3つを入手します。

- API の URL(OpenAI互換の形式で、通常 `/v1` で終わるもの)
- API キー
- 使うモデルの名前

### 3-3 CI変数を登録する

1. **推進担当が**、グループの **Settings → CI/CD** を開き、**Variables(変数)** の欄の **Expand(展開)** を押す
2. **推進担当が**、**Add variable(変数を追加)** を押し、下の表の変数を1つずつ登録する。表に指定が無いかぎり、次のとおりにする
   - Type:**Variable**
   - Environments:**All (default)**
   - **Protect variable:チェックを外す**(付けると、保護されていないブランチのMRで変数が読めず、AIレビューが動きません)

| Key | Value | Mask variable |
|---|---|---|
| `AI_REVIEW_GITLAB_TOKEN` | 3-1 でコピーしたトークン | チェックする |
| `AI_REVIEW_API_BASE` | 社内LLM APIの URL | — |
| `AI_REVIEW_API_KEY` | 社内LLM APIのキー | チェックする |
| `AI_REVIEW_MODEL` | `openai/` + モデル名(例:モデル名が `claude-sonnet` なら `openai/claude-sonnet`) | — |
| `AI_REVIEW_MAX_TOKENS` | モデルが受け付ける最大入力トークン数。分からなければ登録しない(128000 が使われる) | — |
| `PIP_INDEX_URL` | 段階0-3 で控えた社内PyPIミラーのURL。PyPIに出られる場合は登録しない | — |
| `INTERNAL_CA_CERT` | 社内LLM APIが社内CAの証明書を使う場合のみ。**Type を File にして**、Value に証明書(PEM形式)の中身を貼る | — |

**注意**:`AI_REVIEW_MODEL` の先頭の `openai/` は、モデル名に関係なく必ず付けます。付け忘れると AIレビューが「モデルが見つからない」で失敗します。

---

## 段階4 1つのツールで試す

最初は1つのツールだけで行い、問題が出たら直してから段階5に進みます。
試すツールは、小さくて、作者がすぐ対応できるものを選んでください。

### 4-1 テンプレートを入れる

**ツール作者が**、自分のPCで行います。

1. **ツール作者が**、`team-dev-template` を、試すツールのリポジトリと同じ親フォルダに clone する

   ```
   (例)
   C:\work\team-dev-template\     ← テンプレート
   C:\work\bond-reconcile\        ← 試すツール
   ```

2. **ツール作者が**、試すツールのリポジトリで新しいブランチを作る

   ```
   cd C:\work\bond-reconcile
   git switch main
   git pull
   git switch -c adopt-team-template
   ```

3. **ツール作者が**、同じフォルダで、テンプレートも読めるように Claude Code を起動する

   ```
   claude --add-dir ..\team-dev-template
   ```

4. **ツール作者が**、Claude Code に次の文章をそのまま貼り付けて依頼する

   ```
   ../team-dev-template のテンプレートを、このリポジトリに導入してください。
   手順は ../team-dev-template/docs/ROLLOUT.md の「4-1で Claude Code が行う作業」に従ってください。
   業務の背景など、コードから分からないことは推測せず、私に質問してください。
   ```

5. **ツール作者が**、Claude Code の質問(このツールが必要な理由、判定ルールの根拠、利用者、過去の障害など)に答える
6. **ツール作者が**、Claude Code の作業が終わったら、変更されたファイルを一通り目で確認する

#### 4-1で Claude Code が行う作業

(この節は、手順4で Claude Code が読む指示です)

1. このリポジトリに既存の `CLAUDE.md`、`.claude/CLAUDE.md`、`AGENTS.md` があれば読み、内容を次の3つに分けてユーザーに見せる
   - チーム共通ルールにすべきもの → ファイルには反映せず、一覧にしてユーザーに渡す(ユーザーがチーフに渡す)
   - このツール固有の情報 → README.md の該当欄に移す
   - Claude Code への操作上の注意 → 新しい CLAUDE.md の末尾に移す
2. テンプレートから次のファイルをコピーする。同じ名前のファイルがすでにある場合は、各行の括弧内の扱いに従う
   - `AGENTS.md`、`CLAUDE.md`(既存のものは置き換える)
   - `.claude/hooks/`、`.claude/skills/`
   - `.claude/settings.json`(既存があれば、`permissions.deny` と `hooks` を既存の設定に追加する)
   - `.gitlab-ci.yml`(既存があれば、上書きせずにユーザーに相談する)
   - `.pr_agent.toml`、`.gitlab/merge_request_templates/Default.md`
   - `requirements-dev.txt`
   - `pyproject.toml` の `[tool.ruff]`・`[tool.ruff.lint]`・`[tool.pytest.ini_options]`(既存の pyproject.toml があれば、その3つの節だけを追加する)
   - `.gitignore`、`.gitattributes`(既存があれば、足りない行だけを追加する)
3. `requirements.txt` が無ければ、コードの import から作る。Windows でしか動かないライブラリ(`pywin32`、`xlwings` など)には `; sys_platform == "win32"` を付ける(CI は Linux で動くため)
4. テストが `tests/` 以外の場所にあれば、`pyproject.toml` の `testpaths` をその場所に合わせる
5. テンプレートの README.md の見出し構成に沿って、このツールの README.md を作る。コードから分かることは埋め、分からないことはユーザーに質問する
6. `ruff format .` と `ruff check --fix .` を実行する。残ったエラーは、修正内容をユーザーに見せて了承を得てから直す
7. `pytest` を実行し、結果をユーザーに伝える(テストが無いことは問題としない)
8. 変更したファイルの一覧と、手順1の「チーム共通ルールにすべきもの」の一覧を、最後にまとめて表示する

### 4-2 導入のMRを出してマージする

1. **ツール作者が**、変更を commit して push する

   ```
   git add .
   git commit -m "チーム開発テンプレートを導入"
   git push -u origin adopt-team-template
   ```

2. **ツール作者が**、push後にターミナルに表示される URL を開き、MR を作成する
3. **ツール作者が**、MR画面の **Pipelines** タブで、`lint` と `test` が成功(緑)していることを確認する。失敗していたら、ジョブを開いてエラーを確認し、Claude Code に直してもらって push し直す
4. **ツール作者が**、MR をマージする

**注意**:この導入MRでは、AIレビューが日本語にならず、チームルールも参照しません。AIレビューの設定(`.pr_agent.toml`)とルール(`AGENTS.md`)は main ブランチから読まれるため、マージ後の次のMRから効きます。AIレビューの確認は 4-4 で行います。

### 4-3 main ブランチを保護する

**推進担当が**、自分のPCで行います。対象ツールのプロジェクトの Maintainer 権限が必要です。

1. **推進担当が**、自分の GitLab アカウントで個人アクセストークンを作る
   - 画面右上の自分のアイコン → **Edit profile(プロフィールを編集)** → 左のサイドバーの **Access tokens(アクセストークン)** → **Add new token**
   - Token name:`team-admin`、Expiration date:1か月後、Select scopes:**api** → **Create personal access token**
   - 表示されたトークンをコピーする
2. **推進担当が**、`team-dev-template` の `admin/projects.txt` に、試すツールのプロジェクトを1行追加する

   ```
   (例) プロジェクトのURLが https://gitlab.example.local/my-group/bond-reconcile の場合
   my-group/bond-reconcile
   ```

3. **推進担当が**、`team-dev-template` のフォルダで、PowerShell から次を実行する

   ```
   $env:GITLAB_URL = "https://gitlab.example.local"      # 社内GitLabのURL
   $env:GITLAB_TOKEN = "glpat-..."                       # 手順1でコピーしたトークン
   python admin/gitlab_admin.py protect --dry-run
   ```

4. **推進担当が**、表示された内容(対象プロジェクトと、設定される内容)が正しいことを確認し、`--dry-run` を外して実行する

   ```
   python admin/gitlab_admin.py protect
   ```

5. **推進担当が**、`[OK] my-group/bond-reconcile` と表示されたことを確認し、`admin/projects.txt` の変更を `team-dev-template` に MR で反映する

このスクリプトは、対象プロジェクトに次の2つを設定します。

- **main ブランチの保護**:直接 push は誰もできない / MR からのマージは Developer 以上ができる / 強制 push は禁止
- **マージの条件**:パイプライン(lint・test)が成功していないとマージできない

**確認**:**推進担当が**、GitLab で対象プロジェクトの **Settings → Repository → Protected branches** を開き、`main` が上記のとおりになっていることを確認します。

### 4-4 AIレビューが動くか確認する

1. **ツール作者が**、試すツールで小さな改修(誤字の修正など)をブランチで行い、MR を出す
2. **推進担当とツール作者が**、MR画面で次を確認する

| 確認すること | 見る場所 | 正常な状態 |
|---|---|---|
| CI が動いた | MR の **Pipelines** タブ | `lint`・`test`・`ai_review` の3つが表示され、`lint`・`test` が緑 |
| AIレビューが動いた | MR の **Overview** タブのコメント欄 | 「PR Reviewer Guide」と「PR Code Suggestions」のコメントが日本語で付く |
| ルールが効いている | AIレビューのコメント | AGENTS.md のルール番号に触れた指摘がある(指摘が無い場合もある) |
| マージ条件が効いている | MR の **Merge** ボタン | パイプライン実行中はマージできない |

3. **ツール作者が**、問題が無ければ MR をマージする

AIレビューのコメントが付かない場合は、`ai_review` ジョブを開いてログを確認し、末尾の「つまずいたとき」を参照してください。

---

## 段階5 残りのツールに広げる

1. **各ツール作者が**、自分の担当ツールごとに、段階4-1と4-2を行う
2. **推進担当が**、導入が終わったツールを `admin/projects.txt` に追加し、段階4-3の手順3〜5を行う(すでに設定したツールに再実行しても問題ありません)
3. **ツール作者が**、4-1の手順8で表示された「チーム共通ルールにすべきもの」を**チーフに**渡す。**チーフが**必要と判断したものを、[OPERATIONS.md の「チーム共通ルールを変える」](OPERATIONS.md#チーム共通ルールを変える)の手順で反映する

**注意**:main ブランチの保護は、テンプレートを入れ終えたツールだけに行います。テンプレートを入れる前のツールを保護すると、CI が無いのにMRが必須になり、手間だけが増えるためです。

---

## 段階6 各自のPCを整える

**エンジニア全員が**、自分のPCで行います。

### 6-1 開発に必要なものを入れる

1. **各エンジニアが**、作業するツールのリポジトリで、次を実行する

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

2. **各エンジニアが**、`ruff --version` を実行し、バージョンが表示されることを確認する(表示されないと、編集後の自動整形が動きません)
3. **各エンジニアが**、`python --version` を実行し、Python のバージョンが表示されることを確認する。`python` が見つからず `python3` なら動く場合は、各ツールの `.claude/settings.json` の `"command": "python"` を `"python3"` にする

### 6-2 個人用の CLAUDE.md を整理する

1. **各エンジニアが**、自分のPCの `~/.claude/CLAUDE.md`(Windows では `C:\Users\<ユーザー名>\.claude\CLAUDE.md`)を開く
2. **各エンジニアが**、中身を次のように仕分ける
   - 「回答は日本語で」「説明は短めに」のような**個人の好み** → そのまま残す
   - 命名・構成・エラー処理などの**コーディングのルール** → 個人用ファイルから消す。残したいものは**チーフに**渡す

コーディングのルールを個人用に残すと、Claude Code が個人用とチームのルールの両方を読み、食い違ったときにどちらに従うかが不安定になります。

---

## つまずいたとき

| 症状 | 原因 | 対処 |
|---|---|---|
| 1-3 の `git push` が `rejected` で失敗する | プロジェクト作成時に README を作った | `git pull --rebase origin main` の後に、もう一度 `git push -u origin main` |
| `lint` が失敗する | 既存コードが ruff のルールに合っていない | ローカルで `ruff format .` と `ruff check --fix .` を実行して push。残るエラーは Claude Code に直してもらう |
| `test` の `pip install` が失敗する | Windows 専用ライブラリが入っている、または PyPI に出られない | 4-1 の作業3のとおり `; sys_platform == "win32"` を付ける。または CI変数 `PIP_INDEX_URL` を登録する |
| ジョブが `pending` のまま動かない | 使える Runner が無い | GitLab管理者に Runner の割り当てを依頼する |
| ジョブが `pull access denied` などで失敗する | Docker Hub に出られない | 段階1-4のとおり、イメージを社内レジストリのものにする |
| `ai_review` のログに `401` | `AI_REVIEW_GITLAB_TOKEN` が無効か、期限切れ | 3-1 でトークンを作り直し、CI変数を更新する |
| `ai_review` のログに `model` や `LLM Provider NOT provided` | `AI_REVIEW_MODEL` の先頭に `openai/` が無い | CI変数を `openai/<モデル名>` に直す |
| `ai_review` のログに `SSL` や `certificate` | 社内LLM APIの証明書(社内CA)を PR-Agent が知らない | 社内CA証明書(PEM形式)を入手し、3-3 のとおり CI変数 `INTERNAL_CA_CERT` に File型で登録する |
| `ai_review` は成功するが英語でコメントされる | `.pr_agent.toml` がまだ main に無い | テンプレート導入MRをマージした後の MR から日本語になる |
| AIレビューの変数が読めない(`openai__key` が空など) | CI変数に Protect variable が付いている | 3-3 のとおり、Protect variable のチェックを外す |
| 4-3 のスクリプトが `HTTP 403` で失敗する | 推進担当に、そのプロジェクトの Maintainer 権限が無い | プロジェクトの Maintainer に権限を付けてもらう |
