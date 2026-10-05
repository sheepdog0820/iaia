# 画像APIテストのWindows一時ファイル解放

## 範囲と原因

背景透過の権限再確認を検証する際、既存 `CharacterImageAppendOrderTests` の6版・7版の2件が、Windowsで一時画像を削除できず終了エラーになった。HTTPの画像追加・順序のassertionではなく、`TemporaryDirectory` 終了時の `WinError 32` を記録した。

成功したAPI応答の `ReturnDict` はserializer/modelを保持し、保存画像のfile参照が循環して残り得る。テストclientがすでに応答をcloseしていることを確認し、各反復で応答参照を解放、mediaディレクトリの削除前に循環参照を回収する。アプリの画像処理・API・保存仕様は変更しない。

初案の `response.close()` 再実行は採用しない。PostgreSQLで `request_finished` による接続closeがatomicテスト内に波及し、2件が `connection is closed` となったため、`response.closed` の確認へ修正した。SQLiteで初案が通ったことだけを全環境成功とは扱わない。

## 検証と承認境界

同じ画像API・複数画像・背景透過・有料機能ライフサイクルを含む関連143件で、Windows SQLiteと隔離PostgreSQLの最終結果を後続の[背景透過権限確認記録](BACKGROUND_PREMIUM_GATE_2026-10-06.md)にまとめる。途中の失敗ログも保持する。Linux側はread-only source overlay・使い捨てmedia・ネットワーク非公開PGであり、通常配布物の検証ではない。

本変更はテスト後処理のみ。DB・権限・Secrets・課金・AWS・mainを変更せず、正式公開No-Goやアイコン限定反映の承認範囲を変更しない。
