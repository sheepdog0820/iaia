# main基準のアカウント復旧・作成入口候補

## 対象と分離

2026-10-09、GitHub mainの読み取りで `8567f49f8d411bad7f732afaeebad85357eeca09` を確認し、
そのcommitから `codex/main-account-recovery-20261009` を作成した。
先行の復旧 `ff7d49ec`・版選択 `b7e72b78` の変更を限定して取り込み、
Google/Stripe候補の履歴全体や設定ファイル全体をマージしない。

- 共通TemplateViewクラスの変更をやめ、group/statistics/版未指定作成の各URLだけをlogin_requiredで保護する。
- 暗黙に保護されていたcalendarを明示的に保護する。
- 既存の24時間案内に合わせて `PASSWORD_RESET_TIMEOUT=86400` を設定する。
  新規・既発行リンクの両方に、配備後の検査時点で適用される。
- 送信完了画面の閉じタグ誤記を修正し、表示文言/デザインは変えない。
- 版未指定作成の欠落テンプレートを復元せず、既存6版/7版作成・一覧への日本語選択画面へ接続する。
  認証を維持し、GET/HEADやリンク移動では保存せず、POSTは405。

accounts/schedules URL、送信完了/作成入口template、新規2 integration test、永続E2Eの計7 filesは、
先行 `b7e72b78` とstaged内容を照合し、不一致0を確認した。settings差分は期限の2行のみ。
production設定testは期限assertと、検査subprocessが親の開発環境・設定module・env fileを
引き継がないための3項目および回帰2件のみを移す。
Stripe API版/制限付きkey対応、Google beat配送、SDK log変更等を含めない。
依存lock/Docker/entrypoint/static/全migration/インフラ/CI設定/業務viewの変更はない。

## main基準での再検証

修正前の新規17 integration testsは9 failure/5 error（subcaseを含む）で、
mainにも期限不整合・公開画面へのlogin波及・作成template欠落があることを確認した。
productionの期限/検査環境の3件もすべて失敗した。
修正後の局所20件は成功（13.315秒）。
認証・ログイン障害・作成静的UI・production設定・法務表示・文書を含む関連186件が成功
（72.241秒、省略0）。先行候補の194件をこのmain候補の件数として流用しない。

新規作成test76実行文/6分岐先、復旧test124文/8分岐先は100%/除外0。
production設定test176文/4分岐先、accounts URL28文/schedules URL22文も全実行。
設定の新規期限文を実行し、production値は独立subprocessで照合した。
settings全体は70%で、全機能100%とは扱わない。
TemplateViewの使用箇所と派生classも確認し、他の非公開画面のURL decorator/
LoginRequiredMixin/dispatchでの認証を保持することをsource reviewした。
10非公開URLは匿名302/認証済み200、公開home/メール確認/復旧完了は匿名200を検査する。

ローカルサーバースキルの既存実DBを使う標準起動を避け、使い捨てStaticLiveServerTestCaseで実施。
作成入口は試験だけDEBUG=True、永続Playwrightの3browser × 1280/390pxの6ケース成功
（29.4秒、retry/skip/flaky0）。実CSRF開発ログイン、両版/一覧、Enter、戻る/reload、
横溢れなし・pageerror0、前後API内容不変とDB保存0を確認した。
復旧はDEBUG=False/合成の検証済み6利用者で、同じ3browser × 2幅の6ケース成功。
locmem mailの実リンクとCSRF formを通し、期限案内/ホーム、password変更/完了、
実ログインform（合成メールアドレス/password）、非公開calendarの認証前302/認証後200を確認した。
各case form POST3/pageerror0/API応答mock0、DB上の新password一致/旧password不一致も確認。
mobileでは実利用者と同じ「メールでログイン」を開いてからフォーム操作する。
12case全体のDjango runnerは2テスト成功（62.256秒）。390px送信完了の実画像も目視確認した。
外部origin/未mock Requestsを禁止し、実Google/Stripe/メール受信箱には接続しない。
Node所有プロセス残0、Django server/合成DB/mediaは終了時に破棄。
loopback接続終了時のBroken pipe/Node色設定警告を保持し、成功判定はHTTP/画面/DBと独立に照合する。

変更6 PythonのBlack/isort/Flake8、製品3 Pythonと新規test2のBandit指摘0/解析エラー0を確認した。
既存production testの合成資格情報等を今回の「Bandit0」の対象へ拡張しない。
UTF-8/LFは12 text filesで成功。日本語UI・staged差分を確認し、範囲内に残る指摘なし。
最終文書39件成功（0.035秒）、判定表/候補記録の相対リンク152件に欠落なし。
生証拠は `D:/tmp/codex-main-account-recovery-20261009`。
初回RED/局所GREENは先行の `D:/tmp/codex-character-create-entry-20261009/main-*.log` に保持。
既存Windows Twisted import不具合は環境を変更せず別課題として残る。
新しい通常配布image/そのOS再監査/最終SHAの全CI/稼働AWSでの操作は未検証。
先行Google通常imageのHIGH2や検証成功を、この候補の最新image判定へ流用しない。

## AWS読み取りと反映準備

10:21〜10:22 JST、profile `tableno-pre`/account `083773015316` を確認した。
ECS `tableno-aws-pre` は定義54、desired/running=1、pending=0、rollout COMPLETED。
実タスク/コンテナはRUNNING/HEALTHY、定義の固定imageと実行digestは一致する。
復旧先は同じ定義54/image `sha256:adafc0705ded3dabf2a9d2223a5c460b48ff00b2c949f221a4edef3eedee695e`。
WebはCPU256/512MiB、RUN_MIGRATIONS/RUN_COLLECTSTATIC=false、購入開始Falseを保持する。
readinessはstatus/database/cacheがすべてok（応答timestamp `2026-10-09T01:21:46.113113+00:00`）。
実メール/初回登録/退会/共有DBのpending migration/全セキュリティ状態の合格を意味しない。

この候補のCI全6成功と固定配布物検証を揃えた後、候補SHA・image・影響・復旧手順を示して
限定したmainマージ/開発AWS反映の承認を確認する。既存favicon承認へ追加しない。
想定操作は通常のmainマージと、既存Webサービスのimageだけを変える定義登録・更新。
既存容量/role/Secrets/env/networkを保持し、RUN_MIGRATIONS=falseを維持する。
schema/staticの差分がなく新static参照もないため、この限定修正では共有DB migration/
collectstatic/CloudFront invalidationは予定しない。配布物照合で差が出たら計画を再確認する。
反映前にmain/稼働定義/digestを再確認し、配備後はreadiness・実稼働版・匿名完了画面・
版選択/認証拒否を確認する。実メール配送や実ユーザーpassword変更は別の対象承認が必要。
問題時は確認済み定義54へ戻す。24時間を過ぎた既発行リンクへの期限変更も承認案に明記する。

今回はAWS/共有DB・実データ/Secrets/IAM/OAuth/課金・容量・外部通知の変更なし。
元checkoutの13件の別作業と先行候補ブランチを保持する。
正式公開No-Goを維持し、Google認可/運用、課金/メール、外部連携、性能/全体復旧、
運営条件とOS監査などの必須残タスクは継続する。

## 同日後続の通常配布物検証

上記「新しい通常配布image/OS再監査は未検証」は候補作成時点の記録。
`dbe8fca1` の[固定image検証](MAIN_ACCOUNT_RECOVERY_RUNTIME_2026-10-09.md)で
archiveの選択662ファイル/lock111依存の一致、Linux154件/隔離PG17件、
通常entrypointと実HTTP15要求、deploy checkの成功を確認した。
新imageの全パッケージ監査は38指摘（HIGH2/MEDIUM1/LOW35、Python0/native終了2）で未合格。
候補CI全6成功・main/AWS反映・実メール等は未完了、公開No-Goを維持する。

## 同日後続の退会通知とブラウザー検査

記録commit `b790f758` のCIは5ジョブ成功、Playwrightは6件失敗/222件成功。
ログアウト/退会後のhomeへの遷移をlogin画面とする古い検査を修正する過程で、
homeが退会成功通知を描画しない実不具合を発見した。
[後続の通知修正と検証記録](HOME_ACCOUNT_EXIT_FEEDBACK_2026-10-09.md)を参照する。
今回home templateの製品差分があるため、先行dbe8fca1の通常image検証を
後続候補の配布物検証として扱わない。反映承認と正式公開No-Goは維持する。
