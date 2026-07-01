# キャラクター複数画像アップロード仕様書（最新版）

本ドキュメントはキャラクターシートに紐づく複数画像機能の仕様を集約します。詳細な挙動とAPIパスをここに一本化し、他ドキュメントの重複を解消します。

## 機能要件
- 1キャラクターにつき通常ユーザーは最大2枚、プレミアムユーザーは最大10枚まで画像を登録できる
- 対応形式: JPEG / PNG / GIF（アップロードバリデーションはサーバ側で実装）
- サイズ上限: 1ファイル最大5MB、総容量は30MB目安
- 画像がある場合はメイン画像を1枚に保つ（DBユニーク制約は `is_main=True` の重複を防ぐ）
- 並び順(order)を保持し、UIの並べ替えに対応
- 個別削除・メイン切替・並び替えを提供
- 作成画面ではモーダルのドロップゾーンから複数画像を一括添付できる
- 編集画面ではドロップゾーンから複数画像を追加できる
- 参照画面では複数画像を切り替えて表示し、表示可能な画像がある場合だけZIPダウンロードを提供する

## モデル仕様（抜粋）
- `CharacterImage` (FK: `character_sheet`, related_name=`images`)
  - `image` (ImageField, `upload_to='character_images/%Y/%m/%d/'`)
  - `is_main` (Bool, default False)
  - `order` (PositiveInteger, default 0)
  - Meta: `ordering=['order', 'uploaded_at']`
  - Constraint: `unique_main_image_per_character` … `is_main=True` が1件に制約
- 既存の `character_image` フィールドはレガシー互換用に残し、新規の複数画像は `images` で管理する

## APIエンドポイント（Django URL準拠）
- アップロード／一覧: `GET|POST /api/accounts/character-sheets/{character_sheet_id}/images/`
- 詳細／更新／削除: `GET|PUT|PATCH|DELETE /api/accounts/character-sheets/{character_sheet_id}/images/{image_id}/`
- ZIPダウンロード: `GET /api/accounts/character-sheets/{character_sheet_id}/images/download/`
- メイン画像設定: `POST|PATCH /api/accounts/character-sheets/{character_sheet_id}/images/{image_id}/set_main/`
- 並び替え: `PATCH /api/accounts/character-sheets/{character_sheet_id}/images/reorder/`
- 共有リンク画像一覧: `GET /share/characters/{token}/images/`
- 共有リンクZIPダウンロード: `GET /share/characters/{token}/images.zip`

## 動作ルール
- 最初にアップロードした画像は自動でメインに設定する。
- メイン画像を削除する際は、当該フラグを外し、残存画像があれば `order` 先頭をメインに昇格させる。
- `set_main` は POST で実行し、既存メインは内部で解除する。
- 並び替えでは `{id, order}` の配列を受け取り、指定順に更新する。
- ZIPは `CharacterImage` を `order, uploaded_at, id` 順で格納し、`CharacterImage` が0件で旧 `CharacterSheet.character_image` がある場合のみ互換用に1件含める。
- ZIP内ファイル名は `01_main_<元ファイル名>` / `02_<元ファイル名>` 形式で、安全化と重複回避を行う。
- 画像一覧とZIPは、通常APIでは既存のキャラクター閲覧権限に従い、共有リンクAPIでは `link` または `public` のトークン経由のみ許可する。

## テストカバレッジ（関連）
- `accounts.test_character_integration.CharacterIntegrationTestCase.test_character_image_management`
- `accounts.test_character_image_apis.CharacterImageAPISMokeTest`（メイン切替・削除昇格）
