# キャラクター複数画像アップロード仕様書（最新版）

本ドキュメントはキャラクターシートに紐づく複数画像機能の仕様を集約します。詳細な挙動とAPIパスをここに一本化し、他ドキュメントの重複を解消します。

## 機能要件
- 1キャラクターにつき最大10枚（目安）まで画像を登録できる
- 対応形式: JPEG / PNG / GIF / BMP / WEBP（アップロードバリデーションはサーバ側で実装）
- サイズ上限: 1ファイル最大5MB、総容量は30MB目安
- メイン画像を1枚必ず保持する（DBユニーク制約で担保）
- 並び順(order)を保持し、UIの並べ替えに対応
- 個別削除・一括削除・メイン切替・並び替えを提供

## モデル仕様（抜粋）
- `CharacterImage` (FK: `character_sheet`, related_name=`images`)
  - `image` (ImageField, `upload_to='character_images/%Y/%m/%d/'`)
  - `is_main` (Bool, default False)
  - `order` (PositiveInteger, default 0)
  - Meta: `ordering=['order', 'uploaded_at']`
  - Constraint: `unique_main_image_per_character` … `is_main=True` が1件に制約
- 既存の `character_image` フィールドは廃止し、`images` で複数管理（マイグレーションで後方互換対応）

## APIエンドポイント（Django URL準拠）
- アップロード／一覧: `GET|POST /accounts/character-sheets/{character_sheet_id}/images/`
- 詳細／削除: `GET|DELETE /accounts/character-sheets/{character_sheet_id}/images/{image_id}/`
- メイン画像設定: `POST /accounts/character-sheets/{character_sheet_id}/images/{image_id}/set_main/`
- 並び替え: `PATCH /accounts/character-sheets/{character_sheet_id}/images/reorder/`

## 動作ルール
- 最初にアップロードした画像は自動でメインに設定する。
- メイン画像を削除する際は、当該フラグを外し、残存画像があれば `order` 先頭をメインに昇格させる。
- `set_main` は POST で実行し、既存メインは内部で解除する。
- 並び替えでは `{id, order}` の配列を受け取り、指定順に更新する。

## テストカバレッジ（関連）
- `accounts.test_character_integration.CharacterIntegrationTestCase.test_character_image_management`
- `accounts.test_character_image_apis.CharacterImageAPISMokeTest`（メイン切替・削除昇格）
