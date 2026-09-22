# 外部連携の失敗履歴と再試行案内

対象アプリ候補: `c0a2b2773fa7a84fdfbd7a645a9f2acbfca10d83`。

## 修正内容

- Google Calendar同期、Google Sheets出力、Discord通知でbrokerへ登録できなかった場合、失敗履歴へ固定の日本語案内を保存する。
- Google Calendarの新規同期・失敗ジョブ再試行、Discord通知再送で、`queued=false`を成功扱いせず警告する。HTTP 400等の再試行拒否も画面に表示し、利用者が再連携・設定確認・再試行を選べるようにする。
- 再試行受付後に一覧の再読込だけ失敗した場合、受付結果を失敗へ上書きせず、ページ再読込を案内する。
- 過去に保存された英語のbroker停止メッセージは表示時に日本語へ置き換える。
- 過去の失敗履歴にURLを含む外部例外が残っている場合、DBを書き換えず、API応答時にサービス別の固定案内へマスクする。
- Google/DiscordのHTTP例外本文は失敗履歴、Celeryの再試行例外、例外連鎖へ保存しない。Discord Webhook URL、Google Sheetsの出力先ID、上流診断を含み得る例外文字列を、サービス別の固定メッセージへ置き換えてから再試行する。
- 再試行APIの利用者向けエラーを日本語化する。権限判定、失敗状態だけを再試行できる制約、Discord通知設定、Google連携scopeの判定は維持する。

DBマイグレーション、外部API scope、Secrets、IAM、送信先、料金は変更していない。

## TDDとローカル検証

- RED: Google Calendar再試行でbroker登録に失敗しても画面が「再試行ジョブを作成しました」と成功表示すること、保存エラーが英語のままであることを確認した。
- GREEN: Google/Discordのbroker停止、再試行拒否、再試行受付後の一覧更新失敗、固定メッセージによる外部例外非露出を回帰テストへ追加した。
- 関連バックエンド69件をSQLiteで実行し成功した。対象は外部連携API、非同期ジョブ、Discord、Calendar/Sheets配送、ジョブ権限である。
- `tests/e2e/flows/integrations.spec.ts` は外部通信を遮断した使い捨てSQLite環境でChromium、Firefox、WebKitの計6件が成功した。新規確認には失敗履歴表示、broker停止警告、再試行拒否、受付後の一覧更新失敗を含む。
- Black、isort、Flake8、Bandit、差分・UTF-8/LF検査が対象差分で成功した。

## 固定候補のCIと配布イメージ

- [Django CI run 35684257213](https://github.com/sheepdog0820/iaia/actions/runs/35684257213)でUnit / Integration、Playwright、production-database、system、lint-security、infrastructureの全6ジョブが成功した。
- 実Dockerfileと固定依存から`tableno:integration-retry-c0a2b277`を作成した。イメージIDは`sha256:d02d475eb25c911045f78d8e781e69bc77ef6c62217bfbaa704270844211d88a`。
- 同イメージを外部通信なしで実行し、関連バックエンド69件が成功した。
- 専用internalネットワーク、PostgreSQL 18.3のtmpfs、Redis 7で通常entrypointを実行した。全migration、静的227件の収集と617件の後処理、Daphne起動、`/health/ready/`のdatabase/cache `ok`、`migrate --check`を確認した。検証用app/DB/Redisコンテナとネットワークは削除した。

初回のreadinessラッパーは、PowerShellの`Invoke-WebRequest`が同時刻に`curl`で取得できたHTTP 200を検知できず失敗終了した。コンテナは自動削除し、HTTP判定を`curl`へ変更した再実行で上記の全項目を終了0として確認した。

## 限界と公開判断

Google/Discord応答はmockであり、実資格情報、実API障害、実Redis/Celery worker、AWS、共有DBを使った結果ではない。Google Calendar API障害を模擬したローカルの失敗保持・再試行導線は確認したが、Google Sheets大規模出力、実Google/Discordの失敗復旧、外部連携全体の復旧条件は未完了である。

main・AWSへは未反映で、I04〜I06と正式公開No-Goを維持する。復旧はアプリ候補コミットの通常revertで行えるが、broker停止の成功誤表示と外部例外文字列の保存が再導入される。
