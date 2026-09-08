# TerraformのローカルファイルをDockerビルドから除外

## 問題と修正

通常の作業ツリーからビルドしたローカルイメージ `8598e1d5` に、`infrastructure/terraform/bootstrap/.terraform/` 内のWindows用AWSプロバイダーと、`terraform.tfstate`・バックアップが含まれていた。既存の `.dockerignore` は特定階層の `.terraform` と変数ファイルだけを除外しており、入れ子の作業フォルダーを除外できていなかった。これらの内容は公開せず、当該イメージのレジストリへのpushも行っていない。

`.dockerignore` に全階層の `.terraform`、stateとその派生ファイル、`.tfvars`・`.tfvars.json` の除外を追加した。Terraformのソース・ロックファイル・変数例は残す。アプリの実行コードとDBスキーマは変更しない。

## 検証

`scripts/test/check_docker_build_context.py` は、コピーした除外ルールと合成ファイルだけの一時コンテキストを作り、Dockerの実際のマッチングとCOPY結果を検査する。ネットワークなしのscratchビルドを使用し、実際のTerraform stateや変数の内容はテストに使わない。

ルートと複数の入れ子のプロバイダー、state・バックアップ、変数ファイル9件が除外され、ソース・ロック・例の3件は内容を保って渡ることを確認する。修正前は8件の禁止ファイルが渡って失敗、修正後は成功した。CIのUnit / Integrationジョブにも同じ検査を追加した。

- リポジトリ管理・Docker起動設定の既存27テスト成功。
- 新しい検査スクリプトのBlack・isort・Flake8チェック成功。
- 通常イメージを再ビルドし、`tableno-runtime-build-deps:clean`（`sha256:ce8767d4e6dea73fc701a26098e3e4c4daa7626a91e698909d198d94778246ae`）の `/app/infrastructure` 内に対象ファイルが存在しないことを確認した。

ログは `tmp/docker-build-context-{red,green}.log`、`tmp/docker-context-unit-checks.log`、`tmp/runtime-build-deps-clean-build.log`。スキャンは `tmp/runtime-build-deps-clean.sarif.json` に記録する。混入時のスキャンは647パッケージ・134ルール（140検出）であり、除去後の結果と区別する。

除去後の通常イメージは292パッケージ・17脆弱パッケージ・48指摘（HIGH 1 / MEDIUM 1 / LOW 40 / UNSPECIFIED 6）、終了2。Terraformプロバイダー由来の指摘は検出されなくなったが、既存のOS指摘は残るためリリースの監査合格とはしない。スキャナーは一時アーカイブ削除の使用中警告を出したが、索引・SARIF出力は完了した。

## 適用範囲

変更はローカルのビルド除外ルールとCI検証。既存のTerraform state・設定ファイルの内容は変更・削除しない。AWS・共有DB・権限・費用への操作はない。Dockerignore変更をrevertするとローカルファイル混入が再発するため、復旧時もこの除外を維持する。
