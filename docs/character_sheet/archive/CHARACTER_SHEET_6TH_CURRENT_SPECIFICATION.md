# クトゥルフ神話TRPG 第6版キャラクターシート現在仕様

## 概要
本ドキュメントは、2025年6月22日時点でのクトゥルフ神話TRPG第6版キャラクターシート画面の現在の実装仕様を記録したものです。

## 画面構成

### URL
- 新規作成: `/accounts/character/create/6th/`
- 編集: `/accounts/character/create/6th/?id={character_id}`

### 実装方式
- **ビュー**: `Character6thCreateView` (Django FormView)
- **フォーム**: `CharacterSheet6thForm`
- **テンプレート**: `templates/accounts/character_sheet_6th.html`

## フォーム送信処理

### 1. 送信方式の混在
現在、以下の2つの送信方式が混在しています：

#### 新規作成時
- **方式**: 通常のHTMLフォーム送信（POST）
- **エンドポイント**: `/accounts/character/create/6th/`
- **処理**: Django FormViewで処理
- **リダイレクト**: FormViewのsuccess_url (`/accounts/character/list/`)

#### 編集時
- **方式**: AJAX送信
- **エンドポイント**: `/api/accounts/character-sheets/{id}/`
- **メソッド**: PUT
- **処理**: REST APIで処理
- **リダイレクト**: JavaScriptで手動リダイレクト

### 2. データ送信形式

#### 基本データ
フォームフィールドとして送信：
- `name`: キャラクター名
- `age`: 年齢
- `gender`: 性別
- `occupation`: 職業
- `birthplace`: 出身地
- `str_value`, `con_value`, `pow_value`, `dex_value`: 能力値
- `app_value`, `siz_value`, `int_value`, `edu_value`: 能力値

#### 隠しフィールド（ステータス現在値）
```html
<input type="hidden" id="hit_points_current_hidden" name="hit_points_current" value="">
<input type="hidden" id="magic_points_current_hidden" name="magic_points_current" value="">
<input type="hidden" id="sanity_current_hidden" name="sanity_current" value="">
<input type="hidden" id="sanity_max_hidden" name="sanity_max" value="">
```

#### スキルデータ
動的に生成される隠しフィールドとして送信：
```html
<input type="hidden" name="skill_0_name" value="回避">
<input type="hidden" name="skill_0_base" value="12">
<input type="hidden" name="skill_0_occupation" value="5">
<input type="hidden" name="skill_0_interest" value="3">
<input type="hidden" name="skill_0_bonus" value="0">
```

### 3. 問題点と対策

#### 問題1: 画面遷移しない
**原因**: 
- JavaScriptでpreventDefault()を呼んでいるため、通常のフォーム送信が阻止される
- FormViewのリダイレクト処理が実行されない

**対策実施**:
- 新規作成時は通常のフォーム送信を行うよう修正
- 編集時のみAJAX送信を使用

#### 問題2: ステータス値が保存されない
**原因**:
- 隠しフィールドの値が適切に設定されていない
- `updateHiddenFields()`関数の呼び出しタイミング

**対策実施**:
- フォーム送信前に`updateHiddenFields()`を確実に呼び出す
- DOMContentLoadedイベントでも隠しフィールド更新を設定

#### 問題3: スキルデータの重複カウント
**原因**:
- 割り振り済み技能タブで表示用に複製された要素もカウントしていた

**対策実施**:
- 複製要素に`skill-clone`と`cloned-input`クラスを追加
- カウント時にこれらのクラスを除外

## JavaScript処理フロー

### 1. フォーム送信イベント（line 4821）
```javascript
document.getElementById('character-form-6th').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // 隠しフィールド更新
    updateHiddenFields();
    
    // 新規作成時は通常のフォーム送信
    if (!isEditing) {
        this.submit();
        return;
    }
    
    // 編集時はAJAX送信
    // ...
});
```

### 2. 隠しフィールド更新（line 5652）
```javascript
function updateHiddenFields() {
    // HP現在値
    const hpCurrent = document.getElementById('current_hp_combat');
    const hpHidden = document.getElementById('hit_points_current_hidden');
    if (hpCurrent && hpHidden) {
        hpHidden.value = hpCurrent.value || '';
    }
    
    // MP、SAN値も同様に更新
}
```

### 3. スキルデータ収集（line 4365）
```javascript
function collectSkillsData() {
    const skillsData = [];
    // クローンされていない元の要素のみを収集
    const skillItems = document.querySelectorAll('.skill-item-wrapper:not(.skill-clone) .skill-item');
    
    skillItems.forEach(skillItem => {
        // スキルデータ収集処理
    });
    
    return skillsData;
}
```

## データ保存フロー

### 1. フォームのバリデーション（Django側）
`CharacterSheet6thForm.clean()`:
- 能力値範囲制限は削除（ユーザーの自由度向上）
- 必須フィールドの確認

### 2. データ保存処理（Django側）
`CharacterSheet6thForm.save()`:
1. 基本データの保存
2. 隠しフィールドから現在値を取得
   - 空文字や'0'の場合は最大値で初期化
3. 6版固有データ（CharacterSheet6th）の保存
4. スキルデータの保存（_save_skill_data）
5. 画像データの保存（_save_character_images）

### 3. スキルデータ保存詳細
`_save_skill_data()`:
1. 既存スキルを削除
2. skill_*_name形式のデータを探索
3. 各スキルのポイント情報を取得
4. CharacterSkillモデルとして保存

## 今後の改善提案

### 1. 送信方式の統一
- すべてREST API経由に統一するか
- またはすべて通常のフォーム送信に統一する

### 2. エラーハンドリングの改善
- フォーム送信エラー時の詳細表示
- バリデーションエラーの適切な表示

### 3. ユーザビリティ向上
- 保存完了後の自動リダイレクト
- 保存中のローディング表示改善
- 自動保存機能の実装

### 4. データ整合性
- 現在値の初期化ロジックの明確化
- スキルデータの重複チェック強化