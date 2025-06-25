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

#### アクション
- 詳細表示
- 編集
- 複製（新バージョン作成）
- 新規作成

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
   - 副次ステータス自動計算
     - HP: (CON + SIZ) ÷ 2
     - MP: POW
     - SAN: POW × 5
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
     - 職業技能ポイント: EDU × 20
     - 趣味技能ポイント: INT × 10
   - **技能一覧**
     - 職業別推奨技能のハイライト表示
     - リアルタイム合計値計算
     - 技能値上限チェック（90%）
   - **技能フィルタリング**
     - カテゴリ別フィルター
     - 検索機能
     - ポイント割り振り済み技能の表示

4. **プロフィールタブ**
   - 精神的な障害
   - キャラクターメモ
   - バックストーリー

5. **CCFOLIA連携タブ**
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
  - 武器・防具一覧
  - その他アイテム

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

### 2. 技能ポイント管理

#### 自動計算
- 職業技能ポイント: EDU × 20
- 趣味技能ポイント: INT × 10
- リアルタイム残りポイント表示

#### バリデーション
- ポイント超過チェック
- 技能値上限チェック（90%）
- 基本値との合計計算

### 3. 画像管理システム

#### 複数画像対応
- メイン画像設定
- 追加画像アップロード（最大10枚）
- 画像の並び替え
- 画像の削除

#### 画像仕様
- 対応形式: JPEG, PNG, GIF
- 最大サイズ: 5MB
- 推奨解像度: 400×600px

### 4. CCFOLIA連携

#### エクスポート内容
- 基本情報
- 能力値・技能値
- カスタムコマンド
- ステータス設定

#### カスタマイズ
- 独自パラメータ追加
- コマンド編集
- プリセット保存

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
    hit_points_max = IntegerField()  # 最大HP（自動計算）
    hit_points_current = IntegerField()  # 現在HP（任意入力可能）
    magic_points_max = IntegerField()  # 最大MP（自動計算）
    magic_points_current = IntegerField()  # 現在MP（任意入力可能）
    sanity_starting = IntegerField()  # 初期正気度（自動計算）
    sanity_max = IntegerField()  # 最大正気度（99-クトゥルフ神話技能）
    sanity_current = IntegerField()  # 現在正気度（任意入力可能）
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
- `DELETE /api/accounts/character-sheets/{id}/images/{image_id}/` - 画像削除

#### CCFOLIA連携
- `GET /api/accounts/character-sheets/{id}/ccfolia_json/` - CCFOLIA形式エクスポート

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
    "sanity_max": 75,
    "sanity_current": 75,
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

### 2025年6月25日
- **現在値入力機能の追加**
  - キャラクター作成画面に現在HP、現在MP、現在正気度の入力欄を追加
  - 入力制限なし（0、負の値、最大値を超える値も入力可能）
  - 新規作成時のデフォルト値は最大値
  - テストケース追加（`accounts.test_character_current_status`）

### 2025年6月24日
- 初版リリース

---

**最終更新**: 2025年6月25日