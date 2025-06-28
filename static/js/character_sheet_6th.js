/**
 * クトゥルフ神話TRPG 6版 キャラクターシート JavaScript
 */

'use strict';

// ===========================
// グローバル定数・変数
// ===========================
const ABILITIES = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
const ABILITY_NAMES = {
    str: 'STR（筋力）',
    con: 'CON（体力）',
    pow: 'POW（精神力）',
    dex: 'DEX（敏捷性）',
    app: 'APP（外見）',
    siz: 'SIZ（体格）',
    int: 'INT（知性）',
    edu: 'EDU（教育）'
};

// ダイスプリセット
const DICE_PRESETS = {
    standard: {
        str: { count: 3, sides: 6, bonus: 0 },
        con: { count: 3, sides: 6, bonus: 0 },
        pow: { count: 3, sides: 6, bonus: 0 },
        dex: { count: 3, sides: 6, bonus: 0 },
        app: { count: 3, sides: 6, bonus: 0 },
        siz: { count: 2, sides: 6, bonus: 6 },
        int: { count: 2, sides: 6, bonus: 6 },
        edu: { count: 3, sides: 6, bonus: 3 }
    },
    high: {
        str: { count: 4, sides: 6, bonus: -4 },
        con: { count: 4, sides: 6, bonus: -4 },
        pow: { count: 4, sides: 6, bonus: -4 },
        dex: { count: 4, sides: 6, bonus: -4 },
        app: { count: 4, sides: 6, bonus: -4 },
        siz: { count: 3, sides: 6, bonus: 3 },
        int: { count: 3, sides: 6, bonus: 3 },
        edu: { count: 4, sides: 6, bonus: 0 }
    }
};

// スキルカテゴリーとスキル定義
const SKILL_CATEGORIES = {
    combat: {
        name: '戦闘技能',
        skills: ['回避', 'キック', '組み付き', 'こぶし', '頭突き', '投擲', 'マーシャルアーツ', '拳銃', 'サブマシンガン', 'ショットガン', 'マシンガン', 'ライフル']
    },
    search: {
        name: '探索技能',
        skills: ['鍵開け', '隠す', '隠れる', '聞き耳', '忍び歩き', '写真術', '追跡', '登攀', '図書館', '目星']
    },
    action: {
        name: '行動技能',
        skills: ['運転（自動車）', '運転（その他）', '機械修理', '重機械操作', '乗馬', '水泳', '跳躍', '電気修理', 'ナビゲート', '変装']
    },
    negotiation: {
        name: '交渉技能',
        skills: ['言いくるめ', '信用', '説得', '値切り', '精神分析', '応急手当', '母国語', '他の言語']
    },
    knowledge: {
        name: '知識技能',
        skills: ['医学', 'オカルト', '化学', 'クトゥルフ神話', '芸術', '経理', '考古学', 'コンピューター', '心理学', '人類学', '生物学', '地質学', '電子工学', '天文学', '博物学', '物理学', '法律', '薬学', '歴史']
    }
};

// グローバル変数
let currentDiceSettings = { ...DICE_PRESETS.standard };
let uploadedImages = [];
let weaponCount = 0;
let armorCount = 0;
let itemCount = 0;
let sessionRecordCount = 0;
let growthRecordCount = 0;
let customSkillCounts = {
    combat: 0,
    search: 0,
    action: 0,
    negotiation: 0,
    knowledge: 0
};

// ===========================
// 初期化処理
// ===========================
document.addEventListener('DOMContentLoaded', function() {
    initializeProgressBar();
    initializeImageUpload();
    initializeDiceSettings();
    initializeAbilityListeners();
    initializeSkills();
    initializeFormValidation();
    initializeTabChangeHandlers();
    initializeOccupationFormulaListener();
    
    // 初期計算
    calculateDerivedStats();
    calculateSkillPoints();
    updateDynamicSkillBases();
});

// ===========================
// プログレスバー管理
// ===========================
function initializeProgressBar() {
    // セクションインジケーターのクリックイベント
    document.querySelectorAll('.section-indicator').forEach(indicator => {
        indicator.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            const tab = document.getElementById(`${tabId}-tab`);
            if (tab) {
                const tabInstance = new bootstrap.Tab(tab);
                tabInstance.show();
            }
        });
    });
}

function initializeTabChangeHandlers() {
    // タブ変更時の処理
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            updateProgressIndicators();
            updateProgressBar();
            saveToLocalStorage();
        });
    });
}

function updateProgressIndicators() {
    const activeTab = document.querySelector('.nav-link.active');
    if (!activeTab) return;
    
    const activeTabId = activeTab.id.replace('-tab', '');
    
    document.querySelectorAll('.section-indicator').forEach(indicator => {
        indicator.classList.remove('active', 'completed');
        
        const tabId = indicator.dataset.tab;
        if (tabId === activeTabId) {
            indicator.classList.add('active');
        } else if (isTabCompleted(tabId)) {
            indicator.classList.add('completed');
        }
    });
    
    // インジケーターラインの更新
    updateIndicatorLines();
}

function updateIndicatorLines() {
    const indicators = Array.from(document.querySelectorAll('.section-indicator'));
    const lines = Array.from(document.querySelectorAll('.indicator-line'));
    
    indicators.forEach((indicator, index) => {
        if (index < lines.length) {
            if (indicator.classList.contains('completed')) {
                lines[index].classList.add('completed');
            } else {
                lines[index].classList.remove('completed');
            }
        }
    });
}

function updateProgressBar() {
    const totalTabs = 7;
    let completedTabs = 0;
    
    const tabIds = ['basic', 'abilities', 'skills', 'combat', 'inventory', 'background', 'history'];
    tabIds.forEach(tabId => {
        if (isTabCompleted(tabId)) {
            completedTabs++;
        }
    });
    
    const progress = Math.round((completedTabs / totalTabs) * 100);
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }
}

function isTabCompleted(tabId) {
    switch (tabId) {
        case 'basic':
            return checkBasicInfoComplete();
        case 'abilities':
            return checkAbilitiesComplete();
        case 'skills':
            return checkSkillsComplete();
        case 'combat':
            return checkCombatComplete();
        case 'inventory':
            return checkInventoryComplete();
        case 'background':
            return checkBackgroundComplete();
        case 'history':
            return checkHistoryComplete();
        default:
            return false;
    }
}

function checkBasicInfoComplete() {
    const requiredFields = ['name', 'age', 'occupation'];
    return requiredFields.every(field => {
        const element = document.getElementById(field);
        return element && element.value.trim() !== '';
    });
}

function checkAbilitiesComplete() {
    return ABILITIES.every(ability => {
        const element = document.getElementById(ability);
        return element && element.value !== '';
    });
}

function checkSkillsComplete() {
    const occupationUsed = parseInt(document.getElementById('occupation-points-used')?.textContent || '0');
    const interestUsed = parseInt(document.getElementById('interest-points-used')?.textContent || '0');
    return occupationUsed > 0 || interestUsed > 0;
}

function checkCombatComplete() {
    return document.querySelectorAll('#weapons-list .weapon-item').length > 0;
}

function checkInventoryComplete() {
    return document.querySelectorAll('#items-list .item-entry').length > 0;
}

function checkBackgroundComplete() {
    const backgroundFields = ['appearance', 'beliefs', 'personal_history'];
    return backgroundFields.some(field => {
        const element = document.getElementById(field);
        return element && element.value.trim() !== '';
    });
}

function checkHistoryComplete() {
    return document.querySelectorAll('#session-records .session-record').length > 0;
}

// ===========================
// 画像アップロード機能
// ===========================
function initializeImageUpload() {
    const uploadArea = document.getElementById('image-upload-area');
    const fileInput = document.getElementById('character-images');
    
    if (!uploadArea || !fileInput) return;
    
    // クリックイベント
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // ドラッグ&ドロップイベント
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    // ファイル選択イベント
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

function handleFiles(files) {
    const maxFiles = 10;
    const maxSize = 5 * 1024 * 1024; // 5MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
    
    Array.from(files).forEach(file => {
        // バリデーション
        if (uploadedImages.length >= maxFiles) {
            showToast('画像は最大10枚までアップロード可能です', 'warning');
            return;
        }
        
        if (!allowedTypes.includes(file.type)) {
            showToast(`${file.name}はサポートされていない形式です`, 'error');
            return;
        }
        
        if (file.size > maxSize) {
            showToast(`${file.name}はファイルサイズが大きすぎます（最大5MB）`, 'error');
            return;
        }
        
        // プレビュー作成
        const reader = new FileReader();
        reader.onload = (e) => {
            const imageData = {
                id: Date.now() + Math.random(),
                file: file,
                url: e.target.result,
                isMain: uploadedImages.length === 0
            };
            
            uploadedImages.push(imageData);
            renderImagePreviews();
            updateImageCount();
        };
        reader.readAsDataURL(file);
    });
}

function renderImagePreviews() {
    const grid = document.getElementById('image-preview-grid');
    if (!grid) return;
    
    grid.innerHTML = uploadedImages.map((image, index) => `
        <div class="image-item" data-image-id="${image.id}">
            <img src="${image.url}" alt="キャラクター画像${index + 1}" onclick="viewImage('${image.id}')">
            ${image.isMain ? '<div class="main-badge">メイン</div>' : ''}
            <div class="image-item-overlay">
                <div class="image-controls">
                    ${!image.isMain ? `<button type="button" class="btn btn-sm btn-success" onclick="setMainImage('${image.id}')">メイン</button>` : ''}
                    <button type="button" class="btn btn-sm btn-danger" onclick="removeImage('${image.id}')">削除</button>
                </div>
            </div>
        </div>
    `).join('');
    
    // Sortable.jsで並び替え可能にする
    if (typeof Sortable !== 'undefined') {
        new Sortable(grid, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: function(evt) {
                const imageId = evt.item.dataset.imageId;
                const oldIndex = evt.oldIndex;
                const newIndex = evt.newIndex;
                
                // 配列の順序を更新
                const [movedImage] = uploadedImages.splice(oldIndex, 1);
                uploadedImages.splice(newIndex, 0, movedImage);
            }
        });
    }
}

function setMainImage(imageId) {
    uploadedImages.forEach(image => {
        image.isMain = image.id == imageId;
    });
    renderImagePreviews();
}

function removeImage(imageId) {
    uploadedImages = uploadedImages.filter(image => image.id != imageId);
    
    // メイン画像が削除された場合、最初の画像をメインに設定
    if (uploadedImages.length > 0 && !uploadedImages.some(img => img.isMain)) {
        uploadedImages[0].isMain = true;
    }
    
    renderImagePreviews();
    updateImageCount();
}

function viewImage(imageId) {
    const image = uploadedImages.find(img => img.id == imageId);
    if (!image) return;
    
    const modalImage = document.getElementById('modalImage');
    if (modalImage) {
        modalImage.src = image.url;
        const modal = new bootstrap.Modal(document.getElementById('imageViewModal'));
        modal.show();
    }
}

function updateImageCount() {
    const countDisplay = document.getElementById('image-count-display');
    if (countDisplay) {
        countDisplay.innerHTML = `<small>${uploadedImages.length} / 10 枚</small>`;
    }
}

// ===========================
// ダイス設定
// ===========================
function initializeDiceSettings() {
    generateDiceSettingsHTML();
}

function generateDiceSettingsHTML() {
    const container = document.getElementById('dice-settings');
    if (!container) return;
    
    const row = container.querySelector('.row') || document.createElement('div');
    row.className = 'row';
    
    row.innerHTML = ABILITIES.map(ability => `
        <div class="col-md-3 mb-3">
            <div class="dice-setting-item">
                <h6>${ABILITY_NAMES[ability]}</h6>
                <div class="input-group mb-2">
                    <input type="number" class="form-control" id="dice-count-${ability}" min="1" max="10" value="${currentDiceSettings[ability].count}">
                    <span class="input-group-text">D</span>
                    <input type="number" class="form-control" id="dice-sides-${ability}" min="1" max="100" value="${currentDiceSettings[ability].sides}">
                    <span class="input-group-text">+</span>
                    <input type="number" class="form-control" id="dice-bonus-${ability}" min="-50" max="50" value="${currentDiceSettings[ability].bonus}">
                </div>
            </div>
        </div>
    `).join('');
    
    container.appendChild(row);
}

function toggleCustomDiceSettings() {
    const settings = document.getElementById('dice-settings');
    if (settings) {
        settings.style.display = settings.style.display === 'none' ? 'block' : 'none';
    }
}

function applyDicePreset(preset) {
    if (DICE_PRESETS[preset]) {
        currentDiceSettings = { ...DICE_PRESETS[preset] };
        
        // UI更新
        ABILITIES.forEach(ability => {
            const countInput = document.getElementById(`dice-count-${ability}`);
            const sidesInput = document.getElementById(`dice-sides-${ability}`);
            const bonusInput = document.getElementById(`dice-bonus-${ability}`);
            
            if (countInput) countInput.value = currentDiceSettings[ability].count;
            if (sidesInput) sidesInput.value = currentDiceSettings[ability].sides;
            if (bonusInput) bonusInput.value = currentDiceSettings[ability].bonus;
        });
        
        showToast(`${preset === 'standard' ? '標準' : '高ステータス'}プリセットを適用しました`, 'success');
    }
}

function rollDice(count, sides, bonus = 0) {
    let total = bonus;
    for (let i = 0; i < count; i++) {
        total += Math.floor(Math.random() * sides) + 1;
    }
    return Math.max(1, total); // 最小値1
}

function rollSingleAbility(ability) {
    const settings = currentDiceSettings[ability];
    const result = rollDice(settings.count, settings.sides, settings.bonus);
    
    const input = document.getElementById(ability);
    if (input) {
        input.value = result;
        input.classList.add('dice-rolled');
        setTimeout(() => input.classList.remove('dice-rolled'), 1000);
        
        calculateDerivedStats();
        calculateSkillPoints();
    }
}

function rollAllDice() {
    ABILITIES.forEach(ability => {
        rollSingleAbility(ability);
    });
    
    showToast('全能力値をロールしました！', 'success');
}

// ===========================
// 能力値リスナー
// ===========================
function initializeAbilityListeners() {
    ABILITIES.forEach(ability => {
        const input = document.getElementById(ability);
        if (input) {
            input.addEventListener('input', () => {
                calculateDerivedStats();
                calculateSkillPoints();
                updateDynamicSkillBases();
            });
        }
    });
}

// ===========================
// 副次能力値計算
// ===========================
function calculateDerivedStats() {
    const abilities = {};
    ABILITIES.forEach(ability => {
        const input = document.getElementById(ability);
        abilities[ability] = input ? parseInt(input.value) || 0 : 0;
    });
    
    // HP: (CON + SIZ) ÷ 2
    const hp = Math.ceil((abilities.con + abilities.siz) / 2);
    updateValue('hp-value', hp);
    updateValue('hp_max', hp);
    
    // MP: POW
    const mp = abilities.pow;
    updateValue('mp-value', mp);
    updateValue('mp_max', mp);
    
    // SAN: POW × 5
    const san = abilities.pow * 5;
    updateValue('san-value', san);
    updateValue('san_max', san);
    
    // アイデア: INT × 5
    const idea = abilities.int * 5;
    updateValue('idea-value', idea);
    
    // 幸運: POW × 5
    const luck = abilities.pow * 5;
    updateValue('luck-value', luck);
    
    // 知識: EDU × 5
    const knowledge = abilities.edu * 5;
    updateValue('knowledge-value', knowledge);
    
    // ダメージボーナス
    const strSiz = abilities.str + abilities.siz;
    let damageBonus = '';
    if (strSiz <= 12) damageBonus = '-1d6';
    else if (strSiz <= 16) damageBonus = '-1d4';
    else if (strSiz <= 24) damageBonus = '0';
    else if (strSiz <= 32) damageBonus = '+1d4';
    else if (strSiz <= 40) damageBonus = '+1d6';
    else damageBonus = `+${Math.floor((strSiz - 40) / 16) + 2}d6`;
    
    updateValue('damage-bonus-value', damageBonus);
    updateValue('damage_bonus', damageBonus);
    
    // 回避: DEX × 2
    const dodge = abilities.dex * 2;
    updateValue('dodge-value', dodge);
    updateValue('dodge_value', dodge);
    
    // 移動率
    let movement = 8;
    if (abilities.dex < abilities.siz && abilities.str < abilities.siz) movement = 7;
    else if (abilities.str >= abilities.siz || abilities.dex >= abilities.siz) movement = 8;
    else if (abilities.str > abilities.siz && abilities.dex > abilities.siz) movement = 9;
    
    const movementText = `通常: ${movement} / 重荷: ${Math.floor(movement / 2)} / 限界: 1`;
    updateValue('movement-value', movementText);
    
    // 運搬能力
    const carryCapacity = abilities.str * 3;
    updateValue('carry-capacity', carryCapacity);
}

function updateValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        if (element.tagName === 'INPUT') {
            element.value = value;
        } else {
            element.textContent = value;
        }
    }
}

// ===========================
// スキル管理
// ===========================
function initializeSkills() {
    generateAllSkillsHTML();
    initializeSkillFilterTabs();
    
    // 職業ポイント計算式の変更イベント
    const formulaSelect = document.getElementById('occupation-formula');
    if (formulaSelect) {
        formulaSelect.addEventListener('change', calculateSkillPoints);
    }
    
    // 初期値の計算
    updateDynamicSkillBases();
}

function generateAllSkillsHTML() {
    // 全スキルのリストを作成
    const allSkills = [];
    Object.entries(SKILL_CATEGORIES).forEach(([categoryKey, category]) => {
        category.skills.forEach(skill => {
            allSkills.push({ name: skill, category: categoryKey });
        });
    });
    
    // すべての技能タブに表示
    const allSkillsContainer = document.getElementById('all-skills-container');
    if (allSkillsContainer) {
        allSkillsContainer.innerHTML = createSkillListHTML(allSkills) + createAddCustomSkillButton('all');
    }
    
    // カテゴリー別タブに表示
    Object.entries(SKILL_CATEGORIES).forEach(([categoryKey, category]) => {
        const categorySkills = category.skills.map(skill => ({ name: skill, category: categoryKey }));
        const containerId = getCategoryContainerId(categoryKey);
        const container = document.getElementById(containerId);
        
        if (container) {
            container.innerHTML = createSkillListHTML(categorySkills) + createAddCustomSkillButton(categoryKey);
        }
    });
}

function getCategoryContainerId(categoryKey) {
    const mapping = {
        'combat': 'combat-skills-container',
        'search': 'search-skills-container',
        'action': 'action-skills-container',
        'negotiation': 'negotiation-skills-container',
        'knowledge': 'knowledge-skills-container'
    };
    return mapping[categoryKey] || 'knowledge-skills-container';
}

function createSkillListHTML(skills) {
    return `
        <div class="row">
            ${skills.map(skillData => createSkillItemHTML(skillData.name, skillData.category)).join('')}
        </div>
    `;
}

function createSkillItemHTML(skill, category, isCustom = false) {
    const baseValue = getSkillBaseValue(skill);
    const customClass = isCustom ? 'custom-skill' : '';
    const deleteButton = isCustom ? `<button type="button" class="btn btn-sm btn-danger float-end" onclick="removeCustomSkill(this)"><i class="fas fa-times"></i></button>` : '';
    
    return `
        <div class="col-lg-6 mb-3 skill-item-wrapper ${customClass}" data-skill-name="${skill}" data-skill-category="${category}">
            <div class="skill-item">
                <h6 class="skill-name mb-2">
                    ${isCustom ? `<input type="text" class="form-control form-control-sm d-inline-block w-auto" value="${skill}" onchange="updateCustomSkillName(this)">` : skill}
                    ${deleteButton}
                </h6>
                <div class="skill-inputs">
                    <div class="row g-2">
                        <div class="col-2">
                            <label class="form-label small">初期値</label>
                            <input type="number" class="form-control form-control-sm skill-base text-center" value="${baseValue}" ${isCustom ? '' : 'readonly'} onchange="updateSkillTotal(this)">
                        </div>
                        <div class="col-2">
                            <label class="form-label small">職業</label>
                            <input type="number" class="form-control form-control-sm skill-occupation text-center" min="0" max="99" value="0" onchange="updateSkillTotal(this)">
                        </div>
                        <div class="col-2">
                            <label class="form-label small">趣味</label>
                            <input type="number" class="form-control form-control-sm skill-interest text-center" min="0" max="99" value="0" onchange="updateSkillTotal(this)">
                        </div>
                        <div class="col-2">
                            <label class="form-label small">成長</label>
                            <input type="number" class="form-control form-control-sm skill-growth text-center" min="0" max="99" value="0" onchange="updateSkillTotal(this)">
                        </div>
                        <div class="col-2">
                            <label class="form-label small">その他</label>
                            <input type="number" class="form-control form-control-sm skill-other text-center" min="0" max="99" value="0" onchange="updateSkillTotal(this)">
                        </div>
                        <div class="col-2">
                            <label class="form-label small text-primary">合計</label>
                            <input type="number" class="form-control form-control-sm skill-total text-center fw-bold" value="${baseValue}" readonly>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function createAddCustomSkillButton(category) {
    return `
        <div class="col-12 text-center mt-3">
            <button type="button" class="btn btn-outline-primary" onclick="addCustomSkill('${category}')">
                <i class="fas fa-plus"></i> カスタム技能を追加
            </button>
        </div>
    `;
}

function addCustomSkill(category) {
    const targetCategory = category === 'all' ? 'knowledge' : category; // 「すべて」タブの場合は知識に追加
    customSkillCounts[targetCategory]++;
    
    const skillName = `カスタム技能${customSkillCounts[targetCategory]}`;
    const customSkillHTML = createSkillItemHTML(skillName, targetCategory, true);
    
    // 各タブに追加
    if (category === 'all') {
        const allContainer = document.querySelector('#all-skills-container .row');
        if (allContainer) {
            const buttonDiv = allContainer.querySelector('.col-12.text-center');
            if (buttonDiv) {
                buttonDiv.insertAdjacentHTML('beforebegin', customSkillHTML);
            }
        }
    }
    
    // カテゴリー別タブに追加
    const categoryContainer = document.querySelector(`#${getCategoryContainerId(targetCategory)} .row`);
    if (categoryContainer) {
        const buttonDiv = categoryContainer.querySelector('.col-12.text-center');
        if (buttonDiv) {
            buttonDiv.insertAdjacentHTML('beforebegin', customSkillHTML);
        }
    }
    
    // すべてのタブにも追加（カテゴリー別から追加した場合）
    if (category !== 'all') {
        const allContainer = document.querySelector('#all-skills-container .row');
        if (allContainer) {
            const buttonDiv = allContainer.querySelector('.col-12.text-center');
            if (buttonDiv) {
                buttonDiv.insertAdjacentHTML('beforebegin', customSkillHTML);
            }
        }
    }
}

function removeCustomSkill(button) {
    const wrapper = button.closest('.skill-item-wrapper');
    const skillName = wrapper.dataset.skillName;
    
    // すべての同名スキルを削除
    document.querySelectorAll(`.skill-item-wrapper[data-skill-name="${skillName}"]`).forEach(el => {
        el.remove();
    });
}

function updateCustomSkillName(input) {
    const wrapper = input.closest('.skill-item-wrapper');
    const oldName = wrapper.dataset.skillName;
    const newName = input.value;
    
    // すべての同名スキルの名前を更新
    document.querySelectorAll(`.skill-item-wrapper[data-skill-name="${oldName}"]`).forEach(el => {
        el.dataset.skillName = newName;
        const nameInput = el.querySelector('.skill-name input');
        if (nameInput && nameInput !== input) {
            nameInput.value = newName;
        }
    });
}

function initializeSkillFilterTabs() {
    // フィルタータブのクリックイベント
    document.querySelectorAll('#skillFilterTabs button').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.getAttribute('data-bs-target');
            
            if (targetId === '#allocated-skills') {
                updateAllocatedSkillsTab();
            }
        });
    });
}

function updateAllocatedSkillsTab() {
    const container = document.getElementById('allocated-skills-container');
    if (!container) return;
    
    // ポイントが振られている技能を収集（重複を排除）
    const allocatedSkills = [];
    const seenSkills = new Set();
    
    document.querySelectorAll('#all-skills-container .skill-item-wrapper').forEach(wrapper => {
        const occupation = parseInt(wrapper.querySelector('.skill-occupation')?.value || '0');
        const interest = parseInt(wrapper.querySelector('.skill-interest')?.value || '0');
        const growth = parseInt(wrapper.querySelector('.skill-growth')?.value || '0');
        const other = parseInt(wrapper.querySelector('.skill-other')?.value || '0');
        
        if (occupation > 0 || interest > 0 || growth > 0 || other > 0) {
            const skillName = wrapper.dataset.skillName;
            const category = wrapper.dataset.skillCategory;
            
            // 重複チェック
            if (!seenSkills.has(skillName)) {
                seenSkills.add(skillName);
                allocatedSkills.push({ name: skillName, category: category });
            }
        }
    });
    
    if (allocatedSkills.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">まだポイントを振り分けた技能がありません。</p>';
    } else {
        container.innerHTML = createSkillListHTML(allocatedSkills);
        
        // 振り分け済みタブのデータを同期
        allocatedSkills.forEach(skillData => {
            syncSkillData(skillData.name, container);
        });
    }
}

function getSkillBaseValue(skill) {
    // スキルの初期値設定（6版準拠）
    const baseValues = {
        // 戦闘技能
        '回避': 0, // DEX×2で別計算
        'キック': 25,
        '組み付き': 25,
        'こぶし': 50,
        '頭突き': 10,
        '投擲': 25,
        'マーシャルアーツ': 1,
        '拳銃': 20,
        'サブマシンガン': 15,
        'ショットガン': 30,
        'マシンガン': 15,
        'ライフル': 25,
        // 探索技能
        '鍵開け': 1,
        '隠す': 15,
        '隠れる': 10,
        '聞き耳': 25,
        '忍び歩き': 10,
        '写真術': 10,
        '追跡': 10,
        '登攀': 40,
        '図書館': 25,
        '目星': 25,
        // 行動技能
        '運転（自動車）': 20,
        '運転（その他）': 1,
        '機械修理': 20,
        '重機械操作': 1,
        '乗馬': 5,
        '水泳': 25,
        '跳躍': 25,
        '電気修理': 10,
        'ナビゲート': 10,
        '変装': 1,
        // 交渉技能
        '言いくるめ': 5,
        '信用': 15,
        '説得': 15,
        '値切り': 5,
        '精神分析': 1,
        '応急手当': 30,
        '母国語': 0, // EDU×5で別計算
        '他の言語': 1,
        // 知識技能
        '医学': 5,
        'オカルト': 5,
        '化学': 1,
        'クトゥルフ神話': 0,
        '芸術': 5,
        '経理': 10,
        '考古学': 1,
        'コンピューター': 1,
        '心理学': 5,
        '人類学': 1,
        '生物学': 1,
        '地質学': 1,
        '電子工学': 1,
        '天文学': 1,
        '博物学': 10,
        '物理学': 1,
        '法律': 5,
        '薬学': 1,
        '歴史': 20
    };
    
    // 特殊計算が必要なスキル
    if (skill === '回避') {
        const dex = parseInt(document.getElementById('dex')?.value || '0');
        return dex * 2;
    }
    if (skill === '母国語') {
        const edu = parseInt(document.getElementById('edu')?.value || '0');
        return edu * 5;
    }
    
    return baseValues[skill] || 1;
}

function syncSkillData(skillName, targetContainer) {
    // 元のデータを取得
    const originalWrapper = document.querySelector(`.skill-item-wrapper[data-skill-name="${skillName}"]`);
    if (!originalWrapper) return;
    
    const targetWrapper = targetContainer.querySelector(`.skill-item-wrapper[data-skill-name="${skillName}"]`);
    if (!targetWrapper) return;
    
    // 値をコピー
    ['occupation', 'interest', 'growth', 'other'].forEach(type => {
        const originalInput = originalWrapper.querySelector(`.skill-${type}`);
        const targetInput = targetWrapper.querySelector(`.skill-${type}`);
        if (originalInput && targetInput) {
            targetInput.value = originalInput.value;
        }
    });
    
    // 合計を更新
    updateSkillTotal(targetWrapper.querySelector('.skill-occupation'));
}

function updateDynamicSkillBases() {
    // 回避の初期値を更新（DEX×2）
    document.querySelectorAll('.skill-item-wrapper[data-skill-name="回避"]').forEach(wrapper => {
        const dex = parseInt(document.getElementById('dex')?.value || '0');
        const baseInput = wrapper.querySelector('.skill-base');
        if (baseInput) {
            const oldValue = parseInt(baseInput.value || '0');
            baseInput.value = dex * 2;
            // 初期値が変わった場合は合計も更新
            if (oldValue !== dex * 2) {
                updateSkillTotal(baseInput);
            }
        }
    });
    
    // 母国語の初期値を更新（EDU×5）
    document.querySelectorAll('.skill-item-wrapper[data-skill-name="母国語"]').forEach(wrapper => {
        const edu = parseInt(document.getElementById('edu')?.value || '0');
        const baseInput = wrapper.querySelector('.skill-base');
        if (baseInput) {
            const oldValue = parseInt(baseInput.value || '0');
            baseInput.value = edu * 5;
            // 初期値が変わった場合は合計も更新
            if (oldValue !== edu * 5) {
                updateSkillTotal(baseInput);
            }
        }
    });
}

function updateSkillTotal(input) {
    if (!input) return;
    
    const wrapper = input.closest('.skill-item-wrapper');
    if (!wrapper) return;
    
    const base = parseInt(wrapper.querySelector('.skill-base')?.value || '0');
    const occupation = parseInt(wrapper.querySelector('.skill-occupation')?.value || '0');
    const interest = parseInt(wrapper.querySelector('.skill-interest')?.value || '0');
    const growth = parseInt(wrapper.querySelector('.skill-growth')?.value || '0');
    const other = parseInt(wrapper.querySelector('.skill-other')?.value || '0');
    
    const total = Math.min(99, base + occupation + interest + growth + other);
    const totalInput = wrapper.querySelector('.skill-total');
    if (totalInput) {
        totalInput.value = total;
    }
    
    // 同じスキル名の他のタブの値も更新
    const skillName = wrapper.dataset.skillName;
    document.querySelectorAll(`.skill-item-wrapper[data-skill-name="${skillName}"]`).forEach(otherWrapper => {
        if (otherWrapper !== wrapper) {
            ['occupation', 'interest', 'growth', 'other'].forEach(type => {
                const sourceInput = wrapper.querySelector(`.skill-${type}`);
                const targetInput = otherWrapper.querySelector(`.skill-${type}`);
                if (sourceInput && targetInput) {
                    targetInput.value = sourceInput.value;
                }
            });
            
            const otherTotal = Math.min(99, base + occupation + interest + growth + other);
            const otherTotalInput = otherWrapper.querySelector('.skill-total');
            if (otherTotalInput) {
                otherTotalInput.value = otherTotal;
            }
        }
    });
    
    calculateSkillPoints();
}

function calculateSkillPoints() {
    const edu = parseInt(document.getElementById('edu')?.value || '0');
    const int = parseInt(document.getElementById('int')?.value || '0');
    const str = parseInt(document.getElementById('str')?.value || '0');
    const con = parseInt(document.getElementById('con')?.value || '0');
    const pow = parseInt(document.getElementById('pow')?.value || '0');
    const dex = parseInt(document.getElementById('dex')?.value || '0');
    const app = parseInt(document.getElementById('app')?.value || '0');
    const siz = parseInt(document.getElementById('siz')?.value || '0');
    
    // 職業ポイント計算
    const formula = document.getElementById('occupation-formula')?.value || 'edu20';
    let occupationTotal = 0;
    
    switch (formula) {
        case 'edu20':
            occupationTotal = edu * 20;
            break;
        case 'edu10_str10':
            occupationTotal = edu * 10 + str * 10;
            break;
        case 'edu10_con10':
            occupationTotal = edu * 10 + con * 10;
            break;
        case 'edu10_pow10':
            occupationTotal = edu * 10 + pow * 10;
            break;
        case 'edu10_dex10':
            occupationTotal = edu * 10 + dex * 10;
            break;
        case 'edu10_app10':
            occupationTotal = edu * 10 + app * 10;
            break;
        case 'edu10_siz10':
            occupationTotal = edu * 10 + siz * 10;
            break;
        case 'edu10_int10':
            occupationTotal = edu * 10 + int * 10;
            break;
    }
    
    // 趣味ポイント
    const interestTotal = int * 10;
    
    // 使用ポイント計算（重複を防ぐため、すべての技能タブから一度だけ集計）
    let occupationUsed = 0;
    let interestUsed = 0;
    const countedSkills = new Set();
    
    // すべての技能タブから収集（重複を防ぐ）
    document.querySelectorAll('#all-skills-container .skill-item-wrapper').forEach(wrapper => {
        const skillName = wrapper.dataset.skillName;
        if (!countedSkills.has(skillName)) {
            countedSkills.add(skillName);
            const occupation = parseInt(wrapper.querySelector('.skill-occupation')?.value || '0');
            const interest = parseInt(wrapper.querySelector('.skill-interest')?.value || '0');
            
            occupationUsed += occupation;
            interestUsed += interest;
        }
    });
    
    // 表示更新
    updateValue('occupation-points-total', occupationTotal);
    updateValue('occupation-points-used', occupationUsed);
    updateValue('occupation-points-remaining', occupationTotal - occupationUsed);
    
    updateValue('interest-points-total', interestTotal);
    updateValue('interest-points-used', interestUsed);
    updateValue('interest-points-remaining', interestTotal - interestUsed);
}

// ===========================
// 武器・防具・アイテム管理
// ===========================
function addWeapon() {
    const list = document.getElementById('weapons-list');
    if (!list) return;
    
    const weaponId = `weapon-${++weaponCount}`;
    const weaponHTML = `
        <div class="weapon-item mb-3" id="${weaponId}">
            <div class="d-flex justify-content-between align-items-start">
                <h6>武器 ${weaponCount}</h6>
                <button type="button" class="btn btn-sm btn-danger" onclick="removeWeapon('${weaponId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="row">
                <div class="col-md-6 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="武器名" name="weapon_name_${weaponCount}">
                </div>
                <div class="col-md-6 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="使用技能" name="weapon_skill_${weaponCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="ダメージ" name="weapon_damage_${weaponCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="射程" name="weapon_range_${weaponCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <input type="number" class="form-control form-control-sm" placeholder="攻撃回数" name="weapon_attacks_${weaponCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <input type="number" class="form-control form-control-sm" placeholder="弾薬" name="weapon_ammo_${weaponCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <input type="number" class="form-control form-control-sm" placeholder="故障ナンバー" name="weapon_malfunction_${weaponCount}">
                </div>
            </div>
        </div>
    `;
    
    list.insertAdjacentHTML('beforeend', weaponHTML);
}

function removeWeapon(weaponId) {
    const weapon = document.getElementById(weaponId);
    if (weapon) {
        weapon.remove();
    }
}

function addArmor() {
    const list = document.getElementById('armor-list');
    if (!list) return;
    
    const armorId = `armor-${++armorCount}`;
    const armorHTML = `
        <div class="armor-item mb-3" id="${armorId}">
            <div class="d-flex justify-content-between align-items-start">
                <h6>防具 ${armorCount}</h6>
                <button type="button" class="btn btn-sm btn-danger" onclick="removeArmor('${armorId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="row">
                <div class="col-md-6 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="防具名" name="armor_name_${armorCount}">
                </div>
                <div class="col-md-3 mb-2">
                    <input type="number" class="form-control form-control-sm" placeholder="装甲値" name="armor_value_${armorCount}" min="0" onchange="calculateTotalArmor()">
                </div>
                <div class="col-md-3 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="部位" name="armor_location_${armorCount}">
                </div>
            </div>
        </div>
    `;
    
    list.insertAdjacentHTML('beforeend', armorHTML);
}

function removeArmor(armorId) {
    const armor = document.getElementById(armorId);
    if (armor) {
        armor.remove();
        calculateTotalArmor();
    }
}

function calculateTotalArmor() {
    let total = 0;
    document.querySelectorAll('[name^="armor_value_"]').forEach(input => {
        total += parseInt(input.value || '0');
    });
    updateValue('total-armor-value', total);
}

function addItem() {
    const list = document.getElementById('items-list');
    if (!list) return;
    
    const itemId = `item-${++itemCount}`;
    const category = document.getElementById('item-category-filter')?.value || 'other';
    
    const itemHTML = `
        <div class="item-entry mb-2" id="${itemId}" data-category="${category}">
            <div class="row align-items-center">
                <div class="col-md-4">
                    <input type="text" class="form-control form-control-sm" placeholder="アイテム名" name="item_name_${itemCount}">
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control form-control-sm" placeholder="数量" name="item_quantity_${itemCount}" min="1" value="1">
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control form-control-sm" placeholder="重量(kg)" name="item_weight_${itemCount}" min="0" step="0.1" onchange="calculateTotalWeight()">
                </div>
                <div class="col-md-3">
                    <input type="text" class="form-control form-control-sm" placeholder="メモ" name="item_memo_${itemCount}">
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-sm btn-danger" onclick="removeItem('${itemId}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    list.insertAdjacentHTML('beforeend', itemHTML);
}

function removeItem(itemId) {
    const item = document.getElementById(itemId);
    if (item) {
        item.remove();
        calculateTotalWeight();
    }
}

function calculateTotalWeight() {
    let totalWeight = 0;
    
    document.querySelectorAll('[name^="item_weight_"]').forEach((weightInput, index) => {
        const weight = parseFloat(weightInput.value || '0');
        const quantityInput = document.querySelector(`[name="item_quantity_${index + 1}"]`);
        const quantity = parseInt(quantityInput?.value || '1');
        totalWeight += weight * quantity;
    });
    
    updateValue('current-weight', totalWeight.toFixed(1));
    
    // 運搬能力チェック
    const carryCapacity = parseInt(document.getElementById('carry-capacity')?.textContent || '0');
    const penaltyDiv = document.getElementById('weight-penalty');
    
    if (penaltyDiv) {
        if (totalWeight > carryCapacity) {
            penaltyDiv.style.display = 'block';
        } else {
            penaltyDiv.style.display = 'none';
        }
    }
}

// ===========================
// 成長記録
// ===========================
function addSessionRecord() {
    const container = document.getElementById('session-records');
    if (!container) return;
    
    const recordId = `session-${++sessionRecordCount}`;
    const recordHTML = `
        <div class="session-record mb-3 p-3 border rounded" id="${recordId}">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <h6>セッション ${sessionRecordCount}</h6>
                <button type="button" class="btn btn-sm btn-danger" onclick="removeSessionRecord('${recordId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="row">
                <div class="col-md-6 mb-2">
                    <input type="date" class="form-control form-control-sm" name="session_date_${sessionRecordCount}">
                </div>
                <div class="col-md-6 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="シナリオ名" name="session_scenario_${sessionRecordCount}">
                </div>
                <div class="col-md-6 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="GM名" name="session_gm_${sessionRecordCount}">
                </div>
                <div class="col-md-6 mb-2">
                    <div class="input-group input-group-sm">
                        <span class="input-group-text">SAN</span>
                        <input type="number" class="form-control" placeholder="変化量" name="session_san_change_${sessionRecordCount}">
                    </div>
                </div>
                <div class="col-12">
                    <textarea class="form-control form-control-sm" rows="2" placeholder="メモ" name="session_memo_${sessionRecordCount}"></textarea>
                </div>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', recordHTML);
}

function removeSessionRecord(recordId) {
    const record = document.getElementById(recordId);
    if (record) {
        record.remove();
    }
}

function addGrowthRecord() {
    const container = document.getElementById('growth-records');
    if (!container) return;
    
    const recordId = `growth-${++growthRecordCount}`;
    const recordHTML = `
        <div class="growth-record mb-3 p-3 border rounded" id="${recordId}">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <h6>成長記録 ${growthRecordCount}</h6>
                <button type="button" class="btn btn-sm btn-danger" onclick="removeGrowthRecord('${recordId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="row">
                <div class="col-md-6 mb-2">
                    <input type="date" class="form-control form-control-sm" name="growth_date_${growthRecordCount}">
                </div>
                <div class="col-md-6 mb-2">
                    <input type="text" class="form-control form-control-sm" placeholder="スキル名" name="growth_skill_${growthRecordCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <input type="number" class="form-control form-control-sm" placeholder="成長前" name="growth_before_${growthRecordCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <input type="number" class="form-control form-control-sm" placeholder="成長後" name="growth_after_${growthRecordCount}">
                </div>
                <div class="col-md-4 mb-2">
                    <select class="form-select form-select-sm" name="growth_result_${growthRecordCount}">
                        <option value="success">成功</option>
                        <option value="failure">失敗</option>
                    </select>
                </div>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', recordHTML);
}

function removeGrowthRecord(recordId) {
    const record = document.getElementById(recordId);
    if (record) {
        record.remove();
    }
}

// ===========================
// CCFOLIA連携
// ===========================
function exportToCCFOLIA() {
    // TODO: CCFOLIA形式でのエクスポート実装
    showToast('CCFOLIA形式でのエクスポート機能は準備中です', 'info');
}

function generateCCFOLIACommands() {
    // TODO: CCFOLIAコマンド生成実装
    showToast('CCFOLIAコマンド生成機能は準備中です', 'info');
}

// ===========================
// フォームバリデーション
// ===========================
function initializeFormValidation() {
    const form = document.getElementById('character-form-6th');
    if (!form) return;
    
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        event.stopPropagation();
        
        if (form.checkValidity()) {
            // TODO: フォーム送信処理
            showToast('キャラクターシートを保存しました', 'success');
        } else {
            showToast('必須項目を入力してください', 'error');
        }
        
        form.classList.add('was-validated');
    });
    
    // リアルタイムバリデーション
    form.querySelectorAll('input[required], select[required]').forEach(element => {
        element.addEventListener('blur', function() {
            if (this.checkValidity()) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
            }
        });
    });
}

// ===========================
// 職業ポイント計算式リスナー
// ===========================
function initializeOccupationFormulaListener() {
    const formulaSelect = document.getElementById('occupation-formula');
    if (formulaSelect) {
        formulaSelect.addEventListener('change', function() {
            calculateSkillPoints();
        });
    }
}

// ===========================
// ユーティリティ関数
// ===========================
function showToast(message, type = 'info') {
    // Bootstrap toastを使用する場合
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toastHTML = `
        <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : type === 'success' ? 'success' : 'info'} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // 自動削除
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '11';
    document.body.appendChild(container);
    return container;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===========================
// グローバル関数として公開
// ===========================
window.toggleCustomDiceSettings = toggleCustomDiceSettings;
window.applyDicePreset = applyDicePreset;
window.rollSingleAbility = rollSingleAbility;
window.rollAllDice = rollAllDice;
window.updateSkillTotal = updateSkillTotal;
window.addCustomSkill = addCustomSkill;
window.removeCustomSkill = removeCustomSkill;
window.updateCustomSkillName = updateCustomSkillName;
window.addWeapon = addWeapon;
window.removeWeapon = removeWeapon;
window.addArmor = addArmor;
window.removeArmor = removeArmor;
window.calculateTotalArmor = calculateTotalArmor;
window.addItem = addItem;
window.removeItem = removeItem;
window.calculateTotalWeight = calculateTotalWeight;
window.addSessionRecord = addSessionRecord;
window.removeSessionRecord = removeSessionRecord;
window.addGrowthRecord = addGrowthRecord;
window.removeGrowthRecord = removeGrowthRecord;
window.setMainImage = setMainImage;
window.removeImage = removeImage;
window.viewImage = viewImage;
window.exportToCCFOLIA = exportToCCFOLIA;
window.generateCCFOLIACommands = generateCCFOLIACommands;