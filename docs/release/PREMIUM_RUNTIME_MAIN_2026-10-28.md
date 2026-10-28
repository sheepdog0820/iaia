# 運営コード・権限再照合の通常配布物検証（2026-10-28）

## 対象

[Draft PR #10](https://github.com/sheepdog0820/iaia/pull/10)の製品修正 `3884c83febfa87b97826047e1a4cf5e165bb2d77` を、`git archive` から通常Dockerfileで構築した。[運営コードの修正](PREMIUM_CODE_MAIN_FOLLOWUP_2026-10-28.md)と[再照合の修正](PREMIUM_RECONCILIATION_MAIN_2026-10-28.md)を含む。正式公開はNo-Goを維持し、Webの配備・実課金・実データ操作は未実施である。

- ローカルタグ: `tableno:release-candidate-3884c83f`
- イメージID: `sha256:3c8420b6c81fee07585d6f7515d921ab8976bab03d76701530982dfc7c5b44e8`
- Python 3.11.18 / Django 5.2.17、現在の固定依存。pip/pytestを追加していない。
- ECRへのpush・AWS反映はしていない。検証資料だけの後続コミットと、上記の製品修正SHAを区別する。

## 検証条件と結果

製品のbilling/admin/command、モデル、SDK/ICSの先行修正、固定依存、テスト等の計20ファイルがGit blobのSHA-256と一致した。実entrypoint `/entrypoint.sh` もGitの元ファイルと一致した。

UID10001、読み取り専用ファイルシステム、capabilityを全て外した通常イメージから、外部通信のないinternal network上の使い捨てPostgreSQL 18.3へ接続した。DB・cache・mail・保存先だけを合成設定ファイルで置き換え、製品ソースはbind mountしていない。fixtureの所有ラベル・container/network ID・非公開ポートを実行前に確認した。

通常イメージ内のDjango runnerで、次の7モジュールの **253テストが成功、省略なし**。

- 新規の運営コード使用・失効・再照合の3モジュール
- 既存の課金・課金同時処理・退会確認・有料機能一連の利用の4モジュール

実行前に前段のpytestで作成したfixture用 `test_goal_scratch` が存在したため、Djangoの `--noinput` でその使い捨てDBを再作成し、終了後に破棄した。接続先はこのgoal用のtmpfs DBだけであり、実ユーザーDBへ接続していない。Stripe参照はmock、メールはlocmemであり、実契約・決済・コード使用・外部通知の試験ではない。

## 証跡と未完了

Git管理外の専用worktree `tmp/` に、`premium-normal-image-build.log`、`premium-normal-runtime-pg.log`、`premium-normal-source-manifest.json`、`premium-committed-image.json` を保持する。接続用ファイルや値はGit・公開資料に含めない。

この結果は通常配布物に製品修正が入り、固定依存とPGで回帰試験が成立する証拠である。Webサービスの通常起動・readiness、実AWSのCheckout/Webhook/メール、性能・worker/beat・復旧、有料必須ゲートは別途必要。管理者の他の付与/失効・編集・削除経路、StripeClient/SDK/APIの後続、OS残指摘等も解決済みにしない。

先行PR #8/#9と本PRのmainマージは、各最終head・CI・差分を固定した承認が必要。共有DB0068、AWS反映、Secrets/IAM/OAuth、費用・外部送信・公開の承認には拡張しない。取り消しはrevert PRで可能だが、古い権限の上書きや監査の部分保存を再導入するため、それだけで公開可とはしない。
