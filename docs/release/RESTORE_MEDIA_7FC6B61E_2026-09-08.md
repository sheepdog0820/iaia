# 最新候補の全ファイル項目を含む隔離復元試験

2026-09-08、アプリ候補7fc6b61eの通常イメージ `sha256:158c7301a238dc65e800d7979bb7bdc449e5792181aa64d1b8927f244f4c5b02` とPostgreSQL 18.3で実行した。実RDS/S3ではなく、ローカルDockerの外向き通信なしの内部ネットワーク、使い捨てDB、合成データのみ。アプリソースの差し替えはない。メディアは隔離したローカルFileSystemStorage、メールとキャッシュもローカル設定を使用した。

## 対象と照合方法

Djangoの登録済み具体モデルからaccounts/schedules/scenarios/supportのFileField・ImageFieldを列挙し、下記11項目のすべてに非空参照があることをassertした。ソースにあるabstractモデルやSerializerのフィールドを稼働テーブルとして数えていない。

- CustomUser.profile_image
- CharacterSheet6th.character_image / CharacterSheet7th.character_image
- CharacterImage6th.image / CharacterImage7th.image
- ScenarioImage.image、SessionImage.image、HandoutAttachment.file
- SupportMessage.attachment
- BackgroundRemovalJob.source_image / result_image

プロフィール・非公開キャラクター・非公開シナリオ・非公開セッション・秘匿ハンドアウト・合成問い合わせ・未処理/完了の透過ジョブを作成した。画像は13×17pxの生成PNG、ハンドアウト添付は日本語テキスト。透過ジョブのファイルは保存復元試験用の生成画像であり、この試験内でモデル推論をした結果ではない。

全テーブルの行内容と件数、全publicシーケンス、メディア相対パスとSHA-256、DB内のモデル/行/フィールドからファイルへの参照を保存した。別DBへpg_restoreし、ファイルを別の専用メディア先へ復元して同じ情報と照合。各非空参照の存在とハッシュ、ImageFieldの画像デコードも検査した。復元後に追加ユーザーを作成し採番の継続を確認した。

## 結果

| 操作・検査 | 結果 |
| --- | --- |
| 空DBへの移行と合成データ作成 | 成功 |
| pg_dump / メディアアーカイブ | 成功 |
| 別DBへのpg_restore | 成功、0.500秒 |
| DBだけ復元してファイルなしで検査 | 期待した終了1、media manifest differs |
| メディア復元 | 成功、0.375秒 |
| テーブル・シーケンス・ファイル・参照の照合 | 成功、2.282秒 |
| migrate --check / Django check | 成功 |

復元前後で91テーブル・621行・87シーケンス、11ファイル項目・11参照・11実ファイルが一致した。秘匿ハンドアウトのフラグとPL・GMへの所有関係も保持された。HTTPの閲覧拒否試験を実施した結果ではない。

試験コンテナ・ネットワークは所有ラベルを照合して削除し、残存一覧も空だった。Git管理外の `tmp/restore-media-7fc6b61e/` にrun.py、probe.py、drill_settings.py、expected.json、results.json、各ログと合成バックアップを保持する。

## 残条件

各ファイル項目を少数のデータで検証した結果であり、全入力形式・実規模・同時書き込み・破損データ・期限切れ削除・復元時のジョブ再開・HTTP権限の網羅は含まない。DBとローカルメディアが静止している間のバックアップであり、RDSの時点復元とS3 VersionIdの選択を実証していない。表の所要時間だけから実環境のRTOを判定しない。

[DB・メディア復旧の受け入れ条件](DB_MEDIA_RESTORE_ACCEPTANCE.md)にある実世代・内容・権限・削除方針の照合と、ユーザーによるRPO/RTO基準の確定が必要。共有DB、実ユーザーデータ、AWS資源、Secrets、権限、継続費用は変更していない。

## 復元後の秘匿添付へのアクセス検証

同日、同じ通常イメージ・PG18.3で新たな隔離DBを作り、上記のバックアップ/復元・全体ハッシュ照合を再実行した。その復元DBへDjango APIClientでアクセスし、秘匿ハンドアウト添付のAPIダウンロードURLと従来の `/media/handouts/...` URLをそれぞれ検査した。

| アクター | 両URLの結果 |
| --- | --- |
| GM | 200、元ファイルと本文一致 |
| 割り当てられたPL | 200、元ファイルと本文一致 |
| 別のセッション参加者 | 404、添付本文なし |
| 部外者 | 404、添付本文なし |
| 無効ユーザー | 401、添付本文なし |
| 匿名 | 401、添付本文なし |

計12件が期待どおり。取得成功時はContent-Dispositionのattachment、nosniff、Cache-Controlのno-store/private、VaryのCookie/Authorizationも確認した。APIClientのforce_loginでローカルセッションを作るため、パスワードやOAuthでの実ログイン、実ネットワークHTTP/TLS、S3/CDNを検証した結果ではない。

最初の実行は試験用testserverをALLOWED_HOSTSに含めず400となった。隔離設定だけに追加して再実行したところ、未認証の期待値を403としていた試験が401で失敗した。構成上TokenAuthenticationが先頭であることを確認し、未認証の期待値を401に訂正した。拒否条件を許可へ緩める変更やアプリコードの変更はしていない。各回は新規の専用試験ディレクトリ/DBを使用し、失敗時も所有リソースを片付けた。

最終結果は `tmp/restore-access-7fc6b61e-v3/` のaccess-results.json、verify-restored.log、results.json。元の91テーブル・621行・87シーケンス・11ファイル/参照の照合後に、試験専用の部外者等とセッションを追加した。上記件数は追加前の復元照合時点。最終検査、migrate --check、Django checkは成功、コンテナ・ネットワークの残存確認も空。

これは秘匿添付1件の6アクター×2経路の復元後検証である。他の10ファイル項目の取得権限、実環境のS3直アクセス、期限やトークン、参加解除などの状態変化は未確認として残す。
