# JavaScriptエラー防止のベストプラクティスガイド

## 🔍 エラー診断と修正の手順

### 1. **Syntax Error の診断**

```javascript
// Uncaught SyntaxError: Unexpected token '}' の一般的な原因：

// 1. 閉じ括弧の重複
function example() {
    if (condition) {
        // code
    }}  // ← 余分な }
}

// 2. テンプレートリテラル内の未エスケープの中括弧
const template = `
    <div>${value}}</div>  // 正しい
    <div>}</div>          // ← これがエラーの原因になることがある
`;

// 3. JSONのパースエラー
const data = JSON.parse('{"key": "value"}}'); // 余分な }
```

### 2. **エラー防止のための設定**

#### VSCode設定（.vscode/settings.json）
```json
{
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.eslint": true
    },
    "editor.bracketPairColorization.enabled": true,
    "editor.guides.bracketPairs": "active"
}
```

#### ESLint設定（.eslintrc.json）
```json
{
    "env": {
        "browser": true,
        "es2021": true
    },
    "extends": "eslint:recommended",
    "parserOptions": {
        "ecmaVersion": 12,
        "sourceType": "module"
    },
    "rules": {
        "no-unused-vars": "warn",
        "no-undef": "error",
        "no-extra-semi": "error",
        "no-unreachable": "error",
        "curly": ["error", "all"],
        "brace-style": ["error", "1tbs"],
        "indent": ["error", 4],
        "quotes": ["error", "single"],
        "semi": ["error", "always"]
    }
}
```

### 3. **デバッグツール**

#### ブラウザでの即座のエラー検出
```javascript
// 開発環境でのみ有効化
if (window.location.hostname === 'localhost') {
    // エラーの詳細表示
    window.addEventListener('error', (e) => {
        console.group('🔴 JavaScript Error');
        console.error('Message:', e.message);
        console.error('File:', e.filename);
        console.error('Line:', e.lineno, 'Column:', e.colno);
        console.error('Stack:', e.error?.stack);
        console.groupEnd();
    });
}
```

#### コンソールでの診断コマンド
```javascript
// 関数の存在確認
console.log('Function exists:', typeof functionName === 'function');

// DOM要素の存在確認
console.log('Element exists:', document.getElementById('elementId') !== null);

// 変数のスコープ確認
console.log('Variable in scope:', typeof variableName !== 'undefined');
```

### 4. **一般的なエラーパターンと対策**

#### パターン1: 括弧の不一致
```javascript
// ❌ 悪い例
function badExample() {
    if (condition) {
        array.forEach(item => {
            console.log(item);
        }
    }  // ← ) が不足
}

// ✅ 良い例
function goodExample() {
    if (condition) {
        array.forEach(item => {
            console.log(item);
        });  // 正しく閉じる
    }
}
```

#### パターン2: テンプレートリテラルのエスケープ
```javascript
// ❌ 悪い例
const html = `
    <style>
        .class { color: red; }  // ← } が問題を起こす可能性
    </style>
`;

// ✅ 良い例
const html = `
    <style>
        .class { color: red; ${''/* エスケープ */} }
    </style>
`;
```

#### パターン3: 非同期処理のエラーハンドリング
```javascript
// ❌ 悪い例
async function fetchData() {
    const response = await fetch('/api/data');
    return response.json();  // エラーハンドリングなし
}

// ✅ 良い例
async function fetchData() {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        return null;
    }
}
```

### 5. **Django テンプレートでの注意点**

```javascript
// ❌ 危険：Django変数の直接埋め込み
const userMessage = "{{ user.message }}";  // XSSの危険性

// ✅ 安全：json_scriptフィルタの使用
{{ user.message|json_script:"user-message" }}
<script>
const userMessage = JSON.parse(document.getElementById('user-message').textContent);
</script>

// ✅ または、データ属性の使用
<div id="app" data-message="{{ user.message|escapejs }}"></div>
<script>
const userMessage = document.getElementById('app').dataset.message;
</script>
```

### 6. **プリコミットフック**

`.git/hooks/pre-commit`:
```bash
#!/bin/sh
# JavaScriptファイルの構文チェック

files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.js$')

if [ "$files" != "" ]; then
    for file in $files; do
        # 構文チェック
        node -c "$file"
        if [ $? -ne 0 ]; then
            echo "Syntax error in $file"
            exit 1
        fi
    done
fi

# HTMLファイル内のJavaScriptもチェック
html_files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.html$')

if [ "$html_files" != "" ]; then
    for file in $html_files; do
        # <script>タグ内のJavaScriptを抽出してチェック
        grep -Pzo '(?s)<script[^>]*>.*?</script>' "$file" | grep -v 'text/template' > /tmp/js_check.js
        if [ -s /tmp/js_check.js ]; then
            node -c /tmp/js_check.js 2>/dev/null
            if [ $? -ne 0 ]; then
                echo "JavaScript syntax error in $file"
                exit 1
            fi
        fi
    done
fi
```

### 7. **エラー修正のチェックリスト**

- [ ] ブラウザの開発者ツールでエラーメッセージを確認
- [ ] エラーが発生している正確な行番号を特定
- [ ] 括弧（`{}`, `()`, `[]`）のバランスを確認
- [ ] 文字列リテラルやテンプレートリテラルの閉じ忘れを確認
- [ ] セミコロンの付け忘れを確認
- [ ] 関数や変数のスコープを確認
- [ ] `console.log`でデバッグ出力を追加
- [ ] エラーが再現する最小限のコードを作成
- [ ] 修正後、すべての機能が正常に動作することを確認

### 8. **推奨ツール**

1. **ESLint** - JavaScriptの静的解析
2. **Prettier** - コードフォーマッター
3. **JSHint** - 追加の構文チェック
4. **Chrome DevTools** - デバッグとプロファイリング
5. **VS Code** - 統合開発環境

これらのベストプラクティスに従うことで、JavaScriptエラーの発生を大幅に減らすことができます。