# main 14ac4746の開発AWS反映準備

## 承認後の実行結果

ユーザーが共有DB移行2件とS3保護を明示承認したため、以下を実施した。下段の「確認中」「未切り替え」は反映前の記録。

- Webサービスはタスク定義41へ切り替え完了。稼働タスク `28ca52dfbb1444afacfa1fd15c56a7e0` はRUNNING/HEALTHYで、digestは反映候補 `sha256:ab7c8247fe4ac4803dea5c0b35aea738d66b5aaf7cfccf2937cd656687aa9de7` と一致。desired/running=1/1、旧定義40は稼働0。
- 移行タスク `7a0111c5d8ba48278823089dcd3a94e5` は終了0。実行直前にMigrationExecutorの計画が承認済み2件だけであることをassertし、accounts/0064・schedules/0055ともOK、適用後の残計画なしを確認した。lock_timeout=5秒、statement_timeout=120秒を設定。
- 静的収集タスク `04c2cc77851c40188122e2e3db5fc61e` は終了0。Axios・テーマCSS・フォントなど22ファイルについてS3とCloudFrontの配信バイト一致を確認し、配信Axiosの `node --check` 成功。
- 現行S3ポリシーが保存済み元ポリシーと一致することを再確認し、元Allow文を保持して非公開領域12パターンのCloudFront GetObject拒否を追加。Access Analyzerの指摘なし、適用後のポリシー一致を確認した。
- CloudFront失効 `IDQ3OINF0CCLDXYYE1ZGYR7TCM`（`/*`）はCompleted。12パターンの合成ファイルはすべてHTTP403で、内容を返さないことを確認。検証用S3オブジェクトは作成時のVersionIdを指定して全12件削除した。
- S3変更前タスク `459f0ec3889b4417b35911534d5328d9` と変更後タスク `44eee481a7b44479af875ccb7ed99e12` は終了0。候補イメージ・実タスクロールから実S3を読み、問い合わせ添付の認可付きビューは合成権限あり利用者200/バイト一致/no-store、一般・匿名404。利用者は保存しない合成オブジェクト、添付メタデータはトランザクションをロールバックした。ブラウザログインを含む全HTTP認証経路の試験ではない。
- 未ログインでログイン→登録画面へ遷移でき、指定Chromeの既存ログイン状態ではホーム・キャラクター一覧が読み込めた。既存利用者のデータは編集していない。

## 公開フォントの追加修正

画面でアイコンが欠け、独立した新規Chromeセッションの検証でもFont Awesome/テーマフォントのCORSエラーを再現した。公開S3にCORS設定がなく、CloudFrontにも応答ヘッダーポリシーがなかった。

公開済みの `static/*` だけに、既存DefaultCacheBehaviorと同じ配信設定を持つbehaviorを追加し、AWS管理の `Managed-SimpleCORS` を指定した。認証情報を伴うCORS許可・書き込み権限は追加せず、非公開領域のDefaultCacheBehaviorとS3拒否を保持。新しい有料リソースは作成していない。Terraformにも同じ設定を記録し、fmt/validate成功。

CloudFrontはDeployedになったが、Chromeと別Chromiumの新規セッションでもフォント取得に失敗した。HTTPクライアントでは許可ヘッダーが付き、ブラウザでは付かない応答を確認。キャッシュ無効化・一意クエリ・HTTP/1.1でも再現したため、伝播待ちだけが原因とは判断しない。

ユーザーの取得方法変更依頼により、フォントCSSとフォント本体を同一アプリドメインの `/fonts/` から配信する実装へ変更。既存WhiteNoiseを使い、リポジトリ同梱のFont Awesome 6.0.0とテーマフォントの固定ディレクトリのみ起動後初回に索引化する。リクエスト値をファイルパスとして開かず、登録済みURLだけを配信する。GET/HEAD・ETag/304・1時間の公開キャッシュを使用し、DB・S3・IAM変更は不要。テーマCSSの外部ドメイン経由importを除き、baseテンプレートから同一ドメインのCSSを読み込む。移行後のブラウザ検証結果は反映後に追記する。

フォント資産の将来変更では、未ハッシュURLのため既存ブラウザに最大1時間旧フォントが残り得る。新しいCSSが旧フォントと非互換になる変更では、バージョン別ディレクトリを使う。公開範囲はライセンス文書を含む同梱フォント資産のみ。その他の静的ファイルは従来どおりCloudFrontを利用する。

### 同一ドメイン配信の反映・検証結果

- 修正コミット `fa09731c47ee0342dfb344466f9f3cc39963f192` を作業ブランチへpush。関連テスト8件成功、新規配信モジュールの19文・カバレッジ100%。Black/isort・差分・ステージ済みUTF-8/LF確認成功。画面文言の変更なし。固定ディレクトリ外・パストラバーサル・POST拒否、匿名HTTP取得・HEAD・ETag/304を確認した。
- クリーンなコミットからイメージ `aws-pre-fa09731c` をビルド。digest `sha256:f0c900978e2e6b686782fbed2ddf5b007ae5bdbb8deac8f04bbf126a3a890ecd`。定義41のWebイメージだけを変更した定義42へ切り替え、その他の設定が完全一致することを比較した。
- チェック・移行計画確認・静的収集のタスク `c71b214dd70b4964a4d5ca87ddb93ac9` はSTOPPED/終了0。移行計画なし、既存W008のみ。今回はDB移行を適用していない。
- 静的キャッシュ失効 `I1TEACX2FYPTJ0NQX304X3OW8F` はCompleted。新テーマCSS `static/css/arkham_modern.6b5af6300cf0.css` はS3/CloudFrontのバイトが一致し、フォントimportを含まない。
- 定義42のみ稼働1、rollout COMPLETED。タスク `cd4009951ae3488b91a32a4934592118` はHEALTHY、実イメージdigest一致。13:11 UTC時点のreadinessはDB/cacheともok。
- 新規Chromeと別Chromiumで、Font Awesome Free/Brands・Inter・Poppinsの4ファミリーがloaded。ページで必要なwoff2全5件がアプリの `/fonts/` からHTTP200で取得され、フォントerror状態なし。登録画面のスクリーンショットでもサイコロ・メール・鍵等のアイコンを確認し、ログイン画面へのリンク遷移も成功した。不要な言語・ウェイトのunloadedはブラウザが要求していない状態で、失敗ではない。
- 検証スクリプトの最初のリンク完全一致指定は、アイコン文字を含むアクセシブル名に一致せずタイムアウトした。文字列包含で指定し直して遷移成功。フォント読み込み成功と、この検証側セレクター失敗を区別した。
- 既存faviconの404は残るが、フォントCORSエラーは解消。CI run34229623157は記録時点で進行中（lint-security/system/production-database成功、残り未完了）。CI全体成功とはまだ扱わない。
- 復旧はWeb定義41へ戻せるが、アイコン不具合も戻る。今回DB・IAM・S3アクセス権限・常時稼働台数の変更なし。背景透過のIAM追加は引き続き未実施。

今回の実行証跡はGit管理外の `tmp/aws-pre-fa09731c/`、ブラウザの詳細と画像は `tmp/aws-pre-14ac4746/browser-font-check.json`・`signup.png` に保存した。

## 背景透過の追加確認

追記：ユーザーが権限修正を承認したため、定義3の起動許可を追加し、実AI処理・透過PNG保存・合成データの後片付けまで成功した。以下は承認前の記録。最新結果は[背景透過の権限修正記録](BACKGROUND_REMOVAL_IAM_FIX_2026-09-08.md)を参照。

Web環境は背景透過定義2（旧 `aws-pre-2b2f02a3`）を指定する一方、既存の起動用IAM inline policyは定義1だけを許可していた。最新イメージに揃えた定義3を登録し、既存CPU1024/メモリ2048・コマンド・ロール等を保持した。

既存IAM文を変更せず定義3の `ecs:RunTask` 許可だけを追加する案を `tmp/aws-pre-14ac4746/background-launcher-policy-proposed.json` に作成し、IAM追加とWeb参照変更をユーザーへ確認中。IAM変更・Web参照変更・実透過処理はまだ実行していない。今回のWeb/S3反映を背景透過・Stripe・外部連携の全面的な検証完了とは扱わない。

## 反映前の記録

2026-09-08、ユーザーがmainの開発AWS環境への反映を依頼。アプリ反映の準備を実施し、共有DB移行2件とS3アクセス権限変更について個別の実行範囲を確認中。稼働サービスはまだ切り替えていない。

## 確認結果

- main `14ac4746ba06398509d3b84eeaeb9d6c68d1b76b` のCI run34222245873はsuccess。
- クリーンなGitアーカイブから通常Dockerfileでビルド。ローカルimage ID `sha256:bde9955d542f4405b4a0dfc3391bd5ed89d56465d3a1dc2ba6229573ff1d58b7`。
- ECRタグ `aws-pre-14ac4746`、manifest digest `sha256:ab7c8247fe4ac4803dea5c0b35aea738d66b5aaf7cfccf2937cd656687aa9de7`。検証済み4d7c4ea7とOS/Pythonパッケージ一覧が一致。アプリソースは4d7c4ea7以降変更なしで、差分は設定例と文書のみ。
- タスク定義40の既存設定を保持し、イメージだけを上記digestへ変更した定義41を登録。稼働サービスは定義40、desired/running=1/1。
- 単発タスク `a9120502d13c48fdb8404438618799f5` はSTOPPED、終了0。自動移行・静的収集・開発ユーザー作成をfalseにした上で、本番設定チェックと `migrate --plan` だけを実行した。
- 移行計画はaccounts/0064とschedules/0055のみ。旧移行の再実行・データ削除は計画にない。
- 本番設定チェックはSECURE_SSL_REDIRECTのW008を1件報告。ALBのlistenerはHTTPS443だけで、HTTPS readinessは200・HSTSあり。HTTP80は接続タイムアウトであり、HTTPSへの転送成功とは扱わない。設定・listenerの変更は未実施。
- RDSはavailable、バックアップ保持7日、LatestRestorableTimeは11:58:49 UTC。S3バージョン管理Enabled。直前の[実RDS復元試験](RDS_RESTORE_RESULT_2026-09-08.md)は成功したが、全データ/ファイルの復旧保証ではない。

## 確認待ちの実行範囲

1. accounts/0064で後続世代のDjango削除動作を保護し、schedules/0055で単一ロール制約を参加者/ロール単位へ変更する。適用直前に計画が2件のままか確認する。複数ロール作成後の逆移行は衝突し得るため、自動的にロールを削除して戻さない。
2. 新アプリの認可付き取得を確認した後、既存S3ポリシーを保持したまま非公開領域12パターンに対するCloudFront GetObject拒否を追加。キャッシュ失効と合成ファイルでの確認を含む。現在のポリシーは従来のAllow文のみであり、未適用。

その後、承認範囲のDB移行・静的収集・サービス更新・キャッシュ失効を行い、終了コード・稼働digest・health・静的配信・画面と権限を確認する。旧定義40へ戻すだけでは世代削除や非公開取得の不備を再導入するため、安全な復旧とは決めつけない。

実行証跡・元タスク定義・サービス構成・ポリシーはGit管理外の `tmp/aws-pre-14ac4746/` に保存。秘密値は取得・文書掲載していない。Stripe設定・本番環境・継続稼働台数は変更していない。
