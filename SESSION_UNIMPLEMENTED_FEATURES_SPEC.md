# セッション機能未実装仕様書

## 概要
本ドキュメントは、タブレノ TRPGセッション管理システムにおける未実装のセッション関連機能の仕様をまとめたものです。

## 🔴 高優先度機能

### 1. セッションノート・ログシステム

#### 概要
セッション終了後の記録管理機能。GMと参加者が別々にノートを作成でき、キャンペーンの継続性を保つ。

#### 詳細仕様
- **GMプライベートノート**: GM専用の非公開メモ
- **セッションサマリー**: 全員が閲覧可能な公式記録
- **プレイログ**: セッション中の重要な出来事の時系列記録
- **NPCメモ**: 登場したNPCの情報管理
- **次回への引き継ぎ事項**: 未解決の謎、次回の目標など

#### 技術要件
```python
class SessionNote(models.Model):
    session = models.ForeignKey(TRPGSession)
    author = models.ForeignKey(CustomUser)
    note_type = models.CharField(choices=['gm_private', 'public_summary', 'player_note'])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
class SessionLog(models.Model):
    session = models.ForeignKey(TRPGSession)
    timestamp = models.DateTimeField()
    event_type = models.CharField(max_length=50)
    description = models.TextField()
    related_character = models.ForeignKey(CharacterSheet, null=True)
```

### 2. キャラクターシート統合機能

#### 概要
セッションとキャラクターシートの深い統合により、ゲーム中のキャラクター管理を効率化。

#### 詳細仕様
- **キャラクターリンク**: 参加者のキャラクターシートを直接セッションに紐付け
- **ステータストラッキング**: HP/MP/SAN値のリアルタイム追跡
- **セッション開始時スナップショット**: キャラクター状態の記録
- **セッション終了時の変更履歴**: 成長・アイテム取得の記録

#### 技術要件
```python
class SessionCharacterStatus(models.Model):
    participant = models.ForeignKey(SessionParticipant)
    character_sheet = models.ForeignKey(CharacterSheet)
    hp_current = models.IntegerField()
    hp_max = models.IntegerField()
    san_current = models.IntegerField(null=True)  # クトゥルフ専用
    mp_current = models.IntegerField(null=True)
    status_effects = models.JSONField(default=list)
    last_updated = models.DateTimeField(auto_now=True)
```

### 3. セッション素材管理システム

#### 概要
マップ、音楽、画像などのセッション素材を一元管理。

#### 詳細仕様
- **素材ライブラリ**: マップ、トークン、BGMの管理
- **外部リンク管理**: Google Drive、YouTube等へのリンク集約
- **素材カテゴリ分類**: 戦闘マップ、NPCイラスト、BGM等
- **セッション別素材セット**: 各セッション用の素材グループ化

#### 技術要件
```python
class SessionResource(models.Model):
    session = models.ForeignKey(TRPGSession)
    resource_type = models.CharField(choices=['map', 'music', 'image', 'document'])
    name = models.CharField(max_length=200)
    url = models.URLField(null=True, blank=True)
    file = models.FileField(upload_to='session_resources/', null=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
```

## 🟡 中優先度機能

### 4. 高度なスケジューリング機能

#### 概要
定期セッションや複雑なスケジュール調整に対応。

#### 詳細仕様
- **定期セッション設定**: 毎週土曜日19:00等の繰り返し設定
- **キャンペーン管理**: 連続セッションのグループ化
- **参加可能日投票**: Doodle風の日程調整機能
- **タイムゾーン対応**: オンラインセッション用の時差管理

#### 技術要件
```python
class SessionSeries(models.Model):
    name = models.CharField(max_length=200)
    group = models.ForeignKey(Group)
    recurrence_rule = models.CharField(max_length=200)  # RFC 5545 RRULE
    default_duration = models.IntegerField()
    default_gm = models.ForeignKey(CustomUser)
    
class SessionAvailability(models.Model):
    proposed_date = models.DateTimeField()
    user = models.ForeignKey(CustomUser)
    availability = models.CharField(choices=['yes', 'no', 'maybe'])
```

### 5. セッション準備ツール

#### 概要
GM向けのセッション準備支援機能。

#### 詳細仕様
- **準備チェックリスト**: セッション前の確認事項
- **セッションテンプレート**: よく使う設定のテンプレート化
- **必要アイテムリスト**: ダイス、ルルブ等の持ち物リスト
- **セッション0サポート**: キャラ作成セッション用の特別モード

### 6. セッション後機能

#### 概要
セッション終了後の処理を効率化。

#### 詳細仕様
- **フィードバックシステム**: 参加者からの感想・評価
- **経験値配布**: XP/成長ポイントの記録と配布
- **アイテム・報酬管理**: 取得アイテムの記録と分配
- **思い出記録**: 印象的なシーン、名言の保存

## 🟢 低優先度機能

### 7. セッション分析機能

#### 概要
セッションデータの統計分析とビジュアライゼーション。

#### 詳細仕様
- **参加率分析**: プレイヤーごとの出席率
- **人気時間帯分析**: よく開催される曜日・時間帯
- **セッション時間推移**: 平均プレイ時間の変化
- **GM負荷分析**: GM担当の偏り検出

### 8. コミュニケーション機能

#### 概要
セッション前後のコミュニケーション円滑化。

#### 詳細仕様
- **セッション掲示板**: 各セッション専用の議論スペース
- **クイック投票**: セッション中の簡易投票機能
- **セッションチャット**: リアルタイムチャット機能

### 9. 外部サービス連携

#### 概要
他のTRPGツールとの連携強化。

#### 詳細仕様
- **Discord連携**: ボイスチャンネル自動作成
- **VTT連携**: Roll20/Foundry VTTとのデータ同期
- **カレンダー同期**: Google Calendar/Outlook連携
- **配信連携**: YouTube/Twitch配信との連動

## 実装優先順位

### Phase 1（即実装可能）
1. セッションサマリーフィールドの追加
2. 基本的なキャラクターHP/SAN追跡
3. セッション素材URLの複数登録
4. セッションタグ機能

### Phase 2（中期実装）
1. セッションノートシステム全体
2. 定期セッション機能
3. 素材ライブラリ基本機能
4. フィードバックシステム

### Phase 3（長期実装）
1. 完全なキャラクター統合
2. 高度な分析ダッシュボード
3. 外部サービスAPI連携

## データベース設計の考慮事項

既存のモデルフィールドで活用されていないもの：
- `youtube_url`: 汎用的なメディアURLフィールドに拡張可能
- `duration_minutes`: セッション分析に活用可能
- `character_sheet_url`: キャラクター統合の基盤として利用可能

## まとめ

これらの機能を実装することで、タブレノはよりTRPGプレイヤーのニーズに応えるシステムとなります。特にセッションノート、キャラクター統合、素材管理の3つは、実際のプレイ体験を大きく向上させる重要な機能です。