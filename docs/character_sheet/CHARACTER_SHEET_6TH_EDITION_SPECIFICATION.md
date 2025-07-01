# クトゥルフ神話TRPG 6版 キャラクターシート完全仕様書

**作成日**: 2025年6月24日  
**バージョン**: 1.0.0  
**ステータス**: 実装完了

---

## 📋 目次

1. [概要](#概要)
2. [画面構成](#画面構成)
3. [機能詳細](#機能詳細)
4. [データ構造](#データ構造)
5. [技術仕様](#技術仕様)
6. [UI/UX仕様](#uiux仕様)
7. [API仕様](#api仕様)

---

## 概要

### システム概要
クトゥルフ神話TRPG 6版に完全準拠したWeb型キャラクターシート管理システム。探索者（キャラクター）の作成、管理、セッション運用をサポートする包括的な機能を提供。

### 主要機能
- 🎲 **キャラクター作成**: 能力値ダイスロール、技能ポイント自動計算
- 📊 **ステータス管理**: HP/MP/SAN値の自動計算と管理
- 🎯 **技能管理**: 職業技能・趣味技能ポイントの割り振り
- 🖼️ **画像管理**: 複数画像のアップロード対応
- 📤 **CCFOLIA連携**: ワンクリックでCCFOLIA形式にエクスポート
- 📱 **レスポンシブ対応**: PC・タブレット・スマートフォン対応
- 🔒 **公開/非公開設定**: キャラクターの公開範囲を制御
- 👥 **他ユーザー参照**: 公開キャラクターの閲覧機能
- 🔍 **検索・フィルター**: キャラクター名、ステータスでの絞り込み
- 🎮 **セッション連携**: TRPGセッションとの統合

---

## 画面構成

### 1. キャラクター一覧画面 (`/accounts/character/list/`)

#### 機能概要
- 作成済みキャラクターの一覧表示
- サムネイル形式でのカード表示
- フィルタリング機能（版別、キャラクター名検索）

#### 表示要素
- **キャラクターカード**
  - キャラクター画像（デフォルト画像対応）
  - 基本情報（名前、職業、年齢）
  - ステータスバッジ（生存/死亡/発狂等）
  - HP/MP/SAN値の現在値/最大値
  - バージョン情報
  - 作成日時
  - 公開/非公開アイコン
  - 所有者名（他ユーザーのキャラクターの場合）

#### アクション
- 詳細表示
- 編集（自分のキャラクターのみ）
- 複製（新バージョン作成）
- 削除（自分のキャラクターのみ）
- 新規作成
- 検索・フィルター

#### HP表示の整合性（2025年7月1日追加）
- **一覧表示と詳細表示でHP値を一致させる**
- 現在HP/最大HPの表示形式を統一
- 現在HPが0の場合も正しく「0/最大HP」と表示

### 2. キャラクター作成画面 (`/accounts/character/create/6th/`)

#### タブ構成
1. **基本情報タブ**
   - 探索者名（必須）
   - プレイヤー名
   - 年齢（15-90歳）
   - 性別
   - 職業
   - 出身地
   - 居住地

2. **能力値タブ**
   - 8つの基本能力値（STR, CON, POW, DEX, APP, SIZ, INT, EDU）
   - 各能力値に対するダイスロール機能
   - グローバル/個別ダイス設定
   - **能力値の入力制限なし**（任意の値を入力可能）
   - 副次ステータス自動計算
     - HP: (CON + SIZ) ÷ 2（端数切り上げ）
     - MP: POW
     - 初期SAN: POW × 5
     - 最大SAN: 99 - クトゥルフ神話技能
     - アイデア: INT × 5
     - 幸運: POW × 5
     - 知識: EDU × 5
     - ダメージボーナス: STR + SIZによる自動計算
   - **現在値入力機能**（2025年6月25日追加）
     - 現在HP: 任意入力可能（制限なし）
     - 現在MP: 任意入力可能（制限なし）
     - 現在正気度: 任意入力可能（制限なし）
     - 新規作成時のデフォルト値は最大値
     - 0、負の値、最大値を超える値も入力可能

3. **技能タブ**
   - **技能ポイント配分**
     - 職業技能ポイント: 計算方式選択可能（後述）
     - 趣味技能ポイント: INT × 10
   - **技能一覧**
     - 職業別推奨技能のハイライト表示
     - リアルタイム合計値計算
     - 技能値上限チェック（90%）
     - **DEX連動技能**（2025年7月1日追加）
       - 回避技能の基本値はDEX×2で自動計算
       - DEX値変更時に回避技能の基本値も自動更新
     - **技能初期値のカスタマイズ**（2025年7月1日追加）
       - 各技能の初期値をユーザーが変更可能
       - 変更した初期値は保存され、次回作成時に適用
   - **技能フィルタリング**
     - カテゴリ別フィルター
     - 検索機能
     - ポイント割り振り済み技能の表示

4. **プロフィールタブ**
   - 精神的な障害
   - キャラクターメモ
   - バックストーリー
   - 公開/非公開設定

5. **装備品タブ**
   - **武器管理**
     - 武器の追加・編集・削除
     - ドラッグ&ドロップで並び替え
     - 使用技能の自動補完
   - **防具管理**
     - 防具の追加・編集・削除
     - 装甲値と保護部位の設定
   - **一般装備**
     - アイテムの追加・編集・削除
     - 数量管理
     - 重量計算（オプション）

6. **CCFOLIA連携タブ**
   - エクスポート設定
   - カスタムパラメータ設定
   - JSONダウンロード

### 3. キャラクター詳細画面 (`/accounts/character/{id}/`)

#### 表示要素
- **ヘッダー部**
  - キャラクター名
  - 版情報バッジ
  - 編集ボタン
  - 一覧へ戻るボタン

- **画像ギャラリー**
  - メイン画像表示
  - サムネイルギャラリー
  - 画像クリックでモーダル表示

- **基本情報カード**
  - 個人情報一覧
  - ステータス情報

- **能力値表示**
  - 8能力値のグリッド表示
  - 副次ステータス表示

- **技能一覧**
  - 習得技能の一覧
  - 技能値と成長記録

- **装備品・所持品**
  - 武器一覧（使用技能、ダメージ、射程、装弾数表示）
  - 防具一覧（装甲値、保護部位表示）
  - その他アイテム
  - 重量計算（オプション）

---

## 機能詳細

### 1. ダイスロール機能

#### グローバルダイス設定
- プリセット: 3D6, 2D6+6
- カスタム設定: XDY+Z形式
- 設定の保存と読み込み

#### 個別ダイス設定
- 能力値ごとの個別設定
- ロール履歴の表示
- 振り直し機能

### 2. 副次ステータス自動計算

#### 計算式（6版）
- **最大HP**: (CON + SIZ) / 2（端数切り上げ）
- **最大MP**: POW
- **初期SAN（初期正気度）**: POW × 5
- **最大SAN（最大正気度）**: 99 - クトゥルフ神話技能の現在値
- **ダメージボーナス**: STR + SIZの合計値により決定
  - 2-12: -1D6
  - 13-16: -1D4
  - 17-24: 0
  - 25-32: +1D4
  - 33-40: +1D6
  - 41-56: +2D6
  - 57-72: +3D6
  - 73-88: +4D6
  - 89+: +5D6

#### 特殊な計算
- **アイデアロール**: INT × 5
- **幸運ロール**: POW × 5
- **知識ロール**: EDU × 5

#### 最大正気度の更新
- クトゥルフ神話技能が変更されると自動的に再計算
- 計算式: 99 - クトゥルフ神話技能の現在値
- 現在正気度が最大正気度を超えている場合は、最大値に調整

### 3. 技能ポイント管理

#### 職業技能ポイント計算方式
職業に応じて以下の計算方式から選択可能：

| 選択肢 | 計算式 | 説明 |
|--------|--------|------|
| **標準** | EDU×20 | 一般的な職業（デフォルト） |
| **筋力系** | STR×10+EDU×10 | 軍人、警察官、スポーツ選手など |
| **体力系** | CON×10+EDU×10 | 肉体労働者、冒険家など |
| **精神系** | POW×10+EDU×10 | 聖職者、オカルティストなど |
| **敏捷系** | DEX×10+EDU×10 | 盗賊、曲芸師、職人など |
| **魅力系** | APP×10+EDU×10 | 芸能人、セールスマンなど |
| **体格系** | SIZ×10+EDU×10 | ボディガード、レスラーなど |
| **知性系** | INT×10+EDU×10 | 研究者、探偵、医師など |
| **手動入力** | 任意 | カスタム職業用（GM承認必要） |

#### 趣味技能ポイント
- 固定計算式: INT × 10
- 全職業共通

#### 自動計算とリアルタイム更新
- 能力値変更時に自動再計算
- 使用済み/残りポイントのリアルタイム表示
- プログレスバーによる視覚的フィードバック

#### バリデーション
- ポイント超過チェック
- 技能値上限チェック（90%）
- 基本値との合計計算

### 4. 画像管理システム

#### 複数画像対応
- メイン画像設定
- 追加画像アップロード（最大10枚）
- 画像の並び替え（ドラッグ&ドロップ対応）
- 画像の削除
- サムネイル自動生成
- 画像ギャラリー表示

#### 画像仕様
- 対応形式: JPEG, PNG, GIF
- 最大サイズ: 5MB/枚
- 推奨解像度: 400×600px
- 総容量制限: 30MB/キャラクター

#### 画像管理画面
- グリッド表示（サムネイル一覧）
- メイン画像の切り替え（ワンクリック）
- 画像の説明文追加（オプション）
- 画像のプレビューモーダル

### 4. CCFOLIA連携

#### エクスポート形式
```json
{
  "kind": "character",
  "data": {
    "name": "キャラクター名",
    "initiative": DEX値,
    "externalUrl": "キャラクターシートURL",
    "iconUrl": "キャラクター画像URL",
    "commands": "ダイスロールコマンド（複数行）",
    "status": [
      {"label": "HP", "value": 現在HP, "max": 最大HP},
      {"label": "MP", "value": 現在MP, "max": 最大MP},
      {"label": "SAN", "value": 現在SAN, "max": 最大SAN}
    ],
    "params": [
      {"label": "STR", "value": "STR値"},
      {"label": "CON", "value": "CON値"},
      {"label": "POW", "value": "POW値"},
      {"label": "DEX", "value": "DEX値"},
      {"label": "APP", "value": "APP値"},
      {"label": "SIZ", "value": "SIZ値"},
      {"label": "INT", "value": "INT値"},
      {"label": "EDU", "value": "EDU値"}
    ]
  }
}
```

#### コマンドテンプレート
```
1d100<={SAN} 【正気度ロール】
CCB<={アイデア} 【アイデア】
CCB<={幸運} 【幸運】
CCB<={知識} 【知識】
CCB<={技能値} 【技能名】
（以下、設定された全技能）
1d3+{db} 【ダメージ判定】
1d4+{db} 【ダメージ判定】
1d6+{db} 【ダメージ判定】
CCB<={STR}*5 【STR × 5】
CCB<={CON}*5 【CON × 5】
CCB<={POW}*5 【POW × 5】
CCB<={DEX}*5 【DEX × 5】
CCB<={APP}*5 【APP × 5】
CCB<={SIZ}*5 【SIZ × 5】
CCB<={INT}*5 【INT × 5】
CCB<={EDU}*5 【EDU × 5】
```

#### エクスポート内容
- 基本情報（名前、能力値）
- 技能値（習得済み技能のみ）
- ステータス（HP/MP/SAN）
- カスタムコマンド（ダメージボーナス対応）

#### カスタマイズ
- 独自コマンド追加
- 技能の表示/非表示設定
- ダメージボーナスの自動反映

### 5. 公開/非公開機能

#### 公開設定
- **非公開（デフォルト）**: 作成者のみ閲覧・編集可能
- **公開**: 全ユーザーが閲覧可能（編集は作成者のみ）

#### アクセス制御
- 自分のキャラクター: 全権限（閲覧・編集・削除）
- 他ユーザーの公開キャラクター: 閲覧のみ
- 他ユーザーの非公開キャラクター: アクセス不可

### 6. ステータス管理

#### キャラクターステータス
- **alive（生存）**: 通常状態
- **injured（負傷）**: 重傷を負った状態
- **insane（発狂）**: 正気度喪失
- **dead（死亡）**: キャラクターの死亡
- **missing（行方不明）**: 行方不明状態
- **retired（引退）**: プレイから引退

#### ステータス変更
- キャラクター編集画面から変更可能
- セッション中の状態変化を反映
- ステータスバッジで視覚的に表示

### 7. 検索・フィルター機能

#### 検索条件
- キャラクター名（部分一致）
- プレイヤー名
- 職業
- ステータス

#### フィルター
- 版別（6版）
- ステータス別
- 公開/非公開
- 作成日順/更新日順

### 8. 削除機能

#### 削除動作
- 確認ダイアログ表示
- カスケード削除（関連データも削除）
  - キャラクター画像
  - 技能データ
  - 装備データ
  - 6版固有データ

#### 削除制限
- 自分のキャラクターのみ削除可能
- セッション参加中のキャラクターは警告表示

### 9. セッション連携

#### セッション参加
- キャラクターをセッションに登録
- セッション中のHP/MP/SAN値変更
- 秘匿ハンドアウトの受け取り

#### セッション履歴
- 参加セッション数の記録
- プレイ履歴の保存
- 成長記録の管理

### 10. 武器・装備管理

#### 武器の記載項目
クトゥルフ神話TRPG第6版に準拠した武器管理システム

##### 基本項目
| 項目 | 説明 | 例 |
|------|------|-----|
| **武器名** | 武器の名称 | 拳銃（38口径）、ナイフ、ショットガン |
| **使用技能** | 使用する技能名 | 拳銃、ライフル、こぶし、キック |
| **攻撃回数** | 1ラウンドの攻撃回数 | 1、2、3（自動火器） |
| **ダメージ** | 命中時のダメージ | 1D10+2、1D6+DB |
| **射程** | 有効射程距離 | 15m、50m、近接 |
| **装弾数** | 装填可能な弾数 | 6発、10発、なし（近接武器） |
| **故障ナンバー** | 故障する出目 | 98、99、なし |
| **備考** | 特殊効果や特徴 | 両手用、再装填1R、音が大きい |

##### 記載例

###### 拳銃（38口径）
```
武器名：拳銃（38口径）
使用技能：拳銃
攻撃回数：1
ダメージ：1D10
射程：15m
装弾数：6発
故障ナンバー：00
備考：標準的なリボルバー。再装填に1R。
```

###### ナイフ
```
武器名：ナイフ
使用技能：ナイフ
攻撃回数：1
ダメージ：1D4+DB
射程：近接
装弾数：なし
故障ナンバー：なし
備考：片手で使用。隠し持ちやすい。
```

###### ショットガン（ダブルバレル）
```
武器名：ショットガン（ダブルバレル）
使用技能：ショットガン
攻撃回数：1または2（同時発射）
ダメージ：4D6（5m）／2D6（10m）／1D6（20m）
射程：最大20m
装弾数：2発
故障ナンバー：00
備考：2発同時発射可。再装填に1R。
```

#### 防具の記載項目
| 項目 | 説明 | 例 |
|------|------|-----|
| **防具名** | 防具の名称 | 革ジャケット、防弾チョッキ |
| **装甲値** | ダメージ軽減値 | 1、8 |
| **部位** | 保護する部位 | 胴体、全身 |
| **備考** | 特殊効果や制限 | 動きにくい、目立つ |

#### 一般装備
- アイテム名
- 数量
- 重量（オプション）
- 備考

---

## データ構造

### CharacterSheetモデル

```python
class CharacterSheet(models.Model):
    # 基本情報
    user = ForeignKey(User)
    edition = CharField(choices=['6th'])
    name = CharField(max_length=100)
    player_name = CharField(max_length=100)
    status = CharField(choices=['alive', 'dead', 'insane', 'injured', 'missing', 'retired'])
    
    # 個人情報
    age = IntegerField(validators=[15-90])
    gender = CharField(max_length=50)
    occupation = CharField(max_length=100)
    birthplace = CharField(max_length=100)
    residence = CharField(max_length=100)
    
    # 能力値（6版は3-18の値で保存）
    str_value = IntegerField()
    con_value = IntegerField()
    pow_value = IntegerField()
    dex_value = IntegerField()
    app_value = IntegerField()
    siz_value = IntegerField()
    int_value = IntegerField()
    edu_value = IntegerField()
    
    # 副次ステータス
    hit_points_max = IntegerField()  # 最大HP = (CON + SIZ) / 2（端数切り上げ）
    hit_points_current = IntegerField()  # 現在HP（任意入力可能）
    magic_points_max = IntegerField()  # 最大MP = POW
    magic_points_current = IntegerField()  # 現在MP（任意入力可能）
    sanity_starting = IntegerField()  # 初期SAN（初期正気度） = POW × 5
    sanity_max = IntegerField()  # 最大SAN（最大正気度） = 99 - クトゥルフ神話技能
    sanity_current = IntegerField()  # 現在SAN（現在正気度）（任意入力可能）
    
    # 公開設定
    is_public = BooleanField(default=False)  # 公開/非公開設定
    
    # バージョン管理
    version = IntegerField(default=1)
    parent_sheet = ForeignKey('self', null=True)
    
    # セッション関連
    session_count = IntegerField(default=0)
```

### CharacterSheet6thモデル

```python
class CharacterSheet6th(models.Model):
    character_sheet = OneToOneField(CharacterSheet)
    mental_disorder = TextField()  # 精神的な障害
    
    # 自動計算フィールド
    idea_roll = property  # INT × 5
    luck_roll = property  # POW × 5
    know_roll = property  # EDU × 5
    damage_bonus = property  # STR + SIZから計算
```

### CharacterSkillモデル

```python
class CharacterSkill(models.Model):
    character_sheet = ForeignKey(CharacterSheet)
    skill_name = CharField(max_length=100)
    base_value = IntegerField()
    occupation_points = IntegerField()
    interest_points = IntegerField()
    other_points = IntegerField()
    current_value = property  # 合計値
```

### CharacterImageモデル

```python
class CharacterImage(models.Model):
    character_sheet = ForeignKey(CharacterSheet)
    image = ImageField()
    is_main = BooleanField(default=False)
    order = IntegerField(default=0)
    description = CharField(max_length=255, blank=True)  # 画像の説明
    uploaded_at = DateTimeField(auto_now_add=True)
```

### CharacterEquipmentモデル

```python
class CharacterEquipment(models.Model):
    character_sheet = ForeignKey(CharacterSheet)
    item_type = CharField(choices=['weapon', 'armor', 'item'])
    name = CharField(max_length=100)  # 武器/防具/アイテム名
    
    # 武器専用フィールド
    skill_name = CharField(max_length=100, blank=True)  # 使用技能
    damage = CharField(max_length=50, blank=True)  # ダメージ（例：1D10+2）
    base_range = CharField(max_length=50, blank=True)  # 射程
    attacks_per_round = IntegerField(null=True)  # 攻撃回数/ラウンド
    ammo = IntegerField(null=True)  # 装弾数
    malfunction_number = IntegerField(null=True)  # 故障ナンバー
    
    # 防具専用フィールド
    armor_points = IntegerField(null=True)  # 装甲値
    protected_parts = CharField(max_length=100, blank=True)  # 保護部位
    
    # 共通フィールド
    description = TextField(blank=True)  # 備考
    quantity = IntegerField(default=1)  # 数量
    weight = FloatField(null=True)  # 重量（kg）
    
    # 表示順
    order = IntegerField(default=0)
```

---

## 技術仕様

### フロントエンド
- **フレームワーク**: Bootstrap 5.1.3
- **JavaScript**: Vanilla JS (ES6+)
- **HTTP Client**: Axios
- **アイコン**: Font Awesome 6

### バックエンド
- **フレームワーク**: Django 5.2.3
- **API**: Django REST Framework
- **認証**: Django認証 + django-allauth
- **データベース**: SQLite（開発）/ PostgreSQL（本番推奨）

### JavaScript構造

```javascript
// グローバル関数（HTML onclickから呼び出し可能）
function toggleDiceSettings() { }
function loadDiceSetting() { }
function rollDice() { }
function rollAbilityScore() { }
function calculateDerivedStats() { }
function updateSkillTotals() { }

// DOMContentLoadedイベント（初期化処理）
document.addEventListener('DOMContentLoaded', function() {
    // 初期化処理
    updateGlobalDiceFormula();
    generateSkillsList();
    addSkillInputEvents();
    calculateDerivedStats();
    updateSkillTotals();
});
```

---

## UI/UX仕様

### デザイン原則
1. **直感的操作**: 初心者でも迷わない画面構成
2. **リアルタイム反映**: 入力値の即座計算・表示
3. **エラー防止**: 適切なバリデーションとフィードバック
4. **レスポンシブ**: あらゆるデバイスで快適な操作

### カラースキーム
- **プライマリ**: #0d6efd (Bootstrap Blue)
- **成功**: #198754 (Bootstrap Green)
- **警告**: #ffc107 (Bootstrap Warning)
- **危険**: #dc3545 (Bootstrap Danger)
- **背景**: #f8f9fa (Light Gray)

### インタラクション
- **ホバー効果**: カード、ボタンのホバーアニメーション
- **トランジション**: スムーズな画面遷移
- **ローディング**: スピナー表示
- **フィードバック**: 成功/エラーメッセージの表示

---

## API仕様

### エンドポイント一覧

#### キャラクターシート
- `GET /api/accounts/character-sheets/` - 一覧取得
- `POST /api/accounts/character-sheets/` - 新規作成
- `GET /api/accounts/character-sheets/{id}/` - 詳細取得
- `PUT /api/accounts/character-sheets/{id}/` - 更新
- `DELETE /api/accounts/character-sheets/{id}/` - 削除

#### 画像管理
- `GET /api/accounts/character-sheets/{id}/images/` - 画像一覧
- `POST /api/accounts/character-sheets/{id}/images/` - 画像アップロード
- `PUT /api/accounts/character-sheets/{id}/images/{image_id}/` - 画像更新（メイン設定、説明文）
- `DELETE /api/accounts/character-sheets/{id}/images/{image_id}/` - 画像削除

#### 装備管理
- `GET /api/accounts/character-sheets/{id}/equipment/` - 装備一覧
- `POST /api/accounts/character-sheets/{id}/equipment/` - 装備追加
- `PUT /api/accounts/character-sheets/{id}/equipment/{equipment_id}/` - 装備更新
- `DELETE /api/accounts/character-sheets/{id}/equipment/{equipment_id}/` - 装備削除
- `PUT /api/accounts/character-sheets/{id}/equipment/reorder/` - 装備並び替え

#### CCFOLIA連携
- `GET /api/accounts/character-sheets/{id}/ccfolia_json/` - CCFOLIA形式エクスポート

#### バージョン管理
- `POST /api/accounts/character-sheets/{id}/create_version/` - 新バージョン作成

#### 検索・フィルター
- `GET /api/accounts/character-sheets/?search={keyword}` - キャラクター名検索
- `GET /api/accounts/character-sheets/?status={status}` - ステータスフィルター
- `GET /api/accounts/character-sheets/?is_public={true/false}` - 公開設定フィルター

### レスポンス形式

```json
{
    "id": 1,
    "edition": "6th",
    "name": "探索者名",
    "player_name": "プレイヤー名",
    "age": 25,
    "occupation": "ジャーナリスト",
    "str_value": 13,
    "con_value": 14,
    "pow_value": 15,
    "dex_value": 12,
    "app_value": 11,
    "siz_value": 13,
    "int_value": 16,
    "edu_value": 17,
    "hit_points_max": 14,
    "hit_points_current": 14,
    "magic_points_max": 15,
    "magic_points_current": 15,
    "sanity_max": 99,
    "sanity_current": 75,
    "is_public": false,
    "status": "alive",
    "version": 1,
    "session_count": 0,
    "skills": [...],
    "character_image": "https://example.com/media/character_images/..."
}
```

---

## 今後の拡張予定

### 短期計画
- [ ] PDF出力機能
- [ ] キャラクターシート共有機能
- [ ] セッション履歴管理

### 中期計画
- [ ] リアルタイムコラボレーション
- [ ] モバイルアプリ版
- [ ] 多言語対応

### 長期計画
- [ ] AI支援キャラクター作成
- [ ] VTT（Virtual Tabletop）統合
- [ ] キャンペーン管理機能

---

## 更新履歴

### 2025年6月26日（Part 4）
- **能力値入力制限の撤廃**
  - 能力値（STR, CON, POW, DEX, APP, SIZ, INT, EDU）の最小値・最大値制限を削除
  - 任意の値を入力可能に変更（バリデーションなし）
- **CCFOLIA連携仕様の詳細化**
  - エクスポートJSON形式の明確化
  - コマンドテンプレートの追加（正気度ロール、技能判定、能力値×5判定）
  - ダメージボーナス対応

### 2025年6月26日（Part 3）
- **SAN値表示の明確化**
  - 初期SAN（POW × 5）と最大SAN（99 - クトゥルフ神話技能）の表記を統一
  - 画面表示で「初期SAN（正気度）」と「最大SAN」を明示
  - HTMLテンプレートの表示を改善（POW × 5の計算式を表示）

### 2025年6月26日（Part 2）
- **職業技能ポイント計算方式の拡張**
  - 標準計算式（EDU×20）に加えて、職業特性に応じた8種類の計算方式を追加
  - 筋力系（STR×10+EDU×10）、体力系（CON×10+EDU×10）など
  - 手動入力オプションによるカスタム職業対応
  - 画面構成の技能タブ項目を更新

### 2025年6月26日
- **統合テストとの整合性確保**
  - 公開/非公開機能の詳細追加
  - 権限管理とアクセス制御の明文化
  - ステータス管理（alive/dead/insane等）の詳細追加
  - 検索・フィルター機能の仕様追加
  - 削除機能とカスケード削除の仕様追加
  - セッション連携機能の詳細追加
  - データモデルに`is_public`、`version`、`parent_sheet`、`session_count`フィールド追加
  - API仕様にバージョン管理と検索エンドポイント追加
- **武器・装備管理システムの追加**
  - クトゥルフ神話TRPG第6版準拠の武器管理
  - 防具管理機能
  - CharacterEquipmentモデルの追加
- **画像管理システムの強化**
  - 複数画像アップロード（最大10枚）
  - メイン画像切り替え機能
  - CharacterImageモデルの追加

### 2025年6月25日
- **現在値入力機能の追加**
  - キャラクター作成画面に現在HP、現在MP、現在正気度の入力欄を追加
  - 入力制限なし（0、負の値、最大値を超える値も入力可能）
  - 新規作成時のデフォルト値は最大値
  - テストケース追加（`accounts.test_character_current_status`）

### 2025年6月24日
- 初版リリース

---

**最終更新**: 2025年6月26日