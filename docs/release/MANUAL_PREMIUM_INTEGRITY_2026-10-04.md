# 手動プレミアム権限と管理フォームの整合性（2026-10-04）

## 発見と再現

先行 `897e73f0` の[管理操作修正](ADMIN_ACCESS_INTEGRITY_2026-10-04.md)に続き、CustomUserAdminの直接保存とset_premium_userを専用ブランチ `codex/manual-premium-integrity-20261004` で確認した。

ユーザー管理フォームはプロフィール/グループだけの編集でも全モデルを保存し、取得後に課金処理が変えたis_premiumや未変更のemail等を古い値へ戻した。監査失敗時はユーザーの権限/プロフィール変更や新規ユーザーだけが残った。削除後の古いユーザーを保存すると再作成できた。手動設定コマンドも監査失敗時に権限だけを更新した。

- 初回SQLiteの11件は4成功/7失敗（0.080秒・終了1）。権限の誤付与/誤停止、未変更列の上書き、監査rollback不足、削除済み対象の再作成を検出した。
- 初回PG専用5件は全失敗（51.241秒・終了1）。管理フォーム/コマンドとも、競合writerが持つ既存課金行のロックや初回行作成へ到達しなかった。
- 最初のGREEN16件後、自己レビューで「変更なしの旧手動権限にも空の課金行を残すと、監査なしの権限を後の再同期が停止する」リスクを発見。専用2件で空行残留をREDにし、取り消しを実装した。再同期までの保持も最終試験で確認した。
- 取得からロックまでの間の実削除をPGで4件追加し、未処理PremiumSubscription.DoesNotExistを全4件で再現（1.101秒・終了1）。再読み込み/再試行の日本語エラーへ変更した。

実Stripe/署名Webhookではなく、同じ課金行を更新する合成writerとの競合試験である。単独writerの成功を実課金・配送・AWSの成功に拡張しない。

## 修正と仕様の維持

- 実管理フォームのchanged_dataとモデルの具体列から保存対象を限定し、未変更のプレミアムチェックボックスや他の列を保存しない。実列に変更があればupdated_atを更新し、groups/user_permissions等のM2Mは従来のsave_relatedへ任せる。プロフィールだけの保存はuser行のみをロックし、課金行を追加しない。
- 明示的な手動権限変更は共有context managerで課金行→user行の順にロックし、最新フラグを基準に変更と監査を同一transactionへまとめる。初回課金行の同時作成ともunique制約で直列化する。新規ユーザーの作成/監査もatomicにする。
- 既存ユーザーで課金行がなければ空の行を用意する。実際の権限変更時はその行とmanual監査を保持する。変更なしなら今回transaction内で新規作成した空行だけを取り消し、旧手動権限・「課金履歴なし」の既存状態を維持する。既存課金行は削除/更新しない。新規ユーザー追加では課金行を作らない。
- 変更なしの手動設定は監査なし、変更時は従来のactor/source/manual reason/metadataを保持する。form=Noneの従来呼出は明示的なモデル保存として互換性を保つ。通常管理画面のフォームを通さない任意コード全体の部分更新保証にはしない。
- 削除済みユーザーを再作成しない。ロック直前に課金行/ユーザーが消えた場合も変更・監査・成功出力をせず、管理画面はHttp404、コマンドはCommandErrorで再読み込み/再試行を案内する。コマンドの成功出力はcontextのcommit後。
- 既存のmanual override判定、Stripe契約状態/顧客/契約/価格ID、停止・復旧の意味を変更しない。Stripe契約の復活/解約/課金は行わない。UserAdminの認可、フォーム検証、CSRF、M2M保存を維持する。

Stripe監査スキルの方針に沿って隔離fixtureだけを用い、Webhookでの権限付与を購入戻り画面へ移していない。Stripe SDK/API/Client方式・価格・税設定・Secretsは変更しない。本番の販売対象/税務と実外部連携の確認は残る。

課金inlineは既に全表示項目readonly・作成禁止・削除禁止であることをテストで確認した。独立したPremiumSubscriptionAdminの直接編集/削除は別経路であり、今回の修正を全管理経路の合格にはしない。

## 最終検証

| 環境 | 1実行の結果 | 時間 |
| --- | --- | --- |
| Windows Python3.11.1 / Django5.2.17 / SQLiteメモリDB | 360件中342成功・行ロック18省略・終了0 | 48.438秒 |
| Linux / 隔離PostgreSQL18.3、coverage計測付き | 372成功・省略0・終了0 | 63.310秒 |

新規29件は一般20件とPG専用9件（既存/初回課金行の直列化5件、実削除4件）。SQLite実行ではこの9件と先行管理操作のPG専用3件を対象外とし、さらに選択済み既存行ロック18件が省略された。PGではそれらを含め実行しており、SQLiteの対象外/省略を成功数へ含めない。

範囲はbilling・課金競合・paid_feature_lifecycle、コード利用/失効/再同期・管理操作・手動設定、退会ガード、課金メール配送/監視、Event/Invoice/Checkout/Disputeの順序・再試行・復旧・複数停止理由・Portal解約。異常系の403/503/500等は期待結果で、予期しない試験エラーはない。途中の16/22/93件等はこの最終実行と重複するため再加算しない。

Django Test Clientの実GET/フォームPOSTで、課金フラグを保存直前に変更してもプロフィール/グループ保存が権限を戻さないこと、明示的なチェック変更がmanual監査を1件だけ作ること、変更権限なしのstaffが403で拒否されることを確認した。これは実UserAdminフォーム/ルーティングの試験であり、Socket経由のHTTP・ブラウザー描画・AWS実操作ではない。

最終coverage7.15.4のPython/thread tracingでは、CustomUserAdmin.save_model 20文/10分岐、監査保存補助9文/6分岐、共有ロックcontext10文/4分岐、コマンドhandle22文/6分岐が100%。新規テスト350文/38分岐も100%。admin/billing全体や全権限経路の100%ではない。

フォーム試験の初回は未送信のprofile_imageをmultipartへ渡してPOST前に失敗し、FileFieldを送信しないfixtureへ修正した。再同期確認の初回はCLIフラグ名の誤りで失敗し、現行の--skip-expireで再実行した。coverage解析の初回はPowerShellのforeach直後のpipe構文で失敗し、配列へ受けて再実行した。これらの試験/工具側の失敗はアプリ不具合や成功として数えない。期待値・CI条件・再試行予算を緩めていない。

Black/isort/Flake8、Bandit対象4ファイル（0指摘・0解析エラー）、Django check・makemigrations --check --dry-run（変更なし）、workflow YAML/PG対象指定、差分空白・ステージ済みUTF-8/LF/文字化け検査を確認した。新しい4つの日本語エラーをassertし、従来の英語コマンド出力/診断は変更していない。ロック順・初回作成・旧権限・rollback・認可・部分保存・削除・監査を自己レビューし、この修正単位に未解消指摘はない。

## 環境・証跡・反映境界

専用PGはnetwork none・公開ポートなし・512 MiB・DBデータtmpfs。合成SECRET_KEY/利用者/課金ID・ENV_FILE空・APP_ENV=local・locmemメール/cacheで隔離し、実データ/Secrets/共有DBを参照していない。先行通常イメージ `sha256:46795320922764a1bc2065f8c161e8d317cb0f2f5c1588a6d9026660d4a666f4` へ今回ソースをread-only mountした工具実行であり、修正後の通常配布物の証明ではない。coverageも既存工具をread-only mountした。

Djangoが各試験DBを破棄し、最後に専用PGのID/名前/networkを再照合して停止・削除した。tmpfsの合成データは破棄されたが、fixtureから再作成可能。設定/ログ/coverageは `C:/tmp/iaia-manual-premium-20261004` に保持する。

| 証跡 | SHA-256 |
| --- | --- |
| coverage-pg-final.json | 2e6f53ac4a4b1d9f17de34700b566ffce1894c26aec6a02c037709cb0694eab3 |
| bandit-final.json | 2583ec51131752065a9bfa11b3e247ac9f3fb60f355175060fd9f228ae05ce56 |

先行 `897e73f075cb75a2b1500b30986b3a0488225d91` の[CI全6項目success](https://github.com/sheepdog0820/iaia/actions/runs/37191477587)をhead SHAと照合した。今回候補の全CI・通常配布物・AWSと、実Stripe/外部連携/OS HIGH2件等の公開条件は未確認。mainは読み取りで8567f49fと確認し、今回main/ECR/ECS/S3/CloudFront/共有DB/実データ/Secrets/IAM/課金有効化/容量/継続費用を変更していない。元checkoutのハンドアウト差分を保持し、固定承認案6b6c570cへ追加しない。

復旧はfix-forwardを優先する。作業ブランチで今回コミットのみをrevertすることも可能だが、古いフラグの上書き/監査欠落/ユーザー再作成を再導入するため、そのまま正式公開しない。[正式公開No-Go](FORMAL_RELEASE_ACCEPTANCE_MATRIX.md)を維持する。
