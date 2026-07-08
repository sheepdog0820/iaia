# セッション・ハンドアウト・キャラクター紐付け仕様書

## 概要
GMがセッションを作成し、4人のプレイヤーとそのキャラクター、個別のハンドアウト（HO）を管理する機能。

## 機能要件

### 1. セッション参加者管理
- GMは最大4人のプレイヤーを事前に設定可能
- 各プレイヤー枠（プレイヤー1〜4）を定義
- 各枠にプレイヤーとキャラクターを割り当て

### 2. ハンドアウト（HO）管理
- GMは4つのハンドアウト（HO1〜HO4）を作成
- 各HOは特定のプレイヤー枠に紐付け
- HOは割り当てられたプレイヤーのみ閲覧可能

### 3. キャラクター紐付け
- プレイヤーは自分のHOにキャラクターを紐付け可能
- GMは各プレイヤー枠にキャラクターを事前設定可能
- キャラクター情報はセッション内で共有

## 技術仕様

### データモデル

#### SessionParticipant 拡張
```python
class SessionParticipant(models.Model):
    # 既存フィールド
    session = models.ForeignKey(TRPGSession)
    user = models.ForeignKey(CustomUser)
    role = models.CharField(choices=[('gm', 'GM'), ('player', 'PL')])
    
    # 追加フィールド
    player_number = models.IntegerField(null=True, choices=[(1, 'プレイヤー1'), (2, 'プレイヤー2'), (3, 'プレイヤー3'), (4, 'プレイヤー4')])
    character_sheet = models.ForeignKey(CharacterSheet, null=True, blank=True)
    handout = models.ForeignKey(HandoutInfo, null=True, blank=True, related_name='assigned_participant')
```

#### HandoutInfo 拡張
```python
class HandoutInfo(models.Model):
    # 既存フィールド
    session = models.ForeignKey(TRPGSession)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_secret = models.BooleanField(default=True)
    
    # 追加フィールド
    handout_number = models.IntegerField(null=True, choices=[(1, 'HO1'), (2, 'HO2'), (3, 'HO3'), (4, 'HO4')])
    assigned_player_number = models.IntegerField(null=True, choices=[(1, 'プレイヤー1'), (2, 'プレイヤー2'), (3, 'プレイヤー3'), (4, 'プレイヤー4')])
```

### API仕様

#### 1. セッション参加者設定
```
POST /api/schedules/sessions/{session_id}/assign-player/
{
    "player_number": 1,
    "user_id": 123,
    "character_sheet_id": 456  // オプション
}
```

#### 2. ハンドアウト作成・更新
```
POST /api/schedules/sessions/{session_id}/handouts/
{
    "title": "HO1: 私立探偵",
    "content": "あなたは...",
    "handout_number": 1,
    "assigned_player_number": 1,
    "is_secret": true
}
```

#### 3. キャラクター紐付け
```
POST /api/schedules/sessions/{session_id}/link-character/
{
    "character_sheet_id": 456
}
```

### 権限管理
- GM: 全てのHO作成・編集・閲覧可能
- プレイヤー: 自分に割り当てられたHOのみ閲覧可能
- プレイヤー: 自分のキャラクターのみ紐付け可能

## UI仕様

### GM画面
1. セッション編集画面
   - プレイヤー1〜4の枠表示
   - 各枠にユーザー選択ドロップダウン
   - 各枠にキャラクター表示/選択

2. ハンドアウト管理画面
   - HO1〜HO4のタブ/アコーディオン
   - 各HOの編集フォーム
   - プレイヤー割り当て設定

### プレイヤー画面
1. セッション詳細画面
   - 自分のHOのみ表示
   - キャラクター選択/紐付けボタン
   - 他プレイヤーの基本情報表示（キャラクター名等）

## 実装ステップ
1. モデル拡張（マイグレーション）
2. シリアライザー更新
3. API View実装
4. 権限チェック実装
5. フロントエンド実装
6. テスト作成