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
