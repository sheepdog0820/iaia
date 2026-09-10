# Google再試行修正の配布物検証と開発AWS反映

## 対象

コード `595a390acae141e4f4a344a25697a976782dfb4f`。Google連携の再試行受付時に権限を確認する修正と、Sheetsの再試行で最初の対象範囲を維持する修正を含む。

- [再試行の権限確認](GOOGLE_RETRY_AUTHORIZATION_2026-09-10.md)
- [Sheetsの対象範囲維持](GOOGLE_SHEETS_RETRY_TARGETS_2026-09-10.md)

クリーンなgit archiveと通常Dockerfileから `aws-pre-595a390a` を作成。ローカルimage IDは `sha256:40d4bc169336f31286b33fb10d54f4eb24e2fa04d7174dac71788d676975395a`。

## 配布物の確認結果

アプリソースを差し替えず、イメージに含まれる関連27テストが成功。別途、PostgreSQL18.3・Redis7と通常起動のWebでHTTP19ケースが成功した。Webは0.25CPU・512MiB、外部通信を遮断した専用ネットワーク上で動作させた。

HTTP確認では、空/不正な対象指定11種類、所有者によるプレビュー制限、対象省略のプレビュー、選択出力の実キュー投入、未認証拒否、連携OFFの再試行拒否、対象範囲を維持する再試行2回、対象が不明な旧形式ジョブの拒否を検証した。再試行は実RedisメッセージをデコードしてジョブIDと出力行の対象IDも照合した。

workerは起動せず、Google資格情報は与えていない。外部書き込み0件。試験コンテナ3個とネットワークは削除完了し、DB/キューも破棄した。証跡はGit管理外の `tmp/retry-runtime-595a390a/`。

## 反映状況

[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34441714918)・[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34441718759)は全6ジョブ成功。承認済みの開発環境への通常アプリ更新として、Web定義46を複製してイメージだけを変更した定義47へ反映した。

digestは `sha256:ec7d36ca44210f7db5fd71d1267c8e892e6ce21668e4bff00b974e3f90c3c099`。14:56 JSTの確認で、定義47・希望1/稼働1、rollout COMPLETED。タスク `a055172f496c4f789d0b23f322287a35` はRUNNING/HEALTHYで、digestが一致。readinessはdatabase/cacheともok、起動時ログ11件にERROR/Tracebackなし。

Chromeで指定アカウントのログイン維持、ホームの年間26h・43セッション表示を確認。Google認可は保存済みのまま、Calendar/Sheetsの切替はともにOFFを維持。Googleへの実送信は行っていない。

DB移行・静的ファイル変更がないためmigrate/collectstatic・CloudFront無効化は実施不要。権限・Secrets・共有業務データ・常設Redis/workerは変更していない。背景透過定義3を含め、イメージ以外の設定は維持した。

復旧先は定義46、digest `sha256:eb03de941eccbf6432e331614d6aa4021cbb44120e09bf627a35a42c22f99aab`。サービスを46へ戻して正常性を確認できるが、再試行時の権限受付・対象範囲の不備も戻る。証跡はGit管理外の `tmp/aws-pre-595a390a-deploy/`。

本資料の後続文書コミットのCIは上記コードの成功と区別する。新規mainマージ・本番反映は未実施。Google実同期と常設基盤、Stripe、事業者情報、全体性能・復旧、OS指摘等が残るため、正式公開はNo-Goを維持する。
