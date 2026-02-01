# キャラクター装備管理機能 仕様書

## 1. 概要

キャラクターシート（6版）における武器・防具・アイテムの登録・管理機能の仕様書です。

**ステータス**: 実装済み

## 2. 機能概要

### 2.1 対応アイテムタイプ

| タイプ | 説明 | 例 |
|--------|------|-----|
| `weapon` | 武器 | 拳銃、ナイフ、こぶし |
| `armor` | 防具 | 皮製ジャケット、金属製盾 |
| `item` | アイテム | 懐中電灯、ロープ、医療キット |

### 2.2 データ構造

#### 共通フィールド
| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `name` | string | Yes | 装備名 |
| `item_type` | string | Yes | タイプ（weapon/armor/item） |
| `quantity` | int | No | 数量（デフォルト: 1） |
| `weight` | float | No | 重量（kg） |
| `description` | string | No | 説明・メモ |

#### 武器専用フィールド
| フィールド | 型 | 説明 | 例 |
|-----------|-----|------|-----|
| `skill_name` | string | 使用技能 | 拳銃、こぶし（パンチ） |
| `damage` | string | ダメージ | 1D10、1D3+DB |
| `base_range` | string | 射程 | タッチ、10m、30m |
| `attacks_per_round` | int | 攻撃回数/ラウンド | 1、2、3 |
| `ammo` | int | 装弾数 | 6、15 |
| `malfunction_number` | int | 故障ナンバー（1-100） | 98、100 |

#### 防具専用フィールド
| フィールド | 型 | 説明 | 例 |
|-----------|-----|------|-----|
| `armor_points` | int | 装甲ポイント | 1、3、5 |

## 3. API仕様

### 3.1 エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/accounts/character-sheets/{id}/equipment/` | 装備一覧取得 |
| POST | `/api/accounts/character-sheets/{id}/equipment/` | 装備追加 |
| GET | `/api/accounts/character-sheets/{id}/equipment/{pk}/` | 装備詳細取得 |
| PUT | `/api/accounts/character-sheets/{id}/equipment/{pk}/` | 装備全更新 |
| PATCH | `/api/accounts/character-sheets/{id}/equipment/{pk}/` | 装備部分更新 |
| DELETE | `/api/accounts/character-sheets/{id}/equipment/{pk}/` | 装備削除 |

### 3.2 リクエスト例

#### 武器追加
```json
POST /api/accounts/character-sheets/1/equipment/
{
    "item_type": "weapon",
    "name": ".38リボルバー",
    "skill_name": "拳銃",
    "damage": "1D10",
    "base_range": "15m",
    "attacks_per_round": 1,
    "ammo": 6,
    "malfunction_number": 100,
    "quantity": 1,
    "description": "信頼性の高い護身用拳銃"
}
```

#### 防具追加
```json
POST /api/accounts/character-sheets/1/equipment/
{
    "item_type": "armor",
    "name": "厚手の皮ジャケット",
    "armor_points": 1,
    "quantity": 1,
    "description": "多少の防御力を持つ"
}
```

#### アイテム追加
```json
POST /api/accounts/character-sheets/1/equipment/
{
    "item_type": "item",
    "name": "懐中電灯",
    "quantity": 1,
    "weight": 0.3,
    "description": "単三電池2本使用"
}
```

### 3.3 レスポンス例
```json
{
    "id": 1,
    "item_type": "weapon",
    "name": ".38リボルバー",
    "skill_name": "拳銃",
    "damage": "1D10",
    "base_range": "15m",
    "attacks_per_round": 1,
    "ammo": 6,
    "malfunction_number": 100,
    "armor_points": null,
    "description": "信頼性の高い護身用拳銃",
    "quantity": 1,
    "weight": null
}
```

## 4. UI仕様

### 4.1 作成画面（character_6th_create.html）

#### 配置
- **タブ**: 「戦闘・装備」タブ内
- **セクション**: 「武器・防具・アイテム」カード

#### サブタブ構成
1. **武器タブ**: 武器の追加・管理
2. **防具タブ**: 防具の追加・管理
3. **アイテムタブ**: アイテムの追加・管理

#### 操作
- **追加ボタン**: 各タブに「+ 追加」ボタン
- **削除ボタン**: 各装備カードにゴミ箱アイコン
- **入力フォーム**: タイプに応じたフィールドを動的表示

### 4.2 装備カードUI

#### 武器カード
```
┌─────────────────────────────────────────┐
│ 武器                              [削除] │
├─────────────────────────────────────────┤
│ 名称: [____________]  数量: [__] 重量: [__] │
│ 技能: [____________]  ダメージ: [______]  │
│ 射程: [______]  攻撃/R: [__]  装弾数: [__] │
│ 故障: [__]                                │
│ メモ: [________________________________] │
└─────────────────────────────────────────┘
```

#### 防具カード
```
┌─────────────────────────────────────────┐
│ 防具                              [削除] │
├─────────────────────────────────────────┤
│ 名称: [____________]  数量: [__] 重量: [__] │
│ 装甲P: [__]                               │
│ メモ: [________________________________] │
└─────────────────────────────────────────┘
```

#### アイテムカード
```
┌─────────────────────────────────────────┐
│ アイテム                          [削除] │
├─────────────────────────────────────────┤
│ 名称: [____________]  数量: [__] 重量: [__] │
│ メモ: [________________________________] │
└─────────────────────────────────────────┘
```

## 5. JavaScript実装

### 5.1 主要関数（character6th.js）

| 関数名 | 説明 |
|--------|------|
| `createEquipmentCard(itemType, initial)` | 装備カードのDOM生成 |
| `addEquipmentCard(itemType, initial)` | カードをコンテナに追加 |
| `initEquipmentUi()` | UIイベントの初期化 |
| `collectEquipmentFromUi()` | フォームからデータ収集 |
| `renderEquipmentUi(equipmentList)` | 既存データの表示 |
| `syncEquipment(characterId, desiredEquipment)` | APIとの同期 |

### 5.2 データフロー

```
[UIフォーム入力]
      ↓
[collectEquipmentFromUi()] → equipment配列
      ↓
[フォーム送信]
      ↓
[syncEquipment()] → API呼び出し
      ↓
[サーバー保存]
```

## 6. バリデーション

### 6.1 サーバーサイド（CharacterEquipment.clean()）

| フィールド | ルール |
|-----------|--------|
| `name` | 必須、空文字不可 |
| `attacks_per_round` | 0以上 |
| `ammo` | 0以上 |
| `malfunction_number` | 1-100の範囲 |
| `armor_points` | 0以上 |
| `quantity` | 1以上 |
| `weight` | 0以上 |

### 6.2 クライアントサイド

- 名前が空の場合、保存時にスキップ
- 数量のデフォルト値: 1
- 数値フィールドはHTML inputの`min`/`max`属性で制限

## 7. 関連ファイル

### 7.1 バックエンド
- `accounts/character_models.py` - CharacterEquipmentモデル（920-1019行）
- `accounts/serializers.py` - CharacterEquipmentSerializer（206-226行）
- `accounts/views/character_views.py` - CharacterEquipmentViewSet
- `accounts/urls/__init__.py` - APIルーティング（151-165行）

### 7.2 フロントエンド
- `templates/accounts/character_6th_create.html` - 作成画面UI（726-799行）
- `static/accounts/js/character6th.js` - JavaScript実装

### 7.3 テスト
- `accounts/test_inventory_management.py` - 装備管理テスト
- `accounts/test_combat_data.py` - 戦闘データテスト

## 8. 更新履歴

| 日付 | 内容 |
|------|------|
| 2026-01-25 | 仕様書作成（実装確認後） |
