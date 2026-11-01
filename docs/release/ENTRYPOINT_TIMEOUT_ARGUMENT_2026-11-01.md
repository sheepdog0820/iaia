# 起動時タイムアウト引数の保持（2026-11-01）

`docker/entrypoint.sh` の `DAPHNE_APPLICATION_CLOSE_TIMEOUT` 展開に引用符を付け、値をサーバーの一つの引数として渡す。既定10秒と整数値の設定は維持する。

旧scriptでは、例えば `17 --bind 127.0.0.1` が複数の引数に分割され、`*` が作業ディレクトリのファイル名へ展開された。運用側の環境値がサーバーの他のoptionやfilesystemの影響を受ける不具合であり、HTTP入力からの到達性や任意のshell code実行を実証したものではない。修正後はこれらをそのまま一つの値として渡し、既存のDaphne整数parserが不正な値を拒否する。

## 検証と自己レビュー

- syntheticな作業ディレクトリとargvを記録する偽のpythonだけで、実entrypointを `/bin/sh` から実行した。継承環境を渡さず、DB移行・collectstatic・開発ユーザー作成はfalse。アプリ/workerは起動しない。
- 未設定・整数17・空白を含む値・globの4ケースを追加した。旧scriptでは前2ケース成功、後2ケース失敗を確認してから修正し、修正後は4件すべて成功した。sourceの文字列一致だけを検査するテストではない。
- ローカル検査は既存の固定image `sha256:1e4d66ab3c788786e257a1445a3596eb83a22aeee142fb9ddf1e58655976cb09` に対象scriptとテストだけを明示的にread-only mountした。ネットワークなし、UID10001、root filesystem read-only、capability全drop、128MiB/0.25CPU。これは新しい通常配布物内の検証とは区別する。
- 初回fixtureは実行不可のtmpfsに偽pythonを配置したため、4件ともpermission deniedとなった。この失敗を製品のREDとは数えない。証拠を保持し、偽pythonだけを実行する検査用tmpfsの設定を修正して、上記2件の製品不具合を再現した。各コンテナは同じIDの終了・restart0・削除を確認した。
- 実Daphneのparser単体でも、既定値10・整数17の受理と、上記不正値2件のexit2を確認した。ASGIアプリやサーバーは起動していない。
- 固定Linux依存に対象sourceを明示的にread-only mountした関連37試験は省略0で成功した。Windowsではentrypoint関連26件成功・POSIX用4件省略。一方、既存Windows環境のTwisted importでサーバーログ試験の収集とparser単体の実行が失敗し、Linux側で両方を検証した。Windowsの当該試験を成功と数えない。
- 変更は引用符の追加だけで、新しい範囲制限・料金・権限・表示文言は加えない。UI変更はない。syntax・差分・文字コード・関連テスト・formatterとlintを確認する。全体CIと通常配布物の結果は、固定した最終headに結び付けた別の記録で管理する。
- テストファイルの追加Bandit検査はLOW2（subprocess import/実行）・MEDIUM1（期待argvのbind文字列）だった。固定の `/bin/sh` と本repoのentrypoint、テスト定数と継承しない環境だけを使い、実socketを開かないfixtureとして精査した。指摘の除外・nosecは追加せず、製品コードのBandit結果とは区別する。

ローカル証拠は本worktreeの `tmp/entrypoint-argument-{red,red-argv,green}-20261101/` と `tmp/entrypoint-related-linux-20261101/`。実parserの4ケースは後者の `test.stdout.log` に保持する。検証した修正後entrypointのSHA256は `39872c116a38234eaf53d6334b221a2d52d365768eaa91ed9c19aacf17233146`。

## 既存のOS調査との関係と残作業

[OS53追加記録](RUNTIME_OS53_ADDITIONAL_SCOPE_2026-11-01.md)は、旧entrypoint SHA `0e5d175e8a6678f0c85b94dbb41479fcc952af25cc440c2f3eda2ada86cd1c01` を含む固定候補・現行imageを調査した履歴である。本修正でその未引用展開をなくすが、dashのbuild条件・依存内部のshell利用・glibc/native経路や全53件の判定を完了とはしない。OSパッケージ更新、CVE解消、ignore/VEX、リスク受容の根拠へ流用しない。

AWS/共有DB/実データ・Secrets/IAM・実Stripe・通知・費用への変更はない。main統合・AWS反映は承認対象のままで、現行Web定義55の旧imageは更新していない。元25条件と正式公開 **No-Go** を維持する。未配備の修正はコードrevertで戻せるが、引数分割とglobの問題も戻る。
