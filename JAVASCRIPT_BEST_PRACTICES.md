# JavaScript エラー防止のベストプラクティス

## 1. 🔍 開発時のエラー検出

### 1.1 リアルタイムエラー検出
```javascript
// 開発環境でのエラー監視
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', {
        message: e.message,
        file: e.filename,
        line: e.lineno,
        column: e.colno,
        stack: e.error ? e.error.stack : 'N/A'
    });
});
```

### 1.2 ESLint の活用
```json
// .eslintrc.json
{
    "env": {
        "browser": true,
        "es2021": true
    },
    "extends": "eslint:recommended",
    "rules": {
        "no-unused-vars": "warn",
        "no-undef": "error",
        "no-extra-semi": "error",
        "quotes": ["error", "single"],
        "semi": ["error", "always"]
    }
}
```

## 2. 🛡️ エラー防止の基本原則

### 2.1 Strict Mode の使用
```javascript
'use strict';

// これにより以下のエラーが検出されます：
// - 宣言されていない変数の使用
// - 重複した関数パラメータ
// - 削除できないプロパティの削除
```

### 2.2 変数宣言のベストプラクティス
```javascript
// ❌ 悪い例
function badExample() {
    myVar = 10; // グローバル変数になってしまう
    var myVar;  // 巻き上げによる混乱
}

// ✅ 良い例
function goodExample() {
    const CONSTANT_VALUE = 10;    // 定数
    let mutableValue = 20;        // 変更可能な変数
    // var は使用しない
}
```

### 2.3 関数定義の整理
```javascript
// ❌ 悪い例：重複定義
function myFunction() { /* ... */ }
// ... 他のコード ...
function myFunction() { /* ... */ } // 重複！

// ✅ 良い例：名前空間の使用
const MyApp = {
    utils: {
        myFunction: function() { /* ... */ }
    },
    handlers: {
        clickHandler: function() { /* ... */ }
    }
};
```

## 3. 🎯 Django テンプレート内での JavaScript

### 3.1 テンプレートリテラルのエスケープ
```javascript
// ❌ 危険：Django変数が}を含む場合エラーになる
const message = `{{ user.message }}`;

// ✅ 安全：JSONエンコード
const message = {{ user.message|json_script:"user-message" }};
const messageData = JSON.parse(document.getElementById('user-message').textContent);
```

### 3.2 スクリプトブロックの構造化
```html
<!-- ✅ 推奨構造 -->
<script>
(function() {
    'use strict';
    
    // グローバルに必要な関数のみ公開
    window.MyApp = window.MyApp || {};
    
    // プライベート変数・関数
    const privateVar = 'hidden';
    
    function privateFunction() {
        // ...
    }
    
    // パブリックAPI
    window.MyApp.publicFunction = function() {
        // ...
    };
    
    // DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
        // 初期化処理
    });
})();
</script>
```

## 4. 🐛 一般的なエラーパターンと対策

### 4.1 Syntax Error の防止
```javascript
// ❌ よくあるミス
if (condition) {
    // コード
}
} // 余分な閉じ括弧

// ✅ 対策：適切なインデントとエディタの括弧マッチング機能を使用
if (condition) {
    // コード
} // 対応する括弧
```

### 4.2 Reference Error の防止
```javascript
// ❌ 未定義変数の参照
console.log(undefinedVariable);

// ✅ 存在チェック
if (typeof undefinedVariable !== 'undefined') {
    console.log(undefinedVariable);
}

// ✅ オプショナルチェーン
const value = object?.property?.nestedProperty || 'default';
```

### 4.3 Type Error の防止
```javascript
// ❌ null/undefinedのメソッド呼び出し
const element = document.getElementById('missing');
element.addEventListener('click', handler); // エラー

// ✅ 存在チェック
const element = document.getElementById('missing');
if (element) {
    element.addEventListener('click', handler);
}

// ✅ または
document.getElementById('missing')?.addEventListener('click', handler);
```

## 5. 🔧 デバッグツール

### 5.1 Console メソッドの活用
```javascript
// グループ化されたログ
console.group('Function Execution');
console.log('Start:', new Date());
console.log('Parameters:', params);
console.error('Error occurred:', error);
console.groupEnd();

// テーブル形式の出力
console.table([
    { name: 'Function1', time: 10 },
    { name: 'Function2', time: 20 }
]);
```

### 5.2 ブレークポイントの設定
```javascript
function debugFunction() {
    debugger; // ブラウザの開発者ツールで一時停止
    // 処理...
}
```

## 6. 📋 エラーチェックリスト

開発時に以下を確認：

- [ ] **Strict Mode** を有効にしているか
- [ ] **変数宣言** はすべて `const` または `let` を使用しているか
- [ ] **関数の重複定義** がないか
- [ ] **括弧のバランス** が正しいか
- [ ] **セミコロン** の付け忘れがないか
- [ ] **DOM要素の存在確認** をしているか
- [ ] **try-catch** で適切にエラーハンドリングしているか
- [ ] **console.log** を本番環境で削除しているか

## 7. 🚀 自動化ツール

### 7.1 Pre-commit フック
```bash
# .git/hooks/pre-commit
#!/bin/sh
# JavaScriptファイルのlint
files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.js$')
if [ "$files" != "" ]; then
    npx eslint $files
    if [ $? -ne 0 ]; then
        echo "ESLint errors found. Please fix before committing."
        exit 1
    fi
fi
```

### 7.2 CI/CD でのチェック
```yaml
# .github/workflows/javascript-lint.yml
name: JavaScript Lint
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run ESLint
        run: |
          npm install
          npx eslint .
```

## 8. 🎓 学習リソース

- [MDN JavaScript Guide](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide)
- [JavaScript Error Reference](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors)
- [ESLint Rules](https://eslint.org/docs/rules/)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)