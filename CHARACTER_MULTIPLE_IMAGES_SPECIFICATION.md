# キャラクター複数画像アップロード機能仕様書

## 概要
クトゥルフ神話TRPG 6版のキャラクターシートに複数の画像をアップロード・管理できる機能を実装する。

## 機能要件

### 1. 画像アップロード機能
- **複数画像対応**: 1キャラクターにつき最大10枚まで画像をアップロード可能
- **対応フォーマット**: JPEG, PNG, GIF, BMP, WEBP
- **ファイルサイズ制限**: 1ファイルあたり最大5MB
- **総容量制限**: 1キャラクターあたり最大30MB

### 2. 画像管理機能
- **メイン画像設定**: 複数画像のうち1枚をメイン画像として設定可能
- **画像順序管理**: ドラッグ&ドロップまたは番号指定で表示順序を変更可能
- **個別削除**: 画像を個別に削除可能
- **一括削除**: すべての画像を一括削除可能

### 3. 画像表示機能
- **プレビュー表示**: アップロード前に画像をプレビュー表示
- **サムネイル表示**: 一覧画面では最適化されたサムネイル表示
- **レスポンシブ対応**: 画面サイズに応じて自動調整
- **画像拡大表示**: クリックで拡大表示（モーダル）

## 技術仕様

### 1. データモデル

#### CharacterImageモデル（新規作成）
```python
class CharacterImage(models.Model):
    character_sheet = models.ForeignKey(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="キャラクターシート"
    )
    image = models.ImageField(
        upload_to='character_images/%Y/%m/%d/',
        verbose_name="画像"
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name="メイン画像"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="表示順序"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="アップロード日時"
    )
    
    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = "キャラクター画像"
        verbose_name_plural = "キャラクター画像"
        constraints = [
            models.UniqueConstraint(
                fields=['character_sheet'],
                condition=models.Q(is_main=True),
                name='unique_main_image_per_character'
            )
        ]
```

#### CharacterSheetモデルの修正
- 既存の`character_image`フィールドは削除（後方互換性のためマイグレーションで対応）
- `images`関連名で複数画像にアクセス可能

### 2. API仕様

#### 画像アップロードエンドポイント
```
POST /api/characters/{character_id}/images/
Content-Type: multipart/form-data

Parameters:
- image: ファイル（必須）
- is_main: boolean（任意、デフォルト: false）
- order: integer（任意、デフォルト: 最後尾）

Response:
{
    "id": 1,
    "image_url": "/media/character_images/2025/06/21/image.jpg",
    "thumbnail_url": "/media/character_images/2025/06/21/image_thumb.jpg",
    "is_main": false,
    "order": 1,
    "uploaded_at": "2025-06-21T10:00:00Z"
}
```

#### 画像一覧取得エンドポイント
```
GET /api/characters/{character_id}/images/

Response:
{
    "count": 3,
    "results": [
        {
            "id": 1,
            "image_url": "/media/character_images/2025/06/21/image1.jpg",
            "thumbnail_url": "/media/character_images/2025/06/21/image1_thumb.jpg",
            "is_main": true,
            "order": 0
        },
        ...
    ]
}
```

#### 画像順序更新エンドポイント
```
PATCH /api/characters/{character_id}/images/reorder/
Content-Type: application/json

{
    "order": [
        {"id": 3, "order": 0},
        {"id": 1, "order": 1},
        {"id": 2, "order": 2}
    ]
}
```

### 3. フロントエンド仕様

#### アップロードUI
- ドラッグ&ドロップ対応のアップロードエリア
- 複数ファイル同時選択可能
- アップロード進捗表示
- エラーメッセージ表示（ファイルサイズ超過、フォーマット不正等）

#### プレビュー表示
- グリッドレイアウト（PC: 3列、タブレット: 2列、スマホ: 1列）
- 各画像にホバーで操作ボタン表示（削除、メイン設定、順序変更）
- メイン画像には特別なバッジ表示

#### 画像ビューア
- ライトボックス形式での拡大表示
- 左右スワイプ/矢印キーでの画像切り替え
- ピンチイン/アウトでのズーム対応

### 4. バリデーション

#### サーバーサイド
- ファイルサイズチェック（5MB以下）
- ファイル形式チェック（画像ファイルのみ）
- 総容量チェック（30MB以下）
- 画像数チェック（10枚以下）
- ウイルススキャン（オプション）

#### クライアントサイド
- ファイル選択時の即座チェック
- プレビュー生成前のファイルサイズ確認
- 適切なエラーメッセージ表示

### 5. パフォーマンス最適化

#### 画像処理
- アップロード時に自動でサムネイル生成（200x200px）
- 大きすぎる画像は自動リサイズ（最大1920x1080px）
- WebP形式への自動変換（ブラウザ対応時）

#### 遅延読み込み
- 画像一覧では遅延読み込み実装
- IntersectionObserver APIを使用

### 6. セキュリティ

#### アクセス制御
- 画像のアップロード/削除は所有者のみ可能
- 画像の閲覧はキャラクターの閲覧権限に準拠

#### ファイル検証
- MIMEタイプの検証
- ファイルヘッダーの検証
- 悪意のあるコードの検出

## マイグレーション計画

### 既存データの移行
1. 既存の`character_image`フィールドのデータを新しい`CharacterImage`モデルに移行
2. 移行したデータは`is_main=True`として設定
3. 移行完了後、古いフィールドを削除

### 後方互換性
- 移行期間中は両方のフィールドを維持
- APIは新旧両方のデータ形式をサポート
- 完全移行後に旧形式のサポートを削除

## テスト計画

### ユニットテスト
- モデルのバリデーションテスト
- 画像アップロード/削除のテスト
- 権限チェックのテスト
- 順序変更のテスト

### 統合テスト
- 複数画像アップロードのフロー全体
- 画像表示の確認
- エラーハンドリングの確認

### パフォーマンステスト
- 大量画像アップロード時の処理時間
- サムネイル生成の処理時間
- ページ読み込み速度

## 実装優先順位

1. **Phase 1**: 基本機能（必須）
   - CharacterImageモデルの作成
   - 画像アップロード/削除API
   - 基本的な画像表示

2. **Phase 2**: 管理機能（推奨）
   - メイン画像設定
   - 順序変更機能
   - サムネイル生成

3. **Phase 3**: 高度な機能（オプション）
   - ドラッグ&ドロップ
   - 画像ビューア
   - 自動リサイズ/最適化