@AGENTS.md
@README.md

## Claude Code 用の補足

- 上のチーム開発ルール(AGENTS.md)と、READMEの業務文脈を前提に作業する
- ファイル編集後は hooks で ruff が自動実行される。ruff がエラーを返したら修正する
- MRを作る前に `/self-review` を実行する
- 仕様を変えたら `/update-context` でREADMEの業務文脈を更新する
- 初めて触るリポジトリを把握するときは `/handover` を使う
