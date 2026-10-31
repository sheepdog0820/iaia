# HTTP Host制限と内部ヘルスチェック（2026-10-31）

## 問題と方針

10月31日10:08/10:15 JSTに読み取ったECS定義55は`ALLOWED_HOSTS=*`、CSRF/公開URLは`https://stg.tableno.jp`だった。10:46 JSTのALB宣言ではHTTPSのdefault転送だけがあり、Webの8000番はALBのSGからだけ許可されていた。Secretsを含む実効設定・実経路のheader処理は未取得で、稼働環境への攻撃や実データの取得は行っていない。

隔離した本番設定では、全host許可と継承した`USE_X_FORWARDED_HOST=True`の組み合わせにより、実Hostが許可domainでも任意の転送Hostから絶対URLが作られた。これは合成header/設定による再現で、稼働AWSでの悪用を実証したものではない。[Djangoの設定説明](https://docs.djangoproject.com/en/5.2/ref/settings/#allowed-hosts)は、全体wildcardでは独自のHost検証を要求し、転送Hostはそれを設定するproxyがある場合だけ使用する方針である。[ALBの自動付与headerの説明](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html)も照合し、今回のAWS向け本番設定では転送Hostへの依存を除く。

単に明示domainへ絞ると、内部IPをHostにするHTTP health probeがHTTPS転送やCommonMiddlewareのHost検証で失敗する。SecurityMiddlewareだけのprototypeでSSL例外を調べた後、CommonMiddlewareも`get_host()`を呼ぶことを実ソースで確認し、全middlewareを通る回帰で両立を検証する方針にした。ALBへ優先度の高い転送ruleを追加する方法は、既存の夜間scheduleがdefault actionだけを503へ切り替える構成と整合しないため、この変更では採用しない。[ALBのrule評価順序](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-rules.html)と既存Terraformからの影響推論であり、AWSで新ruleを試したものではない。

## 実装と利用者への影響

- 本番/共有開発の`settings_production`は、全体wildcard `*`と空のHost一覧を起動時に拒否する。明示domain/aliasを使い、転送Hostの代わりに実Hostを検査する。ローカル開発のproxy設定は変更しない。
- `ProductionHostMiddleware`をSecurity/WhiteNoiseより前へ置き、公開HTTPS・通常のHTTP・静的ファイルを含む他の要求は、既存のHost検証とmiddlewareへ通す。許可外Hostからの外部redirectを作らず、正しい公開HostへのHTTP→HTTPS転送とHSTSは維持する。
- HTTPのGET/HEADで、`/health/live`・`/health/ready`のslash有無だけは既存の安全なhealth viewを直接呼ぶ。prefixに似せたpathや他methodへ例外を広げない。正常200/失敗503、依存先名と固定`error`を維持し、HEADの本文は空、Content-Lengthは表現の長さを保持する。health応答にno-store/nosniffを付ける。公開HTTPS healthは通常経路を通す。
- 開発/オフラインのTerraform設定例から`*`を除き、既存のdomain既定値を使う。mock planのHost検査を追加し、CIでも両設定例を読む。ALB・IAM・scheduler・DBの実リソースは変更しない。

既存ECS55の宣言は`*`のため、このguardを含むimageを配備する際は、明示domain設定をそろえる必要がある。旧設定のまま配備して稼働を継続できるという変更ではない。必要domain、実効header、対象task定義・image、背景処理の設定ポインターと復旧手順を固定した反映案を作り、別途承認を確認する。

## 検証と自己レビュー

本番設定の全middlewareを使う回帰を先に追加し、修正前は16失敗・2成功、修正後は6件・17 subtests成功となった。内部HTTP GET/HEADの8条件、503の情報保護、公開HTTPS/HSTS、Hostと転送Hostの境界、通常redirect、似たpath/別methodを確認した。製品の認証・Host検証・依存検査を無効化していない。

関連SQLite/本番設定の隔離PG18.3は最終各63件・50 subtests成功、省略0。PG CIと同じ親設定では、既存fixtureがSMTP/SSL設定を継承して2失敗・60成功になったため、親設定が混ざる回帰を追加した。既定cache/SSL/SMTPのfixtureを分離し、明示overrideは維持する。`check --deploy`の試験もSSL転送を明示して、警告なしという期待を弱めず再検証した。PG CIへ設定/healthの両モジュールも追加した。

子プロセスを含むcoverageでは新middlewareの18実行文・6分岐をすべて実行し、除外0だった。追加した本番設定の実行文も計測済みで、設定ファイル全体やプロジェクト全体の100%を意味しない。最終fixture修正後は、同じ製品コードに対する上記63件を両DBで再実行した。

Terraform1.15.6の全providerをmockにしたplanでは、旧wildcard入力が9成功・1失敗、更新した2設定例は各10成功・0失敗。初回のfilter指定は0件だったため合格とせず、filterなしで全件を実行した。fmtは`.example`を直接受け付けないため、同じbytesの`.tfvars`コピーを含む5ファイルで成功を確認した。初回の失敗・未実行ログも保持し、AWS呼び出し・実backend・applyは使っていない。

Host境界・middleware順序・HTTP例外の範囲・親環境の混入・夜間保守との整合を自己レビューした。固定commitの通常配布物で、静的ファイル、実HTTP/WS、実driver障害、起動拒否と最終CIを追加確認し、結果を候補PRへ追記する。親候補の成功は今回の配布物検証へ流用しない。

## 承認・復旧・残課題

PR #46の`a6f88882`、PR #47の`8ff325c8`は変更せず、別ブランチで準備する。mainへのマージやAWS反映の承認はまだなく、共有DB/実データ・IAM/Secrets/OAuth・実Stripe・外部通知・費用は変更しない。モデル/移行・依存lock・新たな画面文言は変更しない。

コードの復旧はrevert PRだが、元のHost信頼と内部healthの問題が戻る。親PR #47の例外本文保護は維持され、DB切戻しは不要。実配備後の復旧はtask/configをそろえた承認済み手順が必要で、今回実行したという意味ではない。実効設定・実環境反映、OS/native52指摘等の残課題と、F/B/I/Q/O全25条件を満たすまでの正式公開No-Goを維持する。

証拠はGit管理外の`tmp/host-boundary-*.log`、`tmp/host-boundary-coverage-sqlite-final/coverage.json`、`tmp/host-boundary-terraform-proof-20261031.json`に保持する。合成fixtureの環境ファイルはcommitしない。
