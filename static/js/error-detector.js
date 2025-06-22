/**
 * 開発環境用JavaScriptエラー検出ツール
 */

(function() {
    'use strict';
    
    // エラー検出を有効化
    const DEBUG = true;
    
    if (!DEBUG) return;
    
    // エラー情報を保存
    const errors = [];
    
    // グローバルエラーハンドラー
    window.addEventListener('error', function(event) {
        const errorInfo = {
            message: event.message,
            source: event.filename,
            line: event.lineno,
            column: event.colno,
            error: event.error,
            stack: event.error ? event.error.stack : null,
            timestamp: new Date().toISOString()
        };
        
        errors.push(errorInfo);
        
        // コンソールに詳細情報を出力
        console.group('%c⚠️ JavaScript Error Detected', 'color: red; font-weight: bold;');
        console.error('Message:', errorInfo.message);
        console.error('Location:', `${errorInfo.source}:${errorInfo.line}:${errorInfo.column}`);
        if (errorInfo.stack) {
            console.error('Stack trace:', errorInfo.stack);
        }
        console.groupEnd();
        
        // 画面上にエラー通知を表示
        showErrorNotification(errorInfo);
    });
    
    // Promiseの未処理エラー
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled Promise Rejection:', event.reason);
    });
    
    // エラー通知を画面に表示
    function showErrorNotification(errorInfo) {
        // 既存の通知を削除
        const existingNotification = document.getElementById('js-error-notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        // エラー通知要素を作成
        const notification = document.createElement('div');
        notification.id = 'js-error-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #f44336;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 9999;
            max-width: 400px;
            font-family: monospace;
            font-size: 12px;
        `;
        
        notification.innerHTML = `
            <strong>JavaScript Error</strong><br>
            ${errorInfo.message}<br>
            <small>${errorInfo.source}:${errorInfo.line}:${errorInfo.column}</small><br>
            <button onclick="this.parentElement.remove()" style="
                background: none;
                border: 1px solid white;
                color: white;
                padding: 5px 10px;
                margin-top: 10px;
                cursor: pointer;
                border-radius: 3px;
            ">閉じる</button>
        `;
        
        document.body.appendChild(notification);
        
        // 10秒後に自動的に削除
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 10000);
    }
    
    // デバッグ情報を表示するコマンド
    window.showJSErrors = function() {
        console.table(errors);
    };
    
    // エラーをクリアするコマンド  
    window.clearJSErrors = function() {
        errors.length = 0;
        console.log('JavaScript errors cleared');
    };
    
})();