/**
 * Character Sheet Error Fixes
 * Temporary fixes for JavaScript errors
 */

// Check if functions exist before calling them
if (typeof calculateDerivedStats === 'undefined') {
    window.calculateDerivedStats = function() {
        console.warn('calculateDerivedStats function is not yet loaded');
    };
}

if (typeof resetDiceSettings === 'undefined') {
    window.resetDiceSettings = function() {
        console.warn('resetDiceSettings function is not yet loaded');
        // Reset to default settings
        if (window.currentDiceSettings && window.DEFAULT_DICE_SETTINGS) {
            window.currentDiceSettings = { ...window.DEFAULT_DICE_SETTINGS };
            
            // Update UI if elements exist
            const abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
            abilities.forEach(ability => {
                const settings = window.currentDiceSettings[ability];
                const countElem = document.getElementById(`dice-${ability}-count`);
                const sidesElem = document.getElementById(`dice-${ability}-sides`);
                const bonusElem = document.getElementById(`dice-${ability}-bonus`);
                
                if (countElem) countElem.value = settings.count;
                if (sidesElem) sidesElem.value = settings.sides;
                if (bonusElem) bonusElem.value = settings.bonus;
            });
            
            // Reset preset selector
            const presetElem = document.getElementById('dice-preset');
            if (presetElem) presetElem.value = 'standard';
        }
    };
}

// Fix for CharacterSheetManager if loadSavedData is missing
document.addEventListener('DOMContentLoaded', function() {
    // Give time for other scripts to load
    setTimeout(function() {
        // Ensure calculateDerivedStats is available globally
        if (typeof window.calculateDerivedStats === 'function') {
            console.log('calculateDerivedStats is available');
        } else {
            console.error('calculateDerivedStats is still not defined');
            
            // Try to find it in the global scope
            const scripts = document.getElementsByTagName('script');
            for (let script of scripts) {
                if (script.textContent && script.textContent.includes('function calculateDerivedStats')) {
                    console.log('Found calculateDerivedStats in script content');
                    break;
                }
            }
        }
    }, 1000);
});

// Export functions to global scope if they're not available
window.calculateDerivedStats = window.calculateDerivedStats || function() {
    // Fallback implementation
    const str = parseInt(document.getElementById('str')?.value) || 0;
    const con = parseInt(document.getElementById('con')?.value) || 0;
    const pow = parseInt(document.getElementById('pow')?.value) || 0;
    const dex = parseInt(document.getElementById('dex')?.value) || 0;
    const siz = parseInt(document.getElementById('siz')?.value) || 0;
    const int = parseInt(document.getElementById('int')?.value) || 0;
    const edu = parseInt(document.getElementById('edu')?.value) || 0;
    
    // HP計算 (CON + SIZ) / 2
    const hp = Math.ceil((con + siz) / 2);
    const hpElement = document.getElementById('hp_value');
    if (hpElement) {
        hpElement.value = hp;
    }
    
    // MP計算 POW
    const mp = pow;
    const mpElement = document.getElementById('mp_value');
    if (mpElement) {
        mpElement.value = mp;
    }
    
    // SAN値 POW × 5
    const san = pow * 5;
    const sanElement = document.getElementById('san_value');
    if (sanElement) {
        sanElement.value = san;
    }
    
    // アイデア INT × 5
    const idea = int * 5;
    const ideaElement = document.getElementById('idea_value');
    if (ideaElement) {
        ideaElement.value = idea;
    }
    
    // 幸運 POW × 5
    const luck = pow * 5;
    const luckElement = document.getElementById('luck_value');
    if (luckElement) {
        luckElement.value = luck;
    }
    
    // 知識 EDU × 5
    const know = edu * 5;
    const knowElement = document.getElementById('know_value');
    if (knowElement) {
        knowElement.value = know;
    }
    
    console.log('Derived stats calculated (fallback)');
};

// Additional missing function definitions
window.toggleDiceSettings = window.toggleDiceSettings || function() {
    const diceSettings = document.getElementById('dice-settings');
    if (diceSettings) {
        if (diceSettings.style.display === 'none' || !diceSettings.style.display) {
            diceSettings.style.display = 'block';
        } else {
            diceSettings.style.display = 'none';
        }
    }
};

window.loadDicePreset = window.loadDicePreset || function() {
    const preset = document.getElementById('dice-preset')?.value;
    if (!preset) return;
    
    console.log('Loading dice preset:', preset);
    // Implementation would go here based on preset selection
};

window.saveCustomDiceSettings = window.saveCustomDiceSettings || function() {
    console.log('Saving custom dice settings');
    // Save to localStorage
    const settings = {};
    const abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
    abilities.forEach(ability => {
        settings[ability] = {
            count: parseInt(document.getElementById(`dice-${ability}-count`)?.value) || 3,
            sides: parseInt(document.getElementById(`dice-${ability}-sides`)?.value) || 6,
            bonus: parseInt(document.getElementById(`dice-${ability}-bonus`)?.value) || 0
        };
    });
    localStorage.setItem('coc6th_dice_settings', JSON.stringify(settings));
    alert('ダイス設定を保存しました');
};

window.loadCustomDiceSettings = window.loadCustomDiceSettings || function() {
    console.log('Loading custom dice settings');
    const saved = localStorage.getItem('coc6th_dice_settings');
    if (saved) {
        const settings = JSON.parse(saved);
        const abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
        abilities.forEach(ability => {
            const data = settings[ability];
            if (data) {
                const countElem = document.getElementById(`dice-${ability}-count`);
                const sidesElem = document.getElementById(`dice-${ability}-sides`);
                const bonusElem = document.getElementById(`dice-${ability}-bonus`);
                if (countElem) countElem.value = data.count;
                if (sidesElem) sidesElem.value = data.sides;
                if (bonusElem) bonusElem.value = data.bonus;
            }
        });
        alert('ダイス設定を読み込みました');
    }
};

window.rollSingleAbility = window.rollSingleAbility || function(ability) {
    console.log('Rolling for ability:', ability);
    // Get dice settings
    const count = parseInt(document.getElementById(`dice-${ability}-count`)?.value) || 3;
    const sides = parseInt(document.getElementById(`dice-${ability}-sides`)?.value) || 6;
    const bonus = parseInt(document.getElementById(`dice-${ability}-bonus`)?.value) || 0;
    
    // Roll dice
    let total = 0;
    for (let i = 0; i < count; i++) {
        total += Math.floor(Math.random() * sides) + 1;
    }
    total += bonus;
    
    // Set value
    const abilityInput = document.getElementById(ability);
    if (abilityInput) {
        abilityInput.value = total;
        // Trigger change event
        abilityInput.dispatchEvent(new Event('input', { bubbles: true }));
        abilityInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
};

window.resetAllSkills = window.resetAllSkills || function() {
    if (confirm('すべての技能ポイントをリセットしますか？')) {
        document.querySelectorAll('.occupation-points-input, .interest-points-input, .skill-bonus').forEach(input => {
            input.value = 0;
        });
        // Update totals
        if (typeof updateSkillPointsUsage === 'function') {
            updateSkillPointsUsage();
        }
    }
};

window.showRecommendedSkills = window.showRecommendedSkills || function() {
    const occupation = document.getElementById('occupation')?.value || '';
    let message = '推奨技能：\n\n';
    
    const recommendations = {
        '医師': '医学、応急手当、精神分析、薬学、生物学、図書館、信用、心理学',
        '警察官': '拳銃、法律、目星、聞き耳、心理学、追跡、運転（自動車）、組み付き',
        '探偵': '目星、聞き耳、心理学、追跡、鍵開け、法律、写真術、図書館',
        'ジャーナリスト': '図書館、説得、心理学、写真術、信用、聞き耳、目星、他の言語'
    };
    
    if (occupation && recommendations[occupation]) {
        message += `${occupation}の推奨技能：\n${recommendations[occupation]}`;
    } else {
        message += '一般的な推奨技能：\n回避、目星、聞き耳、図書館、心理学、応急手当、信用、運転（自動車）';
    }
    
    alert(message);
};