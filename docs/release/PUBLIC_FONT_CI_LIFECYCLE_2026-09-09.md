# フォント配信テストのHTTP後処理修正

## 原因

コミット31f5c100のCI run34231517141は、lint-security・production-database・playwright・system成功、Unit / Integration失敗。GitHubの実ログで `tests/unit/test_public_fonts.py` の3件が失敗していることを確認した。

レスポンスの終了時にDjangoのrequest_finishedシグナルがDB接続の状態を確認する。先行DBテストの接続が残るpytest全体実行では、この通常の後処理がSimpleTestCaseのDBアクセス禁止と衝突していた。フォントのHTTP200取得・バイト内容の検査は成功しており、公開フォントビューのDBクエリが原因ではない。

## 修正と検証

- HTTPライフサイクルを扱うテストをDjangoのTestCaseへ変更し、テストDBの管理下で接続後処理を実行する。
- 匿名HTTP取得と応答終了を `assertNumQueries(0)` で囲み、フォント配信によるSQL実行がないことは引き続き検証する。シグナルの無効化や応答closeの省略はしない。
- 修正前、`python -m pytest accounts/test_character_factories_test.py tests/unit/test_public_fonts.py -q --create-db` でCIと同じ3件の失敗を再現。
- 修正後、上記2モジュールとtest_static_manifest・test_theme_fontsを同時実行し、9テスト・52サブテスト成功。既存のDjango 6非推奨警告9件あり。
- Black/isort・差分整合確認成功。変更はテストと文書のみで、AWSアプリの再デプロイ・DB移行・権限変更は不要。

2026-09-10追記：修正コミットdd0fe128のCI run34306247763は全5ジョブsuccessとGitHub APIで確認した。フォントテストの失敗は解消。正式公開全体の条件は別途未完了のためNo-Goを維持する。
