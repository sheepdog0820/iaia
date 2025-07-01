# JavaScript開発ガイドライン

## ⚠️ JavaScriptエラー予防の必須ルール

**この文書は、JavaScriptスコープエラーの再発防止のために必須で遵守してください。**

## 🚨 スコープエラーの根本原因と対策

### ❌ 典型的な失敗パターン
```javascript
// 悪い例: DOMContentLoaded内で関数定義
document.addEventListener('DOMContentLoaded', function() {
    function toggleDiceSettings() {
        // この関数はonclick="toggleDiceSettings()"から呼び出せない
    }
});

// HTML側でエラーが発生
<button onclick="toggleDiceSettings()">表示</button>
```

### ✅ 正しい実装パターン
```javascript
// 良い例: グローバルスコープで関数定義
function toggleDiceSettings() {
    // この関数はonclickから呼び出し可能
}

// または、イベントリスナーを使用
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('toggleBtn')?.addEventListener('click', toggleDiceSettings);
});

// HTML側
<button id="toggleBtn">表示</button>
```

## 📋 JavaScript実装チェックリスト

### 必須チェック項目（実装前）
- [ ] **関数スコープ確認**: onclickから呼び出す関数はグローバルスコープに配置
- [ ] **HTML要素ID確認**: 対応するHTML要素が存在することを確認
- [ ] **重複関数チェック**: 同名関数が複数定義されていないか確認
- [ ] **依存関数チェック**: 呼び出す他の関数もグローバルに配置されているか確認

### 必須チェック項目（実装後）
- [ ] **ブラウザテスト**: 実際にボタンクリックして動作確認
- [ ] **開発者ツール確認**: Console Errorが発生しないことを確認
- [ ] **関数可視性テスト**: `console.log(typeof functionName)`でundefinedでないことを確認

## 🔧 JavaScript関数配置ルール

### Rule 1: onclick用関数はグローバル配置
```javascript
// ❌ 悪い例: DOMContentLoaded内
document.addEventListener('DOMContentLoaded', function() {
    function handleClick() { /* onclick から呼べない */ }
});

// ✅ 良い例: グローバルスコープ
function handleClick() { /* onclick から呼べる */ }
```

### Rule 2: イベントリスナーパターンを推奨
```javascript
// ✅ 推奨: onclick属性を避ける
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('myButton')?.addEventListener('click', handleClick);
});
```

### Rule 3: 関数重複の回避
```javascript
// ❌ 悪い例: 関数の重複定義
function myFunction() { /* グローバル */ }
document.addEventListener('DOMContentLoaded', function() {
    function myFunction() { /* 重複！ */ }
});

// ✅ 良い例: 一箇所での定義
function myFunction() { /* グローバルで一度だけ */ }
```

## 🧪 JavaScript動作確認手順

### 開発時確認ステップ
1. **構文チェック**: ブラウザの開発者ツールでエラーなし
2. **関数存在確認**: `console.log(typeof functionName)` → `'function'`
3. **クリックテスト**: 実際にボタンをクリックして動作確認
4. **ネットワークエラー確認**: 404やJSエラーがないことを確認

### エラー発生時のデバッグ手順
```javascript
// デバッグ用コード例
console.log('=== デバッグ開始 ===');
console.log('toggleDiceSettings type:', typeof toggleDiceSettings);
console.log('rollCustomDice type:', typeof rollCustomDice);
console.log('Element exists:', document.getElementById('targetElement'));
console.log('=== デバッグ終了 ===');
```

## 🔄 JavaScript修正時の必須手順

### 修正ワークフロー
1. **🔍 問題特定**: Console Errorメッセージの確認
2. **🧩 スコープ分析**: 関数がどこで定義されているか確認
3. **✂️ 重複削除**: 同じ関数の重複定義を削除
4. **🌐 グローバル移動**: onclick用関数をグローバルスコープに移動
5. **🔗 イベント接続**: DOMContentLoaded内でイベントリスナー設定
6. **✅ 動作確認**: ブラウザで実際にテスト実行

### テンプレート（理想的な構造）
```javascript
// === グローバル関数群（onclick用） ===
function toggleDiceSettings() { /* ... */ }
function rollCustomDice() { /* ... */ }
function applyPresets() { /* ... */ }

// === DOMContentLoaded（初期化・イベント接続） ===
document.addEventListener('DOMContentLoaded', function() {
    // イベントリスナー設定
    document.getElementById('toggleBtn')?.addEventListener('click', toggleDiceSettings);
    document.getElementById('rollBtn')?.addEventListener('click', rollCustomDice);
    
    // 初期化処理
    initializeComponents();
    
    // ローカル関数（onclickからは呼ばない）
    function initializeComponents() { /* ... */ }
});
```

## 🚨 JavaScript重複・スコープエラーの完全予防ガイド

### 最重要ルール
1. **変数重複の絶対禁止**: 同じ変数名（特に`const abilities`）を複数箇所で宣言しない
2. **グローバル定数の活用**: 共通で使用する配列はグローバル定数として定義
3. **関数重複の完全排除**: 同名関数を複数箇所で定義しない
4. **onclick属性の段階的廃止**: addEventListener方式への全面移行

### 🔍 エラーパターンと対策

#### パターン1: 変数重複エラー
```javascript
// ❌ 危険: 変数の重複宣言
const abilities = ['str', 'con', 'pow'];  // グローバル
function myFunction() {
    const abilities = ['STR', 'CON', 'POW'];  // エラー: 重複
}

// ✅ 安全: グローバル定数の活用
const ABILITIES_LOWER = ['str', 'con', 'pow'];
const ABILITIES_UPPER = ['STR', 'CON', 'POW'];
function myFunction() {
    ABILITIES_UPPER.forEach(ability => { /* ... */ });
}
```

#### パターン2: 関数重複エラー
```javascript
// ❌ 危険: 関数の重複定義
function loadDiceSetting() { /* グローバル */ }
document.addEventListener('DOMContentLoaded', function() {
    function loadDiceSetting() { /* 重複エラー */ }
});

// ✅ 安全: 一箇所での定義
function loadDiceSetting() { /* グローバルで一度だけ */ }
document.addEventListener('DOMContentLoaded', function() {
    // 重複定義なし
});
```

#### パターン3: スコープアクセスエラー
```javascript
// ❌ 危険: onchangeから呼び出せない
document.addEventListener('DOMContentLoaded', function() {
    function handleChange() { /* onchangeから見えない */ }
});

// ✅ 安全: グローバル関数 + イベントリスナー
function handleChange() { /* グローバルで定義 */ }
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('mySelect')?.addEventListener('change', handleChange);
});
```

## 📋 JavaScript品質チェックリスト（拡張版）

### コード作成前チェック
- [ ] **グローバル定数確認**: 共通配列をグローバル定数で定義済みか
- [ ] **関数配置計画**: どの関数をグローバル、どの関数をローカルにするか明確化
- [ ] **イベント戦略**: onclick vs addEventListener のどちらを使用するか決定

### コード作成中チェック  
- [ ] **変数名重複チェック**: 同じ変数名を複数箇所で宣言していないか
- [ ] **関数名重複チェック**: 同じ関数名を複数箇所で定義していないか
- [ ] **スコープ一貫性**: HTML属性から呼び出す関数がグローバルスコープにあるか

### コード完成後チェック
- [ ] **ブラウザConsoleテスト**: 一切のSyntaxErrorとReferenceErrorがないか
- [ ] **全ボタン動作確認**: すべてのクリック可能要素が正常動作するか
- [ ] **ドロップダウン動作確認**: すべてのselect要素のonchangeが正常動作するか

## 🛠️ 修正作業時の標準手順

### Step 1: エラー種別の特定
```javascript
// Console Errorメッセージから判断
// "Identifier 'abilities' has already been declared" → 変数重複
// "ReferenceError: loadDiceSetting is not defined" → スコープエラー
// "SyntaxError: Unexpected token" → 構文エラー
```

### Step 2: 重複要素の洗い出し
```bash
# 重複変数の検索
rg -n "const abilities.*=.*\[" file.html

# 重複関数の検索  
rg -n "function functionName" file.html

# onclick属性の検索
rg -n "onclick=" file.html
```

### Step 3: 統一・整理作業
1. **グローバル定数化**: 共通配列をファイル先頭で定義
2. **関数統合**: 重複関数を削除、グローバル関数を一箇所に統合
3. **イベントリスナー化**: onclick属性をaddEventListener方式に変更

### Step 4: 完全性確認
```javascript
// 全関数の存在確認
console.log('Function checks:');
console.log('toggleDiceSettings:', typeof toggleDiceSettings);
console.log('loadDiceSetting:', typeof loadDiceSetting);
console.log('rollCustomDice:', typeof rollCustomDice);

// 全グローバル定数の確認
console.log('Constants checks:');
console.log('ABILITIES_LOWER:', ABILITIES_LOWER);
console.log('ABILITIES_UPPER:', ABILITIES_UPPER);
```

## 📚 推奨テンプレート構造

```javascript
// === ファイル先頭: グローバル定数群 ===
const ABILITIES_LOWER = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
const ABILITIES_UPPER = ['STR', 'CON', 'POW', 'DEX', 'APP', 'SIZ', 'INT', 'EDU'];

// === グローバル関数群 ===
function toggleDiceSettings() { /* ... */ }
function loadDiceSetting() { /* ... */ }
function rollCustomDice() { /* ... */ }

// === DOMContentLoaded: 初期化のみ ===
document.addEventListener('DOMContentLoaded', function() {
    // イベントリスナー設定のみ
    document.getElementById('btn1')?.addEventListener('click', toggleDiceSettings);
    document.getElementById('select1')?.addEventListener('change', loadDiceSetting);
    
    // 初期化処理
    initializeApp();
    
    // ローカル関数（HTML要素から直接呼ばれない）
    function initializeApp() { /* ... */ }
});
```

## 🚨 緊急修正プロトコル（更新版）

JavaScriptエラーが発生した場合の対応順序：

1. **🔍 即座診断**: Console Errorメッセージの完全確認
2. **🧩 エラー分類**: 重複エラー / スコープエラー / 構文エラーの判別
3. **✂️ 重複削除**: 同名変数・関数の重複をすべて削除
4. **🌐 構造整理**: グローバル定数・関数の適切な配置
5. **🔗 イベント変換**: onclick属性をaddEventListener方式に統一
6. **✅ 全面テスト**: 全ボタン・ドロップダウンの動作確認
7. **📝 文書更新**: 修正内容をCLAUDE.mdに反映

**絶対ルール**: 同じエラーを二度と発生させないよう、このガイドラインを厳格に遵守してください。

## DOM要素アクセス時の安全性確保

### 要素の存在確認
```javascript
// 悪い例 - 要素が存在しない場合エラーになる
document.getElementById('some-id').textContent = 'value';

// 良い例 - 要素の存在を確認
const element = document.getElementById('some-id');
if (element) {
    element.textContent = 'value';
}

// または オプショナルチェーンを使用
document.getElementById('some-id')?.textContent = 'value';
```

### input要素の値取得/設定
```javascript
// input要素の場合は value プロパティを使用
const inputElement = document.getElementById('input-id');
if (inputElement) {
    inputElement.value = '123';  // textContent ではなく value を使用
}

// 読み取り時も同様
const value = document.getElementById('input-id')?.value || '0';
```

### 関数の存在確認
```javascript
// 関数を呼び出す前に定義されているか確認
if (typeof someFunction === 'function') {
    someFunction();
}

// または try-catch を使用
try {
    someFunction();
} catch (error) {
    console.error('関数が存在しません:', error);
}
```

### イベントリスナー登録時の要素確認
```javascript
const button = document.getElementById('button-id');
if (button) {
    button.addEventListener('click', handleClick);
}
```

## エラーハンドリングのベストプラクティス

### try-catch の活用
```javascript
try {
    // リスクのある処理
    const data = JSON.parse(jsonString);
} catch (error) {
    console.error('JSONパースエラー:', error);
    // 適切なフォールバック処理
}
```

### デフォルト値の設定
```javascript
// parseInt の結果が NaN の場合に備える
const value = parseInt(element?.value) || 0;

// textContent が null の場合
const text = element?.textContent || '';
```

### 配列やオブジェクトの安全なアクセス
```javascript
// 配列の場合
const firstItem = array?.[0] || defaultValue;

// オブジェクトの場合
const value = object?.property?.nestedProperty || defaultValue;
```

## 修正時のチェックリスト

- [ ] HTMLに該当するIDの要素が存在するか確認
- [ ] input要素は`value`、その他の要素は`textContent`を使用しているか
- [ ] 要素が存在しない場合のエラーハンドリングがあるか
- [ ] 関数呼び出し前に関数が定義されているか確認
- [ ] イベントリスナー登録時に要素の存在確認をしているか
- [ ] 数値変換時のNaN対策（デフォルト値）があるか

## 【必須】JavaScript作成・修正前のチェックリスト

**すべてのJavaScript作成・修正時に、以下のベストプラクティスを必ず確認してください：**

1. **事前確認（必須）**
   - [ ] `JAVASCRIPT_BEST_PRACTICES.md` を参照
   - [ ] `js_best_practices_guide.md` でエラーパターンを確認
   - [ ] 既存のコードスタイルを確認

2. **コーディング時（必須）**
   - [ ] 'use strict' を使用
   - [ ] const/let を使用（var は禁止）
   - [ ] 関数の重複定義がないか確認
   - [ ] DOM要素の存在確認を実装
   - [ ] try-catch でエラーハンドリング

3. **修正後の確認（必須）**
   - [ ] すべての括弧のバランスを確認
   - [ ] console.log でデバッグ出力を確認
   - [ ] ブラウザでエラーがないことを確認
   - [ ] 関連する全機能の動作確認

## 🚨 緊急時対応プロトコル

本番環境でJavaScriptエラーが発生した場合：
1. **即座確認**: ブラウザ開発者ツールでエラー内容確認
2. **一時回避**: onclick → addEventListener に変更
3. **根本修正**: グローバル関数配置とスコープ整理
4. **動作テスト**: 全ボタン・機能の動作確認
5. **デプロイ**: 修正版のデプロイ

## 📚 関連ドキュメント

- **JavaScript基礎**: [MDN - Functions](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Functions)
- **イベント処理**: [MDN - Event Handling](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener)
- **スコープ**: [MDN - Variable Scope](https://developer.mozilla.org/en-US/docs/Glossary/Scope)

**重要**: 今後、JavaScriptでonclick関数エラーが発生した場合は、必ずこのガイドラインに従って修正してください。