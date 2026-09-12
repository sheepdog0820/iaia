# ハンドアウト添付とGM権限の整合

## 問題と変更

追加のGMロールを持つ参加者はハンドアウト本文を管理できるが、添付サービスはセッションの元のGMのIDだけを検査していた。このため追加GMによるアップロードと、元のGMがアップロードした添付の削除が403になっていた。

添付の追加・削除にも既存の `can_manage_secret_content` を利用する。閲覧判定とダウンロードの認証は維持し、PLにGM権限を付与する変更はしない。従来のアップロード者による削除条件は維持する。AWS IAMや実ユーザーのロールを変更するものではない。

## 検証

- 新規API回帰テスト4件のうち、追加GMの追加・削除が403になる2件の失敗を修正前に再現。
- 修正後、追加GMの追加・削除成功、PLの閲覧成功と変更拒否、GMロール取り消し後の追加・削除拒否を確認。削除成功時のDB行とファイルの消去、拒否時の残存も検査。
- 既存の添付モデル・サービス・API、秘密ファイルのダウンロード・保存済みURL・迂回パス、内部エラー非開示、ハンドアウト本文の書き込み権限を含む39件が成功（1.424秒）。使い捨てテストDBで実行し、共有DBやAWSは使用していない。

実行対象:

```text
schedules.test_handout_attachment_roles
schedules.test_attachment_error_privacy
schedules.test_handout_download_access
schedules.test_handout_attachments
schedules.test_handout_write_permissions
```

この検証は実S3、ブラウザでの添付操作、ロール変更と同時操作の競合を証明しない。全体CIはpush後の確認対象。先行コミットのCI成功を今回の修正の成功として扱わない。

DBスキーマ・Secrets・継続費用の変更なし。mainマージ・AWS反映は未実施。復旧は作業ブランチで当該変更をrevertして関連テストを再実行する。元に戻すと追加GMの添付操作は再び拒否される。
