# アプリ静的セキュリティ検査の分類

2026-09-05、対象コミット494abd0d。Banditをaccounts/api/scenarios/schedules/support/tablenoに再帰適用した。リポジトリ全体や実環境の検査ではない。

検査エラー0、HIGH 0、MEDIUM 0、LOW 557、終了コード1。指摘が残るため終了コードを成功へ変換しない。証跡はtmp/bandit-494abd0d-apps.jsonと同.log。

## 分類

| 対象 | 件数 | 判定と限界 |
| --- | ---: | --- |
| testで始まるモジュール・tests配下 | 475 | テスト用パスであり、本番リクエスト処理の指摘ではない。各指摘の個別安全性を一律に承認したものではない |
| データ作成用management command | 71 | 6ファイルすべてhandleにlocal_development_onlyを付けていることをASTとコードで確認。DEBUG/APP_ENV/ENVIRONMENTを検査し、共有環境ではDB操作前に拒否する。既知のテスト用パスワードや非暗号乱数を本番アカウントへ使用してよいという意味ではない |
| その他のコード・既存移行処理 | 11 | 下表で用途と残作業を個別に確認 |

## 実行コード側の11件

| ファイル・行 | 指摘 | 判定 |
| --- | --- | --- |
| accounts/character_models.py:1938 | B311 | TRPGダイスの乱数。認証トークン・パスワード生成に使用する箇所ではなく、この指摘は公開阻害にしない |
| accounts/utils/dice.py:297 | B311 | 能力値のダイス。上記と同じ判定 |
| accounts/views/api_auth_views.py:140 | B105 | Google token_uriという設定キーと公開エンドポイントのURL。ハードコードされた秘密情報ではない |
| schedules/google_tokens.py:10 | B105 | 公開GoogleトークンエンドポイントのURL。秘密情報ではない |
| schedules/views.py:3111 | B105 | can_manage_secret_content=Falseという権限フラグ。パスワードではない |
| tableno/settings.py:319 | B105 | reset_passwordフォームのクラスパス。パスワードではない |
| accounts/forms.py:80 | B110 | allauthメール照合例外を無視して別の照合へ移る。認証時の例外範囲と障害の識別を追加確認する |
| accounts/serializers.py:1129 | B110 | キャラクター画像の代替表示で例外を無視する。既存表示へのフォールバック範囲と障害検知を追加確認する |
| accounts/serializers.py:1524 | B110 | 容量推定後のseek(0)失敗を無視する。読み取り位置・検証後の保存への影響を追加確認する |
| accounts/views/character_views.py:2400 | B112 | 技能一括作成で例外を無視して次の入力へ進む。部分失敗の応答と保存結果の整合性を追加確認する |
| schedules/migrations/0041_remove_sessiontemplate_group_and_more.py:17 | B110 | 旧テンプレート画像の削除失敗を無視する既存移行。適用済み移行を独断で書き換えず、未削除ファイルの確認・対処方針が必要 |

6件は用途から分類できたが、例外処理5件とテスト側の個別判定は残る。実サービスの認可、ストレージ/CDN迂回防止、過去ログ、データ保持・削除の検証はこの検査では証明できない。Q04と正式公開判定は未達を維持する。検査・分類に伴うコード変更や実データ操作は行っていない。

開発コマンドの境界テストも再実行し、1件・56 subtests成功（0.27秒）。SimpleTestCaseでDBアクセスを禁止した状態で、共有環境の設定ではコマンドが拒否されることを確認した。対象コマンド・ガード・テストは固定イメージ58a27172と494abd0dで差分なし。証跡はtmp/command-boundaries-static-triage.log。

## 後続の是正

技能一括保存のB112は03c53fc5で例外の無視を廃止し、全件保存または全件巻戻しに変更した。さらにポイント再配分の順序依存を回帰テストで確認し、同じトランザクション内で対象技能の配分を解放してから通常のモデル検証付きで保存するよう是正した。未編集技能を含む最終合計の上限超過は拒否する。詳細・検証結果は公開監査記録を参照。上表の494abd0d時点の走査結果は書き換えず、残る4箇所の例外処理、他経路との同時編集、実サービスの検証は引き続き未完了とする。

続いてaccounts/forms.pyのメール照合時のB110を是正した。EmailAddressのDB障害を無視してCustomUser照合へ進む動作を廃止し、DatabaseError時は日本語の再試行案内でフォームを拒否する。CustomUserメール照合・必須メール確認のDB障害も同じ拒否に統一し、ログは例外型だけとする。通常のメール・ユーザー名ログイン、未確認メールの拒否は既存認証テストで検証。残る画像関連2箇所・既存移行1箇所の例外処理、および実サービス検証は未完了。

画像容量検証後のseek(0)失敗を無視するB110も是正した。OSError/ValueError時は日本語の選び直し案内で入力を拒否し、読み取り位置が戻らないまま保存へ進めない。正常PNGの全内容が検証後も先頭から読めることを確認。残るメイン画像代替表示と既存移行の例外処理は未完了。

一覧のメイン画像代替表示にあるB110も是正した。存在しないcreated_atでの並べ替えが例外となり、画像が選ばれない不具合を6版/7版で再現。実在するuploaded_atを使い、メイン指定・表示順・日時・IDで一意に選ぶ単一クエリへ変更した。広い例外の無視は廃止した。ここで挙げた例外処理5件のうち、残るのは既存移行における旧ファイル削除失敗の扱いであり、適用済み移行の書き換えや共有ストレージ削除は行っていない。

## d572a618での再検査

2026-09-05、同じ6アプリ範囲を再検査。解析エラー0、HIGH/MEDIUM 0、LOW556、Bandit終了コード1。テスト478、開発コマンド71、その他7。その他は既述のゲーム乱数2・定数名等4と、旧移行のファイル削除例外1で、修正したforms.py/serializers.py/character_views.pyには指摘なし。テスト側の指摘は増えており、総件数の減少を包括的安全性の根拠にしない。証跡はtmp/bandit-d572a618-apps.jsonとtmp/bandit-d572a618-run.log。実ストレージ/CDN・実連携の残作業は解消していない。

## 77b10dedでの再検査とテスト内プロセス起動の確認

- 6アプリをBandit1.9.4で再解析し、解析エラー0、HIGH/MEDIUM 0、LOW556、終了コード1。内訳はテスト478・開発コマンド71・その他7。証跡tmp/bandit-77b10ded-apps.json、tmp/bandit-77b10ded-run.log。d572a618とファイル/指摘ID/指摘本文の多重集合を照合して差分なし。行番号の移動は同一問題として扱った。これだけでコードの同一性や安全性を証明しない。
- accounts/test_character_ccfolia_export.pyのB404（2行）とB603/B607（142・257・310・375行、各2件）、計9件を個別に確認。全てDjango TestCase内で、リポジトリ内のstatic/js/ccfolia_character_copy.jsを固定のJavaScriptテスト入力でNode実行する用途。引数配列を使い、shell=TrueやHTTP入力からのコマンド組み立てはない。本番リクエストのコマンド注入経路としては扱わない。
- NodeはPATHに依存するため、任意の信頼できないPATHで実行してよいという判定ではない。検証用イメージのNodeを使う現行手順が対象。起動タイムアウトが明示されていないため、プロセスの応答停止時にテストが長時間待つ可能性も残る。
- テスト側の残る469件、既存移行のファイル削除例外、実ログ・実ストレージ/CDN・実外部連携の検証は未完了。指摘を抑制するコード変更は行っていない。正式公開No-Goを維持する。

## 課金テストの固定値56件の用途確認

77b10dedのaccounts/test_billing.pyにあるB106 53件・B105 3件を、指摘行のリテラルとAST上の呼出先、TestCase・一時ファイルの使用箇所で照合した。アプリの秘密設定を検索・表示した結果ではない。

| 指摘・件数 | 使用箇所 | 判定と証拠 |
| --- | --- | --- |
| B106 5件 | 67、209、441、470、1043行 | User.objects.create_userのテスト用固定パスワード。Django TestCase内の使い捨てDB用アカウント。実アカウント用の初期パスワードには使わない |
| B106 46件 | override_settingsのSTRIPE_SECRET_KEY引数 | 空値・無効形式・dummy/page/preflight/remote等の名前付きテスト値。テスト実行中の設定検証・模擬Stripe検証用。sk_live接頭辞の例も本番用キーの利用を意味せず、モード拒否の試験入力。実キーの有効性を外部へ問い合わせる検証はしていない |
| B106 2件 | 4981、4994行 | TemporaryDirectory内のbase_dirを渡すself._write_envで開発設定チェックを試験。実作業ディレクトリの.envを書き換えるものではない |
| B105 3件 | 5021、5025、5026行 | 上記一時ファイル用ヘルパーの固定SECRET_KEYと空のStripe設定。呼出元の一時ディレクトリとBASE_DIRの上書きを確認 |

この56件は、本番資格情報がコードへ埋め込まれた指摘としては扱わない。テストの固定値を本番へ転用してよいという意味ではない。TestCaseの分離、実DBに接続しない実行設定、外部呼出の模擬が前提となる。実Stripe/課金ライフサイクルの合格証拠ではない。

先に確認したNode関係9件と合わせ、テスト側478件のうち65件の判定を記録した。残る413件は未判定。検査の抑制やアプリコード変更は行っていない。

## f692b994移行修正後の再解析

- 6アプリをBandit1.9.4で再解析し、解析エラー0、HIGH/MEDIUM 0、LOW556、終了コード1。77b10dedのファイル/指摘ID/指摘本文の多重集合との差分は0。accounts0055のSET CONSTRAINTSと専用PostgreSQLスキーマを使う移行テストに指摘なし。
- テストスキーマ名は固定prefixとuuid.uuid4().hexのみで構成し、外部入力からSQLを作成する経路ではないこともソース確認した。静的ツールの未検出を全SQL経路の安全性の証明にはしない。
- 証跡tmp/bandit-f692b994-apps.json、tmp/bandit-f692b994-run.log。テスト側65件の用途判定と残り413件、その他の既存指摘・実サービスの未確認事項を維持する。抑制の追加やコード変更は行っていない。

## 旧テンプレート画像の残存と配信拒否案の補完

- 2026-09-05、schedules0030のupload_toがsession_template_images/<id>/<filename>であり、0041がstorage.exists/deleteの全例外を無視して画像モデルを削除することを確認。削除対象のDB記録が失われるため、マイグレーション成功だけではファイル削除を証明できない。適用済み0041は変更しない。
- 稼働タスク定義tableno-aws-pre:40でS3有効と対象バケットを照合。S3 ListObjectsV2の読み取り集計で、media/session_template_images/に119件・21264バイト、直下session_template_images/には0件。ファイル名・本文・所有者は取得結果として表示していない。残存の理由、実ユーザーデータか試験データか、過去の削除失敗との因果関係は未確認。
- 現行バケットポリシーは対象CloudFrontからbucket/*へのAllowのみ。未適用のTerraform拒否案も旧prefixを含んでいなかったため、session_template_images/*と*/session_template_images/*を追加した。既存Allow、ECS権限、オブジェクトは変更していない。データの削除方針が決まるまで配信経路の保護対象に含める案である。
- terraform fmt -check / validateが成功。現行Allowを保持した具体ポリシー案8パターンに対するAWS Access AnalyzerのRESOURCE_POLICY / AWS::S3::Bucket検査はfindings=[]。これは適用・実配信拒否・データ削除の証拠ではない。
- tmp/private-template-containment-42219b05のbefore-policy.json/proposed-policy.jsonがローカル証跡。実設定への適用と削除は未実施。0041の静的指摘は対応方針と残存確認まで進んだが、実保護・保存/削除判断は未完了。Q04は引き続き未達。

## 596bcd4cの起動・ログ保護追加後の再解析

- 6アプリを同じBandit対象範囲で再解析。解析エラー0、HIGH/MEDIUM 0、LOW556、終了コード1。f692b994とfilename/指摘ID/本文の多重集合を比較して追加・削除0件。
- 新しいtableno.server/error_reporting、招待応答・競合修正にBanditの新規指摘はない。検出なしを全ログ経路の安全性や実サービス検証の代替にはしない。既存LOWの用途判定65件・未判定413件等の扱いを維持する。
- 証跡tmp/bandit-596bcd4c-apps.json、tmp/bandit-596bcd4c-run.log。新しい抑制は追加していない。正式公開No-Goを維持。

## 7cdd7cf8の再解析とグループテスト25件の用途確認

- 固定ソースの検証用イメージで同じ6アプリを再解析。解析エラー0、HIGH/MEDIUM 0、LOW556、終了コード1。Windows/Linuxのパス区切りを正規化し、596bcd4cとファイル/指摘ID/本文の多重集合を比較して追加・削除0件。証跡tmp/bandit-7cdd7cf8-apps.json、同-run.log。静的解析はテンプレートやJavaScriptのXSS検証を代替しない。
- accounts/test_group_features.pyのB106 25件について、各指摘行をAST上の呼出・クラス・メソッドへ対応させた。全てrest_framework.test.APITestCase派生クラスのsetUp内で、User.objects.create_userへ渡す文字列の固定パスワード。28/34/41、74/79、135/142/147、259/262、302/305、355/358、382/385/388、468/474/480、573/579/585、776/781行を確認した。
- UserはDjangoのget_user_modelであり、これらは隔離テストDBに作成されるアカウントの準備値。本番資格情報の埋め込みとしては扱わない。実DB接続や固定値の実ユーザーへの転用を認める判定ではない。既存65件と重複せず、テスト478件中90件を用途判定済み、残る388件は未判定。開発コマンド71件・その他7件の従前の扱いと実サービス検証の残条件は維持する。
## 63bd2436時点のテスト準備用パスワード229件の用途確認

7cdd7cf8のBandit JSONにあるB106を、63bd2436と同一の対象テストソースでAST照合した。既に分類した課金・グループ・CCFOLIA出力の3ファイルを除外し、次の条件を全て満たす229件・68ファイルを追加分類した。対象ファイルは7cdd7cf8以降に変更されていない。

- Django TestCaseまたはDRF APITestCaseを直接継承するクラスのsetUp/setUpTestData内であることをimport先まで照合した。
- get_user_modelのimportとモデル変数への代入、またはCustomUserのimportを辿り、そのモデルのobjects.create_userへのpassword引数が文字列リテラルであることを確認した。
- Banditの指摘行が当該呼び出しの範囲内にあり、ファイル・行の重複がないことを確認した。条件外の呼び出しは未判定のまま残した。

これらは隔離されたテストDBのアカウント準備値であり、本番資格情報の埋め込みとしては扱わない。実DBを使ったテスト実行や固定値の本番転用を認める判定ではない。モデルはCustomUser(AbstractUser)で、ここでは実サービスへのログイン・認証の安全性までは証明しない。

証跡はtmp/classify-test-passwords.pyとtmp/classified-test-passwords.json。再確認用のファイル・行を下表に残す。既存90件と重複せず、テスト478件中319件を用途判定済み、159件は未判定。Banditの検出総数556・終了コード1を変更せず、抑制も追加していない。開発コマンド71件・その他7件の従前の扱い、実ストレージ/CDN・実外部連携等の未達条件は維持する。

| ファイル | B106の行番号 | 件数 |
| --- | --- | --- |
| accounts/test_authentication.py | 27, 356, 359, 381 | 4 |
| accounts/test_background_info.py | 24, 104, 250 | 3 |
| accounts/test_character_6th.py | 28, 206, 287, 347, 392, 405 | 6 |
| accounts/test_character_6th_api.py | 42, 530, 573, 624 | 4 |
| accounts/test_character_6th_bonus_points.py | 19, 145 | 2 |
| accounts/test_character_6th_custom_formula.py | 20, 131 | 2 |
| accounts/test_character_6th_dice_roll_settings.py | 24, 304 | 2 |
| accounts/test_character_6th_versioning.py | 40, 184, 246 | 3 |
| accounts/test_character_api_endpoints.py | 30 | 1 |
| accounts/test_character_background_removal.py | 36 | 1 |
| accounts/test_character_create_player_name.py | 12 | 1 |
| accounts/test_character_current_status.py | 21 | 1 |
| accounts/test_character_edition_image_api.py | 12 | 1 |
| accounts/test_character_image_apis.py | 25, 108, 113, 281 | 4 |
| accounts/test_character_image_upload.py | 22 | 1 |
| accounts/test_character_integration.py | 43, 444, 445, 576 | 4 |
| accounts/test_character_multiple_images.py | 30, 107, 108, 336 | 4 |
| accounts/test_character_save.py | 28 | 1 |
| accounts/test_character_sheet_api.py | 38 | 1 |
| accounts/test_character_sheets_integration.py | 47, 48, 232, 233, 386, 387, 483, 486 | 8 |
| accounts/test_character_skill_update_validation.py | 11 | 1 |
| accounts/test_character_system_data_models.py | 22 | 1 |
| accounts/test_character_to_session_integration.py | 33, 38, 42, 46 | 4 |
| accounts/test_combat_data.py | 24, 74, 182, 249, 392 | 5 |
| accounts/test_custom_skill_addition.py | 21, 126, 257, 315 | 4 |
| accounts/test_dynamic_dice_roll.py | 28, 346, 392 | 3 |
| accounts/test_export.py | 34, 467, 472 | 3 |
| accounts/test_fixed_share_urls.py | 19, 24 | 2 |
| accounts/test_friend_requests.py | 21, 120, 123, 127 | 4 |
| accounts/test_group_invite_links.py | 18, 24, 30 | 3 |
| accounts/test_growth_record.py | 32, 113, 217, 351 | 4 |
| accounts/test_inventory_management.py | 26, 65, 124, 215, 343 | 5 |
| accounts/test_login_lookup_failures.py | 13 | 1 |
| accounts/test_session_integration.py | 43, 48, 52 | 3 |
| accounts/test_session_simple.py | 27, 29 | 2 |
| accounts/test_share_links.py | 20, 26 | 2 |
| accounts/test_skill_point_management.py | 24, 95, 167, 286 | 4 |
| accounts/test_statistics.py | 25, 28 | 2 |
| accounts/test_tindalos_detailed_api.py | 26, 253, 449 | 3 |
| accounts/tests.py | 31, 498 | 2 |
| scenarios/test_scenario_images.py | 29, 35, 41 | 3 |
| scenarios/test_scenarios.py | 19, 136, 139, 142 | 4 |
| scenarios/tests.py | 14 | 1 |
| schedules/test_advanced_scheduling.py | 31, 106, 112, 118 | 4 |
| schedules/test_analytics_dashboard.py | 21, 27, 33 | 3 |
| schedules/test_async_jobs.py | 19, 24 | 2 |
| schedules/test_calendar_apis.py | 26, 28, 179, 209, 331 | 5 |
| schedules/test_character_session_ho_integration.py | 27, 36 | 2 |
| schedules/test_external_integrations.py | 111 | 1 |
| schedules/test_groupless_session_creation.py | 16, 22 | 2 |
| schedules/test_handout_management.py | 29, 32, 35, 38 | 4 |
| schedules/test_handout_permissions.py | 22, 27, 32 | 3 |
| schedules/test_handouts.py | 26, 30, 34, 292, 296 | 5 |
| schedules/test_japanese_holidays.py | 90 | 1 |
| schedules/test_occurrences.py | 21, 27 | 2 |
| schedules/test_player_slots_handouts.py | 27, 35 | 2 |
| schedules/test_recommended_skill_comparison.py | 19, 20, 301, 302, 303 | 5 |
| schedules/test_schedules.py | 32, 35, 100, 103, 1376, 1379 | 6 |
| schedules/test_session_images.py | 29, 33, 37, 41 | 4 |
| schedules/test_session_integration.py | 34, 42, 458, 575 | 4 |
| schedules/test_session_notes_logs.py | 18, 61, 67 | 3 |
| schedules/test_session_notifications.py | 27, 30, 33, 168, 169, 171, 257, 258 | 8 |
| schedules/test_session_permissions.py | 30, 31, 32, 33, 37, 42, 146, 147, 151, 156, 161 | 11 |
| schedules/test_session_rewards.py | 19, 25, 31, 37, 43, 260, 266, 272 | 8 |
| schedules/test_session_role_integration.py | 20, 21, 22, 23, 103, 105, 107, 108, 112 | 9 |
| schedules/test_session_visibility.py | 20, 25, 30 | 3 |
| schedules/test_youtube_links.py | 27, 31, 184, 188, 192, 196, 600, 745, 749, 753 | 10 |
| schedules/tests.py | 19, 22 | 2 |
## 権限応答修正後の0cd9fe45での再解析

Bandit1.9.4でaccounts/api/scenarios/schedules/support/tablenoを再帰解析した。解析エラー0、HIGH/MEDIUM 0、LOW556、終了コード1。ファイルパスの区切りと先頭の./を正規化し、ファイル・指摘ID・本文の多重集合を7cdd7cf8と比較して追加0・削除0だった。新しいグループAPIキャッシュ禁止処理を含むソースの結果であり、過去の検出件数を流用したものではない。

証跡はtmp/bandit-0cd9fe45-apps.jsonとtmp/bandit-0cd9fe45-run.log。テスト側319件の用途判定・未判定159件を維持する。指摘の差分なしは、全経路の安全性や実サービスでの保護を証明しない。コードと警告抑制の変更は行っていない。
## 09d15575での再解析と追加56件のテスト用パスワード分類

- Bandit1.9.4で6アプリを再帰解析し、解析エラー0、HIGH/MEDIUM 0、LOW556、終了コード1。0cd9fe45とのファイル・指摘ID・本文の多重集合比較では追加0・削除0。区切り文字と先頭./を正規化して比較した。証跡tmp/bandit-09d15575-apps.json、同-run.log。
- 前回未分類のB106から、テストメソッド内43件・setUp/setUpTestData内13件、計56件・26ファイルを追加分類した。Django TestCase/DRF APITestCaseの直接継承をimport先まで確認し、get_user_modelのモジュール/メソッド直下の代入またはCustomUserのimportを辿った。対象呼び出しはモデルのobjects.create_userで、password引数が固定文字列であること、Bandit指摘行が呼び出し範囲内であることをAST照合した。
- 既存分類319件とのファイル/行の重複を除外し、テスト478件中375件を用途判定済み、103件は未判定。対象は隔離テストDBのアカウント準備値であり、本番資格情報の埋め込みとしては扱わない。実DBへの転用を認めるものではなく、実認証/外部連携の合格証拠でもない。警告抑制やアプリコードの変更なし。
- 再現用スクリプトtmp/classify-extra-test-passwords.py、結果tmp/classified-extra-test-passwords.json。対象行は下表。開発コマンド71件・その他7件の従前の扱いと、実ストレージ/CDN等の未達条件は維持する。

| ファイル | B106の行番号 | 件数 |
| --- | --- | --- |
| accounts/test_api_auth_discord.py | 136, 179 | 2 |
| accounts/test_api_auth_google.py | 124 | 1 |
| accounts/test_character_6th.py | 153 | 1 |
| accounts/test_character_6th_api.py | 516 | 1 |
| accounts/test_character_6th_dice_roll_settings.py | 287 | 1 |
| accounts/test_character_background_removal.py | 226 | 1 |
| accounts/test_character_ccfolia_export.py | 13, 392, 422, 448, 505, 540 | 6 |
| accounts/test_character_factories_test.py | 9 | 1 |
| accounts/test_character_integration.py | 897 | 1 |
| accounts/test_character_sheet_api.py | 199 | 1 |
| accounts/test_custom_skill_addition.py | 179 | 1 |
| accounts/test_dynamic_dice_roll.py | 271 | 1 |
| accounts/test_export.py | 258 | 1 |
| accounts/test_group_invite_links.py | 153 | 1 |
| accounts/test_session_simple.py | 130 | 1 |
| accounts/test_statistics.py | 363 | 1 |
| accounts/tests.py | 107, 113, 119, 142, 171, 177, 183, 255, 261, 267, 273, 333, 382 | 13 |
| schedules/test_analytics_dashboard.py | 111 | 1 |
| schedules/test_discord_and_release.py | 23, 28, 278, 283 | 4 |
| schedules/test_external_integrations.py | 28, 33 | 2 |
| schedules/test_group_links_and_guests.py | 20, 25, 30, 111, 116, 121, 126 | 7 |
| schedules/test_groupless_session_creation.py | 131 | 1 |
| schedules/test_handouts.py | 354 | 1 |
| schedules/test_occurrences.py | 141 | 1 |
| schedules/test_schedules.py | 728, 945, 1350 | 3 |
| schedules/test_session_integration.py | 667 | 1 |
## Djangoテストクライアントの固定ログイン値15件

09d15575のB106のうち、7ファイル15件を追加分類した。全てTestCase/APITestCase内のself.client.loginへの固定password引数。クラスのimport/継承とself.clientの代入先をASTで照合し、明示代入がある場合もdjango.test.ClientまたはDRF APIClientであることを確認した。Djangoのローカル認証処理を使うテスト入力であり、実サービスの認証情報埋め込みとしては扱わない。

既存375件との重複なし。テスト478件中390件を用途判定済み、88件は未判定。解析の総検出数・終了コードは変わらず、抑制やコード変更も行っていない。テストクライアントの確認は、実DB接続や本番での固定値利用を認める判定ではない。証跡tmp/classify-test-client-logins.pyとtmp/classified-test-client-logins-table.md。実外部認証/配送等の未達条件は維持する。

| ファイル | B106の行番号 | 件数 |
| --- | --- | --- |
| accounts/test_character_current_status.py | 22 | 1 |
| accounts/test_character_integration.py | 52, 582 | 2 |
| accounts/test_character_multiple_images.py | 337 | 1 |
| accounts/test_character_to_session_integration.py | 78, 118, 155, 329 | 4 |
| schedules/test_handouts.py | 317, 330, 349, 358 | 4 |
| schedules/test_session_notes_logs.py | 87 | 1 |
| schedules/test_session_rewards.py | 293, 301 | 2 |
## 残るB106とGoogleトークン更新試験の固定値

09d15575の残るB106 13件とB105 3件をソースで確認し、以下の用途へ分類した。

| 対象・行 | 件数 | 用途と確認根拠 |
| --- | --- | --- |
| schedules/test_past_import_repair_command.py:22,28 | 2 | TestCaseのsetUp内でget_user_modelをimportし、隔離DB用のowner/playerを作成する固定パスワード。前回の機械照合が対象外にしたメソッド内import |
| schedules/test_websocket_notifications.py:20,25 | 2 | TransactionTestCaseのsetUpで通知送受信対象を作る固定パスワード。通信はChannels WebsocketCommunicatorとアプリのASGI経路を使う試験 |
| accounts/test_api_auth_google.py:28 | 1 | DummyFlow.fetch_tokenがSimpleNamespaceへ設定する模擬IDトークン。Flow.from_client_configとIDトークン検証をpatchした認証コード試験で使用 |
| accounts/test_api_auth_discord.py:25、accounts/test_api_auth_google.py:31、accounts/test_api_auth_twitter.py:24 | 3 | override_settingsの固定client secret。認証交換/検証はrequests・Flow・id_tokenのpatchで模擬したAPI試験 |
| accounts/test_auth_error_logging.py:61、accounts/test_oauth_inactive_users.py:13 | 2 | override_settingsの固定認証設定。requestsのpost/getをpatchし、例外文の漏えい拒否・停止済みユーザー拒否を検証 |
| schedules/test_external_integrations.py:136,231 | 2 | 隔離SocialTokenの模擬access token/空refresh tokenと、更新試験用override_settings。Credentialsをpatchした更新結果をDBへ保存する試験 |
| support/tests.py:17 | 1 | LINE署名試験用の固定設定。HMACはテスト内で作成、LINE返信等はpatch、メールはlocmemを指定。実LINEの秘密情報を読み取る試験ではない |
| schedules/test_external_integrations.py:238,242,243（B105） | 3 | 同じ更新試験の旧refresh tokenと、mock Credentialsが返す新access/refresh token。更新呼び出しと保存値を照合 |

合計16件はテスト固定値のため、本番資格情報の埋め込みとしては扱わない。実キーの有効性を外部サービスへ問い合わせた判定でも、本番への転用を認める判定でもない。先行390件と重複せず、テスト478件中406件を用途判定済み、残る72件（B105）は未判定。テスト側B106の未判定は0となったが、総LOW556・終了コード1は変わらない。抑制・アプリ変更は行っていない。対象の一覧はtmp/remaining-security-inventory.jsonから照合した。実OAuth・LINE・Google連携の公開条件は未達のまま維持する。
