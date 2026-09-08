# ココフォリアの画像連携の制限と未確認事項

2026-09-08、67221be6時点のコードと[公式Clipboard API](https://docs.ccfolia.com/developer-api/clipboard-api)を照合した。公式形式にはiconUrlとfacesが含まれるが、外部データからiconUrlおよびfaces[].iconUrlを設定できない旨が明記されている。

現行CharacterExportManager.export_ccfolia_formatは6版・7版ともdata.iconUrlを空文字にする。APIのccfolia_jsonも同じ出力を返し、static/js/ccfolia_character_copy.jsに画像URLを追加する処理はない。6版仕様書のJSON例には画像URLが出力されるような記載が残っていたため、現行出力に合わせて空文字へ訂正した。画像の自動転送を実装・検証済みとはしない。

この制限に対して、非公開画像URLの公開化、長期共有URLの発行、data URL等による回避は実施していない。画像付きで利用する場合の受け取り側での画像登録・差分設定は、別途操作と検証が必要。公式の[立ち絵・表情差分](https://docs.ccfolia.com/pl-tutorial/character-edit/character-icon)も参照し、どの利用手順を正式公開の対象とするかを確定する。

以前の実ルーム検証は能力値・ステータス・チャットパレットの取り込みまでで、画像アップロードは未実施（[記録](FULL_VALIDATION_2026-09-06.md)）。今回、操作ツールの利用可能ブラウザを照会したところ、Chromeは一覧に存在せず、タブなしのCodex内蔵ブラウザだけだった。ユーザーの既存Chromeセッション・テストルームを読み取れなかったため、実画像の受け取り検証は未完了。別ブラウザでログインやルーム変更を行って代替していない。

I07の完了条件を縮小したり、画像確認を成功へ変更したりする記録ではない。Chromeの接続回復、合成テスト画像と対象ルームの確認、受け取り側の画像登録・表示・差分の実証を残す。コード、実ルーム、DB、Secrets、公開範囲は変更していない。
