# 保存済み画像の容量確認後にファイルを解放する

PR61の固定head `7c94d2c8`を親にした別ブランチで、画像追加・編集時の容量確認によるファイルハンドル残留を修正する。PR60/PR61のheadと既存のmain確認、固定3de/image4617のコピー内5移行リハーサル確認は変更しない。全25条件と正式公開No-Goを維持する。

## 原因と変更

`CharacterImageSerializer.validate`は保存済み画像と新規アップロードの寸法・容量を調べ、最後に`seek(0)`で巻き戻していた。Pillowへファイルオブジェクトを渡した場合、image contextを抜けても呼び出し元のstreamは閉じない。Django FieldFileが開いたstorage fileをそのまま保持し、Windowsでは既存の6版/7版画像順序試験のTemporaryDirectory削除がWinError32で失敗していた。

[Pillowのfile lifecycle](https://pillow.readthedocs.io/en/stable/reference/open_files.html)と、ローカルPillow12.2・固定配布物Pillow13の実装を照合した。FieldFileは未開封なら`storage.open(name, "rb")`で開く。Pillowのimage contextだけで、そのFieldFileの解放を代用しない。

保存済み画像は巻き戻し後の`finally`で閉じる。メタデータ読取や巻き戻しに失敗しても解放を試み、既存の安全な日本語ValidationErrorを維持する。新規アップロードは、後続の保存処理が全bytesを読めるよう、従来どおり開いたまま先頭へ戻す。寸法による容量見積もり、30MB上限、画像数/形式/サイズ上限、更新対象の除外、main画像処理は変更しない。

固定imageのDjango FieldFileとS3Fileの実装も確認した。通常の保存済み読取はrbで、S3Fileの空file作成はw modeの条件付きである。今回、実S3の読取/書込み・permission変更を実行したという意味ではない。

## 再現と検証

6版/7版の正常読取、メタデータ取得失敗、総容量超過、close失敗の5失敗を変更前に再現した。新しい4テストは実FileSystemStorageが返したhandleのclosed状態を検査し、失敗時も合成fixtureを確実に片付ける。既存2テストのアップロード巻き戻し・全bytes読取も維持する。CIのPG明示対象へこの6テストのmoduleを追加した。

修正後は、Windowsで以前失敗していた2件を含む関連5 module・60件が成功・省略0。固定したtest dependency imageのLinux source overlayでも同じ60件が成功・省略0。変更した製品実行行6/6と分岐2/2を実行し、除外0。Black/isort/Flake8/Bandit0、差分・日本語説明・UTF-8/LF/no BOMを確認した。最終commit由来の通常配布物とCIは、そのheadの結果を別に追跡する。

これはハンドル残留の修正であり、先の0.25 CPU/512 MiB・swap上限同値の負荷試験で起きたOOMの原因を確定した結果ではない。全操作p95≤3秒/エラー0、実AWS/S3と画像5枚付近・長時間等の性能条件は引き続き未完了。親候補や過去の増強案の成功を、このheadの性能合格へ読み替えない。

## 影響・復旧

画面文言・モデル/移行・依存lock・ファイル内容/保存名・DBデータ・共有権限を変更しない。AWSリソース/反映・Secrets/IAM・継続費用・実Stripe・外部通知・公開は含まない。未適用コードはrevert PRで戻せるが、ハンドル残留とWindowsでの後片付け失敗も戻る。DBの逆移行は不要。OS52指摘と他の全25条件、正式公開No-Goを維持する。
