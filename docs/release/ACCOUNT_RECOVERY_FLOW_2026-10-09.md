# アカウント復旧: 有効期限・公開画面・URL認証境界

後続の[版未指定作成URLの復旧](CHARACTER_CREATE_ENTRY_2026-10-09.md)で、以下の検査時点に
残したテンプレート欠落を修正し、認証済み10 URLへ検査を拡張した。main/AWS未反映は継続する。

## 修正と利用者への影響

2026-10-09、基準 `7feff647d11107bb3c2186720a58f7f77ac8160e`。
F01のアカウント復旧を実URLで検査し、次の製品不整合を修正した。

- 復旧リンクの案内は24時間だが、設定が未指定で実際にはDjango既定72時間だった。
  `PASSWORD_RESET_TIMEOUT=86400` を共通設定に明示し、production設定への継承も確認する。
  既存の24時間という案内を変更せず、新規・既発行のリンクの検査に適用する。
- accounts URL設定が共通の `TemplateView` 自体を3回login_requiredで装飾し、
  復旧完了/メール確認案内/ホーム等にもログイン必須が波及していた。
  各URLの `as_view()` の戻り値だけを保護し、共通クラスを変更しない。
  暗黙に保護されていたcalendar画面には明示的なlogin_requiredを加え、認証条件を維持する。
- ログイン制限修正後の送信完了画面は、末尾の `{% endblock %>` 誤記でTemplateSyntaxErrorになった。
  閉じタグだけを修正し、表示内容・デザイン・既存の日本語案内は維持する。

main `8567f49f8d411bad7f732afaeebad85357eeca09` のsourceにも共通クラス装飾と閉じタグ誤記があることを確認した。
今回の隔離再現を稼働AWSでの再現結果とは扱わない。main/AWSには未反映。

## 回帰検証

新規11テストは、Django Client→実CustomPasswordResetForm→locmem mailの実リンク→
実allauth token検査/パスワード保存→実CustomLoginViewまでを通す。
HTTP/provider・token照合・DBの保存をmockしない。境界検査ではtoken generatorの時計だけを固定する。
合成の検証済み利用者/使い捨てSQLite、メールはメモリ内のみ、未mock Requestsは禁止。

- 24時間ちょうどのリンクは使用可能、24時間1秒後は拒否。フォームを開いた後の期限切れPOSTも拒否。
- 新パスワードで復旧し、旧パスワード・使用済みリンク・tokenを隠した旧フォームURLは無効。
  既存ログインsessionは次の認証必須アクセスで失効し、新パスワードではログインできる。
- 入力不一致では変更せず、有効な再送で復旧可能。改変tokenとメール変更後の旧リンクは拒否。
- 未ログインでも復旧完了/メール確認案内/ホームは200。
  10個の非公開URLは未ログイン302、現行の9画面は認証済み200。
- 旧汎用 `character_create` URLは匿名の認証制限だけを確認。
  認証済みでは現在存在しない `accounts/character_sheet.html` 参照で500になる別課題を発見した。
  テスト内に対象の限界を明記し、旧画面の独断復元・新しい転送先の決定は今回行わない。

初回8失敗にはfixtureのrate-limit設定/URL期待の誤りを含む。
fixtureを直した9件の検査は、設定・期限・公開完了画面の6失敗を示した。
公開画面だけの追加1テストも3 subcaseで失敗。製品修正後は11件成功（9.783秒）。
初回広域47件の4エラーは、追加の閉じタグ/旧作成画面の欠落/調査runnerのRedis環境引継ぎを含む。
runnerから不要なRedis指定を除き、現行画面と旧URLの検証範囲を明記して再検証した。

Windowsの関連143件は142成功/1 importエラー。
同環境で `import twisted.logger` だけでも同じ循環importが失敗し、既存venvは変更しない。
該当moduleを分離した関連142件は成功（75.270秒、省略0）。
新規module126実行文/10分岐先は100%/除外0。accounts/schedules URL moduleの全実行文と
新規timeout設定文を実行した。settings全体の100%を主張せず、production値は独立subprocessでも照合する。

## 実ブラウザー・隔離配布環境

ローカルserver用スキルの既存DBを使う標準起動は避け、Djangoの使い捨てStaticLiveServerTestCaseを使った。
新しい合成検証済み利用者6人を作り、chromium/firefox/webkit×1280/390pxの6ケースを実行。
実CSRF付きフォームで復旧要求→24時間案内→ホーム、メールから抽出した実リンクでパスワード変更→
完了→実ログインを確認した。匿名calendarは302、復旧後の認証済みcalendarは200。
API応答mock0、各ケース実フォームPOST3、pageerror0。6人の新password hashと旧password不一致をDBでも確認。
全6ケース成功（36.590秒）。外部originはブラウザーで遮断し、実メール受信・Google/Stripeには接続しない。
初回の曖昧なbutton locator、次回のメール名に似た合成password拒否はfixture失敗として保持し、
locatorと合成値を修正した。製品validator・タイムアウト・再試行条件は緩めていない。
390px送信完了画面の実スクリーンショットを確認し、案内/2遷移ボタンの表示を確認した。
Node browser/contextはfinallyで閉じ、LiveServer/DB/mediaはDjango runnerの終了で破棄する。

Linux確認は、先行679固定imageに変更source/test/runnerをread-only mountする追加試験で、
新しい配布imageのbuild/一致・全リリース検証ではない。network none/nonroot10001/read-only/cap-drop ALL/
no-new-privileges、512MiB/1CPU、専用tmpfs256MiB、SQLite memory/locmem mailで行う。
初回149件の文書検査1件は配布imageに含めないAGENTS.md参照でエラーとなったため、
文書はhostの39件で確認し、Linux側はアプリ/設定/アクセスログの関連110件を対象にする。
最終110件成功（59.686秒、省略0/終了0/OOM false）。変更7 source/testのhost hashは前後一致。
これはsource mount追加試験で、配布image全体のhash一致や新image合格とは扱わない。
停止済み2containerの正確なID/name/label/image/mount/stateを検査して撤去し、所有container残0。
専用tmpfsは撤去し、先行image・生証拠・元の別作業は保持する。

証拠/script/スクリーンショットは `D:/tmp/codex-account-recovery-20261009`。
先行fixture失敗の生ログは `D:/tmp/codex-google-target-unknown-deletion-20261009` にも保持する。

## 品質・残作業・復旧

変更5 PythonのBlack/isort/Flake8を確認。変更製品3 Pythonと新規testのBanditは指摘0/解析エラー0。
追加で既存production設定test全体を走査した際は26 LOWを報告した（既存の合成資格情報/subprocess等）。
その全体走査を指摘0とは説明せず、今回はtestの既存fixtureやscanner設定を変更しない。
文書39テストも成功（0.036秒）。相対リンク・差分・UTF-8/LF・staged整合を確認する。
テンプレートは閉じタグだけの変更で、既存の装飾用英語引用を含む表示文言は変更なし。

実SMTP/受信箱、AWSの初回登録・復旧・退会、全画面/実機、旧作成URLの整理は残る。
OS HIGH2・Google認可/運用・課金/性能/復旧等も未完了で、正式公開No-Goを維持する。
mainへのマージ/AWS反映、共有DB・実データ、Secrets/IAM、課金・容量・外部通知・承認範囲の変更なし。
source候補は通常revertで戻せる。配備時には修正対象・既発行リンクへの期限適用・復旧手順を示して承認を確認する。
