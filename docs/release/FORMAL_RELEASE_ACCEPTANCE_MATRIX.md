# 有料プラン・外部連携を含む正式公開の受け入れ条件

## 現在の公開判断（2026-10-06）

後続a266dd12の[Google通常配布物検証](GOOGLE_RUNTIME_A266DD12_2026-10-06.md)で、固定archiveから構築した通常Docker imageの693選定source/assets・entrypoint一致、111 packages/先行依存10 layers一致を確認した。source overlayなし・外部通信不可の隔離PGでGoogle110件（実loopback HTTP8ケース/refresh認可競合を含む）、設定/ログ保護70件が成功・省略0。文書39件は含まず、実Google・常設Celery・今回Web/U2NET/OS再監査・AWS成功へ拡張しない。候補CIは4成功/2実行中、使い捨てDB/containerを削除し証跡を保持。main/AWS追加反映・schema/Secrets/課金/容量変更・承認拡張なし、HIGH3等の未達条件と正式公開No-Goを維持する。

後続の[Google Calendar予定の照合・条件付き書き込み](GOOGLE_CALENDAR_EVENT_GUARD_2026-10-06.md)で、保存済み外部IDでも遠隔のID/既存private情報を確認し、4変更経路へ強いETag/If-Matchを追加する。412の自動再試行を止め、固定日本語案内・削除済み応答の書き込みなし完了・更新応答ID照合・URL境界を確認した。新規13件117 subtest、実Requests＋loopbackの8ケースを含む。最終PG149成功/省略0・SQLite145成功/PG専用4省略（文書39含む）、本体差分40文16分岐/新規293文66分岐100%、PG CI対象追加。メタデータは認証証明ではなく接続先別の永続ID管理・古い予定移行/実GoogleのETag・原子的取消等は残る。main/AWS追加反映・schema/Secrets/課金/容量変更・承認拡張なし、HIGH3未解消・正式公開No-Goを維持する。

後続の[Google待機ジョブの接続先固定](GOOGLE_QUEUED_CONNECTION_2026-10-06.md)で、作成時の接続先を用途別HMACとして3生成経路で保存し、待機中の変更・旧/不正ジョブをtoken取得前に停止する。認証情報/UIDそのものの追加保存・schema/鍵変更なし。通常access更新・設定保存・接続変更後の新ジョブ・ローカルプレビューを維持し、remote欠落tokenを日本語400で拒否する。修正前8件96 failure/0 error、レビューで旧ジョブの説明を訂正し、最終PG116成功/省略0、SQLite110成功/PG専用6省略、差分本体31文14分岐・新規176文38分岐100%、PG CI対象追加。原子的取消・旧worker混在・遠隔token所有者/失効・接続先別外部ID/解除UI・実Google/AWS/全CIは未解消/未証明。隔離DB/container/volume削除・記録保持、main/AWS追加反映・Secrets/課金/容量変更・承認拡張なし、HIGH3未解消・正式公開No-Goを維持する。

後続の[Google資格情報の削除・差し替えガード](GOOGLE_CREDENTIAL_GUARD_2026-10-06.md)で、連携行を残したtoken/account変更・実allauth解除後の追加送信を再現・修正。取得前の行/account/app/UIDとHTTP直前の最新token/返されたaccess値を照合し、追加送信/retryを止める。固定日本語エラー・部分進捗・通常refresh/設定保存/最終受理後の成功を維持する。最終PG106成功/省略0、SQLite100成功/PG専用6省略、差分本体15文6分岐・新規78文28分岐100%、PG CI対象追加。キュー時点の固定・チェック直後の競合/原子的取消・解除UI・接続先別外部ID・実Google/AWS/全CIは未証明/未解消。隔離DB/container/volume削除・記録保持、main/AWS追加反映・schema/Secrets/課金/容量変更・承認拡張なし、HIGH3未解消・正式公開No-Goを維持する。

後続の[Google処理途中の再接続検知](GOOGLE_CONNECTION_GUARD_2026-10-06.md)で、scope/有効フラグを保った再接続後も古いtokenで送信が続く問題を27 subtest失敗として再現。開始時の連携ID/接続日時とHTTP直前のDB値を照合し、次の送信/retryを止め、Sheetsの部分進捗を保持する。レビューで設定保存による誤停止2例も再現・修正し、通常更新/設定保存/最終受理後の成功を維持する。最終PG101成功/省略0、SQLite97成功/PG専用4省略、差分本体34文14分岐・新規210文38分岐100%、PG CIへ新規module追加。キュー待ち中の変更・token/accountだけの変更/解除・原子的な取消・実Google/外部IDの接続先別管理/AWS/全CIは未解消/未証明。隔離DB/コンテナ/volume削除・記録保持、main/AWS追加反映・schema/Secrets/課金/容量変更・承認拡張なし、HIGH3未解消・正式公開No-Goを維持する。

後続の[Google Sheets出力先のURL境界](GOOGLE_SHEETS_DESTINATION_2026-10-06.md)で、記号によるfragment/query/path分断・不正ID受理・先行token更新を新規34 failureとして再現し、path要素の個別エンコードとAPI/workerの検証へ修正。ID未指定のプレビュー・17列/100行分割/RAW/認可/再試行snapshotを維持する。最終SQLite90成功/PG専用4省略、差分本体48文6分岐・新規116文10分岐100%。実Requestsの生成後URLを6組×2チャンク確認したが、Google側の受理/書き込み・今回PG/ブラウザー/AWS/全CIは未証明。main/AWS追加反映・schema/Secrets/課金/容量変更・承認拡張なし、元worktreeの別作業を保持・HIGH3未解消・正式公開No-Goを維持する。

後続の[Googleトークン更新の整合性](GOOGLE_REFRESH_INTEGRITY_2026-10-06.md)で、再接続情報の上書き/解除後の保存エラー/並列更新の2成功を隔離PGで7 failure/5 errorとして再現。初案68件成功後も、2 UPDATEの実Lock待機を強制した追加試験で競合1 failureを確認し、比較条件をUPDATE対象WHEREに保持する形へ修正した。最終PG69成功/省略0、SQLite65成功/PG専用4省略、更新モジュール36文12分岐・新規215文20分岐100%。競合では接続情報を保持し、両workerは固定日本語エラーで終了・外部送信なし。新規2 moduleをPG CIへ追加したが、実Googleのtoken回転/HTTP・全CI/AWS等は未証明。隔離DB/コンテナ削除・記録保持、main/AWS追加反映・schema/Secrets/課金/容量変更・承認拡張なし、HIGH3未解消・正式公開No-Goを維持する。

後続の[Google Calendar同期途中の失効チェック](GOOGLE_CALENDAR_REVOCATION_2026-10-06.md)で、トークン取得・409応答・予定確認GET中に連携/scope/利用者/セッション閲覧権限を失ってもHTTPが続く問題を新規35 subtest失敗で再現・修正。全6呼び出し箇所の直前にDBから認可を確認し、観測した失効では追加送信/retryなし・同期/ジョブ失敗を記録する。関連49件成功/省略0、本体差分26文4分岐・新規139文28分岐100%。最終書き込み受理後の失効は成功を維持し、自動巻き戻しをしない。チェック後の競合/開始済みHTTP取消・PG並列/実Google/AWS・全CIは未証明。main/AWS追加反映・DBスキーマ/Secrets/課金/容量変更・承認拡張なし、HIGH3未解消・正式公開No-Goを維持する。

後続の[Google Sheets分割出力中の失効チェック](GOOGLE_SHEETS_REVOCATION_2026-10-06.md)で、トークン取得中・チャンク間の連携無効化/scope取り消し/利用者停止/連携削除後も送信が続く問題を8 subtest失敗で再現・修正。開始時と各送信前にDBから状態を読み直し、観測した失効では追加送信・自動再試行なし、送信済み分の進捗を保持して部分出力を日本語で通知する。関連45件成功/省略0、本体差分12文6分岐・新規66文12分岐100%。チェック直後の競合や開始済みHTTPの取消・実Google/PG並列/AWS・全CIは未証明。main/AWS追加反映・DBスキーマ/Secrets/課金/容量変更・既存承認の拡張なし、HIGH3未解消・正式公開No-Goを維持する。

後続の[アカウント削除E2E起動予算分離](ACCOUNT_DELETE_PAGE_BUDGET_2026-10-06.md)で、先行WebKit traceのCreate page約20.6秒が操作30秒枠を消費し、timeout後のcontext closeで最終clickが失敗したことを確認。モーダル不具合とは断定せず、当該flowだけpage作成を独立・有限30秒枠にし、操作30秒/assertion5秒/flaky時CI失敗を維持。実runnerの新規3正負例は未実装時2 failureを経て成功、実3ブラウザー72件成功/再試行・省略・flaky0、新fixture2関数のV8観測4区間100%。アプリ削除仕様/権限・Stripe・実性能基準は変更せず、今回全CI/他flow/実AWS等へ結果を拡張しない。隔離user/契約0・起動分server停止、main/AWS追加反映・承認拡張なし・HIGH3未解消/正式公開No-Goを維持する。

後続の[LLVM上流ソース署名検証](LLVM_SOURCE_PROVENANCE_2026-10-06.md)で、公式sourceの固定identity/issuer/ref/source・signer digest/GitHub-hosted runner条件のcrypto正例終了0、誤identity/digest/issuerの負例終了1を確認。先行source走査168,946件/約2.02GB/PBDS文字列0を再確認し、現在39b43286の267 ELFも先行1aとbytes差分0。ただしsource tarball生成の来歴でありconda/wheelのcompile・compiler headers/生成物/他native閉包は未証明。Debian signed APT policyで修正candidateなし、OS新規scan/指摘抑制/リスク受容なし・HIGH3未解消。先行39 CIは5成功/Playwright290成功・flaky1で失敗、アプリコード同一の後続5deb9b6dは全6成功/pytest2,285成功85省略/Playwright291成功と区別する。main/AWS追加反映・承認拡張なし、正式公開No-Goを維持する。

後続39b43286の[通常配布物・Sentry収集再検証](SENTRY_RUNTIME_39B43286_2026-10-06.md)で684選定ファイル/entrypoint一致、source overlayなしsettings70/PG187成功・省略0、実HTTP44確認・実U2NET完了/再実行不変を確認。実SDK更新警告とERROR eventを試験用offline transportで収集し、event/breadcrumb/Logs・headersで合成本文露出0。実HTTPのSDK Logs WARNING2/コード位置を保持し、全9 envelope・Webログの合成本文/資格情報値露出0。samplingで得たtransaction4件を全監視privacyとは扱わず、実Sentry受信・新OS監査/全CI・HIGH3/native閉包・実AWS/連携/運用等は未達。CI4成功/2実行中、main/AWS未反映・承認範囲は拡張せず正式公開No-Goを維持する。

後続の[Sentry SDK本文保護](SENTRY_SDK_PRIVACY_2026-10-06.md)で、stream formatterを迂回するSentry event/breadcrumb/Logsへの合成本文露出を実SDK・offline transportで再現・修正。SDK専用の安全な診断/分類へ置換し、元データ・SDK以外の監視・既定Logs無効・samplingを維持する。新規9・Linux76/最終header9・Windows背景回帰223成功/PG専用16省略、保護78文16分岐・新規146文22分岐100%。先行dc0b053e CI全6成功は確認したが、新候補の全CI/通常配布物/実HTTP・PG・実受信は未証明。未識別例外/transaction/span/attachment等の範囲は拡張せず、HIGH3未解消・main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。

後続dc0b053eの[通常配布物・SDKログHTTP再検証](SDK_LOG_RUNTIME_DC0B053E_2026-10-06.md)で683選定ファイル/entrypoint一致・source/SDK overlayなしPG191成功/省略0・settings/アクセスログ67成功・実HTTP44確認と実U2NET完了/再実行不変を確認。実SDK WARNING2件・CredentialRetrievalError/コード位置を残し、合成資格情報/ECS応答本文・raw traceback・資格情報値のログ露出0。初回の旧証拠指定/settings環境衝突/readiness待機期限は訂正・記録。新規Scout1.26は39指摘（HIGH3/MEDIUM1/LOW35、Python0）/終了2で未合格、候補CIは4成功/2実行中。独立収集経路・実AWS/課金/外部連携/運用/性能/復旧等は未達、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。

後続の[SDKログ本文保護](SDK_LOG_PRIVACY_2026-10-06.md)で、boto3/botocore専用の安全なstream/file経路とroot伝播停止を追加。実SDKのmandatory/advisory更新警告・例外classを残し、合成応答本文/message/args/chainを出さず、既存メール通知・SDK再試行・課金/DBは変更しない。新規6・Windows settings60・Linuxアクセスログ含む67成功、Windows背景回帰214成功/PG専用16省略、formatter39文10分岐・新規93文12分岐・追加本番経路6文4分岐100%。初回の環境/DB設定/Twisted import失敗は訂正・記録。今回の通常配布物/実HTTP/PG・全CI・独立収集経路は未証明、OS再監査なし・HIGH3未解消、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。

後続b3496898の[通常配布物・資格情報更新HTTP検証](BACKGROUND_SIGNING_RUNTIME_B3496898_2026-10-06.md)で682選定ファイル一致・source/SDK overlayなしPG185成功/省略0・実HTTP44確認と実U2NET完了/再実行不変を確認。loopback資格情報のmandatory refresh失敗後も入力を保持し、初回の確定失敗・重複409・期限・所有者制限を維持した。初回のbuild通信設定/probe import/再実行CLI判定/JSON型比較の検証側失敗を訂正・記録し、初回全成功とは扱わない。SDK警告への合成資格情報エラー本文の露出を新規観測し、全SDKログ保護は未達。新規Scout1.26監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2、候補CIは後続照合で全6項目success。実AWS/課金/外部連携/運用/性能/復旧等は未達、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。

後続の[背景透過SDK署名途中の結果不明判定](BACKGROUND_SIGNING_OUTCOME_2026-10-06.md)で、先行timeout/500後の署名・資格情報更新失敗や最終HTTP200/明示failuresで入力を誤削除する問題を再現・修正。実SDKイベントで先行の結果不明を保持し、初回の確定失敗・token/期限・重複防止・handler解除を維持した。新規14を含むWindows SQLite208成功/PG専用16省略、隔離PG224成功/省略0、変更起動/observer50文16分岐・新規147文14分岐100%。CI PG対象へ追加したが今回全CI/通常配布物/実HTTP・AWS/実S3等は未証明。OS再監査なし・HIGH未解消、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。

後続の[背景透過SDK再試行後の拒否判定](BACKGROUND_RETRY_OUTCOME_2026-10-06.md)で、timeout/500後の最終400/403だけを確定失敗として元画像を削除する問題を新規8 test中6 failureで再現・修正。実SDKのRetryAttemptsを観測し、再試行後のClientErrorは既存の結果不明/入力保持202、初回400/403は既存失敗503を維持。Windows SQLite194成功/PG専用16省略・隔離PG210成功/省略0、変更関数36文/10分岐・新規108文/8分岐100%。重複409・遅いworker完了・既存timeoutも確認。新規moduleをPG CIへ追加したが、今回全CI/通常配布物/実HTTP・AWS/実S3等は未確認。OS監査再実行なし・HIGH未解消、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。

後続の[LLVM同梱レシピ・ソース調査](LLVM_SOURCE_BOUNDARY_2026-10-06.md)で公開llvmdev manylinux_1 archiveの全体ハッシュ・実同梱build_number1/patches:nullを確認し、後のwheelソースrecipe（build0/Windows patchあり）と区別した。指定LLVM公式sourceの全体ハッシュ一致、通常168,946ファイル/約2.02GBでPBDS関連4文字列一致0、検出器の境界/binary正例とハッシュ不一致拒否を確認。追加調査で5月run26481208591と固定f3dbf3bbのrecipe/build script完全一致を確認したが、実ログHTTP410/artifacts0、同梱info/gitは空、workflowの可変image/solver入力が残る。19 linkは未追跡で、当時取得archiveのdigest・全compiler headers/生成物/他native閉包・署名付きsource attestationは未証明。文字列不在やrun成功をPBDS非該当/HIGH解消にせず、OS再スキャンなし・最新39指摘（HIGH3/MEDIUM1/LOW35、Python0）/終了2・正式公開No-Goを維持。main/AWS未反映・既存承認へ追加しない。

後続ba51bdd8の[通常配布物・実HTTP無効化競合検証](BACKGROUND_ACTIVE_RUNTIME_BA51BDD8_2026-10-06.md)で680選定ファイル/entrypoint一致・source/SDK差替えなしPG153成功/省略0・実HTTP25確認を完了。失効/削除/無効化commit/無効化rollbackの実Web行ロック待機4件を観測し、無効化確定後の日本語403・job/画像/dispatch0とrollback後202、初期無効Token401、作成後無効化時のjob保持/復帰後参照を確認した。回帰初回の誤指定3 import errorと診断summary/ログ検索の誤りは訂正・記録し、初回全成功とは扱わない。候補CI全6成功・pytest2248成功/85省略/全体表示88%・Playwright291成功。新規全OS監査39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2で未合格。実AWS/S3/worker運用/実課金/外部連携/性能/復旧等は未達、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。以下のCI/配布物未確認は各先行記録時点として区別する。

後続の[native配布物・公開署名の再照合](RUNTIME_NATIVE_REVALIDATION_2026-10-06.md)で通常1a738d2aの267 ELF全RECORD一致、main8567時点との欠落/追加0・266同一/mysqlclient1変更を確認。今回取得したllvmlite/ONNXの固定wheelと4個の実ELFが一致し、llvmlite公開署名の正例成功・配布元違い/1 byte改変の負例拒否も確認した。署名・ビルドログ自体は先行調査済みで、新しいビルド閉包の証明とは扱わない。ONNXの同API署名情報は404、PBDS非該当/全native閉包は未達。OS再スキャンなし、最新39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2を維持する。先行52acfba2 CI全6成功を確認、ba51候補は4成功/2実行中の照合時点で全成功未確認。main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。

後続の[背景透過job作成時の有効アカウント再確認](BACKGROUND_ACTIVE_GATE_2026-10-06.md)で、認証後/実user行ロック待機中のアカウント無効化が確定しても202で作成される問題を再現・修正した。既存ロック内でis_activeも読み、日次制限/期限処理/画像/job/dispatchの前に日本語403で拒否する。新規10件は実Token認証8件・実PG競合2件（commit拒否/rollback許可）、最終Windows SQLite137成功/PG専用16省略、隔離PG153成功/省略0。変更POST51文/24分岐・追加149文/4分岐100%。既存jobの独断キャンセルや管理者運用方針は追加しない。今回CI/通常配布物/実HTTP・AWS/実S3等は未確認で、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。以下の状態は各先行記録時点として区別する。

後続1a738d2aの[通常配布物・実HTTP権限競合検証](BACKGROUND_PREMIUM_RUNTIME_1A738D2A_2026-10-06.md)で680選定ファイル同一・source/SDK overlayなしPG143成功/省略0・実HTTP16確認を完了。実Webのuser行ロック待機を失効/削除の2ケースで観測し、commit後の日本語403・job/画像/dispatch 0、復帰後202・重複409・作成後失効時の既存job保持・期限処理を確認した。全OSの新規監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2で未合格。候補CIは全6ジョブsuccess、pytest2240成功/83省略/全体表示88%、Playwright291成功（16.9分）。実AWS/ECS/S3・課金/外部連携・worker運用・性能/復旧等の合格には拡張せず、main/AWS未反映・既存承認へ追加しない。正式公開No-Goを維持し、以下の未確認/CI状態は各先行記録時点として区別する。

後続の[背景透過job作成時のプレミアム再確認](BACKGROUND_PREMIUM_GATE_2026-10-06.md)で、古い認証flag・画像検証中/行ロック待機中の失効による不正作成と、削除確定後の500を再現・修正した。画像検証後のuser行ロック下で最新flagを読み、副作用前に日本語403で拒否する。新規11件（実PGロック2件）、最終Windows SQLite129成功/PG専用14省略・隔離PG143成功/省略0、変更POST47文/20分岐・新規155文/2分岐100%。画像APIテストの一時file参照解放も修正し、途中の期待値/Windows/保存先/harness/PG接続失敗を記録した。認可済みjobの後続失効時の扱いは変更しない。今回CI/通常配布物/実HTTP・AWS/実S3等は未確認で、main/AWS未反映・既存承認へ追加せずB01/B03と正式公開No-Goを維持する。

後続3e5d46eeの[通常配布物・起動応答消失検証](BACKGROUND_DISPATCH_RUNTIME_3E5D46EE_2026-10-06.md)で679選定ファイル同一・overlayなしPG97成功/省略0・実HTTP35確認を完了。合成ECS wireの接続断/500/SDK回復/400、入力と時刻の保持、同一token/parameters、実U2NET完了/PNG/権限制限、再実行不変/期限後拒否を確認。初回probe4失敗を記録し、未観測running HTTPを合格扱いしない。候補CI全6ジョブ成功、pytest2231成功/81省略/全体表示88%・Playwright291成功/flakyなし。新しい全OS監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2で未合格。実AWS/ECS/S3・課金/外部連携/運用/性能/復旧等は未達で、main/AWS未反映・既存承認へ追加せず正式公開No-Goを維持する。以下の未確認/CI状態は各先行記録時点として区別する。

後続の[背景透過起動結果不明時の入力保持](BACKGROUND_DISPATCH_UNCERTAIN_2026-10-06.md)で、応答障害後もpendingのjobをWebがfailedへ変更して元画像を削除する問題を再現・修正。関連136件はSQLite124成功/PG専用12省略、隔離PG136成功/省略0。新規14件には実SDK再試行3経路・実PG lock1件があり、変更2関数79文/28分岐・新規テスト267文/22分岐100%。確定失敗と結果不明を区別し、既存timeout/上限を維持した。親a97f07b0のCIはUnit jobがrunner shutdown/canceledでfailure・Playwright実行中のため全成功ではない。今回CI/通常配布物/実ECS・S3/再送parameters永続化/孤立回収等は未確認、既存承認へ追加せずmain/AWS未反映・正式公開No-Goを維持する。

後続7106f6fbの[通常配布物・保持HTTP検証](BACKGROUND_RETENTION_RUNTIME_7106F6FB_2026-10-06.md)で678選定ファイル同一・overlayなし隔離PG83成功/省略0・実HTTP27確認に成功。結果ファイル欠損時の日本語/非公開503、同じ参照への復元後200と時刻不変、実Webのcleanup待機と削除後503、終端削除後404・権限制限を確認した。観測probe3失敗のログを保持し、初回全成功/原因確定とは扱わない。候補CI全6項目success・pytest2218成功/80省略/全体88%・Playwright291成功/flakyなし。新しい全OS監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2で未合格。実ECS/S3/AWS性能・課金/外部連携/運用等は未達、main/AWS未反映で既存承認へ追加せず正式公開No-Goを維持する。

## 2026-10-05時点の経過記録

後続の[背景透過の結果取得・保持削除の競合防止](BACKGROUND_RESULT_RETENTION_2026-10-05.md)で、取得ロック解除後のstorage削除、古い期限snapshotによる誤削除、欠損/アクセス/接続/read障害の500を再現・修正した。最終SQLite111成功/PG専用11省略、隔離PG122成功/省略0、新規20件・実PGロック6ケース、変更2関数68文/32分岐と新規テスト290文/18分岐100%。取得失敗の日本語/非公開503、部分削除失敗、期限境界、同時cleanupの削除1回も確認した。補助コードのPG2 failureと日本語RED5 failureを成功扱いせず記録。親2bac942bのCI全6項目successを確認したが、今回CI/通常配布物/AWS・実S3/分散原子性/性能/孤立回収等は未証明。main/AWS未反映、既存承認へ追加せず正式公開No-Goを維持する。

後続7b75105eの[通常配布物検証](BACKGROUND_RUNTIME_7B75105E_2026-10-05.md)で677選定ファイル同一・overlayなし隔離PG63成功/省略0・実U2NET worker4ケース/HTTP21確認に成功。実モデルworkerのrunning中のtimeout後も終端状態/時刻を保持し遅い結果なし、成功/再実行/破損/所有者制限/保持cleanupも確認した。候補CI全6項目success、pytest2205成功/73省略/全体88%・Playwright291成功/flakyなしを照合。初回102件の文書ファイル欠落1エラーと容量不足の監査失敗を成功扱いせず記録。新しい全OS監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2で未合格、native/実ECS・S3/AWS/課金/外部連携等の不足は維持する。main/AWS未反映、既存承認へ追加せず正式公開No-Go。以下の今回CI/配布物未確認は各先行記録時点の状態として区別する。

後続の[背景透過起動応答とworker進行の競合防止](BACKGROUND_DISPATCH_INTEGRITY_2026-10-05.md)で、応答消失後の古いinstanceによる状態巻き戻り/元画像削除、消えた行の500、task ARN保存による期限延長を再現・修正。最終SQLite98成功/PG専用4省略、隔離PG102件成功/省略0、新規13件・実行ロック1ケース、変更2関数60文/22分岐と新規テスト198文100%を確認。今回CI/通常配布物/実ECS・S3/AWS・pendingの曖昧な起動失敗/孤立ファイル回収等は未証明。親c0b5380bのCIは記録時点で実行中。main/AWS未反映、既存承認へ追加せず正式公開No-Goを維持する。

後続の[背景透過終端状態・タイムアウト競合防止](BACKGROUND_JOB_FINALIZATION_2026-10-05.md)で、遅いworkerによるtimeout状態の巻き戻り、古い取得結果の誤失敗、削除後の遅い画像保存、行ロック前のstorage変更とWindows file lockを再現・修正。最終SQLite86成功/PG専用3省略、隔離PG89成功/省略0、新規15件と実行ロック2ケース、変更2関数61文/18分岐・新規テスト223文/4分岐100%を確認。CI PG対象へ追加したが、今回CI/通常配布物/AWS・実S3/分散原子性/dispatch競合は未確認。main/AWS未反映、既存承認に追加せず正式公開No-Goを維持する。

同日後続の[c7390ee3背景透過worker通常配布物](BACKGROUND_WORKER_RUNTIME_C7390EE3_2026-10-05.md)は固定commit/675対象ファイル一致、Linux/隔離PG31件成功、実U2NET worker3ケースと実HTTP18確認成功。透過PNG・所有者制限・元画像削除・再実行・破損storage失敗・期限後の結果削除を確認した。全OSの新規監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2、先行からID/重大度の変化0。候補CI全6項目success・pytest2181成功/69省略/全体88%・Playwright291成功/flakyなしも後続確認した。実ECS dispatch/S3/AWS性能/worker運用・実課金等の合格に拡張しない。main/AWS未反映、既存承認の対象を維持し正式公開No-Goのまま。以下の今回未確認は先行記録時点の範囲として区別する。

後続の[背景透過native telemetry初期化防止](BACKGROUND_REMOVAL_TELEMETRY_2026-10-05.md)で、通常ONNX importのみの永続識別子/DB作成をネットワーク遮断下で再現し、import前opt-outとnative API無効化を追加した。関連99件・変更サービス/モデルテストの文/分岐100%、通常staged-tree配布物675ファイル同一、実U2NET推論2ケースのPNG透過/telemetryファイル0を確認。過去の外部送信・AWS・全CI/全OS/通常Web/API/PGは今回未確認で、OS/native閉包等のゲート合格には拡張しない。main/AWS未反映、既存承認へ追加せず正式公開No-Goを維持する。

同日後続の[6828f209通常配布物](STRIPE_COMMAND_RUNTIME_6828F209_2026-10-05.md)は675選定ファイル同一・overlayなし隔離PG609件成功/省略0・通常起動/静的収集/実HTTP27件成功。全OSの新しい監査は39指摘（HIGH3/MEDIUM1/LOW35、Python0）・終了2。先行からdashの重大度だけMEDIUM→LOWで、修正解消ではない。最新コマンド保護を含む配布物未検証は限定範囲で解消したが、OS/native閉包・実RAK/Endive/共有運用・管理方針・外部連携・AWS性能/復旧・事業者運用等は未達。main/AWSを変更せず、正式公開No-Goと既存承認範囲を維持する。以下の配布物未確認・旧OS重大度は記録時点の状態として区別する。

10月5日の[Firefox登録ページ遷移調査](FIREFOX_SIGNUP_DIAGNOSTICS_2026-10-05.md)で、最新アプリ6828f209のCI全6ジョブsuccess・Playwright291成功/flakyなし、pytest2176成功/69省略/全体88%を確認した。失敗f355df1cのartifact digestを照合し、描画済みフォームと17件のHTTP200を確認したがtimeout原因は未確定。隔離Windowsの初回表示30回と3ブラウザーの既存退会フロー30件は成功し、待機条件・上限・retry・合格条件を緩めていない。最新通常配布物は未検証、mainは8567f49f、AWSは今回再照合・変更していない。以下の「今回CI未確認」は各記録時点の状態であり、この候補の自動検証範囲で更新する。OS/実環境/外部連携/運用等の不足と正式公開No-Go、固定6b6c570cの承認範囲は維持する。

## 2026-10-04時点の経過記録

正式公開は **No-Go** を維持する。承認済みの[セキュリティ更新](AWS_SECURITY_UPDATE_RESULT_2026-10-04.md)と[アイコン反映](TABLENO_FAVICON_DEPLOYMENT_2026-10-04.md)が完了し、20:23 JSTの先行照合ではmain8567f49f・CI全6項目success、開発AWSは定義54・同一digest・1タスクHEALTHY・readinessのDB/cache正常だった。Web設定/容量を維持し、DB移行・Secrets/権限・課金有効化は行っていない。後続StripeClient通常配布物の検証ではAWSを再照合・変更していない。

同日先行の[稼働配布物の全OS再監査と適用条件](RUNTIME_HIGH_APPLICABILITY_2026-10-04.md)は39指摘（HIGH2/MEDIUM2/LOW35、Python0）、終了1。当時はzlibの重大度だけがHIGH→LOWとなり、修正による解消ではない。後続候補f4ea34caと最新2ff6a4c8の[通常配布物監査](STRIPE_CLIENT_RUNTIME_2FF6A4C8_2026-10-04.md)では同CVEが再びHIGH評価で、HIGH3/MEDIUM2/LOW34・終了2。先行値を現在の候補安全性の証拠にはしない。aligned newのLinux実行経路とzlibのソースに条件不一致の証拠を得たが、指摘抑制・リスク受容・全体合格はしていない。PBDSのnative依存由来と、下表の共有DB・課金実運用・外部連携・性能・復旧・事業者運用等は未達のまま。

[native依存の来歴照合](RUNTIME_NATIVE_PROVENANCE_2026-10-04.md)では267 ELFのRECORD一致、21パッケージ266ファイルの固定公開wheel一致、残るmysqlclientの固定Cソース構成を確認した。改変・配布物同一性の調査を進めたが、外部LLVM/ONNX等のビルド閉包とPBDSの使用条件は未確認。CVE解消や公開ゲートの合格にはしない。

[CCFOLIA JSONの版情報保持](CCFOLIA_EDITION_ROUNDTRIP_2026-10-04.md)を作業ブランチで修正し、7版が6版として再取り込みされる不備を再現・解消。関連41テストと3ブラウザ12件で版・無料保存・能力値/幸運の保持を確認し、759aca7aの[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37180388301)も照合した。main/AWSには未反映で、実CCFOLIAでの画像・ダイス・逆方向取り込みやICS受信側のI07条件は維持する。

[ICSダウンロードの文字・時刻保持](ICAL_DOWNLOAD_INTEGRITY_2026-10-04.md)で、改行による予定混入・未エスケープ・日本語長文・UTC指定漏れを再現し修正した。Windows/Linuxで既存回帰と独立パーサーを含む各31件成功。実受信アプリの購読/更新/失効、main/AWS反映、I07全体の検証は未完了として維持する。

[停止中アカウントのICS購読拒否](ICS_SUBSCRIPTION_AUTHORIZATION_2026-10-04.md)を追加し、GET/HEADで予定を取得できる不備を再現・修正した。SQLite/隔離PostgreSQL 18.3で各35テスト成功し、参加資格の喪失・トークン再発行・削除後の失効も確認。main/AWS未反映・実受信アプリの既存キャッシュ等は未確認で、I07/Q04全体の合格に拡張しない。

3修正を含む `6b6c570c` の[通常配布物](ICS_CCFOLIA_RUNTIME_CANDIDATE_2026-10-04.md)を構築し、575ファイル同一・76関連テスト成功・隔離PG/Redisの通常起動・19件の実HTTPを確認。[候補CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37181732546)も確認した。全OS監査は39指摘（HIGH2/MEDIUM2/LOW35、Python0）・終了1のまま。main/AWSへは未反映で、[今回専用の承認案](AWS_APP_APPROVAL_6B6C570C_2026-10-04.md)を準備した。既存のfavicon反映承認とは区別し、正式公開No-Goを維持する。

[プレミアムコードの競合防止](PREMIUM_CODE_SERIALIZATION_2026-10-04.md)で、同一利用者の別コード二重消費・最新Stripe権限の上書き・ロック待ち中の期限切れを再現し修正した。SQLite289件/隔離PostgreSQL301件が成功し、購入完了ハンドラーとの共有行ロックも確認。先行a0f94a40の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37184128999)を後続確認したが、通常配布物/AWSは未確認。先行6b6c570cの承認対象へ無断で追加せず、B03/B04/Q04と正式公開No-Goを維持する。

[コード由来権限の失効・監査の競合防止](PROMO_REVOCATION_SERIALIZATION_2026-10-04.md)で、古い取得結果/旧コードによる新しい権限の誤失効と、監査保存失敗時の部分更新を再現し修正した。SQLite300件/隔離PG315件成功、購入完了ハンドラーとの行ロック待機と監査rollbackも確認した。PG専用試験をCIに追加したが、今回候補のCI/通常配布物/AWSは未確認で、手動付与等の全経路や正式公開条件の合格には拡張しない。main/AWS反映案の固定対象6b6c570cへ追加せず、No-Goを維持する。

後続 `3492d3d3` の[通常配布物](PROMO_RUNTIME_CANDIDATE_2026-10-04.md)を構築し、577ファイル同一・PG389回帰テスト成功・隔離PG/Redisの通常起動・19 HTTPと13コード利用/失効操作を確認した。全OS監査は39指摘（HIGH2/MEDIUM2/LOW35、Python0）・終了1でゲート未合格。後続で候補CI全6項目successを照合したが、main/AWSは未反映。これら2修正の通常配布物未検証を限定範囲で解消したが、既存反映案の対象6b6c570cは変えず、正式公開No-Goを維持する。

[native公開署名とビルド由来](NATIVE_BUILD_ATTESTATION_2026-10-04.md)を追加確認し、固定llvmlite wheelの署名・公開元・現在候補内のnative bytes一致を検証した。公開runからLLVM22.1.0/GCC10.2.1のビルドログへ追跡できたが、完全なビルド閉包・PBDS非該当は未証明。ONNX対象wheelのIntegrity APIはprovenanceなしの404。現行DebianにはHIGH2件を解消する新しい候補もなく、指摘を抑制・受容せずNo-Goを維持する。

[権限再同期の競合・監査原子性](PREMIUM_RECONCILIATION_INTEGRITY_2026-10-04.md)で、コマンド/管理画面の古い取得結果による新しい課金権限の上書きと、監査保存失敗時の部分更新を再現・修正した。SQLite309件/隔離PG327件成功、購入完了との行ロック待機・同時再同期の監査1件・dry-runの読み取り専用を確認した。今回候補のCI/通常配布物/AWSと、管理者直接付与等の全経路は未確認。固定反映案6b6c570cへ追加せず、B03/B04/Q04と正式公開No-Goを維持する。

後続 `cea7e76b` の[通常配布物](RECONCILE_RUNTIME_CANDIDATE_2026-10-04.md)は578ファイル同一・隔離PG401回帰テスト成功・通常起動・先行19 HTTP・コード利用/失効/再同期23操作成功。Docker Scout1.26.0でも全OS監査39指摘（HIGH2/MEDIUM2/LOW35）・終了1でゲート未合格。候補CIは5項目success・Playwright failure（WebKit退会キャンセル後の確認で30秒上限、233 passed/1 flaky）。traceでnewPageに23.740秒を要したことを確認したが、遅延原因とアプリ不具合の有無は未確定。再試行成功を全CI合格にせず、main/AWS未反映・管理者全経路/OS/実環境等の不足とNo-Goを維持する。

[確認ダイアログの選択保持と終了処理](CONFIRMATION_MODAL_LIFECYCLE_2026-10-04.md)で、表示中キャンセルの喪失/後続確認の誤採用、後片付け前の結果返却、Bootstrapなしの例外を単独再現し修正した。3ブラウザー57件と隔離DBの実退会画面6件が成功。CI予算/合格条件を変えず、変更byteの限定V8計測にも未実行0。後続c9f3e783の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37190166680)を確認したが、先行CI失敗の原因確定や修正後の配布物/AWS/OSゲート合格には拡張せず、B04/Q04と正式公開No-Goを維持する。

[管理画面の停止・復旧・返金確認の整合性](ADMIN_ACCESS_INTEGRITY_2026-10-04.md)で、古い状態による権限上書き/検知監査と、監査失敗時の部分更新を再現・修正した。SQLite322成功・行ロック18省略、隔離PG343成功・省略0。新規16件を含むPG52件で共有行ロック待機・rollback・削除候補・最新検知・繰り返し監査と既存手動付与方針を確認し、変更3メソッドの文/分岐は100%。今回候補のCI/通常配布物/AWS、管理者直接編集等の別経路は未確認。固定反映案6b6c570cへ追加せず、B03/B04/Q04と正式公開No-Goを維持する。

[手動プレミアム権限と管理フォームの整合性](MANUAL_PREMIUM_INTEGRITY_2026-10-04.md)で、プロフィール保存時の古い権限/未変更列の上書き、監査失敗時の部分更新、削除済みユーザーの再作成を再現・修正した。最終SQLite342成功・18省略、隔離PG372成功・省略0。新規29件で共有ロック/初回行作成・旧手動権限・rollback・実削除・UserAdminフォームPOST/グループ保存/403を確認し、変更4メソッドの文/分岐は100%。先行897e73f0の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37191477587)を照合したが、今回の全CI/通常配布物/AWSと独立課金レコード直接編集等の別経路は未確認。固定承認案6b6c570cへ追加せず、正式公開No-Goを維持する。

後続の[課金レコード管理フォーム](SUBSCRIPTION_ADMIN_SAVE_INTEGRITY_2026-10-04.md)で、未編集/readonly列の古い書き戻しと削除後の再作成を再現・修正した。署名付き全列digestと共有行ロックでGETからcommitまでの競合を検出し、古い画面は日本語で再読み込みへ案内する。SQLite361成功・18省略、隔離PG394成功・省略0、新規22件、変更メソッド/新規フォームの文・分岐100%。先行f543f784のCI全6項目successを照合したが、今回CI/通常配布物/AWS、課金レコード削除/ユーザー付け替え等は未確認。固定承認案6b6c570cへ追加せず、正式公開No-Goを維持する。

[課金レコード所有者・削除の運用確認](SUBSCRIPTION_OWNERSHIP_POLICY_2026-10-04.md)で、直接削除による購入再試行/請求/配送記録の消失、付け替え後の別ユーザー権限/メール宛先/Portal顧客指定、Stripe顧客IDの重複/置換、promo期限処理消失を隔離DBで再現した。診断10項目は危険な挙動9項目と空行整理1項目の観測で、受け入れ合格ではない。対象限定保護または全件参照/監査操作専用の運用選択を依頼し回答待ち。今回は記録のみで未修正。既存のユーザー退会保護や署名付き更新確認の成功をこの経路の合格へ拡張せず、正式公開No-Goを維持する。

[リクエスト実行時の課金所有者照合](BILLING_REQUEST_OWNER_INTEGRITY_2026-10-04.md)で、取得後/保存後の所有者・顧客ID変化と、持越した顧客作成/購入リクエストの不一致を再現・修正した。顧客作成・Checkout・Portalの共有行ロックと日本語拒否を追加し、再試行キー/元プロフィール・プラン変更は維持する。最終SQLite377成功・31省略、隔離PG416成功・省略0、新規22件、変更3関数/4ヘルパーの88文/40分岐100%。先行ae4d12efのCI全6項目successを確認したが、今回CI/通常配布物/AWSと既存の誤結合・管理削除/付け替えの運用選択は未完了。固定承認案6b6c570cへ追加せず、B03/B04/Q04と正式公開No-Goを維持する。

後続 `f4ea34ca` の[通常配布物・管理HTTP検証](BILLING_RUNTIME_F4EA34CA_2026-10-04.md)で、追跡668ファイル同一・隔離PG490回帰成功/省略0・通常起動・68確認（61 HTTP/7コマンド）成功を確認した。古い管理フォーム拒否/最新保存、停止/復旧/返金確認/手動付与、保存済み購入intentの不一致と実HTTP中の所有者変更拒否を含む。候補CI全6項目successもSHA照合済み。最新OS監査は39指摘（HIGH3/MEDIUM2/LOW34、Python0）・終了2でゲート未合格。20:23 JSTの読み取りでmain8567f49f・AWS定義54/HEALTHY/DBcache正常・favicon200を再確認し、完了済みアイコン承認を後続候補へ転用しない。管理削除/所有者付け替え方針は回答待ち、main/AWSへの今回候補反映・実決済/外部連携/税務等は未完了で正式公開No-Goを維持する。

[Stripeクライアント設定の分離](STRIPE_CLIENT_ISOLATION_2026-10-04.md)で、モジュール共有のキー/API版書換えをStripeClientへ移行し、SDK15.5.1・既定API版・再試行intent/キー・所有者照合/共有ロックは維持した。実SDKのメモリーtransport試験14件を追加し、最終隔離PG458件成功/省略0・SQLite計測289成功/6省略、新規テスト/設定生成/再試行ヘルパーの文・分岐100%、変更33文未実行0を確認した。本体/新規テストのBandit指摘0だが、変更25ファイル全体には既存合成資格情報LOW6件があり全体合格とはしない。先行3804dbc5のCI全6項目successを後続確認したが、今回CI/通常配布物/AWS・実Stripe・RAK/SDK/API更新・税務等は未完了。管理運用方針は回答待ちで、固定反映案6b6c570cへ追加せず正式公開No-Goを維持する。

後続 `2ff6a4c8` の[通常配布物](STRIPE_CLIENT_RUNTIME_2FF6A4C8_2026-10-04.md)で、追跡670ファイル同一・実SDK試験を含む隔離PG529テスト成功/省略0・通常起動・実HTTP27件成功・静的manifest232件変化0を確認した。全OS監査は39指摘（HIGH3/MEDIUM2/LOW34、Python0）・終了2で、CVE ID/重大度の変化0。候補CIは当初4項目success/2項目実行中だったが、後続で[全体success](https://github.com/sheepdog0820/iaia/actions/runs/37200546871)とSHA/branch一致を確認。main/AWSへは未反映。StripeClient移行の通常配布物未検証を限定範囲で解消したが、実決済/RAK/SDK・API更新/税務・管理運用方針・外部連携等は未完了。既存承認へ追加せず、正式公開No-Goを維持する。

[Stripe SDK/API更新](STRIPE_SDK_API_UPGRADE_2026-10-04.md)で公式のSDK16.0.0/API2026-09-30.endiveを選定し、明示pin・Checkout追跡ラベルのintent単位保持・pause/resume/invoice.paid処理と必須証拠・Webhook版照合を追加した。新規22件を含む隔離PG588件成功/省略0、SQLite478成功/39省略、production設定28件成功。比較した変更20実行文は未実行0、新規テスト208文/4分岐100%、Python lock111件監査0・CI対象Bandit0。今回CI/通常配布物/OS/実Stripe・共有環境の版切替は未検証で、main/AWSへ反映していない。RAK/共有DB/worker/メール/税務/管理運用方針・外部連携等を含む正式公開No-Goを維持する。

後続 `2b70f1d5` の[通常配布物](STRIPE_ENDIVE_RUNTIME_2B70F1D5_2026-10-04.md)で、追跡671ファイルの欠落/不一致0、SDK16.0.0/API Endive、overlayなし隔離PG545件成功/省略0・production設定28件成功・通常起動・実HTTP27件成功を確認した。静的manifest232件変化0。全OS監査は39指摘（HIGH3/MEDIUM2/LOW34、Python0）・終了2で、前候補からCVE ID/重大度の変化0だがOSゲート未合格。候補CIは当初4項目success/2項目実行中だったが、後続で[全体success](https://github.com/sheepdog0820/iaia/actions/runs/37204401824)とSHA/branch一致を確認した。通常配布物の未検証を限定範囲で解消し、RAK/実Sandbox/共有環境切替・管理運用方針・外部連携/性能/復旧/税務等は未完了。main/AWSには反映せず、正式公開No-Goを維持する。

[Stripe制限付きキー対応](STRIPE_RESTRICTED_KEYS_2026-10-04.md)で、既存のskキー互換性を維持してrkキーを各検査・Price作成・production/staging設定へ共通対応し、モード違い/不明形式を拒否した。隔離PG広域598件成功/省略0、最終新規16件成功（重複のため合算しない）、SQLite279件/production設定33件成功。新規helper/単体の文・分岐100%、変更32文未実行0、CI対象Bandit0だが広い変更範囲の既存テストLOW26件は残る。基点847ad563のCI全体successは確認済みで、今回CI/通常配布物/実RAKの認証・権限・アカウント一致は未検証。実キー/Secrets/権限・DB・共有AWS・Taxは変更せず、既存反映承認へ追加しない。正式公開No-Goを維持する。

後続 `529c30c7` の[RAK通常配布物](STRIPE_RAK_RUNTIME_529C30C7_2026-10-04.md)で、選定673ファイル欠落/不一致0、overlayなし隔離PG561件成功/省略0、production設定33件/起動時キー境界7ケース/実HTTP27件成功、通常起動/DBcache readiness正常・静的manifest232件変化0を確認した。全OS監査は39指摘（HIGH3/MEDIUM2/LOW34、Python0）・終了2で、先行2b70f1d5からCVE ID/重大度変化0だがOSゲート未合格。今回CIは当初4項目成功/2項目実行中だったが、後続でUnit / Integrationのproduction設定試験23件失敗を確認し、親環境を継承するfixtureの再現/修正が必要。mainは8567f49fのまま、AWSは再照合・変更していない。RAK形式対応の通常配布物未検証は限定範囲で解消したが、CI・実RAKの最小権限/認証・Sandbox・共有環境切替・管理運用方針・外部連携/性能/復旧/税務等は未完了。既存承認へ追加せず正式公開No-Goを維持する。

[本番設定テストの環境独立化](PRODUCTION_PROBE_ISOLATION_2026-10-04.md)で、529c30c7のCI23件失敗を親development下で再現し、テストsubprocessのモード/Django設定/envファイルを明示した。本番アプリのモード境界やruntime selectorは変更しない。新規3試験のRED、関連pytest97件成功・設定36件/テストモジュール209文6分岐100%を確認した。Banditの既存LOW26件は残り、新規0。修正後の全CI/通常配布物は未確認で、先行CI失敗を合格へ置換しない。main/AWS/実キー/DB/Taxは変更せず、正式公開No-Goを維持する。

後続の[Stripe検証コマンドのAPI例外・SDKログ保護](STRIPE_COMMAND_ERROR_REDACTION_2026-10-04.md)で、実SDK/合成transportの401/403と途中失敗を再現し、固定日本語分類/安全な数値HTTPだけを表示、同期コマンドのSDKログをContextVarで保護、直接stderr詳細ログはAPI前に拒否した。Product無効化失敗の成功誤表示と、確認記録への予期しない例外本文保存も修正。隔離PG609件成功/省略0、最終関連SQLite36件/新規共通処理43文8分岐100%、変更Python7ファイルのBandit0。ソースoverlayの回帰であり、今回通常配布物/全CI/AWSの成功ではない。正常出力・既存CommandError/Web処理等の全ログ保護へ拡張しない。main/AWS/実キー/Secrets/DB/課金/Stripe Taxは変更せず、OS39指摘と正式公開No-Goを維持する。

基点f355df1cの[CI最終結果](https://github.com/sheepdog0820/iaia/actions/runs/37209632857)は全体failure。Unit / Integrationを含む5ジョブはsuccessだが、Playwrightは290 passed/1 flaky・終了1で、Firefoxのaccount-deletion初回signupページ遷移がload待ち30秒timeout。production設定fixtureのCI失敗解消と全CI成功を区別し、ブラウザー失敗の精査/再現を残す。

## 2026-10-02時点の経過記録

同日後続の[通常配布物検証](RUNTIME_SECURITY_2026-10-02.md): 稼働版c6226ddbの画像ギャラリーを保持するブランチへPython修正を統合し、ベースdigest固定とPCRE2更新を追加した。修正後イメージは隔離PG/Redisで通常起動・146テスト成功、全パッケージスキャンは39件（HIGH3/MEDIUM2/LOW34、Python0）。AWSは旧版のままであり、残るOS指摘・修正後CI・実環境検証のためNo-Goを維持する。

正式公開は **No-Go**。現行版・CI・AWSの読み取り照合は[10月2日の確認記録](RELEASE_STATE_2026-10-02.md)を優先する。以下の過去記録にある「main未反映」「AWS定義49」「反映承認待ち」は当時の情報であり、現在の反映手順にそのまま使わない。

同日後続の[依存監査と修正](DEPENDENCY_SECURITY_2026-10-02.md): 文書更新89f999a0のCIで依存監査が失敗。稼働digestの全パッケージ監査にも71指摘（OS53/Python18）がある。Python依存4件と必須推移依存1件をローカル更新し、3ロック/実インストール環境の監査0件、関連130テスト成功・2省略を確認したが、修正後CI・配布物・AWS反映は未完了。下記の9月25日のCI成功や旧OS指摘数を最新安全性の証明にしない。

- 依頼された候補は `5caeaf2c` でmainへマージ・push済み。同コミットのCI全6項目成功を確認した。現在のmain `35ecfd5c` はこの変更を含み、そのCIも成功。
- 開発AWSは定義52、`aws-pre-c6226ddb` が稼働。ECRと実行タスクのdigest一致、1タスクHEALTHY、DB/cache readiness成功。`c6226ddb` は現在のmainに画像ギャラリー関連2コミットを加えた履歴で、mainより先にある。旧候補への反映はこれらの変更を落とすため実施しない。
- Web容量は0.25 vCPU/512 MiB、購入開始は無効。共有DBの0065〜0067適用、課金メールの実効設定・配送、外部連携、現行イメージのOS監査、総合性能・復旧・事業者運用は今回の読み取り確認では証明していない。
- 最新状態の確認は公開条件の緩和や新たなデプロイ・DB変更・課金有効化の承認ではない。下表の機能別証拠は記載された版・範囲に限定する。

## 2026-09-22までの候補・監査の経過記録

反映案: [fec10aa0対象の最新計画](AWS_APP_APPROVAL_FEC10AA0_2026-09-22.md)を準備した。17:21 JSTの読み取り確認でmain=d875d028、開発AWS定義49・desired/running=1・pending=0・readiness正常。CI全体成功の確認と反映/共有DBの承認は残り、変更操作は未実施。以下の「最新候補へ反映案の更新が必要」はこの計画作成の範囲で解消した。

最新OS監査: `fec10aa0` の[専用キャッシュによる再監査](RUNTIME_HISTORY_PERMISSIONS_FEC10AA0_2026-09-22.md#os監査の初回失敗と専用キャッシュでの完了)が完了し、36指摘（HIGH 2 / MEDIUM 1 / LOW 33）が残る。以下のキャッシュ障害による未完了は解消したが、脆弱性ゲートは未合格。Perlの対象モジュール不在という限定的証拠を得たものの適用除外はしていない。最新CI/AWS検証と正式公開No-Goは継続する。

最新確認: 先行 `d9a61f4c` のCI全6ジョブ成功を確認。後続の非公開情報保護を含む `fec10aa0` は[通常配布物・隔離PG/Redis](RUNTIME_HISTORY_PERMISSIONS_FEC10AA0_2026-09-22.md)で起動と関連19テスト（SQLite/PGそれぞれ）が成功した。最新修正のCI/AWS検証は別途必要で、先行CI成功とは区別する。

追加の権限修正: [履歴による非公開シナリオ/セッション参照](HISTORY_RELATED_OBJECT_PERMISSIONS_2026-09-22.md)を再現し、作成/変更時の権限検査と読み出し時の関連情報の非表示化を追加。ローカル検証済みだが44a18301の配布物には含まれず、同候補の反映案は更新が必要。CI/最新配布物/AWS未検証としてNo-Goを維持する。

最新配布物の起動確認: [44a18301の同一イメージ](RUNTIME_CANDIDATE_44A18301_2026-09-22.md#同イメージのpostgresqlredis検証)で、隔離PostgreSQL 18.3/Redis・aws-pre設定の通常起動、全マイグレーション、readiness、deploy checkが成功。関連10テストも隔離PGで成功。以下の最新PG/Redis起動未確認はこの範囲で解消したが、実AWS・S3・外部連携の証明ではない。最新CIは実行中で、OS指摘とNo-Goを維持する。

最新配布候補の検証: [44a18301の通常コンテナ](RUNTIME_CANDIDATE_44A18301_2026-09-22.md)を構築し、通信禁止の一時コンテナで関連144テストと静的227ファイル収集、変更ソースのハッシュ一致を確認。OS再監査は36指摘（HIGH 2 / MEDIUM 1 / LOW 33）が残る。候補CIと最新イメージのPostgreSQL/Redis起動・AWS検証は未完了。以下の旧候補の成功と区別する。

探索者履歴の追加実証: `d0a73eae` の[実API保存から非空表示まで](CHARACTER_HISTORY_LOADING_2026-09-22.md#後続の保存表示一貫試験)を、6版/7版×3ブラウザー6件で確認した。探索者2名の履歴分離・再読み込み後の一致・保存文字列のHTML保護が成功。以下の非空表示一貫試験の未実施は、このローカルadmin/API作成条件で解消。通常利用者のフォーム操作やAWSの完了を意味しない。

探索者履歴の後続修正: [取得API契約の修復](CHARACTER_HISTORY_LOADING_2026-09-22.md)で、所有者本人の対象探索者を指定したセッション履歴に絞って取得するよう変更した。API権限・絞り込みと3ブラウザーの空履歴取得をローカル確認。以下の「取得が開始されない問題」はこの範囲で修正済みだが、非空履歴の保存から表示までのブラウザー一貫試験・AWS反映は未完了。

最新の追加修正: `709d476f` の[一覧表示](CHARACTER_LIST_SECURITY_2026-09-22.md)、`3a01be91` の[成長表示](CHARACTER_GROWTH_SECURITY_2026-09-22.md)、後続の[詳細表示](CHARACTER_DETAIL_SECURITY_2026-09-22.md)をローカル検証した。以下の候補 `1b051dba` / 配布物 `f8aa55a9` には含まれず、そのCI/配布物の成功を後続修正へ拡張しない。探索者履歴の取得が現行API契約と不整合で開始されない問題も確認し、未修正として記録した。正式公開No-Goを維持する。

反映案の更新: [f8aa55a9対象の承認案](AWS_APP_APPROVAL_F8AA55A9_2026-09-22.md)と静的資産の復旧証拠を準備済み。以下に残る「9889f4c8案から未更新」「AWS認証失効」は過去時点の情報で、9月22日16:05 JSTにはAWS認証とECS/RDSを再確認済み。ただし反映承認は未取得で、後続表示修正を含む最新候補の反映案・配布物は別途更新が必要。

配布物の後続確認: 文書更新を含む`f8aa55a9`から[通常イメージの構築・関連62テスト・静的ファイル227件収集・6版/7版JavaScriptのハッシュ一致](CHARACTER_CUSTOM_SKILL_SECURITY_2026-09-22.md#通常配布イメージの確認)を確認した。同イメージの[隔離PostgreSQL/Redis起動とOS再監査](CHARACTER_CUSTOM_SKILL_SECURITY_2026-09-22.md#postgresqlredis起動とos再監査)も完了し、全移行・readinessが成功した。以下の「通常イメージ再構築・OS再監査は未実施」はこの範囲で解消した。OSの36指摘（HIGH 2 / MEDIUM 1 / LOW 33）とAWS配信未確認は残る。

最新アプリ候補は`1b051dba`。同候補の[CI全6ジョブ成功](https://github.com/sheepdog0820/iaia/actions/runs/35695689750)を確認した。先行候補`898e8dda`の[通常コンテナと隔離PostgreSQL/Redis起動](GOOGLE_SHEETS_LARGE_EXPORT_2026-09-22.md)も保持するが、最新候補の通常イメージ再構築とOS再監査は未実施である。基礎となるStripe・Google統合候補`9889f4c8`の[固定候補検証](RUNTIME_CANDIDATE_9889F4C8_2026-09-22.md)、先行Stripe実装の[配布コンテナ内の課金メール監視検証](BILLING_EMAIL_HEALTH_2026-09-19.md)、[4削除経路の実Stripe試験](STRIPE_DELETION_PATHS_API_2026-09-19.md)も保持する。main・開発AWSへの反映は[承認待ち](STRIPE_AWS_APP_APPROVAL_2026-09-19.md)。先行OS監査には36指摘（HIGH 2件・MEDIUM 1件）が残る。9月13日以降の実サンドボックス試験で解消した範囲はB01〜B05を参照する。他分野の過去記録を最新の実証として扱わず、正式公開No-Goを維持する。

以下は9月12日以前の経過記録。

ハンドアウトの更新（2026-09-12）: `06343834` で受取人による不正な更新・削除と、管理権限のないセッションへの移動を拒否するよう修正した。[権限とHTTP検証](HANDOUT_WRITE_AUTHORIZATION_2026-09-12.md)は隔離環境で800要求が期待結果に一致。`d9e65188` の[一覧再測定](HANDOUT_LIST_PERFORMANCE_2026-09-12.md)は100人・同時10件、閲覧可能な20件のID・本文が全100要求で一致し、p95は3.797秒から1.694秒へ改善。通常配布物の関連53テストも成功した。F05/Q02/Q04の局所的な改善であり、main・開発AWSへは未反映。旧稼働版への切戻しは修正前の書き込み権限不備を再導入するため、復旧案でもこの修正を維持する必要がある。

候補CI: 上記のアプリ変更を含む `7a6719a2` の[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34697074333)と[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34697076411)は確認時点で実行中。下表の旧候補CI成功は、この候補の成功を証明しない。

画像操作の性能: [cc160e7bの画像追加試験](CHARACTER_IMAGE_PERFORMANCE_2026-09-12.md)は登録100人・同時10人、6版/7版で約1.1MB・約4.5MB各500要求が期待結果に一致しエラー0。ただし0.25 CPU/512 MiBで大きな画像の追加p95は7.098秒、一覧3.485秒となり3秒基準に未達。画像操作全体の性能は未達として扱い、Q02の改善・実環境検証を継続する。

日程調整の性能（2026-09-12）: [最新通常配布物の500要求](DATE_POLL_PERFORMANCE_2026-09-12.md)は内容一致・エラー0。ただし100人・同時10フローの日程確定p95が3.489秒で、採用した3秒基準を超過した。日程確定の原因分析・改善・再測定が必要であり、過去の一覧/基本作成APIの基準達成を通常操作全体の合格へ拡張しない。

同日の改善後: [82712c24の通常配布物による再測定](DATE_POLL_PERFORMANCE_2026-09-12.md)で、日程確定p95は2.227秒、5操作すべて3秒以内・500件内容一致・エラー0。表示データの重複取得を削減し、権限/ロックを維持した。上記の日程調整の未達は今回の限定条件では解消したが、実AWS・その他の主要操作・長時間負荷・候補CIは未確認でQ02全体は未達。

2026-09-12の決定: [個人事業者・請求開示方式](INDIVIDUAL_SELLER_POLICY_2026-09-12.md)を採用。氏名・所在地・電話番号の公開方法、support@tableno.jp、税込価格、解約期限、法令上必要な場合を除く原則返金なしを確定した。以下の事業者表示・返金方針「未確定」はこの決定で置き換える。実情報の非公開保管、開示窓口の受信・返信、Stripe最終確認画面・提供開始の実証、保存期間等は未完了で、O04全体は未達。表示修正のmainマージ・AWS反映は未実施。

正式公開はNo-Go。以下の「判定表」は現在の確認結果へ更新した。冒頭の経過記録と各資料の過去時点の記述より、判定表および日付の新しい実施結果を優先する。要件を削除したり、限定試験で全体合格としたりしない。

Googleトークン更新の追加修正（2026-09-22）: [期限不明のアクセストークンを有効扱いせずrefreshする修正](GOOGLE_TOKEN_EXPIRY_2026-09-22.md)を実装し、関連75件成功・3件skip、変更モジュール行カバレッジ100%、候補`9ca92792`の[CI全6ジョブ成功](https://github.com/sheepdog0820/iaia/actions/runs/35674518374)を確認した。実Google API・実トークン・AWS workerは未使用で、実認可の取消・失効・更新やCalendar/Sheets配送の完了証拠にはしない。修正はmain・AWSへ未反映で、I01/I04/I05と正式公開No-Goを維持する。

外部連携の失敗導線（2026-09-22）: [Calendar/Sheets/Discordの失敗履歴と再試行案内](INTEGRATION_RETRY_GUIDANCE_2026-09-22.md)を修正し、外部例外文字列の非保存、broker停止・再試行拒否・受付後の一覧更新失敗をローカル69件と3ブラウザ6件で確認した。実資格情報・実API・worker・AWSは未使用で、I04〜I06と正式公開No-Goを維持する。

Google Sheets大規模出力（2026-09-22）: [100行単位の分割・進捗・途中失敗表示](GOOGLE_SHEETS_LARGE_EXPORT_2026-09-22.md)を実装し、205行の3分割と進捗、201行の途中失敗、不正A1範囲・応答の非露出を含むローカル26件に成功した。`898e8dda`のCI全6ジョブと、通常イメージによる隔離PostgreSQL 18.3/Redis起動も成功した。実Google資格情報・実シート・worker・AWSは未使用で、I05と正式公開No-Goを維持する。

統計画面の動的HTML保護（2026-09-22）: [Tindalos MetricsのAPI値エスケープ](STATISTICS_DYNAMIC_HTML_SECURITY_2026-09-22.md)を追加し、修正前の要素・イベント生成をブラウザで再現した。修正後は悪意あるグループ名・GM名・セッション名・ランキング名を文字として表示し、3ブラウザでイベント実行0を確認した。AWS未反映かつ全表示経路の監査完了ではないため、Q04と正式公開No-Goを維持する。

キャラクター技能名の動的HTML保護（2026-09-22）: [6版・7版カスタム技能名のHTMLエスケープ](CHARACTER_CUSTOM_SKILL_SECURITY_2026-09-22.md)を追加し、悪意あるタグ・イベント属性を含む技能名が文字として保持され、要素・イベントを生成しないことを3ブラウザ6件で確認した。安定化後候補`1b051dba`の[CI全6ジョブ](https://github.com/sheepdog0820/iaia/actions/runs/35695689750)も成功した。AWS未反映かつ全キャラクター表示経路の監査完了ではないため、Q04と正式公開No-Goを維持する。

| 区分 | 現在の状態 |
| --- | --- |
| 開発環境 | [9月22日の再確認](RUNTIME_OS_BB61B0E6_2026-09-22.md)ではWeb定義49・コードd875d028、desired/running=1、readinessのDB/cache正常。後続のStripe修正は未反映 |
| main / 作業候補 | 9月22日にorigin/main=d875d028を再確認。最新アプリ候補は非公開関連情報保護を含むfec10aa0。main・開発AWSへ未反映。[44a18301の反映案](AWS_APP_APPROVAL_44A18301_2026-09-22.md)は後続修正を含まないため更新が必要。9月22日16:58 JSTのAWS再確認では定義49・desired/running=1・pending=0、HTTP readinessのDB/cache正常。反映承認は未取得で、実行直前にも再確認する。本番反映は未実施 |
| 自動検査 | 先行d9a61f4cのCI全6ジョブ成功。fec10aa0を含む[e2d08157のCI](https://github.com/sheepdog0820/iaia/actions/runs/35703522004)は実行中。[最新通常配布物](RUNTIME_HISTORY_PERMISSIONS_FEC10AA0_2026-09-22.md)はSQLite/PG各19テスト、隔離PG/Redis・aws-pre設定の通常起動、全移行、readiness、deploy check成功。OS監査は36指摘が残る。実AWS・外部連携の検証を代替しない |
| Google | 実認可の保存成功。実同期・トークン更新・公開審査は未完了。[一時Redis/workerのAWS接続試験](GOOGLE_WORKER_CONNECTIVITY_RESULT_2026-09-10.md)は成功・削除済み |
| Stripe | 登録保留は解除済み。9月13日に月額・年額・更新・支払失敗/回復・解約・返金/異議を実サンドボックスで確認。[候補監査](STRIPE_CANDIDATE_AUDIT_2026-09-19.md)。AWS検証と残る異常系は未完了 |
| 性能・復旧 | 隔離環境の対象APIは基準内、実RDSの限定復元は成功。実AWSの全操作性能とDB/S3を含むRPO/RTOは未証明 |
| 人間の判断・情報 | 個人事業者・請求開示方式と返金条件は承認済み。実情報の非公開保管、開示窓口の受信/返信、保存方針、継続費用、反映操作・正式公開の判断は残る |

## 過去の経過記録

最新確認（2026-09-10、統計反映後）: コード20803480のpush/PR CIが成功し、[開発AWSのWeb定義45へ反映](AWS_PRE_STATISTICS_2026-09-10.md)。Chromeで平均時間0.6hを確認し、以下の統計修正のCI・反映待ちは解消した。[Google再連携](GOOGLE_RECONNECT_2026-09-10.md)も認可保存まで成功。ただし処理待ち行列・workerがなく実同期は未確認で、追加構成と継続費用の承認が必要。正式公開はNo-Goを維持する。以下は各確認時点の履歴である。

通常配布物での再測定（2026-09-10）: [7b196988の一覧API反復測定](READ_API_OPTIMIZED_RUNTIME_2026-09-10.md)は100人・同時10件・3回計900件がHTTP200、全一覧のp95が約1.9〜2.2秒。前回の代表データにおける一覧APIの未達は改善した。[基本APIの作成・編集・再取得](WRITE_API_RUNTIME_2026-09-10.md)も1,200件エラー0、各操作p95が約1.3〜2.5秒だった。実AWS・長時間負荷・その他主要操作は未完了のため、Q02全体や正式公開を合格とはしない。修正は[開発AWSのWeb定義44へ反映済み](AWS_PRE_SESSION_PERFORMANCE_2026-09-10.md)。Chromeで認証済みの一覧・詳細表示を確認。統計の平均時間表示に不具合を発見し、[APIの応答欠落をローカル修正](SESSION_STATISTICS_AVERAGE_2026-09-10.md)。[年指定の無視も修正](SESSION_STATISTICS_YEAR_2026-09-10.md)し、SQLite/PG双方12テスト・20サブテスト成功。これら追加修正のCI・AWS反映は未完了。実AWSの性能測定と全操作確認は未完了。

一覧処理の改善（2026-09-10）: [セッション参加者の二重変換と項目定義再構築を削減](SESSION_SERIALIZATION_PROFILE_2026-09-10.md)。関連30テスト・12サブテスト成功、応答形式とハンドアウト権限を維持。隔離APIClient診断の5回合計は2.889秒から1.277秒へ短縮した。その後、上記の通常配布物での同時10件再測定と7b196988のCI全5ジョブ成功を確認。開発AWS反映も完了したが、性能ゲート全体は未完了。

最新確認（2026-09-10）: dd0fe128のCI run34306247763は全5ジョブsuccessで、下段のフォント修正後CI待ちは解消。[登録100人・同時10件の一覧API反復測定](READ_API_100_USERS_2026-09-10.md)を現行配布物・隔離ローカル環境で実施し、900件エラー0。ただしセッション一覧p95が3回とも3秒を超え、シナリオ一覧も1回超過した。今回の構成では応答時間未達で、性能条件と正式公開はNo-Go。全利用フローや実AWSの性能を証明する試験ではない。

最新確認（2026-09-09）: 正式公開はNo-Goを維持。main 14ac4746へのマージと[開発AWS反映](AWS_PRE_DEPLOYMENT_14AC4746_2026-09-08.md)を完了し、フォント修正fa09731cが稼働中。Web定義43で[背景透過の権限修正と実AI処理](BACKGROUND_REMOVAL_IAM_FIX_2026-09-08.md)も成功した。最新CI run34231517141は4ジョブ成功・単体/統合失敗で、[フォントテストのHTTP後処理](PUBLIC_FONT_CI_LIFECYCLE_2026-09-09.md)を再現・修正した。修正後の全体CIは未確認。以下の古い「未反映」「PR #2 open」「mainマージ未実行」「背景透過起動未確認」は過去時点の記録であり、この実施範囲では解消している。背景透過のブラウザ全経路、実外部連携、合意した性能・サービス全体の復旧、Stripe、事業者情報などの公開条件は未完了。

実RDS復元（2026-09-08）: [承認済み試験](RDS_RESTORE_RESULT_2026-09-08.md)で指定snapshotを一時非公開DBへ復元し、読み取り専用の検査が終了0。対象の移行履歴・列・ロール制約の結果は昼の元DB検査と一致。一時DB/自動バックアップ/SG/専用イメージタグは削除済み、元サービスの正常を確認。以下の「実RDS復元未実施」はこの限定範囲で解消。S3ファイル・全データ整合・アプリ切り替え・RPO/RTOを含むサービス全体の復旧は未完了。

2026-09-08のユーザー決定: [性能・復旧基準](RELEASE_CRITERIA_DECISIONS_2026-09-08.md)として登録100人・同時10人、通常操作の95%が3秒以内、予期しないエラー0件、RPO24時間・復旧対応開始からRTO4時間を採用。RDS復元試験案も承認済み。以下の「基準回答待ち」「RDS復元承認待ち」はこの決定で置き換えるが、実測の合格や復元成功は別の証拠を要する。事業者情報は未確定、Stripeは保留継続。

最新確認（2026-09-08）: 正式公開はNo-Go。アプリ候補 `4d7c4ea7` の[PR CI](https://github.com/sheepdog0820/iaia/actions/runs/34214020802)・[push CI](https://github.com/sheepdog0820/iaia/actions/runs/34214015906)は全5ジョブsuccess。単体/統合1,775成功・30省略、カバレッジ86.87%、PG286成功・38サブテスト、3ブラウザ186成功。詳細と制約は[配布物・CI記録](RUNTIME_PRIVATE_MEDIA_4D7C4EA7_2026-09-08.md)を参照。Draft PR #2はopen、対象main、head 4d7c4ea7とAPI照合済み。以下の過去経過にある「CI待ち」「未修正」等はその記録時点の状態であり、現状は判定表と参照先の後続記録で判断する。

最新配布物: [4d7c4ea7の通常イメージ](RUNTIME_PRIVATE_MEDIA_4D7C4EA7_2026-09-08.md)で対象ソース514ファイルが一致し、隔離PG18.3/Redis7の実HTTP34件が成功。問い合わせ添付・透過結果の取得/拒否・成功応答のキャッシュ制御を含む。旧通常イメージとOS/Pythonパッケージ一覧は一致するが、新たなOSスキャンや実S3/CDN検証を代替しない。

通常配布物の画像検証（2026-09-08）: [候補1edab4f2の解像度試験](IMAGE_RESOLUTION_RUNTIME_2026-09-08.md)を実施。通常イメージとソース553ファイルが一致し、0.25 CPU/512 MiBの隔離環境で6版・7版のHTTP14件（保存6件・拒否8件）が期待どおり。画像一覧の枚数・順序も確認。実S3・同時負荷・最大メモリ・全体CIは未確認で、正式公開No-Goを維持する。

画像順序の修正（2026-09-08）: [画像追加時の順序](CHARACTER_IMAGE_ORDER_2026-09-08.md)で既存最大値0を未登録と誤判定し、次も0になる不具合を6版・7版で再現。Noneだけを未登録扱いに修正し、連続追加・明示順序の保持を含むPG45件が成功。過去データの自動整理は行わず、実環境未反映・新候補CI未確認。

画像HTTP試験の更新（2026-09-08）: [サイズ・形式試験のデータを分離](IMAGE_UPLOAD_PROBE_2026-09-08.md)し、5枚上限と衝突する旧期待値を修正。隔離本番設定の実HTTP27件で18件の保存と9件のサイズ超過拒否が期待どおり。単体2件も成功。下段の負荷プローブ期待値修正待ちは解消した。高解像度画像・実S3・合意した性能基準は未確認で、Q02と正式公開は未完了。

画像上限の競合修正（2026-09-08）: [残り1枠への同時追加](CHARACTER_IMAGE_CONCURRENCY_2026-09-08.md)で6版・7版とも2件が保存される不具合を再現し、キャラクター行のロック内で検証・保存するよう修正。修正後は1件成功・1件上限エラーとなり、既存画像保持を確認。関連PG43件成功、並行処理テストをPG CIへ追加。実環境未反映・新候補CI未確認。HTTP負荷プローブの期待値修正と実アップロード性能検証は残る。

一覧APIの性能測定（2026-09-08）: [候補bca01195の構成比較](READ_API_CAPACITY_2026-09-08.md)を完了。4構成・計720件はHTTP 200だが、同時アクセス時の遅延と単発測定の限界があり、性能合格値は未確定。同候補のPR/push CIは全5ジョブsuccess。下段の同候補CI待ちは解消した。AWS容量変更は行わず、正式公開No-Go・Stripe保留・RDS復元承認待ちは維持する。

性能上の修正（2026-09-08）: [世代選択の重複走査](LINEAGE_LOCK_LOAD_2026-09-08.md)で6版1,000件・10同時作成のロックタイムアウトを再現し、親ID辞書の作成を1操作1回に修正。同条件の中央値は約9.96秒から1.36秒へ変化し、修正後160操作とPG27テストが成功。ロック範囲・後続保護は維持。局所測定であり、全体CIと正式な性能条件の達成は未確認。RDS復元の承認待ちとStripe保留は継続する。

配布物の更新（2026-09-08）: [候補46530ebc](RUNTIME_CANDIDATE_46530EBC_2026-09-08.md)の通常Dockerイメージを作成し、PostgreSQL 18.3・本番設定での隔離起動、HTTP静的配信、check --deployに成功。同候補のPR/push CIも全5ジョブsuccess。単体・統合1747成功/28省略、PG284成功/38サブテスト、ブラウザ186成功。下段の同候補CI待ちは解消。共有環境への反映や既存DBの復旧を証明する結果ではない。

ブラウザ検証の追加（2026-09-08）: [テーマフォントの自己配信](LOCAL_THEME_FONTS_2026-09-08.md)と[登録時のフォーカス保護](SIGNUP_FOCUS_2026-09-08.md)を実装。外部通信なしでゲスト参加・通常登録・引継ぎが3ブラウザ成功。認証30件と静的配信・回帰4件も成功。変更後のCI全体・実環境反映は未確認。Stripeは引き続き手動操作待ちで保留する。

O02/Q03の18系検証（2026-09-08）: [PostgreSQL 18.3の隔離復旧](RESTORE_POSTGRES18_2026-09-08.md)に成功。91テーブル/608行/87採番/画像1件を照合し、復元漏れの検出も成功。production-database CIを18.3へ合わせたが、変更後CIは未確認。実RDS/S3の復元・全運用条件・正式公開判定は未完了。

O02/O03の実環境照合（2026-09-08）: [RDS復元の事前調査](RDS_RESTORE_PREFLIGHT_2026-09-08.md)で実RDSがPostgreSQL 18.3と確認。隔離復旧の16.15とは異なるため、18系での検証を追加する。最新snapshotと基本単価を読み取り確認したが、復元先の隔離・総費用・後片付けを含む実行案は未確定。RDS作成・復元・Secrets/権限変更は未実施。

O02の候補更新（2026-09-08）: [固定候補10d21e42の隔離復旧訓練](RESTORE_CANDIDATE_10D21E42_2026-09-08.md)に成功。PG16.15でDBを別の空DBへ復元し、91テーブル/608行/87採番/画像1件が一致。画像未復元を失敗として検出し、復元後の追加採番・移行チェックも成功。試験DB/networkは削除済み。実RDS/S3・同時書き込み・RPO/RTO・旧版切戻しは別の残条件であり、正式公開No-Goを維持する。

HIGHの追加照合（2026-09-08）: [zlibの先行監査](RUNTIME_OS_AUDIT_2026-09-06.md)に、固定候補10d21e42のバージョン・ライブラリSHA-256・dpkg検証結果を追記。旧候補だけだった実測を補った。以前参照したNULL演算の上流修正を、このCVE全体の修正証拠にはしないと明記した。公式の対象バージョンとパッケージ判定の不一致は残り、HIGH・正式公開No-Goを維持する。

OS監査の一次評価完了（2026-09-08）: [残るファイル操作LOW 6件](RUNTIME_FILE_TOOLS_APPLICABILITY_2026-09-08.md)を確認し、LOW 40件すべての記録を[監査一覧](RUNTIME_OS_REVIEW_INDEX_2026-09-08.md)にまとめた。未評価0は解決済みを意味しない。旧候補の証拠を最終イメージへ照合する作業、HIGHの判定不一致、GnuTLSや依存内部の到達経路、実配備の制限などが残る。スキャン48指摘と正式公開No-Goを維持する。

OS監査の追加評価（2026-09-08、管理ツール）: 固定候補10d21e42で[LOW 4件](RUNTIME_ADMIN_TOOLS_APPLICABILITY_2026-09-08.md)を照合。btmpの初期権限・apt-key不在・chfn/chshの提供元は報告条件と不一致。File::Tempは搭載され利用経路の確認が残る。LOW個別評価は34件、未評価は6件。スキャン48指摘・正式公開No-Goを維持する。

OS監査の追加評価（2026-09-08、glibc）: 固定候補10d21e42で[LOW 7件の条件](RUNTIME_GLIBC_APPLICABILITY_2026-09-08.md)を整理。パターン入力の資源消費・不審ELFの解析・メモリ保護回避を区別し、非root/ローカルASLR有効だけで除外しない。LOWの個別評価は30件、未評価は10件。評価済みにも未解決条件があり、スキャン48指摘・正式公開No-Goを維持する。

OS監査の追加評価（2026-09-08、TLS）: 固定候補10d21e42で[TLS関連LOW 2件](RUNTIME_TLS_APPLICABILITY_2026-09-08.md)を照合。物理攻撃の報告対象構成は不一致。Pythonの既定はTLS 1.2以上だが、GnuTLS既定にはTLS 1.0が残るためBEASTは未解決として利用経路を追跡する。LOW個別評価は23件、未評価は17件。スキャン48指摘と正式公開No-Goを維持する。

OS監査の追加評価（2026-09-08、Kerberos）: 固定候補10d21e42で[LOW 4件の適用条件](RUNTIME_KRB5_APPLICABILITY_2026-09-08.md)を照合。管理ツール・KDB/RPCライブラリは未搭載だが、GSSAPIクライアントはlibpqの依存として存在するため一括除外しない。LOWの個別評価は計21件、未評価は19件。評価済みの残条件・スキャン48指摘・正式公開No-Goを維持する。

OS監査の追加評価（2026-09-08、SQLite）: 固定候補10d21e42で[LOW 2件の適用条件](RUNTIME_SQLITE_APPLICABILITY_2026-09-08.md)を照合。ZIP拡張は標準接続で利用できず条件不一致。細工されたDBの読み取りに関する1件は、本番DjangoでSQLiteを選択できないことを確認したが、依存経由を含む非該当は未確定。LOWの個別評価は計17件、未評価は23件。スキャン48指摘と正式公開No-Goを維持する。

OS監査の追加評価（2026-09-08、systemd）: 固定候補10d21e42で[LOW 4件の実行条件](RUNTIME_SYSTEMD_APPLICABILITY_2026-09-08.md)を照合。systemd実行条件の1件は不一致、journal 3件は通常アプリ経路を確認できないがライブラリ全体の非該当は未確定。LOWの個別評価は計15件、未評価は25件。スキャン48指摘と正式公開No-Goを維持する。

OS監査の追加評価（2026-09-08）: 固定候補10d21e42で[OpenLDAPのLOW 5件](RUNTIME_LDAP_APPLICABILITY_2026-09-08.md)を照合。NSS/サーバー/未搭載ツールに依存する4件は条件不一致、証明書検証の1件は未解決。curlと合わせてLOW 11件を個別照合し、残るLOW 29件とHIGH/MEDIUM/MariaDBの残条件を維持する。スキャナーの件数削減や公開合格には読み替えない。

レビュー準備（2026-09-08）: [Draft PR #2](https://github.com/sheepdog0820/iaia/pull/2)を作成。対象はcodex/formal-release-resumeからmain、作成時HEADは0a0a2e79、52コミット・91ファイル。GitHub連携は403、CLIは未ログインだったが、指定Chromeのログイン済みアカウントで作成し、Draft表示を確認できた。以前の「PR未作成」は解消したが、連携ツール自体の権限を変更したわけではない。固定候補10d21e42以降は文書変更のみとgit diffで照合。PR最新HEADのCI、マージ判断、実環境反映、正式公開判定は別に扱う。mainマージは未実行。

CI完了（2026-09-08）: 固定候補10d21e42の[CI](https://github.com/sheepdog0820/iaia/actions/runs/34191048141)は全5ジョブ成功。単体・統合1745成功/28省略/カバレッジ86.87%、PostgreSQL284成功/38サブテスト成功、ブラウザ186成功。[候補記録](RUNTIME_CANDIDATE_10D21E42_2026-09-08.md)に完了ログを照合した結果を記載。下段の同候補CI待ちは解消した。OS監査48指摘・共有環境未反映・実外部連携・運用/事業条件が残るため正式公開No-Goは維持する。

I07の接続確認（2026-09-08）: 指定Chromeから両ココフォリアテストルームに接続でき、既存の6版・7版テスト駒の能力値・ステータス・パレット保持を確認。[実ルーム再確認](CCFOLIA_ROOM_RECHECK_2026-09-08.md)に具体的な実ダイス送信候補を整理した。チャット送信の許可は質問中、画像・逆方向取り込みも未実施。最新候補の再取り込みやI07全体の成功とはしない。

固定候補の更新（2026-09-08）: [10d21e42の通常本番用イメージ](RUNTIME_CANDIDATE_10D21E42_2026-09-08.md)を新規ビルドし、アプリ510ファイルの一致、隔離PG/Redisでの通常起動・移行・登録画面・静的配信・本番設定チェックに成功。CIはproduction-database/lint-security/system成功、残る2ジョブは実行中。実外部連携・実環境反映・正式公開判定は未完了。

直近修正のDB検証（2026-09-08）: アプリ候補59f07079で、報酬反映先の照合・同時反映・添付エラー秘匿・ダウンロード保護を隔離PostgreSQL 16でも実行し、36件成功、省略なし。[実行条件とCI補完](RECENT_FIXES_POSTGRESQL_2026-09-08.md)を参照。専用DBコンテナは削除済み。CI全体は実行中で、実稼働イメージや共有環境の検証完了ではない。

F03 / F04の追加修正（2026-09-08）: [報酬再反映時のキャラクター照合](REWARD_CHARACTER_TARGET_2026-09-08.md)を実装した。参加キャラクターの差し替え後に以前の成長記録を誤更新する経路を再現し、不一致時は既存記録を保持して400とする。報酬API5件成功。実環境未反映・候補CI未確認で、既存データの自動復元は含まない。

F05 / Q04の追加修正（2026-09-08）: [添付アップロードの内部エラー情報保護](ATTACHMENT_ERROR_PRIVACY_2026-09-08.md)を実装・局所検証した。予期しない例外は詳細を含まない500応答とし、アプリの権限不足と保存先のアクセス拒否を区別する。関連26件と追加ケースを含む情報保護7件が成功。実環境未反映であり、実S3/CDN保護・候補CI・全体公開判定の未完了は維持する。

現在地（2026-09-08、後続更新）: アプリ候補63734b29の[CI](https://github.com/sheepdog0820/iaia/actions/runs/34185286562)はsuccessを確認済み。下段の同候補CI待ちは解消。Stripeはユーザーの依頼により[手動操作待ちの再開タスク](STRIPE_CONNECTION_PENDING.md)として保留し、他の作業を先行する。B01〜B05の実サービス検証は未完了。OS監査では[curl 6件の適用条件](RUNTIME_CURL_APPLICABILITY_2026-09-08.md)を固定イメージのバックエンドと照合した。指摘の抑制や全体合格への変更はない。

最新更新（2026-09-08）: 世代削除修正456bc615のCIは全5ジョブ成功（単体・統合1731成功/27省略、PostgreSQL273成功、ブラウザ186成功）。日程変更はユーザー承認のA案に基づき[セッション編集に限定する修正](DATE_POLL_FINAL_DATE_POLICY_2026-09-08.md)を実装し、関連PostgreSQL32件・ブラウザ3件成功。こちらは別候補のためCI完了を確認する。

共有DBの[一時読み取り検査](DATABASE_PREFLIGHT_2026-09-06.md)は1米ドル以内の見積もりでユーザー承認範囲内として実行し、終了0・read_only=true。旧キャラクター列なし、複数ロール0件・重複0組。schedules/0055とaccounts/0064は未適用。検査用タスク停止・定義登録解除・専用タグ削除まで完了し、サービスは定義40のまま正常。以下の旧記録にある「検査承認待ち」「日程変更方針回答待ち」はこの結果で置き換わる。DB移行・アプリ反映・実サービス検証と正式公開判定は未完了。

2026-09-08の世代削除修正（F04 / Q04）: ユーザーが「後続を残す」方針を承認。6版・7版とも、通常削除では後続の履歴をつなぎ直し、一括削除でも後続の版別データが連動して消えないよう修正した。隔離PostgreSQLで関連30テスト成功、省略なし。[世代削除の記録](CHARACTER_LINEAGE_DELETION_FINDING_2026-09-08.md)を参照。実環境反映・共有DBマイグレーション適用・既存データの影響調査は未実施。旧候補のCI成功を今回の修正候補の成功とは扱わない。

現況の照合（2026-09-08、アプリ候補3da61949時点）: codex/formal-release-resumeへpush済み。[同候補のCI](https://github.com/sheepdog0820/iaia/actions/runs/34175817824)は実行中であり、全体合格は未確定。全5ジョブの成功を確認済みの直近アプリ候補は67221be6（[CI](https://github.com/sheepdog0820/iaia/actions/runs/34174163214)）。以下の旧候補の結果を最新候補の成功として扱わない。今回の作業ではmainへの追加マージ・実環境への配備は未実施。CIの本番DB検証は隔離PostgreSQLであり、共有環境のDB検査を完了した意味ではない。

### 直近の修正と受け入れ条件の対応

この表は下段の旧候補の証拠を補足する。各公開条件の未確認範囲は維持する。

| 条件 | 新たな証拠 | 未完了の範囲 |
| --- | --- | --- |
| F03 | 日程調整の競合・入力検証に加え、[確定後はセッション編集で変更](DATE_POLL_FINAL_DATE_POLICY_2026-09-08.md)する承認済み方針を63734b29で実装。異なる投票からの上書き・再開を拒否し履歴を保持。PG32件・3ブラウザ確認済み | 方針の回答待ちは解消。実環境への反映、実プレイ履歴と残る画面状態の確認は未完了 |
| F05 / Q04 | 他者の公開メモを更新・削除できる不備を3da61949で修正。関連77テスト成功、変更分岐の両経路を実行。[権限修正](SCENARIO_NOTE_PERMISSIONS_2026-09-08.md)を参照 | 実環境未反映。シナリオ・添付・共有・配送全体の監査完了ではない |
| I07 | CCFOLIAの外部画像URLに関する公式仕様と既存出力を照合し、[画像互換性の記録](CCFOLIA_IMAGE_COMPATIBILITY_2026-09-08.md)を作成 | 実ルームでの画像・ダイス・逆方向取り込みとICS受信側検証は未確認。画像要件を削除して完了にはしない |
| Q01 | 67221be6のCIで3ブラウザ計186件成功。グループ作成モーダルの準備待ちも[修正・反復検証](GROUP_MODAL_READINESS_2026-09-08.md)済み | 3da61949のCI完了、実契約導線・実機・残る画面状態は未確認 |
| Q03 | SQLiteで省略される25件を照合し、PostgreSQL CIで漏れていた並行処理11件を含む6モジュールを25b43346で追加。拡張後のコマンドを本番設定・隔離PGで実行し263件成功。[CI補完記録](POSTGRESQL_CI_CONCURRENCY_2026-09-08.md)を参照 | 後続4d7c4ea7のCIは成功。共有DBの限定した履歴/制約検査も本日12:44に完了し、CloudWatchログを再照合済み。全スキーマ監査・実環境配備・復旧は未完了 |

次の実行順序は、残るローカル検証とOS指摘の評価、承認待ちの一時DB検査、実環境への反映案の確定、承認済み対象での実OAuth・決済・配送・復旧検証。実操作の承認待ちを模擬テストで代替しない。Stripe再認証、背景透過の利用/保持条件、事業者・税表示、規模/SLO・RPO/RTO・費用等の判断も必要。既に確定した無料範囲・画像5枚・月額480円/年額4,800円は再判断待ちに戻さない。

OSパッケージ監査の更新: 不要なビルド用パッケージ除去とTerraform作業ファイル除外後の通常イメージでScoutは終了2、High 1・Medium 1・Low 40・Unspecified 6を報告。旧候補のLow 105から65件減ったが、合格ではない。対象イメージIDと検証範囲は[削減記録](RUNTIME_BUILD_DEPENDENCIES_PROBE_2026-09-06.md)を参照。zlibは説明対象とDebianのパッケージ判定に不一致があり、非該当とは未確定。Python/npm監査とは別の未解決事項として、[調査記録](RUNTIME_OS_AUDIT_2026-09-06.md)の公開前条件を維持する。

再開時の更新: 654d5bb2をユーザー承認によりmainへマージ・push済み。同SHAの[作業ブランチCI](https://github.com/sheepdog0820/iaia/actions/runs/34012144928)は全5ジョブ成功し、Banditの個別判定・例外報告の修正を含む。下記の「LOW560でCI未達」「mainマージ待ち」は過去候補の記録であり、現在の阻害要因ではない。main反映後の[CI](https://github.com/sheepdog0820/iaia/actions/runs/34013963856)もsuccessを確認済み。実AWSは旧版・worker/beat未作成のままで、正式公開は引き続きNo-Go。DB履歴・スキーマの実環境検査を進めるため、[読み取り専用検査](DATABASE_PREFLIGHT_2026-09-06.md)を作業ブランチで追加・隔離検証した。共有DBへは未実行。

01a52f52の更新: 固定候補のブラウザ全体は25フローファイル・3ブラウザ各58件、計174成功、skip/retry/flakyなしで完了。通常本番用イメージの隔離起動・静的配信・設定検査も成功。SQLite1683成功/11skip・86.99%、PG1694成功/skipなし・87.62%、双方終了0で完了。SQLiteのskip11件はPGで成功。CI相当のflake8/Black/isortは成功、BanditはLOW560・終了1であり、リモートCIと実サービスの未完了は維持する。以下の前候補の失敗は監査履歴として保持する。

前候補の検証: 固定4499b243はSQLite1683成功/11skip、PG1693成功/1失敗、ブラウザ166成功/2失敗。時間計測・動画操作のテスト修正後は関連検証に成功したが、ホーム画面も読み込み中クリックの再現・配置修正後に関連15件が成功。これらを含む固定候補の全体再検証が残る。ユーザー指定の実CCFOLIAルームでは6版・7版のサーバー出力から各1体の取り込みと値・パレットの保持を確認した。画像・実ダイス・逆方向取り込みは未確認。下記の過去候補の成功で置き換えず、[最新の検証記録](FULL_VALIDATION_2026-09-06.md)を参照する。正式公開のNo-Goは維持する。

2026-09-06更新: ユーザーが料金（月額480円・年額4,800円）、背景透過のみ有料、シナリオ作成編集・CCFOLIAインポート・関連シナリオ変更は無料、画像は全プラン5枚と確定した。[反映記録](FREE_FEATURE_POLICY_2026-09-06.md)を参照。以下の2026-09-05の料金・範囲に関する「未承認」「回答待ち」と旧比較表はこの決定で置き換わる。実Priceとの照合・実サービス検証・公開判定は未完了で、過去の704c6f06の全体検証を今回の変更後の全体合格として扱わない。

更新日: 2026-09-05。検証ごとに対象コミットが異なるため、監査記録の各実行条件を参照する。過去の成功結果を最新コード全体の合格証拠として扱わない。

現時点の公開判定は **No-Go（必須検証・事業判断が未完了）**。無料βへの縮小はしない。以下の「部分確認」は公開条件の合格を意味しない。実行結果の詳細・対象コミット・ローカル証跡は [監査記録](FORMAL_RELEASE_AUDIT_2026-09-05.md) を参照する。

2026-09-06の追加検証: f016a66dのブラウザ全体はChromium/Firefox/WebKit各49件、計147件成功（再試行・skip・flakyなし）。同候補の通常本番用イメージも隔離PG/Redisで起動・静的配信・check --deploy成功。バックエンド全体もf016a66dでSQLite1673件成功/10skip・86.98%、PG1683件成功/skipなし・87.56%、双方終了コード0。件数はJUnitのtestcase要素を集計し、SQLiteのskip10件はPGで成功している。以後の変更には関連検証が必要。過去のブラウザ失敗・未再現の停止記録は保持する。リモートCI・実サービス検証の未完了は変わらない。[追加検証記録](FULL_VALIDATION_2026-09-06.md)を参照。

カレンダー・アイコンのCDN停止、manifest生成、本番保存設定、日程投票の時間帯/キャッシュ、グループ権限応答、HTML挿入、明暗配色、ゲスト参加の失効再確認と引き継ぎ案内を是正した。固定候補704c6f06で3ブラウザ33件と追加75件（別DB・別通信条件）、両DB全体テスト、本番用イメージの隔離起動/HTTP配信が成功。追加75件の通信遮断時は73成功/2失敗であり、全件のオフライン動作を保証しない。実S3/CDN配信とリモートCI、実認証/決済/配送等は未検証。

## 判定表

各行の必須条件を満たすまで、その行は未完了とする。機能を一覧から削除して完了扱いにしない。証跡には日時、対象コミット/イメージ、環境、入力条件、期待値、実結果、証跡の場所を記録する。

| ID | 公開条件・合格の定義 | 現在の証拠と限界 | 次の作業 / 担当 |
| --- | --- | --- | --- |
| F01 | 新規登録、ログイン、ログアウト、復旧、退会が通常ユーザーで成立する | 登録・メール資格情報ログインは3ブラウザで確認。復旧・退会の実運用は未確認 | メールの宛先と専用アカウントを定め、復旧・退会・保持データを確認 / Codex、宛先・保持方針は人間 |
| F02 | グループ作成・参加・招待・ゲスト参加と所有権引継ぎが成立する | 通常ユーザーの非公開グループ作成と非参加者の閲覧拒否を3ブラウザで確認。5244399b後の追加E2Eで通常登録・公開グループ参加・管理者追加/解除・解除直後の更新拒否・作成者の降格/除名拒否が3ブラウザ成功。招待の同一利用者による同時参加の410/500を修正しPG関連54件成功。追加E2Eで通常登録GM・未ログインゲストの参加、通常登録後のclaim、使用済み招待拒否、claim前404/後200を3ブラウザ確認。後続で招待発行/claimを画面操作に更新し、日本語案内・390px幅での引き継ぎ入力/保存を3ブラウザ確認。所有権移譲は未実装で公開範囲を確認中 | 招待失効・ゲスト参加・競合を継続検証。所有権引継ぎの範囲を確定し実装/検証 / Codex、範囲判断は人間 |
| F03 | 日程候補、回答、確定、セッション準備・完了・履歴が保存される | 通常登録GM/PLの日程作成・投票・確定・セッション完了を3ブラウザ確認。[確定後はセッション編集で変更](DATE_POLL_FINAL_DATE_POLICY_2026-09-08.md)を承認・実装し、修正を含む20803480は開発AWS定義45へ反映済み。競合・異なる投票からの上書き拒否はPG検証済み | 実プレイ履歴、残る画面状態と実環境の全フローを検証 / Codex |
| F04 | CoC 6版/7版の作成・編集・画像・技能・版管理・削除が仕様どおり | 両版の保存・画像5枚上限・既存超過画像保持を局所/ブラウザ検証。後続世代保持、同時画像追加、順序0の修正は反映済み。[accounts/0064の適用は終了0](AWS_PRE_DEPLOYMENT_14AC4746_2026-09-08.md)。背景透過は権限修正後に実AWSで合成画像の処理成功 | 実ファイル保持、全技能種別/計算方式、プレミアム利用者の背景透過画面全経路を確認。実データの破壊的試験は承認対象 / Codex |
| F05 | シナリオ管理、秘匿HO、添付、GMメモを対象者だけが操作・閲覧できる | 認可付き配信とGMメモの権限修正を開発AWSへ反映済み。[非公開12パターンのCDN拒否](AWS_PRE_DEPLOYMENT_14AC4746_2026-09-08.md)は合成ファイルで全403、権限ありの実S3取得は200/no-store、一般・匿名404。試験データは削除/ロールバック済み | 全添付・共有・秘匿HO・外部出力とブラウザ認証を通る配送経路の監査を継続 / Codex |
| B01 | 月額・年額料金と無料/有料の機能差が承認され、表示・Price・権限と一致する | 月額480円/年額4,800円、背景透過のみ有料、画像5枚共通は承認済み。[実テストPriceの金額・通貨・周期・同一商品](STRIPE_SANDBOX_VERIFICATION_2026-09-13.md)を照合済み | 本番Price・公開画面・AWS設定との最終照合 / Codex、設定変更は承認対象 |
| B02 | 実Stripeテストモードの月額・年額Checkoutで権限と監査ログが正しく更新される | [月額Checkout](STRIPE_SANDBOX_VERIFICATION_2026-09-13.md)と[年額・3D Secure](STRIPE_ADDITIONAL_VERIFICATION_2026-09-13.md)の実画面・署名付きWebhook・隔離DBの権限反映を確認 | AWSでログイン済み購入・戻り画面・監査記録を照合 / Codex、設定変更は承認対象 |
| B03 | 更新・期間末解約・支払失敗/回復・返金/異議・退会で権限が過不足なく変化する | 月額・年額更新、失敗/回復、返金、異議、カード変更、期間末解約を実サンドボックスで確認。[解約後勝訴による誤付与も修正・実証](STRIPE_ADDITIONAL_VERIFICATION_2026-09-13.md) | [権限停止中・未終了契約の退会防止](STRIPE_DELETION_GUARD_2026-09-19.md)を修正し隔離DBで検証。[ユーザーAPI・管理画面の削除経路](STRIPE_DELETION_PATHS_2026-09-19.md)も共通課金確認へ統一しPGで検証。[4経路と実Stripeの接続](STRIPE_DELETION_PATHS_API_2026-09-19.md)も23項目成功。[購入画面失効・Stripe残契約照会・退会中の購入防止](STRIPE_DELETION_CHECKOUT_2026-09-19.md)も修正しPG・実APIで検証。[退会画面の3ブラウザー検証](STRIPE_DELETION_BROWSER_2026-09-19.md)も成功。[退会後の実署名付き購読通知の逆順・重複](STRIPE_DELETION_SIGNED_2026-09-19.md)も13項目成功。[退会と実署名付き購読作成通知のPG同時処理](STRIPE_DELETION_RACE_2026-09-19.md)も両ロック順で成功。実Stripe契約を伴うブラウザー退会、その他通知種別との並行処理、複数返金/異議、AWS上の全フローを確認 / Codex |
| B04 | Webhook重複・順序変動・一時DB障害で課金権限を失わず再処理できる | 実署名通知の重複・失敗再送・購読通知の逆順を確認。[重複購入防止・応答喪失の実API再送・PG同時購入](STRIPE_CHECKOUT_RETRY_2026-09-13.md)も成功 | [請求成功/失敗の逆順・別請求同時更新](STRIPE_INVOICE_ORDERING_2026-09-19.md)は修正し実署名通知・隔離PGで検証済み。[複数停止理由の保持](STRIPE_MULTIPLE_REVOCATIONS_2026-09-19.md)も修正・実検証済み。[同一異議の通知逆順](STRIPE_DISPUTE_ORDERING_2026-09-19.md)も実署名通知・隔離PGで検証済み。[古い購入完了通知・同時処理](STRIPE_CHECKOUT_ORDERING_2026-09-19.md)も修正し単体/PG・実API読み取りを確認。[課金メールの永続キュー・再試行](BILLING_EMAIL_DELIVERY_2026-09-19.md)を実装し隔離PG・ローカルSMTPで検証。[候補99acd8caの全6ジョブCI・コンテナ/DB互換性](STRIPE_CANDIDATE_CONTAINER_2026-09-19.md)は成功。[実署名付きCheckout完了を解約後に処理する試験](STRIPE_CHECKOUT_SIGNED_ORDER_2026-09-19.md)も10項目成功。[統合候補0f6b81feのコンテナ8項目](STRIPE_CONTAINER_0F6B81FE_2026-09-19.md)も成功し同候補のCIは全6ジョブ成功。後続の[削除経路修正6ff9a1f9の配布コンテナ](STRIPE_CONTAINER_6FF9A1F9_2026-09-19.md)も起動・9回帰テスト成功。[6ff9a1f9のCI全6ジョブ成功](STRIPE_CI_6FF9A1F9_2026-09-19.json)を確認。AWS配送、ログイン状態での購入戻り画面、その他Webhook競合を確認 / Codex |
| B05 | 有料必須ゲートが成功し、その記録が実Stripe/アプリ状態に一致する | ゲートの動作確認と個別の実サンドボックス証跡あり。[候補監査](STRIPE_CANDIDATE_AUDIT_2026-09-19.md)。実AWSの有料有効状態の正式記録は未作成 | AWSの実証跡を作成し、形式チェックと独立照合を実行 / Codex |
| I01 | Google認証の初回・既存連携・取消・失効が実認可で成立する | ID優先・追加メール確認・明示的連携・登録競合を修正。[承認済みChromeで再連携](GOOGLE_RECONNECT_2026-09-10.md)し、実コールバック後の認可保存と再読み込み後の維持を確認。[期限不明トークンの更新](GOOGLE_TOKEN_EXPIRY_2026-09-22.md)もローカル検証済み。Google未確認アプリの案内は残る | 初回登録、取消・失効・実トークン更新、メール到達、Google公開審査/設定を実証 / Codex、権限変更は人間承認 |
| I02 | Discord認証の初回・既存連携・取消・失効が実認可で成立する | ローカルAPIテスト、停止済み利用者の拒否、[外部通信障害と設定不足の再試行可能な応答](OAUTH_PROVIDER_RESILIENCE_2026-09-22.md)を確認。実認可・取消・失効は未確認 | 同上 / Codex、人間 |
| I03 | X認証の初回・既存連携・取消・失効が実認可で成立する | ローカルAPIテスト、停止済み利用者の拒否、[外部通信障害と設定不足の再試行可能な応答](OAUTH_PROVIDER_RESILIENCE_2026-09-22.md)を確認。実認可・取消・失効は未確認 | 利用条件と公開設定を確認し実認可 / Codex、人間 |
| I04 | Google Calendar片方向同期が成功し、再試行・解除で重複/漏えいがない | 実行時権限再確認・既存予定更新と[期限不明トークンの更新](GOOGLE_TOKEN_EXPIRY_2026-09-22.md)をローカル検証。[API障害・broker停止時の失敗保持と再試行案内](INTEGRATION_RETRY_GUIDANCE_2026-09-22.md)もmockで確認。Google認可は保存済みだが、ブローカー/workerがなく実同期は未確認。現行実装はprimaryカレンダー固定 | [一時AWS接続試験](GOOGLE_WORKER_CONNECTIVITY_RESULT_2026-09-10.md)は成功・削除済み。継続基盤の構成・承認後、primary内の限定テスト予定で作成/変更/失効/再試行/解除を検証 / Codex、対象・変更範囲は人間承認 |
| I05 | Google Sheets出力が対象データだけを出力し失効・再試行から復旧できる | 連携無効化・スコープ削除・ユーザー無効化後の送信拒否と[期限不明トークンの更新](GOOGLE_TOKEN_EXPIRY_2026-09-22.md)をローカル検証。[外部例外の非露出と再試行案内](INTEGRATION_RETRY_GUIDANCE_2026-09-22.md)、[大規模出力の分割・進捗・部分反映警告](GOOGLE_SHEETS_LARGE_EXPORT_2026-09-22.md)もmockで確認。Google認可保存は成功、実出力は未確認。対象ID省略時の全キャラクター出力で実試験を代用しない | worker基盤の承認・起動後、専用シートと限定キャラクターで内容・権限・失効・再試行を確認 / Codex、人間は対象承認 |
| I06 | Discord通知が指定先だけへ届き、失敗・再送・無効化が機能する | [Webhook URLを履歴へ残さない失敗保存と模擬画面再送](INTEGRATION_RETRY_GUIDANCE_2026-09-22.md)をローカル確認。実配送は未確認 | テスト専用宛先で実配送。送信内容・宛先を事前に具体化 / Codex、送信承認は人間 |
| I07 | ICS購読の更新・トークン失効とCCFOLIA出力/無料インポートが受け取り側で使える | ICSの日本語長文・CR改行の出力を修正し、折り返し・内容保持・旧トークン失効をローカル確認。CCFOLIA JSONダウンロードとTablenoへの無料インポートE2E成功。4499b243のサーバー出力をユーザー指定の実6版/7版ルームへ各1体取り込み、能力値・ステータス・パレット保持を確認。画像・実ダイス・ICS購読は未確認 | 専用の受け取り側で内容、秘匿、文字化け、失効を確認 / Codex |
| Q01 | PC・スマートフォンの主要操作が読めて操作でき、重大なJSエラーがない | 20803480のPlaywright CIが成功し、開発AWS反映後に既存ログインで一覧・詳細・統計表示を確認。平均時間undefinedhは0.6hへ改善。旧候補で3ブラウザ186件の成功記録もある | 実機・全状態・実契約導線は未確認。後続Terraform/文書を含む候補CIは別途完了確認 / Codex |
| Q02 | 合意した人数・データ量・同時利用で応答/エラー率の目標を満たす | 基準は登録100人・同時10人、通常操作p95が3秒以内、予期しないエラー0件として承認済み。7b196988の隔離通常イメージで[一覧900件](READ_API_OPTIMIZED_RUNTIME_2026-09-10.md)と[基本の作成・編集・再取得1,200件](WRITE_API_RUNTIME_2026-09-10.md)がエラー0、各操作p95は基準内。背景透過は別枠で、[実AWSの処理成功](BACKGROUND_REMOVAL_IAM_FIX_2026-09-08.md)を確認済み。全通常操作・実AWSの性能合格は未確認 | 画像・日程・参加者/秘匿情報等の不足操作、長時間・本番相当試験、開発AWS反映後の認証済み操作と性能再測定 / Codex |
| Q03 | リリース候補SHAのCI・固定依存関係・本番DB検証が成功する | [10月2日の照合](RELEASE_STATE_2026-10-02.md)でマージ5caeaf2c、現main35ecfd5c、AWSタグ対応c6226ddbの各CI成功を確認。稼働定義52の実行digestはECRと一致しreadiness成功。先行候補の隔離PG/Redis検証は当該版の証拠として保持 | mainと稼働版の統一、ソース/配布物の一致、共有DB0065〜0067の適用証拠、全スキーマ/実データ監査、本番相当の移行・復旧は未完了 / Codex、人間 |
| Q04 | 情報保護の重大な既知欠陥がなく、セキュリティ指摘に判定がある | 非公開ファイル保護を反映し、実S3/CDNの12パターン拒否と認可付き取得を実証済み。[統計画面のAPI値](STATISTICS_DYNAMIC_HTML_SECURITY_2026-09-22.md)と[6版・7版カスタム技能名](CHARACTER_CUSTOM_SKILL_SECURITY_2026-09-22.md)による動的HTML生成を修正し3ブラウザで非実行を確認。[bb61b0e6の通常配布物](RUNTIME_OS_BB61B0E6_2026-09-22.md)の再スキャンは36件（HIGH2/MEDIUM1/LOW33）。Perl HIGHは脆弱なPod::Textが配布物にないことを確認したが、zlib HIGHはDebianで未修正 | 未修正zlib、tar、スキャナー非ゼロを含む残リスク判定、全動的表示・配送・権限経路監査を継続 / Codex、人間 |
| O01 | 本番設定・秘密情報・監視・問い合わせ配送が正しく構成され実証される | [10月2日の読み取り確認](RELEASE_STATE_2026-10-02.md)ではWeb定義52が正常稼働。対象clusterのサービス一覧はWeb1件で常設worker/beatサービスは見つからない。過去のアラーム3件・SNS購読confirmedは実通知到達を証明しない | 一時AWS通信試験は成功・削除済み。継続運用/夜間停止・監視・問い合わせ配送と課金メール実効設定を別途実証 / Codex、人間承認 |
| O02 | DBと画像のバックアップを復元し、合意RPO/RTOと整合性を満たす | [実RDS snapshot復元](RDS_RESTORE_RESULT_2026-09-08.md)は承認後に実施し、別の非公開DBの読み取り検査が終了0、限定メタデータが一致。一時リソース削除済み。ローカルではDB/11ファイル項目の復元も成功 | 実S3の世代選択とDB整合、アプリ切り替え、主要操作、RPO24時間/RTO4時間を含むサービス全体の復旧は未証明 / Codex、人間承認 |
| O03 | リリース候補の移行・ロールバックが本番相当で実証される | 隔離環境のデータ入り移行・旧イメージ復元成功に加え、共有DB0064/0055適用と開発AWS反映が完了。直近の統計反映はDB変更なしで旧定義44への復旧手順を記録 | 本番相当の同時書き込み・全UI・DB/S3の切り戻しとRPO/RTOを検証。旧定義へ戻すだけで過去の脆弱性を再導入しない / Codex、人間承認 |
| O04 | 料金・事業者表示・保存方針・問い合わせ・公開時期・費用上限が確定する | 無料範囲・画像5枚共通は承認済み。9月12日に[個人事業者・請求開示方式](INDIVIDUAL_SELLER_POLICY_2026-09-12.md)、support@tableno.jp、月額480円/年額4,800円（税込）、解約期限・返金条件を確定し、画面と4種類の設定例へ反映。変更はmainへマージ済みだが、現行AWSの公開表示・実運用の最終照合は未完了 | 実情報の非公開保管、開示窓口の受信/返信、保存期間・背景透過保持条件・税務対応・公開時期・費用上限等の残る判断と実運用を確認 / 人間、反映はCodex |


## 人間の判断に使う現行案

Q04補足: グループ詳細の説明・メンバー名・作成者名のHTML挿入を修正し、別利用者による文字表示と管理者操作の6件が3ブラウザで成功。66bab03f後、招待一覧のグループ名・招待者名・メッセージも修正。5cd8f3ec後のE2Eでは、アプリ内招待通知の安全な文字表示・既読保存から招待一覧の文字表示・画像要素/実行フラグなし・承認後のメンバー登録まで3ブラウザ成功。全表示経路の監査は継続し、実環境未反映のためNo-Goを維持する。

以下は2026-09-06の承認済み方針。実Stripe設定や全APIの検証完了を示すものではない。

| 項目 | 無料 | 有料 |
| --- | --- | --- |
| 料金 | 無料 | 月額480円 / 年額4,800円 |
| キャラクター・セッション管理 | 利用可 | 利用可 |
| シナリオアーカイブ・作成・編集 | 利用可 | 利用可 |
| 作成済みセッションの関連シナリオ変更 | GM・閲覧権限に従い利用可 | 同左 |
| CCFOLIAインポート | 利用可 | 利用可 |
| キャラクター画像 | 1キャラクター5枚 | 同左 |
| 画像の背景透過 | 利用不可 | 利用可 |
| 支払い方法・解約・請求履歴 | 対象外 | Stripe Customer Portal |
| 運営発行コード | 入力可 | 期限付き/無期限の権限付与。課金契約とは別 |

シナリオ画像の既定上限は全員共通で1枚5 MiB・1回10枚。キャラクター画像5枚の総枚数上限とは別の制限である。キャラクターの既存の上限超過画像は維持する。無料化後もログイン・可視性・所有権・GM権限による制御を維持する。返金・保存・事業者表示の方針は別途確認する。

性能・復旧基準は[2026-09-08の承認記録](RELEASE_CRITERIA_DECISIONS_2026-09-08.md)に基づき、登録100人・同時10人、通常操作の95%が3秒以内、予期しないエラー0件、RPO24時間・復旧対応開始からRTO4時間とする。背景透過は別枠で測定する。データ量・操作配分・アップロード容量・実行環境は各試験の条件として記録し、測定範囲を超えて合格としない。合格基準を緩めて成功扱いにしない。

## 実環境検証を開始するための準備（9月8日以前の経過記録）

- GitHub: [Draft PR #2](https://github.com/sheepdog0820/iaia/pull/2)は作成済み。2026-09-08にopen/draft、対象main、head 4d7c4ea7をAPIで確認。通常push可能。PR作成用の接続を再度依頼する必要はない。4d7c4ea7のCIは完了したが、mainへのマージ承認と共有環境の実証は別の条件。
- Stripe: 当時は登録待ちだったが9月13日に解消済み。現在は[再開タスク](STRIPE_CONNECTION_PENDING.md)のAWS接続・配送基盤・実環境確認を進める。古い登録待ちを現在の操作停止指示として扱わない。
- AWS開発環境: 2026-09-05の再確認でECS desired/runningは1/1、ヘルス200へ変化。このタスクから起動していない。稼働版との差分にはDB移行があり、[配備準備計画](AWS_PRE_FORMAL_RELEASE_VALIDATION_PLAN.md)で対象SHA・移行・復旧・費用の未完了項目を整理した。稼働中サービスを勝手に停止せず、配備前に具体案を揃えて承認を求める。
- 外部の検証対象: Googleの専用カレンダー/シート、Discordの専用通知先、ICS購読先、CCFOLIAの専用ルームを定める。一般利用者へ試験通知しない。

上記の接続・判断待ちだけで全作業を停止しない。Codexは権限のある範囲で固定依存関係検証、通常ユーザーの検証不足、性能試験設計、復旧計画、残るコード監査を進める。

Google認証の固定ID優先・追加メール確認・明示的連携の修正と隔離検証結果は[詳細記録](GOOGLE_IDENTITY_REMEDIATION.md)を参照。実OAuth/メール到達・ブラウザ同時登録・最終候補検証は残り、正式公開判定はNo-Goを維持する。

2026-09-06の実Google確認: ユーザーが指定したChromeのGoogleアカウントから、stg.tableno.jpの既存「しぇぱ」へ再ログインできた。追加認可の未確認アプリ警告後、ユーザーから連携操作完了の連絡を受けて再確認したが、Calendar設定の保存完了表示は出ず、再読み込みで無効・未連携に戻った。ユーザー操作待ちではなくアプリ側の保存・認可結果の調査が必要で、原因と付与scopeは未確定。実同期・出力は未実施で、Google側の公開/審査状態と稼働アプリの候補SHA照合も必要。既存アカウントの再ログイン以外のI01/I04/I05条件は未達。詳細は[追加検証記録](FULL_VALIDATION_2026-09-06.md)を参照する。

後続のローカル修正で、追加連携の認可scope・資格情報を保存する経路を追加し、関連SQLite70件/1skip、PG71件/skipなし、双方31サブテスト成功、新規保存処理の行・分岐カバレッジ100%を確認した。Google応答は模擬しており、共有環境は未反映。ユーザーごとに有効なGoogle連携資格情報を1件に揃えるため、適用後の追加連携は以前のGoogleトークンをローカルで置き換える。配備範囲の確認と実認可・期限更新・同期検証が必要で、I04/I05を完了扱いにしない。
