/**
 * ダイス設定のデバッグスクリプト
 * 値が正しく設定・表示されることを確認
 */

function debugDiceSettings() {
    console.log('=== ダイス設定デバッグ開始 ===');
    
    // すべてのダイス設定input要素を確認
    const abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
    
    abilities.forEach(ability => {
        const countInput = document.getElementById(`dice-${ability}-count`);
        const sidesInput = document.getElementById(`dice-${ability}-sides`);
        const bonusInput = document.getElementById(`dice-${ability}-bonus`);
        
        console.log(`--- ${ability.toUpperCase()} ---`);
        
        if (countInput) {
            console.log(`Count: 要素存在=○, 値=${countInput.value}, 表示=${window.getComputedStyle(countInput).display}`);
            // 強制的にスタイルを適用（幅を狭めに）
            countInput.style.cssText = 'display: inline-block !important; width: 40px !important; height: 28px !important; background-color: white !important; color: black !important; border: 1px solid #ced4da !important; padding: 2px 4px !important; text-align: center !important; font-size: 0.875rem !important;';
        } else {
            console.log('Count: 要素存在=×');
        }
        
        if (sidesInput) {
            console.log(`Sides: 要素存在=○, 値=${sidesInput.value}, 表示=${window.getComputedStyle(sidesInput).display}`);
            // 強制的にスタイルを適用（幅を狭めに）
            sidesInput.style.cssText = 'display: inline-block !important; width: 40px !important; height: 28px !important; background-color: white !important; color: black !important; border: 1px solid #ced4da !important; padding: 2px 4px !important; text-align: center !important; font-size: 0.875rem !important;';
        } else {
            console.log('Sides: 要素存在=×');
        }
        
        if (bonusInput) {
            console.log(`Bonus: 要素存在=○, 値=${bonusInput.value}, 表示=${window.getComputedStyle(bonusInput).display}`);
            // 強制的にスタイルを適用（幅を狭めに）
            bonusInput.style.cssText = 'display: inline-block !important; width: 40px !important; height: 28px !important; background-color: white !important; color: black !important; border: 1px solid #ced4da !important; padding: 2px 4px !important; text-align: center !important; font-size: 0.875rem !important;';
        } else {
            console.log('Bonus: 要素存在=×');
        }
    });
    
    console.log('=== ダイス設定デバッグ終了 ===');
}

// ページ読み込み後に実行
document.addEventListener('DOMContentLoaded', function() {
    // 1秒後に実行（他のスクリプトの後）
    setTimeout(debugDiceSettings, 1000);
});