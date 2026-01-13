document.addEventListener('DOMContentLoaded', function() {

    
    const urlParams = new URLSearchParams(window.location.search);
    const editCharacterId = urlParams.get('id');
    const isEditMode = !!editCharacterId;

    const bodyEl = document.body;
    if (bodyEl) {
        bodyEl.classList.add('character-create-page');
    }

    const autosizeTextareas = () => {
        document.querySelectorAll('.autosize-textarea').forEach(textarea => {
            const resize = () => {
                textarea.style.height = 'auto';
                textarea.style.height = `${textarea.scrollHeight}px`;
            };
            if (!textarea.dataset.autosizeBound) {
                textarea.addEventListener('input', resize);
                textarea.dataset.autosizeBound = 'true';
            }
            resize();
        });
    };
    autosizeTextareas();

    const initTooltips = () => {
        if (!window.bootstrap?.Tooltip) return;
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            if (el.dataset.tooltipBound) return;
            new bootstrap.Tooltip(el);
            el.dataset.tooltipBound = 'true';
        });
    };
    initTooltips();

    const initTabs = () => {
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tabButton => {
            if (tabButton.dataset.tabBound) return;

            tabButton.addEventListener('click', event => {
                const bootstrapTab = window.bootstrap?.Tab;
                if (bootstrapTab) {
                    event.preventDefault();
                    event.stopPropagation();
                    try {
                        const instance = bootstrapTab.getOrCreateInstance
                            ? bootstrapTab.getOrCreateInstance(tabButton)
                            : new bootstrapTab(tabButton);
                        instance.show();
                        return;
                    } catch {}
                }

                event.preventDefault();

                const targetSelector = tabButton.getAttribute('data-bs-target');
                if (!targetSelector) return;

                const targetPane = document.querySelector(targetSelector);
                if (!targetPane) return;

                const tabList = tabButton.closest('[role="tablist"]') || tabButton.closest('.nav');
                const tabContent = targetPane.closest('.tab-content');

                if (tabList) {
                    tabList.querySelectorAll('[data-bs-toggle="tab"]').forEach(btn => {
                        btn.classList.remove('active');
                        btn.setAttribute('aria-selected', 'false');
                    });
                }

                if (tabContent) {
                    tabContent.querySelectorAll('.tab-pane').forEach(pane => {
                        pane.classList.remove('active', 'show');
                    });
                }

                tabButton.classList.add('active');
                tabButton.setAttribute('aria-selected', 'true');
                targetPane.classList.add('active', 'show');
            });

            tabButton.dataset.tabBound = 'true';
        });
    };
    initTabs();

    // 6th edition skill data
    const SKILLS_6TH = {
        combat: {
            dodge: { base: "DEX*2", name: "回避" },
            kick: { base: 25, name: "キック" },
            grapple: { base: 25, name: "組み付き" },
            fist_punch: { base: 50, name: "こぶし（パンチ）" },
            head_butt: { base: 10, name: "頭突き" },
            throw: { base: 25, name: "投擲" },
            martial_arts: { base: 1, name: "マーシャルアーツ" },
            handgun: { base: 20, name: "拳銃" },
            submachine_gun: { base: 15, name: "サブマシンガン" },
            shotgun: { base: 30, name: "ショットガン" },
            machine_gun: { base: 15, name: "マシンガン" },
            rifle: { base: 25, name: "ライフル" }
        },
        exploration: {
            first_aid: { base: 30, name: "応急手当" },
            locksmith: { base: 1, name: "鍵開け" },
            appraise: { base: 5, name: "鑑定" },
            conceal: { base: 15, name: "隠す" },
            hide: { base: 10, name: "隠れる" },
            listen: { base: 25, name: "聞き耳" },
            sneak: { base: 10, name: "忍び歩き" },
            photography: { base: 10, name: "写真術" },
            psychoanalysis: { base: 1, name: "精神分析" },
            track: { base: 10, name: "追跡" },
            climb: { base: 40, name: "登攀" },
            library_use: { base: 25, name: "図書館" },
            spot_hidden: { base: 25, name: "目星" }
        },
        action: {
            drive_auto: { base: 20, name: "運転" },
            mechanical_repair: { base: 20, name: "機械修理" },
            operate_heavy_machine: { base: 1, name: "重機械操作" },
            ride: { base: 5, name: "乗馬" },
            swim: { base: 25, name: "水泳" },
            craft: { base: 5, name: "製作" },
            pilot: { base: 1, name: "操縦" },
            jump: { base: 25, name: "跳躍" },
            electrical_repair: { base: 10, name: "電気修理" },
            navigate: { base: 10, name: "ナビゲート" },
            sleight_of_hand: { base: 10, name: "手さばき" },
            survival: { base: 10, name: "サバイバル" },
            disguise: { base: 1, name: "変装" }
        },
        social: {
            fast_talk: { base: 5, name: "言いくるめ" },
            charm: { base: 15, name: "魅惑" },
            credit_rating: { base: 15, name: "信用" },
            persuade: { base: 15, name: "説得" },
            bargain: { base: 5, name: "値切り" },
            intimidate: { base: 15, name: "威圧" },
            language_other: { base: 1, name: "他の言語" },
            language_own: { base: "EDU*5", name: "母国語" }
        },
        knowledge: {
            medicine: { base: 5, name: "医学" },
            occult: { base: 5, name: "オカルト" },
            chemistry: { base: 1, name: "化学" },
            cthulhu_mythos: { base: 0, name: "クトゥルフ神話" },
            art: { base: 5, name: "芸術" },
            accounting: { base: 10, name: "経理" },
            archaeology: { base: 1, name: "考古学" },
            computer_use: { base: 1, name: "コンピューター" },
            psychology: { base: 5, name: "心理学" },
            anthropology: { base: 1, name: "人類学" },
            biology: { base: 1, name: "生物学" },
            geology: { base: 1, name: "地質学" },
            electronics: { base: 1, name: "電子工学" },
            astronomy: { base: 1, name: "天文学" },
            natural_world: { base: 10, name: "博物学" },
            physics: { base: 1, name: "物理学" },
            law: { base: 5, name: "法律" },
            pharmacy: { base: 1, name: "薬学" },
            history: { base: 20, name: "歴史" }
        }
    };

    const SKILL_CATEGORY_KEYS = {
        combat: new Set(Object.keys(SKILLS_6TH.combat)),
        exploration: new Set(Object.keys(SKILLS_6TH.exploration)),
        action: new Set(Object.keys(SKILLS_6TH.action)),
        social: new Set(Object.keys(SKILLS_6TH.social)),
        knowledge: new Set(Object.keys(SKILLS_6TH.knowledge))
    };
    
    // Combined skills map (backward compatibility)
    const ALL_SKILLS_6TH = {
        ...SKILLS_6TH.combat,
        ...SKILLS_6TH.exploration,
        ...SKILLS_6TH.action,
        ...SKILLS_6TH.social,
        ...SKILLS_6TH.knowledge
    };
    const SKILL_NAME_TO_KEY = new Map(
        Object.entries(ALL_SKILLS_6TH)
            .map(([key, skill]) => [skill?.name, key])
            .filter(([name]) => !!name)
    );
    const CUSTOM_SKILL_CATEGORIES = ['combat', 'exploration', 'action', 'social', 'knowledge', 'all'];
    const CUSTOM_SKILL_DEFAULT_CATEGORY = 'knowledge';
    let customSkillCounter = 0;

    const ABILITIES_6TH = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
    const ABILITY_LABELS = {
        str: 'STR（筋力）',
        con: 'CON（体力）',
        pow: 'POW（精神力）',
        dex: 'DEX（敏捷性）',
        app: 'APP（外見）',
        siz: 'SIZ（体格）',
        int: 'INT（知性）',
        edu: 'EDU（教育）'
    };
    const DEFAULT_ABILITY_DICE_SETTINGS_6TH = {
        str: { count: 3, sides: 6, bonus: 0 },
        con: { count: 3, sides: 6, bonus: 0 },
        pow: { count: 3, sides: 6, bonus: 0 },
        dex: { count: 3, sides: 6, bonus: 0 },
        app: { count: 3, sides: 6, bonus: 0 },
        siz: { count: 2, sides: 6, bonus: 6 },
        int: { count: 2, sides: 6, bonus: 6 },
        edu: { count: 3, sides: 6, bonus: 3 }
    };
    let abilityDiceSettings = {};

function updateGlobalDiceFormula() {
        const count = parseInt(document.getElementById('globalDiceCount')?.value) || 3;
        const sides = parseInt(document.getElementById('globalDiceSides')?.value) || 6;
        const bonus = parseInt(document.getElementById('globalDiceBonus')?.value) || 0;
        
        const formula = `${count}d${sides}${bonus >= 0 ? '+' : ''}${bonus}`;
        const formulaSpan = document.getElementById('globalDiceFormula');
        if (formulaSpan) {
            formulaSpan.textContent = formula;
        }
        
        return { count, sides, bonus };
    }

    function formatDiceFormula(count, sides, bonus) {
        const sign = bonus >= 0 ? '+' : '';
        return `${count}d${sides}${sign}${bonus}`;
    }

    function parseDiceFormula(formula) {
        if (!formula) return null;
        const match = formula.trim().match(/^(\d+)\s*[dD]\s*(\d+)\s*([+-]\s*\d+)?$/);
        if (!match) return null;
        const count = parseInt(match[1], 10);
        const sides = parseInt(match[2], 10);
        const bonus = match[3] ? parseInt(match[3].replace(/\s+/g, ''), 10) : 0;
        if (!Number.isFinite(count) || !Number.isFinite(sides) || !Number.isFinite(bonus)) return null;
        if (count < 1 || count > 10) return null;
        if (sides < 2 || sides > 100) return null;
        if (bonus < -50 || bonus > 50) return null;
        return { count, sides, bonus };
    }

    function setAbilityDiceSettingsFromGlobal() {
        const globalSettings = updateGlobalDiceFormula();
        ABILITIES_6TH.forEach(ability => {
            abilityDiceSettings[ability] = { ...globalSettings };
        });
    }

    function setAbilityDiceSettingsToDefault6th() {
        abilityDiceSettings = Object.fromEntries(
            ABILITIES_6TH.map(ability => [
                ability,
                { ...(DEFAULT_ABILITY_DICE_SETTINGS_6TH[ability] ?? updateGlobalDiceFormula()) }
            ])
        );
    }

    function buildAbilityDiceSettingsHTML() {
        const container = document.getElementById('ability-dice-settings');
        if (!container) return;
        if (!Object.keys(abilityDiceSettings).length) {
            setAbilityDiceSettingsToDefault6th();
        }
        container.innerHTML = ABILITIES_6TH.map(ability => {
            const settings = abilityDiceSettings[ability];
            return `
                <div class="col-md-3 mb-3">
                    <div class="dice-setting-item border rounded p-2 h-100">
                        <h6 class="mb-2">${ABILITY_LABELS[ability]}</h6>
                        <div class="input-group input-group-sm mb-2">
                            <input type="number" class="form-control" id="ability-dice-count-${ability}" min="1" max="10" value="${settings.count}">
                            <span class="input-group-text">D</span>
                            <input type="number" class="form-control" id="ability-dice-sides-${ability}" min="2" max="100" value="${settings.sides}">
                            <span class="input-group-text">+</span>
                            <input type="number" class="form-control" id="ability-dice-bonus-${ability}" min="-50" max="50" value="${settings.bonus}">
                        </div>
                        <div class="input-group input-group-sm">
                            <span class="input-group-text">式</span>
                            <input type="text" class="form-control" id="ability-dice-formula-${ability}" value="${formatDiceFormula(settings.count, settings.sides, settings.bonus)}" placeholder="3d6+0">
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        attachAbilityDiceSettingListeners();
    }

    function attachAbilityDiceSettingListeners() {
        ABILITIES_6TH.forEach(ability => {
            const countInput = document.getElementById(`ability-dice-count-${ability}`);
            const sidesInput = document.getElementById(`ability-dice-sides-${ability}`);
            const bonusInput = document.getElementById(`ability-dice-bonus-${ability}`);
            const formulaInput = document.getElementById(`ability-dice-formula-${ability}`);

            const syncFormula = () => {
                const count = parseInt(countInput?.value, 10) || 1;
                const sides = parseInt(sidesInput?.value, 10) || 2;
                const bonus = parseInt(bonusInput?.value, 10) || 0;
                abilityDiceSettings[ability] = { count, sides, bonus };
                if (formulaInput) {
                    formulaInput.value = formatDiceFormula(count, sides, bonus);
                    formulaInput.classList.remove('is-invalid');
                }
            };

            countInput?.addEventListener('input', syncFormula);
            sidesInput?.addEventListener('input', syncFormula);
            bonusInput?.addEventListener('input', syncFormula);

            formulaInput?.addEventListener('change', () => {
                const parsed = parseDiceFormula(formulaInput.value);
                if (!parsed) {
                    formulaInput.classList.add('is-invalid');
                    return;
                }
                formulaInput.classList.remove('is-invalid');
                if (countInput) countInput.value = parsed.count;
                if (sidesInput) sidesInput.value = parsed.sides;
                if (bonusInput) bonusInput.value = parsed.bonus;
                abilityDiceSettings[ability] = parsed;
            });
        });
    }

    function isAbilityDiceEnabled() {
        const checkbox = document.getElementById('useAbilityDiceSettings');
        if (!checkbox) return true;
        return checkbox.checked;
    }

    function getDiceSettingsForAbility(ability) {
        if (isAbilityDiceEnabled() && abilityDiceSettings[ability]) {
            return abilityDiceSettings[ability];
        }
        return updateGlobalDiceFormula();
    }

    function rollSingleAbility(ability) {
        const settings = getDiceSettingsForAbility(ability);
        const result = rollDice(settings.count, settings.sides, settings.bonus);
        const input = document.getElementById(ability);
        if (input) {
            input.value = result;
            input.classList.add('dice-rolled');
            setTimeout(() => input.classList.remove('dice-rolled'), 1000);
        }
        calculateDerivedStats();
    }

    function initAbilityDiceSettings() {
        buildAbilityDiceSettingsHTML();
        document.getElementById('toggleAbilityDiceSettings')?.addEventListener('click', () => {
            const wrapper = document.getElementById('ability-dice-settings-wrapper');
            if (!wrapper) return;
            wrapper.style.display = wrapper.style.display === 'none' ? 'block' : 'none';
        });
        document.getElementById('resetAbilityDiceSettings')?.addEventListener('click', () => {
            setAbilityDiceSettingsToDefault6th();
            buildAbilityDiceSettingsHTML();
        });
        document.querySelectorAll('.ability-roll-btn').forEach(button => {
            button.addEventListener('click', () => {
                const ability = button.dataset.ability;
                if (ability) rollSingleAbility(ability);
            });
        });
    }

    // ダイスロール関数
    function rollDice(count, sides, bonus) {
        let total = 0;
        for (let i = 0; i < count; i++) {
            total += Math.floor(Math.random() * sides) + 1;
        }
        return total + bonus;
    }

    // 全能力値ロール
    function rollAllAbilities() {
        ABILITIES_6TH.forEach(abilityName => {
            const settings = getDiceSettingsForAbility(abilityName);
            const total = rollDice(settings.count, settings.sides, settings.bonus);
            const input = document.getElementById(abilityName);
            if (input) {
                input.value = total;
                
                // ダイスロールした入力欄を短時間ハイライト
                input.classList.add('dice-rolled');
                setTimeout(() => input.classList.remove('dice-rolled'), 1000);
            }
        });
        
        // Update derived values after rolling
        calculateDerivedStats();
    }

    // Derived stats auto calculation
    function calculateDerivedStats(options = {}) {
        const { setCurrentDefaults = !isEditMode } = options;
        const str = parseInt(document.getElementById('str')?.value) || 0;
        const con = parseInt(document.getElementById('con')?.value) || 0;
        const pow = parseInt(document.getElementById('pow')?.value) || 0;
        const dex = parseInt(document.getElementById('dex')?.value) || 0;
        const int = parseInt(document.getElementById('int')?.value) || 0;
        const edu = parseInt(document.getElementById('edu')?.value) || 0;
        const siz = parseInt(document.getElementById('siz')?.value) || 0;
        
        // 6th edition formulas (round up fractions)
        const hp = Math.ceil((con + siz) / 2);
        const mp = pow;  // MP = POW
        const san = pow * 5;  // SAN = POW *5
        
        if (document.getElementById('hp')) document.getElementById('hp').value = hp;
        if (document.getElementById('mp')) document.getElementById('mp').value = mp;
        if (document.getElementById('san')) document.getElementById('san').value = san;
        
        // Set current values as starting defaults
        const currentHpEl = document.getElementById('current_hp');
        const currentMpEl = document.getElementById('current_mp');
        const currentSanEl = document.getElementById('current_san');
        if (currentHpEl && (setCurrentDefaults || currentHpEl.value === '')) currentHpEl.value = hp;
        if (currentMpEl && (setCurrentDefaults || currentMpEl.value === '')) currentMpEl.value = mp;
        if (currentSanEl && (setCurrentDefaults || currentSanEl.value === '')) currentSanEl.value = san;
        
        if (document.getElementById('sanity_max')) document.getElementById('sanity_max').value = san;
        
        const updateDisplay = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };
        updateDisplay('hp_display', hp);
        updateDisplay('mp_display', mp);
        updateDisplay('san_display', san);
        
        // 6th edition specific derived calculations
        calculateDerivedStats6th(str, con, pow, dex, int, edu, siz);
        
        // Recalculate skill points after ability changes
        calculateSkillPoints();
        
        // Refresh dynamic skill bases (DEX/EDU dependent)
        updateDynamicSkillBases();
    }

    // Derived stats specific to 6th edition
    function calculateDerivedStats6th(str, con, pow, dex, int, edu, siz) {
        // アイデア = INT*5
        if (document.getElementById('idea')) {
            document.getElementById('idea').value = int * 5;
        }
        // 幸運 = POW*5
        if (document.getElementById('luck')) {
            document.getElementById('luck').value = pow * 5;
        }
        // 知識 = EDU*5
        if (document.getElementById('know')) {
            document.getElementById('know').value = edu * 5;
        }

        const setDisplay = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };
        setDisplay('idea_display', int * 5);
        setDisplay('luck_display', pow * 5);
        setDisplay('know_display', edu * 5);

        // ダメージボーナス（6版表に準拠）
        const total = str + siz;
        let damageBonus;
        if (total <= 12) damageBonus = "-1d4";
        else if (total <= 16) damageBonus = "-1d2";
        else if (total <= 24) damageBonus = "+0";
        else if (total <= 32) damageBonus = "+1d4";
        else if (total <= 40) damageBonus = "+1d6";
        else damageBonus = "+2d6";

        const damageBonusDisplay = (damageBonus || '').toUpperCase();
        if (document.getElementById('damage-bonus')) {
            document.getElementById('damage-bonus').value = damageBonusDisplay;
        }
        const damageDisplayEl = document.getElementById('damage_bonus_display');
        if (damageDisplayEl) {
            damageDisplayEl.textContent = damageBonusDisplay;
        }
    }

    // Occupation skill points calculation
    function calculateOccupationSkillPoints(method) {
        const str = parseInt(document.getElementById('str')?.value) || 0;
        const con = parseInt(document.getElementById('con')?.value) || 0;
        const pow = parseInt(document.getElementById('pow')?.value) || 0;
        const dex = parseInt(document.getElementById('dex')?.value) || 0;
        const app = parseInt(document.getElementById('app')?.value) || 0;
        const siz = parseInt(document.getElementById('siz')?.value) || 0;
        const edu = parseInt(document.getElementById('edu')?.value) || 0;

        const calculationMethods = {
            edu20: edu * 20,
            edu10app10: edu * 10 + app * 10,
            edu10dex10: edu * 10 + dex * 10,
            edu10pow10: edu * 10 + pow * 10,
            edu10str10: edu * 10 + str * 10,
            edu10con10: edu * 10 + con * 10,
            edu10siz10: edu * 10 + siz * 10,
        };

        return calculationMethods[method] ?? edu * 20;
    }

    // Total skill points calculation
    function calculateSkillPoints() {
        const intVal = parseInt(document.getElementById('int')?.value) || 0;
        const method = document.getElementById('occupationMethod')?.value || 'edu20';

        const occupationPoints = calculateOccupationSkillPoints(method);
        const interestPoints = intVal * 10;

        const occupationTotalEl = document.getElementById('occupationTotal');
        if (occupationTotalEl) occupationTotalEl.value = occupationPoints;

        const occupationPointsDisplay = document.getElementById('occupation_points_display');
        if (occupationPointsDisplay) occupationPointsDisplay.textContent = occupationPoints;

        const interestTotalEl = document.getElementById('interestTotal');
        if (interestTotalEl) interestTotalEl.value = interestPoints;
    }

    // Skill item HTML generation
    function createSkillItemHTML(key, skill, category = 'all', options = {}) {
        const { isCustom = false, displayName = null, baseValueOverride = null } = options;
        const skillName = displayName || skill?.name || key;
        let baseValue = baseValueOverride;

        if (typeof baseValue !== 'number') {
            baseValue = skill?.base ?? 0;
        }

        if (!isCustom && typeof baseValue === 'string') {
            if (baseValue === 'DEX*2') {
                const dex = parseInt(document.getElementById('dex')?.value) || 0;
                baseValue = dex * 2;
            } else if (baseValue === 'EDU*5') {
                const edu = parseInt(document.getElementById('edu')?.value) || 0;
                baseValue = edu * 5;
            }
        }
        baseValue = Math.min(parseInt(baseValue, 10) || 0, 999);

        const customClass = isCustom ? ' custom-skill' : '';
        const nameMarkup = isCustom
            ? `<input type="text" class="form-control form-control-sm custom-skill-name" value="${skillName}" data-skill="${key}">`
            : `<label for="base_${key}" class="form-label small fw-bold mb-0 skill-name" title="${skillName}">${skillName}</label>`;
        const deleteButton = isCustom
            ? `<button type="button" class="btn btn-outline-danger btn-sm custom-skill-remove" data-skill="${key}" aria-label="削除"><i class="fas fa-times"></i></button>`
            : '';

        return `
            <div class="col-6 col-sm-6 col-md-4 col-lg-3 col-xl-2${customClass}">
                <div class="skill-item border rounded p-1">
                    <div class="d-flex justify-content-between align-items-center skill-item-header">
                        <div class="d-flex align-items-center gap-1 skill-item-title">
                            ${nameMarkup}
                            <span class="badge bg-info text-dark recommended-badge d-none">推奨</span>
                            <span class="badge bg-warning text-dark occupation-badge d-none">職業</span>
                        </div>
                        <div class="d-flex align-items-center gap-1 skill-item-actions">
                            ${deleteButton}
                            <span class="badge skill-total" id="total_${key}">${baseValue}%</span>
                        </div>
                    </div>
                    
                    <div class="row g-1 mt-1">
                        <div class="col-6 col-lg-3">
                            <div class="input-group input-group-sm skill-input-group skill-input-group-base" data-skill-kind="初" title="初期値">
                                <input type="number" class="form-control form-control-sm text-center skill-base"
                                       id="base_${key}" value="${baseValue}" min="0" max="999"
                                       data-skill="${key}" data-default="${skill?.base ?? 0}"
                                       aria-label="${skillName} 初期値"
                                       title="Base value (left click to edit, right click to reset)"
                                       data-bs-toggle="tooltip"
                                       data-bs-placement="top">
                            </div>
                        </div>
                        <div class="col-6 col-lg-3">
                            <div class="input-group input-group-sm skill-input-group skill-input-group-occ" data-skill-kind="職" title="職業">
                                <input type="number" class="form-control form-control-sm occupation-skill text-center"
                                       id="occ_${key}" min="0" max="999" value="0"
                                       data-skill="${key}" aria-label="${skillName} 職業" title="職業技能">
                            </div>
                        </div>
                        <div class="col-6 col-lg-3">
                            <div class="input-group input-group-sm skill-input-group skill-input-group-int" data-skill-kind="趣" title="趣味">
                                <input type="number" class="form-control form-control-sm interest-skill text-center"
                                       id="int_${key}" min="0" max="999" value="0"
                                       data-skill="${key}" aria-label="${skillName} 趣味" title="趣味技能">
                            </div>
                        </div>
                        <div class="col-6 col-lg-3">
                            <div class="input-group input-group-sm skill-input-group skill-input-group-other" data-skill-kind="他" title="その他">
                                <input type="number" class="form-control form-control-sm other-skill text-center"
                                       id="other_${key}" min="0" max="999" value="0"
                                       data-skill="${key}" aria-label="${skillName} その他" title="その他">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function createCustomSkillItemHTML(skillName, category) {
        return createSkillItemHTML('custom_preview', { name: skillName, base: 0 }, category, {
            isCustom: true,
            displayName: skillName,
            baseValueOverride: 0
        });
    }

    function createAddCustomSkillButton(category) {
        return `
            <div class="col-12 text-center mt-2 custom-skill-button" data-custom-skill-category="${category}">
                <button type="button" class="btn btn-outline-primary btn-sm" data-custom-skill-category="${category}">
                    <i class="fas fa-plus"></i> カスタム技能を追加
                </button>
            </div>
        `;
    }

    function buildSkillCardElement(key, skill, category, options = {}) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = createSkillItemHTML(key, skill, category, options);
        return wrapper.firstElementChild;
    }

    function registerSkillCard({ key, category, card, skillName = '' }) {
        card.dataset.category = category;
        card.dataset.skillKey = key;
        if (skillName) {
            card.dataset.skillName = skillName;
        }
        skillCards.push({ key, category, card });
        skillCardByKey.set(key, card);
    }

    function getSkillDisplayName(key, card) {
        const input = card.querySelector('.custom-skill-name');
        const fromInput = input?.value?.trim();
        if (fromInput) return fromInput;
        const fromDataset = card.dataset.skillName;
        if (fromDataset) return fromDataset;
        return ALL_SKILLS_6TH[key]?.name || key;
    }

    function bindSkillCardEvents(card) {
        card.querySelectorAll('.occupation-skill, .interest-skill, .other-skill').forEach(input => {
            input.addEventListener('input', updateSkillTotals);
        });

        card.querySelectorAll('.skill-base').forEach(input => {
            input.addEventListener('input', function() {
                try {
                    const skillKey = this.dataset.skill;
                    const value = Math.min(parseInt(this.value, 10) || 0, 999);
                    this.value = value;

                    if (!window.customBaseValues) {
                        window.customBaseValues = {};
                    }
                    window.customBaseValues[skillKey] = value;

                    this.classList.add('customized');
                    updateSkillTotals();
                } catch (error) {
                    console.error('Error in skill base input handler:', error);
                }
            });

            input.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                try {
                    const skillKey = this.dataset.skill;

                    if (window.customBaseValues && window.customBaseValues[skillKey] !== undefined) {
                        delete window.customBaseValues[skillKey];
                    }

                    const skill = ALL_SKILLS_6TH[skillKey];
                    if (!skill) {
                        return;
                    }

                    let baseValue = skill.base;
                    if (typeof baseValue === 'string') {
                        if (baseValue === 'DEX*2') {
                            const dex = parseInt(document.getElementById('dex')?.value) || 0;
                            baseValue = dex * 2;
                        } else if (baseValue === 'EDU*5') {
                            const edu = parseInt(document.getElementById('edu')?.value) || 0;
                            baseValue = edu * 5;
                        }
                    }

                    this.value = baseValue;
                    this.classList.remove('customized');
                    updateSkillTotals();
                    this.style.backgroundColor = '#d4edda';
                    setTimeout(() => {
                        this.style.backgroundColor = '';
                    }, 300);
                } catch (error) {
                    console.error('Error in skill base reset handler:', error);
                }
            });
        });

        const nameInput = card.querySelector('.custom-skill-name');
        if (nameInput) {
            nameInput.addEventListener('input', function() {
                updateCustomSkillName(this);
            });
        }

        const removeButton = card.querySelector('.custom-skill-remove');
        if (removeButton) {
            removeButton.addEventListener('click', function() {
                removeCustomSkill(this.dataset.skill || this);
            });
        }
    }

    // 保持用: 生成した技能カードDOM
    let skillCards = [];
    const skillCardByKey = new Map();
    let skillTabContainers = null;
    let recommendedSkillKeys = new Set();
    let occupationSkillKeys = new Set();
    let userTouchedRecommended = false;
    let userTouchedOccupation = false;

    // Skill list generation (single source, moved per tab)
    function generateSkillsList() {
        const containers = {
            combat: document.getElementById('combatSkills'),
            exploration: document.getElementById('explorationSkills'),
            action: document.getElementById('actionSkills'),
            social: document.getElementById('socialSkills'),
            knowledge: document.getElementById('knowledgeSkills'),
            all: document.getElementById('allSkills'),
            occupationSkill: document.getElementById('occupationSkillSkills'),
            recommended: document.getElementById('recommendedSkills'),
            allocated: document.getElementById('allocatedSkills')
        };
        skillTabContainers = containers;
        // Build cards once
        skillCards = [];
        skillCardByKey.clear();
        Object.entries(SKILLS_6TH).forEach(([category, skills]) => {
            Object.entries(skills).forEach(([key, skill]) => {
                const card = buildSkillCardElement(key, skill, category);
                registerSkillCard({ key, category, card, skillName: skill?.name || key });
            });
        });

        // Render all skills first soイベントが全カードに紐付く
        renderSkillTab('all', containers);

        // Tab switching: move cards into the active tab container
        document.querySelectorAll('#skillTabs button').forEach(btn => {
            btn.addEventListener('shown.bs.tab', function () {
                const targetId = this.getAttribute('data-bs-target')?.replace('#', '') || 'combat';
                renderSkillTab(targetId, containers);
            });
        });
    }

    function renderSkillTab(category, containers) {
        const validCategories = ['combat', 'exploration', 'action', 'social', 'knowledge', 'all', 'occupationSkill', 'recommended', 'allocated'];
        const targetCategory = validCategories.includes(category) ? category : 'combat';

        // Clear all containers
        Object.values(containers).forEach(c => {
            if (c) c.innerHTML = '';
        });

        // Select destination container
        const dest = containers[targetCategory];
        if (!dest) return;

        let appended = 0;
        // Append matching cards
        skillCards.forEach(({ key, category: cardCategory, card }) => {
            const isRecommended = recommendedSkillKeys.has(key);
            const isOccupationSkill = occupationSkillKeys.has(key);
            const isCustomSkill = key.startsWith('custom_');
            const categorySet = SKILL_CATEGORY_KEYS[targetCategory];
            const isAllocated = targetCategory === 'allocated'
                && ((parseInt(card.querySelector('.occupation-skill')?.value, 10) || 0) > 0
                    || (parseInt(card.querySelector('.interest-skill')?.value, 10) || 0) > 0
                    || (parseInt(card.querySelector('.other-skill')?.value, 10) || 0) > 0);
            const shouldShow = targetCategory === 'all'
                || (targetCategory === 'allocated' && isAllocated)
                || (targetCategory === 'occupationSkill' && isOccupationSkill)
                || (targetCategory === 'recommended' && isRecommended)
                || (isCustomSkill && cardCategory === targetCategory)
                || (categorySet ? categorySet.has(key) : targetCategory === cardCategory);

            if (shouldShow) {
                dest.appendChild(card);
                appended += 1;
            }
        });

        if (CUSTOM_SKILL_CATEGORIES.includes(targetCategory)) {
            appendCustomSkillButton(dest, targetCategory);
        }

        if (targetCategory === 'recommended' && appended === 0) {
            dest.innerHTML = `
                <div class="col-12 text-center text-muted p-4">
                    <i class="fas fa-star fa-2x mb-2"></i>
                    <p class="mb-0">推奨技能が未設定です。上の入力欄から追加してください。</p>
                </div>
            `;
        }

        if (targetCategory === 'occupationSkill' && appended === 0) {
            dest.innerHTML = `
                <div class="col-12 text-center text-muted p-4">
                    <i class="fas fa-briefcase fa-2x mb-2"></i>
                    <p class="mb-0">職業技能が未設定です。上の入力欄か職業テンプレートから追加してください。</p>
                </div>
            `;
        }

        if (targetCategory === 'allocated' && appended === 0) {
            dest.innerHTML = `
                <div class="col-12 text-center text-muted p-3" id="noAllocatedMessage">
                    <i class="fas fa-info-circle fa-lg mb-1"></i>
                    <p class="mb-0 small">まだポイントを振り分けた技能がありません。</p>
                </div>
            `;
        }

        initTooltips();
    }

    function appendCustomSkillButton(container, category) {
        if (!container) return;
        const wrapper = document.createElement('div');
        wrapper.innerHTML = createAddCustomSkillButton(category);
        const buttonWrapper = wrapper.firstElementChild;
        if (!buttonWrapper) return;
        const button = buttonWrapper.querySelector('button');
        if (button) {
            button.addEventListener('click', () => addCustomSkill(category));
        }
        container.appendChild(buttonWrapper);
    }

    function addCustomSkill(category, options = {}) {
        const targetCategory = category === 'all' ? CUSTOM_SKILL_DEFAULT_CATEGORY : category;
        customSkillCounter += 1;
        const defaultName = `カスタム技能${customSkillCounter}`;
        const skillName = (options.name || defaultName).trim() || defaultName;
        const baseValue = Math.min(parseInt(options.baseValue, 10) || 0, 999);
        const occupationPoints = Math.min(parseInt(options.occupationPoints, 10) || 0, 999);
        const interestPoints = Math.min(parseInt(options.interestPoints, 10) || 0, 999);
        const otherPoints = Math.min(parseInt(options.otherPoints, 10) || 0, 999);

        const skillKey = `custom_${Date.now()}_${customSkillCounter}`;
        const card = buildSkillCardElement(
            skillKey,
            { name: skillName, base: baseValue },
            targetCategory,
            { isCustom: true, displayName: skillName, baseValueOverride: baseValue }
        );

        registerSkillCard({ key: skillKey, category: targetCategory, card, skillName });
        bindSkillCardEvents(card);

        const baseInput = card.querySelector('.skill-base');
        if (baseInput) {
            baseInput.value = baseValue;
            baseInput.classList.add('customized');
        }
        const occInput = card.querySelector('.occupation-skill');
        if (occInput) occInput.value = occupationPoints;
        const intInput = card.querySelector('.interest-skill');
        if (intInput) intInput.value = interestPoints;
        const otherInput = card.querySelector('.other-skill');
        if (otherInput) otherInput.value = otherPoints;

        if (options.render !== false) {
            refreshActiveSkillTab();
            updateSkillTotals();
        }

        return card;
    }

    function removeCustomSkill(target) {
        let card = null;
        let skillKey = null;

        if (typeof target === 'string') {
            skillKey = target;
            card = skillCardByKey.get(skillKey);
        } else if (target instanceof Element) {
            card = target.closest('.custom-skill') || target.closest('[data-skill-key]');
            skillKey = target.dataset?.skill || card?.dataset?.skillKey || null;
        }

        if (!card) return;
        if (!skillKey) skillKey = card.dataset?.skillKey || null;
        if (!skillKey) return;

        skillCards = skillCards.filter(entry => entry.key !== skillKey);
        skillCardByKey.delete(skillKey);
        card.remove();
        updateSkillTotals();
    }

    function updateCustomSkillName(input) {
        const card = input.closest('.custom-skill');
        if (!card) return;
        const nextName = input.value.trim();
        if (nextName) {
            card.dataset.skillName = nextName;
        } else {
            card.dataset.skillName = 'カスタム技能';
        }
        updateSkillTotals();
    }

    function setRecommendedSkills(skillKeys, options = {}) {
        const { mode = 'replace', persist = false } = options;
        const normalized = Array.isArray(skillKeys) ? skillKeys.filter(Boolean) : [];
        const nextKeys = mode === 'merge'
            ? new Set([...recommendedSkillKeys, ...normalized])
            : new Set(normalized);
        recommendedSkillKeys = nextKeys;

        skillCards.forEach(({ key, card }) => {
            const isRecommended = recommendedSkillKeys.has(key);
            card.classList.toggle('skill-recommended', isRecommended);
            const badge = card.querySelector('.recommended-badge');
            if (badge) {
                badge.classList.toggle('d-none', !isRecommended);
            }
        });

        if (skillCardByKey.size > 0) {
            const missing = Array.from(recommendedSkillKeys).filter(key => !skillCardByKey.has(key));
            if (missing.length > 0) {
                console.warn('Unknown recommended skills:', missing);
            }
        }

        renderRecommendedChips();
        if (getActiveSkillTabCategory() === 'recommended') {
            refreshActiveSkillTab();
        }
        if (persist) persistCustomRecommendedSkills();
    }

    function setOccupationSkills(skillKeys, options = {}) {
        const { mode = 'replace', persist = false } = options;
        const normalized = Array.isArray(skillKeys) ? skillKeys.filter(Boolean) : [];
        const nextKeys = mode === 'merge'
            ? new Set([...occupationSkillKeys, ...normalized])
            : new Set(normalized);
        occupationSkillKeys = nextKeys;

        skillCards.forEach(({ key, card }) => {
            const isOccupation = occupationSkillKeys.has(key);
            card.classList.toggle('skill-occupation', isOccupation);
            const badge = card.querySelector('.occupation-badge');
            if (badge) {
                badge.classList.toggle('d-none', !isOccupation);
            }
        });

        if (skillCardByKey.size > 0) {
            const missing = Array.from(occupationSkillKeys).filter(key => !skillCardByKey.has(key));
            if (missing.length > 0) {
                console.warn('Unknown occupation skills:', missing);
            }
        }

        renderOccupationChips();
        if (getActiveSkillTabCategory() === 'occupationSkill') {
            refreshActiveSkillTab();
        }
        if (persist) persistCustomOccupationSkills();
    }

    function safeGetLocalStorage(key) {
        try {
            return localStorage.getItem(key);
        } catch (_) {
            return null;
        }
    }

    function safeSetLocalStorage(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (_) {
            // Ignore storage errors
        }
    }

    function parseSkillList(raw) {
        if (!raw) return [];
        if (Array.isArray(raw)) return raw;
        if (typeof raw !== 'string') return [];
        const trimmed = raw.trim();
        if (!trimmed) return [];
        try {
            const parsed = JSON.parse(trimmed);
            if (Array.isArray(parsed)) return parsed;
        } catch (_) {
            // fall through to delimiter parsing
        }
        return trimmed.split(/[\n,、]+/).map(item => item.trim()).filter(Boolean);
    }

    function resolveSkillKey(value) {
        if (!value) return null;
        const trimmed = value.trim();
        if (!trimmed) return null;
        if (ALL_SKILLS_6TH[trimmed]) return trimmed;
        const lower = trimmed.toLowerCase();
        if (ALL_SKILLS_6TH[lower]) return lower;
        return SKILL_NAME_TO_KEY.get(trimmed) || null;
    }

    function resolveSkillKeys(values) {
        const resolved = [];
        const unknown = [];
        (values || []).forEach(value => {
            const key = resolveSkillKey(value);
            if (key) {
                resolved.push(key);
            } else {
                unknown.push(value);
            }
        });
        return { resolved: Array.from(new Set(resolved)), unknown };
    }

    function buildRecommendedSkillOptions() {
        const datalist = document.getElementById('recommendedSkillOptions');
        if (!datalist) return;
        datalist.innerHTML = '';
        Object.values(ALL_SKILLS_6TH).forEach(skill => {
            if (!skill?.name) return;
            const option = document.createElement('option');
            option.value = skill.name;
            datalist.appendChild(option);
        });
    }

    function buildOccupationSkillOptions() {
        const datalist = document.getElementById('occupationSkillOptions');
        if (!datalist) return;
        datalist.innerHTML = '';
        Object.values(ALL_SKILLS_6TH).forEach(skill => {
            if (!skill?.name) return;
            const option = document.createElement('option');
            option.value = skill.name;
            datalist.appendChild(option);
        });
    }

    function renderRecommendedChips() {
        const container = document.getElementById('recommendedSkillsChips');
        if (!container) return;

        if (recommendedSkillKeys.size === 0) {
            container.innerHTML = '<span class="text-muted">推奨技能はまだ設定されていません。</span>';
            return;
        }

        container.innerHTML = '';
        const fragment = document.createDocumentFragment();
        Array.from(recommendedSkillKeys).forEach(key => {
            const name = ALL_SKILLS_6TH[key]?.name || key;
            const badge = document.createElement('span');
            badge.className = 'badge bg-info text-dark me-1 mb-1 recommended-chip';
            badge.dataset.skill = key;
            badge.textContent = name;

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-link btn-sm p-0 ms-1 text-dark remove-recommended-skill';
            removeBtn.setAttribute('aria-label', '削除');
            removeBtn.dataset.skill = key;
            removeBtn.innerHTML = '&times;';
            badge.appendChild(removeBtn);

            fragment.appendChild(badge);
        });

        container.appendChild(fragment);

        container.querySelectorAll('.remove-recommended-skill').forEach(button => {
            button.addEventListener('click', () => {
                const skillKey = button.dataset.skill;
                if (!skillKey) return;
                userTouchedRecommended = true;
                const next = Array.from(recommendedSkillKeys).filter(key => key !== skillKey);
                setRecommendedSkills(next, { persist: true });
            });
        });
    }

    function renderOccupationChips() {
        const container = document.getElementById('occupationSkillsChips');
        if (!container) return;

        if (occupationSkillKeys.size === 0) {
            container.innerHTML = '<span class="text-muted">職業技能はまだ設定されていません。</span>';
            return;
        }

        container.innerHTML = '';
        const fragment = document.createDocumentFragment();
        Array.from(occupationSkillKeys).forEach(key => {
            const name = ALL_SKILLS_6TH[key]?.name || key;
            const badge = document.createElement('span');
            badge.className = 'badge bg-warning text-dark me-1 mb-1 occupation-chip';
            badge.dataset.skill = key;
            badge.textContent = name;

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-link btn-sm p-0 ms-1 text-dark remove-occupation-skill';
            removeBtn.setAttribute('aria-label', '削除');
            removeBtn.dataset.skill = key;
            removeBtn.innerHTML = '&times;';
            badge.appendChild(removeBtn);

            fragment.appendChild(badge);
        });

        container.appendChild(fragment);

        container.querySelectorAll('.remove-occupation-skill').forEach(button => {
            button.addEventListener('click', () => {
                const skillKey = button.dataset.skill;
                if (!skillKey) return;
                userTouchedOccupation = true;
                const next = Array.from(occupationSkillKeys).filter(key => key !== skillKey);
                setOccupationSkills(next, { persist: true });
            });
        });
    }

    function getActiveSkillTabCategory() {
        const activeTab = document.querySelector('#skillTabs .nav-link.active');
        const target = activeTab?.getAttribute('data-bs-target')?.replace('#', '');
        return target || 'combat';
    }

    function refreshActiveSkillTab() {
        if (!skillTabContainers) return;
        const activeCategory = getActiveSkillTabCategory();
        renderSkillTab(activeCategory, skillTabContainers);
    }

    function persistCustomRecommendedSkills() {
        safeSetLocalStorage('custom_recommended_skills', JSON.stringify(Array.from(recommendedSkillKeys)));
    }

    function persistCustomOccupationSkills() {
        safeSetLocalStorage('custom_occupation_skills', JSON.stringify(Array.from(occupationSkillKeys)));
    }

    function loadCustomRecommendedSkills() {
        const stored = safeGetLocalStorage('custom_recommended_skills');
        if (!stored) return [];
        try {
            const parsed = JSON.parse(stored);
            return Array.isArray(parsed) ? parsed : [];
        } catch (_) {
            return parseSkillList(stored);
        }
    }

    function getScenarioRecommendedSkillPayload() {
        const params = new URLSearchParams(window.location.search);
        const rawFromQuery = params.get('recommended_skills') || params.get('scenario_recommended_skills');
        const titleFromQuery = params.get('scenario_title');
        const idFromQuery = params.get('scenario_id');
        const systemFromQuery = params.get('game_system') || params.get('scenario_game_system');
        const rawFromStorage = safeGetLocalStorage('scenario_recommended_skills');
        const titleFromStorage = safeGetLocalStorage('scenario_recommended_skills_title');
        const idFromStorage = safeGetLocalStorage('scenario_recommended_skills_id');
        const systemFromStorage = safeGetLocalStorage('scenario_recommended_skills_system');
        const hasQueryScenario = !!(rawFromQuery || idFromQuery || titleFromQuery || systemFromQuery);
        const hasStorageScenario = !!(rawFromStorage || idFromStorage || titleFromStorage || systemFromStorage);
        return {
            raw: rawFromQuery || rawFromStorage || '',
            title: titleFromQuery || titleFromStorage || '',
            source: hasQueryScenario ? 'query' : (hasStorageScenario ? 'storage' : ''),
            scenarioId: idFromQuery || idFromStorage || '',
            gameSystem: systemFromQuery || systemFromStorage || ''
        };
    }

    function persistScenarioRecommendedSkills(payload) {
        if (!payload) return;
        if (payload.scenarioId) {
            safeSetLocalStorage('scenario_recommended_skills_id', String(payload.scenarioId));
        }
        safeSetLocalStorage('scenario_recommended_skills', payload.raw || '');
        safeSetLocalStorage('scenario_recommended_skills_title', payload.title || '');
        safeSetLocalStorage('scenario_recommended_skills_system', payload.gameSystem || '');
    }

    async function fetchScenarioPayload(scenarioId) {
        const numericId = parseInt(scenarioId, 10);
        if (!Number.isFinite(numericId) || numericId <= 0) return null;
        try {
            const response = await axios.get(`/api/scenarios/scenarios/${numericId}/`, {
                timeout: 8000
            });
            return response.data;
        } catch (error) {
            console.warn('Failed to load scenario details:', error);
            return null;
        }
    }

    async function fetchNextSessionContext(sessionId) {
        try {
            const params = new URLSearchParams();
            if (sessionId) {
                params.set('session_id', sessionId);
            }
            const url = params.toString()
                ? `/api/schedules/sessions/next-context/?${params.toString()}`
                : '/api/schedules/sessions/next-context/';
            const response = await axios.get(url, {
                timeout: 8000
            });
            return response.data;
        } catch (error) {
            console.warn('Failed to load next session context:', error);
            return null;
        }
    }

    function loadCustomOccupationSkills() {
        const stored = safeGetLocalStorage('custom_occupation_skills');
        if (!stored) return [];
        try {
            const parsed = JSON.parse(stored);
            return Array.isArray(parsed) ? parsed : [];
        } catch (_) {
            return parseSkillList(stored);
        }
    }

    async function fetchParticipatingScenarios({ days = 365, limit = 50 } = {}) {
        try {
            const params = new URLSearchParams();
            if (Number.isFinite(days)) params.set('days', String(days));
            if (Number.isFinite(limit)) params.set('limit', String(limit));
            const url = params.toString()
                ? `/api/schedules/sessions/participating-scenarios/?${params.toString()}`
                : '/api/schedules/sessions/participating-scenarios/';
            const response = await axios.get(url, { timeout: 8000 });
            return response.data;
        } catch (error) {
            console.warn('Failed to load participating scenarios:', error);
            return null;
        }
    }

    function initOccupationSkillControls() {
        const input = document.getElementById('occupationSkillInput');
        const addBtn = document.getElementById('addOccupationSkill');
        const clearBtn = document.getElementById('clearOccupationSkills');

        if (!input) return;

        buildOccupationSkillOptions();

        const stored = loadCustomOccupationSkills();
        if (stored.length > 0) {
            setOccupationSkills(stored, { persist: false });
        } else {
            setOccupationSkills([], { persist: false });
        }

        const addFromInput = () => {
            const rawValue = input.value;
            const parsed = resolveSkillKeys(parseSkillList(rawValue));
            if (parsed.resolved.length === 0) {
                alert('技能が見つかりません。名称またはキーを確認してください。');
                return;
            }
            userTouchedOccupation = true;
            setOccupationSkills(parsed.resolved, { mode: 'merge', persist: true });
            input.value = '';
            if (parsed.unknown.length > 0) {
                alert(`未対応の技能: ${parsed.unknown.join(', ')}`);
            }
        };

        addBtn?.addEventListener('click', addFromInput);
        input.addEventListener('keydown', event => {
            if (event.key === 'Enter') {
                event.preventDefault();
                addFromInput();
            }
        });

        clearBtn?.addEventListener('click', () => {
            userTouchedOccupation = true;
            setOccupationSkills([], { persist: true });
        });
    }

    async function initRecommendedSkillControls() {
        const input = document.getElementById('recommendedSkillInput');
        const addBtn = document.getElementById('addRecommendedSkill');
        const clearBtn = document.getElementById('clearRecommendedSkills');
        const scenarioBtn = document.getElementById('loadScenarioRecommended');
        const selectScenarioBtn = document.getElementById('selectScenarioRecommended');
        const scenarioSelectModalEl = document.getElementById('scenarioSelectModal');
        const scenarioSelectListEl = document.getElementById('scenarioSelectList');
        const scenarioSelectStatusEl = document.getElementById('scenarioSelectStatus');
        const scenarioSelectReloadBtn = document.getElementById('scenarioSelectReload');
        const retryBtn = document.getElementById('retryScenarioRecommended');
        const hintEl = document.getElementById('scenarioRecommendedHint');
        const sessionParams = new URLSearchParams(window.location.search);
        const sessionIdFromQuery = sessionParams.get('session_id');

        if (!input) return;

        // Bootstrap modal works best when it is a direct child of <body> (avoid stacking-context/layout issues).
        if (scenarioSelectModalEl && scenarioSelectModalEl.parentElement !== document.body) {
            document.body.appendChild(scenarioSelectModalEl);
        }

        buildRecommendedSkillOptions();

        let scenarioPayload = getScenarioRecommendedSkillPayload();
        const storedSessionId = safeGetLocalStorage('scenario_recommended_session_id');
        const sessionIdForContext = sessionIdFromQuery || (scenarioPayload.source === 'query' ? null : storedSessionId);
        let scenarioParsed = scenarioPayload.raw ? resolveSkillKeys(parseSkillList(scenarioPayload.raw)) : { resolved: [], unknown: [] };
        let handoutPayload = { rawList: [], titles: [] };
        let handoutParsed = { resolved: [], unknown: [] };
        let scenarioFetchPromise = null;
        const appendHandoutHint = (message) => {
            if (!handoutPayload.rawList.length) return message || '';
            const suffix = '秘匿推奨技能あり';
            if (!message) return suffix;
            return `${message} / ${suffix}`;
        };
        const getCombinedRecommendedKeys = () => (
            Array.from(new Set([...scenarioParsed.resolved, ...handoutParsed.resolved]))
        );
        const updateScenarioHint = (message, { showRetry = false } = {}) => {
            if (!hintEl) return;
            hintEl.textContent = message || '';
            if (retryBtn) {
                retryBtn.classList.toggle('d-none', !showRetry);
            }
        };
        const updateScenarioHintFromPayload = () => {
            if (!hintEl) return;
            let message = '';
            if (scenarioPayload.raw) {
                message = scenarioPayload.title
                    ? `シナリオ推奨技能: ${scenarioPayload.title}`
                    : 'シナリオ推奨技能を読み込み可能';
            } else if (scenarioPayload.scenarioId && scenarioPayload.source !== 'api') {
                message = 'シナリオ推奨技能を読み込み可能';
            } else if (scenarioPayload.title) {
                message = `シナリオ「${scenarioPayload.title}」には推奨技能がありません。`;
            }
            updateScenarioHint(appendHandoutHint(message));
        };
        const parseHandoutRecommendedSkills = (rawList) => {
            if (!Array.isArray(rawList) || rawList.length === 0) {
                return { resolved: [], unknown: [] };
            }
            const combined = [];
            rawList.forEach(raw => {
                combined.push(...parseSkillList(raw));
            });
            return resolveSkillKeys(combined);
        };
        const setScenarioFetchState = (isLoading) => {
            if (!scenarioBtn) return;
            if (!scenarioBtn.dataset.defaultLabel) {
                scenarioBtn.dataset.defaultLabel = scenarioBtn.innerHTML;
            }
            scenarioBtn.disabled = isLoading;
            if (isLoading) {
                scenarioBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 取得中...';
                scenarioBtn.setAttribute('aria-busy', 'true');
            } else {
                scenarioBtn.innerHTML = scenarioBtn.dataset.defaultLabel;
                scenarioBtn.removeAttribute('aria-busy');
            }
            if (retryBtn) {
                retryBtn.disabled = isLoading;
            }
        };
        if (scenarioParsed.unknown.length > 0) {
            console.warn('Unknown scenario recommended skills:', scenarioParsed.unknown);
        }

        updateScenarioHintFromPayload();

        if (scenarioParsed.resolved.length > 0) {
            setRecommendedSkills(scenarioParsed.resolved, { persist: false });
        } else {
            const stored = loadCustomRecommendedSkills();
            if (stored.length > 0) {
                setRecommendedSkills(stored, { persist: false });
            } else {
                setRecommendedSkills([], { persist: false });
            }
        }

        const applySessionContext = async (sessionId, options = {}) => {
            const { forceScenario = false, autoApply = false, persistSelection = false } = options;
            const context = await fetchNextSessionContext(sessionId);
            if (!context || !context.session_id) {
                updateScenarioHint('セッション情報の取得に失敗しました。');
                return false;
            }

            if (persistSelection) {
                safeSetLocalStorage('scenario_recommended_session_id', String(context.session_id));
            }

            const hasScenarioRaw = !!(scenarioPayload.raw || '').trim();
            if (context.scenario && (forceScenario || scenarioPayload.source !== 'query' || !hasScenarioRaw)) {
                const scenarioRaw = (context.scenario.recommended_skills || '').trim();
                scenarioPayload = {
                    ...scenarioPayload,
                    raw: scenarioRaw,
                    title: context.scenario.title || scenarioPayload.title,
                    gameSystem: context.scenario.game_system || scenarioPayload.gameSystem,
                    scenarioId: context.scenario.id ? String(context.scenario.id) : scenarioPayload.scenarioId,
                    source: 'session'
                };
                persistScenarioRecommendedSkills(scenarioPayload);
                scenarioParsed = scenarioRaw
                    ? resolveSkillKeys(parseSkillList(scenarioRaw))
                    : { resolved: [], unknown: [] };
                if (scenarioParsed.unknown.length > 0) {
                    console.warn('Unknown scenario recommended skills:', scenarioParsed.unknown);
                }
            }

            handoutPayload = {
                rawList: Array.isArray(context.handout_recommended_skills)
                    ? context.handout_recommended_skills.map(raw => (raw || '').trim()).filter(Boolean)
                    : [],
                titles: Array.isArray(context.handout_titles)
                    ? context.handout_titles.map(title => (title || '').trim()).filter(Boolean)
                    : []
            };
            handoutParsed = parseHandoutRecommendedSkills(handoutPayload.rawList);
            if (handoutParsed.unknown.length > 0) {
                console.warn('Unknown handout recommended skills:', handoutParsed.unknown);
            }

            updateScenarioHintFromPayload();

            const combined = getCombinedRecommendedKeys();
            if (autoApply && combined.length > 0) {
                userTouchedRecommended = true;
                setRecommendedSkills(combined, { mode: 'merge', persist: true });
            } else if (combined.length > 0 && !userTouchedRecommended) {
                setRecommendedSkills(combined, { persist: false });
            }

            return true;
        };

        const shouldApplySessionContext = !isEditMode && (sessionIdForContext || scenarioPayload.source !== 'query');
        if (shouldApplySessionContext) {
            void applySessionContext(sessionIdForContext).then(success => {
                if (!success && !scenarioPayload.raw && scenarioPayload.scenarioId) {
                    void fetchScenarioRecommended(true);
                }
            });
        }

        const addFromInput = () => {
            const rawValue = input.value;
            const parsed = resolveSkillKeys(parseSkillList(rawValue));
            if (parsed.resolved.length === 0) {
                alert('技能が見つかりません。名称またはキーを確認してください。');
                return;
            }
            userTouchedRecommended = true;
            setRecommendedSkills(parsed.resolved, { mode: 'merge', persist: true });
            input.value = '';
            if (parsed.unknown.length > 0) {
                alert(`未対応の技能: ${parsed.unknown.join(', ')}`);
            }
        };

        addBtn?.addEventListener('click', addFromInput);
        input.addEventListener('keydown', event => {
            if (event.key === 'Enter') {
                event.preventDefault();
                addFromInput();
            }
        });

        clearBtn?.addEventListener('click', () => {
            userTouchedRecommended = true;
            setRecommendedSkills([], { persist: true });
        });

        const scenarioSelectModal = scenarioSelectModalEl && window.bootstrap?.Modal
            ? (bootstrap.Modal.getOrCreateInstance
                ? bootstrap.Modal.getOrCreateInstance(scenarioSelectModalEl)
                : new bootstrap.Modal(scenarioSelectModalEl))
            : null;

        const setScenarioSelectStatus = (message, { showReload = false } = {}) => {
            if (scenarioSelectStatusEl) scenarioSelectStatusEl.textContent = message || '';
            if (scenarioSelectReloadBtn) {
                scenarioSelectReloadBtn.classList.toggle('d-none', !showReload);
            }
        };

        const buildScenarioSelectItem = (choice) => {
            const sessionId = choice?.session_id ? String(choice.session_id) : '';
            const scenarioId = choice?.scenario?.id ? String(choice.scenario.id) : '';
            if (!sessionId || !scenarioId) return null;

            const scenarioTitle = choice?.scenario?.title || '（無題シナリオ）';
            const gameSystem = choice?.scenario?.game_system || '';
            const groupName = choice?.group_name || '';
            const sessionTitle = choice?.session_title || '';
            const sessionDateDisplay = choice?.session_date_display || '';

            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'list-group-item list-group-item-action';
            button.dataset.sessionId = sessionId;
            button.dataset.scenarioId = scenarioId;
            button.dataset.scenarioTitle = scenarioTitle;
            button.dataset.gameSystem = gameSystem;

            const header = document.createElement('div');
            header.className = 'd-flex w-100 justify-content-between align-items-start gap-2';

            const textWrap = document.createElement('div');
            textWrap.style.minWidth = '0';

            const titleEl = document.createElement('div');
            titleEl.className = 'fw-semibold text-truncate';
            titleEl.textContent = scenarioTitle;

            const metaEl = document.createElement('small');
            metaEl.className = 'text-muted d-block text-truncate';
            const metaParts = [sessionDateDisplay, sessionTitle, groupName].filter(Boolean);
            metaEl.textContent = metaParts.join(' / ');

            textWrap.appendChild(titleEl);
            textWrap.appendChild(metaEl);

            const badge = document.createElement('span');
            badge.className = 'badge bg-secondary flex-shrink-0';
            badge.textContent = gameSystem;

            header.appendChild(textWrap);
            header.appendChild(badge);
            button.appendChild(header);

            const activeSessionId = safeGetLocalStorage('scenario_recommended_session_id');
            if (activeSessionId && String(activeSessionId) === sessionId) {
                button.classList.add('active');
            }

            button.addEventListener('click', () => {
                void applySessionContext(sessionId, { forceScenario: true, autoApply: true, persistSelection: true })
                    .then(success => {
                        if (success) scenarioSelectModal?.hide();
                    });
            });

            return button;
        };

        const loadScenarioChoices = async () => {
            if (!scenarioSelectListEl) return;
            scenarioSelectListEl.innerHTML = '';
            setScenarioSelectStatus('読み込み中...');

            const choices = await fetchParticipatingScenarios({ days: 365, limit: 50 });
            if (!Array.isArray(choices)) {
                const errorEl = document.createElement('div');
                errorEl.className = 'text-center text-muted py-3';
                errorEl.textContent = '参加予定のシナリオの取得に失敗しました。';
                scenarioSelectListEl.appendChild(errorEl);
                setScenarioSelectStatus('取得に失敗しました。', { showReload: true });
                return;
            }

            const list = choices;
            if (list.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'text-center text-muted py-3';
                empty.textContent = '参加予定のシナリオがありません。';
                scenarioSelectListEl.appendChild(empty);
                setScenarioSelectStatus('0件');
                return;
            }

            const fragment = document.createDocumentFragment();
            let added = 0;
            list.forEach(choice => {
                const item = buildScenarioSelectItem(choice);
                if (!item) return;
                fragment.appendChild(item);
                added += 1;
            });
            scenarioSelectListEl.appendChild(fragment);
            setScenarioSelectStatus(`${added}件`);
        };

        const openScenarioSelectModal = async () => {
            if (!scenarioSelectModal) return;
            scenarioSelectModal.show();
            await loadScenarioChoices();
        };

        selectScenarioBtn?.addEventListener('click', () => {
            void openScenarioSelectModal();
        });
        scenarioSelectReloadBtn?.addEventListener('click', () => {
            void loadScenarioChoices();
        });

        const fetchScenarioRecommended = async (autoApply = false) => {
            if (!scenarioPayload.scenarioId) return null;
            if (scenarioFetchPromise) return scenarioFetchPromise;
            setScenarioFetchState(true);
            updateScenarioHint('シナリオ推奨技能を取得中...');
            scenarioFetchPromise = fetchScenarioPayload(scenarioPayload.scenarioId)
                .then(scenarioData => {
                    if (!scenarioData) {
                        updateScenarioHint('シナリオ推奨技能の取得に失敗しました。再試行できます。', { showRetry: true });
                        return null;
                    }
                    scenarioPayload = {
                        ...scenarioPayload,
                        raw: (scenarioData.recommended_skills || '').trim(),
                        title: scenarioData.title || scenarioPayload.title,
                        gameSystem: scenarioData.game_system || scenarioPayload.gameSystem,
                        scenarioId: scenarioData.id ? String(scenarioData.id) : scenarioPayload.scenarioId,
                        source: 'api'
                    };
                    persistScenarioRecommendedSkills(scenarioPayload);
                    scenarioParsed = scenarioPayload.raw
                        ? resolveSkillKeys(parseSkillList(scenarioPayload.raw))
                        : { resolved: [], unknown: [] };
                    if (scenarioParsed.unknown.length > 0) {
                        console.warn('Unknown scenario recommended skills:', scenarioParsed.unknown);
                    }
                    updateScenarioHintFromPayload();
                    const combined = getCombinedRecommendedKeys();
                    if (autoApply && combined.length > 0 && !userTouchedRecommended) {
                        setRecommendedSkills(combined, { persist: false });
                    }
                    return scenarioParsed.resolved;
                })
                .finally(() => {
                    scenarioFetchPromise = null;
                    setScenarioFetchState(false);
                });
            return scenarioFetchPromise;
        };

        scenarioBtn?.addEventListener('click', () => {
            userTouchedRecommended = true;
            const combined = getCombinedRecommendedKeys();
            if (combined.length > 0) {
                setRecommendedSkills(combined, { mode: 'merge', persist: true });
                return;
            }
            if (!scenarioPayload.scenarioId) {
                updateScenarioHint('シナリオ推奨技能がありません。');
                return;
            }
            void fetchScenarioRecommended().then(() => {
                const refreshed = getCombinedRecommendedKeys();
                if (refreshed.length > 0) {
                    setRecommendedSkills(refreshed, { mode: 'merge', persist: true });
                }
            });
        });
        retryBtn?.addEventListener('click', () => {
            if (!scenarioPayload.scenarioId) return;
            void fetchScenarioRecommended();
        });

        if (!isEditMode && !scenarioPayload.raw && scenarioPayload.scenarioId && !shouldApplySessionContext) {
            void fetchScenarioRecommended(true);
        }
    }

    // Skill input event bindings
    function addSkillInputEvents() {
        try {
            skillCards.forEach(({ card }) => {
                bindSkillCardEvents(card);
            });
        } catch (error) {
            console.error('Error in addSkillInputEvents:', error);
        }
    }

    // 動的基本値を持つ技能の更新
    function updateDynamicSkillBases() {
        try {
            // 回避はDEX依存
            const dexEl = document.getElementById('dex');
            if (!dexEl) {
                console.warn('DEX element not found');
                return;
            }
            const dex = parseInt(dexEl.value) || 0;
            const dodgeCard = skillCardByKey.get('dodge');
            const dodgeBaseEl = dodgeCard?.querySelector('.skill-base') || document.getElementById('base_dodge');
            if (dodgeBaseEl && (!window.customBaseValues || window.customBaseValues['dodge'] === undefined)) {
                dodgeBaseEl.value = Math.min(dex * 2, 999);
            }

            // 母国語 = EDU依存
            const eduEl = document.getElementById('edu');
            if (!eduEl) {
                console.warn('EDU element not found');
                return;
            }
            const edu = parseInt(eduEl.value) || 0;
            const languageOwnCard = skillCardByKey.get('language_own');
            const languageOwnBaseEl = languageOwnCard?.querySelector('.skill-base') || document.getElementById('base_language_own');
            if (languageOwnBaseEl && (!window.customBaseValues || window.customBaseValues['language_own'] === undefined)) {
                languageOwnBaseEl.value = Math.min(edu * 5, 999);
            }

            // 技能合計も更新
            updateSkillTotals();
        } catch (error) {
            console.error('Error in updateDynamicSkillBases:', error);
        }
    }
    
    // 技能合計の更新
    function updateSkillTotals() {
        // console.log('updateSkillTotals called');
        let occupationUsed = 0;
        let interestUsed = 0;
        let allocatedCount = 0;

        skillCards.forEach(({ key, card }) => {
            const baseEl = card.querySelector('.skill-base');
            const occEl = card.querySelector('.occupation-skill');
            const intEl = card.querySelector('.interest-skill');
            const otherEl = card.querySelector('.other-skill');
            const totalEl = card.querySelector('.skill-total');

            if (!baseEl || !occEl || !intEl || !otherEl || !totalEl) return;

            const base = Math.min(parseInt(baseEl.value, 10) || 0, 999);
            const occ = Math.min(parseInt(occEl.value, 10) || 0, 999);
            const int = Math.min(parseInt(intEl.value, 10) || 0, 999);
            const other = Math.min(parseInt(otherEl.value, 10) || 0, 999);
            if (parseInt(baseEl.value, 10) !== base) baseEl.value = base;
            if (parseInt(occEl.value, 10) !== occ) occEl.value = occ;
            if (parseInt(intEl.value, 10) !== int) intEl.value = int;
            if (parseInt(otherEl.value, 10) !== other) otherEl.value = other;
            const total = Math.min(base + occ + int + other, 999);
            totalEl.textContent = `${total}%`;

            if (occ > 0 || int > 0 || other > 0) {
                allocatedCount++;
            }

            occupationUsed += occ;
            interestUsed += int;
        });
        
        // 配分済み技能数のバッジ更新
        const allocatedCountBadge = document.getElementById('allocatedCount');
        if (allocatedCountBadge) {
            allocatedCountBadge.textContent = allocatedCount;
        }
        
        // 職業/趣味ポイントの残数表示を更新
        const occupationTotal = parseInt(document.getElementById('occupationTotal')?.value) || 0;
        const interestTotal = parseInt(document.getElementById('interestTotal')?.value) || 0;
        
        if (document.getElementById('occupationUsed')) {
            document.getElementById('occupationUsed').textContent = occupationUsed;
        }
        if (document.getElementById('occupationRemaining')) {
            const occupationRemainingEl = document.getElementById('occupationRemaining');
            const remaining = Math.max(0, occupationTotal - occupationUsed);
            occupationRemainingEl.textContent = remaining;
            occupationRemainingEl.classList.toggle('bg-danger', remaining === 0);
            occupationRemainingEl.classList.toggle('bg-success', remaining !== 0);
        }
        if (document.getElementById('interestUsed')) {
            document.getElementById('interestUsed').textContent = interestUsed;
        }
        if (document.getElementById('interestRemaining')) {
            const interestRemainingEl = document.getElementById('interestRemaining');
            const remainingInt = Math.max(0, interestTotal - interestUsed);
            interestRemainingEl.textContent = remainingInt;
            interestRemainingEl.classList.toggle('bg-danger', remainingInt === 0);
            interestRemainingEl.classList.toggle('bg-success', remainingInt !== 0);
        }
        
        // フッターの技能ポイント表示も更新
        if (document.getElementById('occupationUsedFooter')) {
            document.getElementById('occupationUsedFooter').textContent = occupationUsed;
        }
        if (document.getElementById('occupationTotalFooter')) {
            document.getElementById('occupationTotalFooter').textContent = occupationTotal;
        }
        if (document.getElementById('interestUsedFooter')) {
            document.getElementById('interestUsedFooter').textContent = interestUsed;
        }
        if (document.getElementById('interestTotalFooter')) {
            document.getElementById('interestTotalFooter').textContent = interestTotal;
        }
    }

    // 全能力値ダイス（ボタン）
    document.getElementById('rollAllAbilities')?.addEventListener('click', rollAllAbilities);
    document.getElementById('statusRollAllAbilities')?.addEventListener('click', rollAllAbilities);
    
    // 全能力値ダイス設定の変更時にフォーミュラを更新
    document.getElementById('globalDiceCount')?.addEventListener('input', updateGlobalDiceFormula);
    document.getElementById('globalDiceSides')?.addEventListener('input', updateGlobalDiceFormula);
    document.getElementById('globalDiceBonus')?.addEventListener('input', updateGlobalDiceFormula);
    
    // Recalculate when occupation method changes
    document.getElementById('occupationMethod')?.addEventListener('change', function() {
        calculateSkillPoints();
        updateSkillTotals();
    });
    
    // 能力値変更時に派生ステータスを更新
    document.querySelectorAll('.ability-score').forEach(input => {
        input.addEventListener('input', calculateDerivedStats);
    });

    const resetSkillAllocations = () => {
        skillCards.forEach(({ card }) => {
            card.querySelectorAll('.occupation-skill, .interest-skill').forEach(input => {
                input.value = 0;
            });
        });
        updateSkillTotals();
    };

    // リセットボタン（誤操作防止の確認つき）
    const confirmAndResetSkills = () => {
        const ok = window.confirm('技能ポイントの割り振り（職業/趣味）をリセットします。よろしいですか？');
        if (!ok) return;
        resetSkillAllocations();
    };
    document.getElementById('footerResetSkills')?.addEventListener('click', confirmAndResetSkills);

    // 職業テンプレートデータ
    
    // Occupation template data (skill keys are mapped to display names later)
    const OCCUPATION_TEMPLATES = {
        academic: [
            {
                name: "大学教授",
                skills: ["library_use", "psychology", "persuade", "credit_rating", "history", "natural_world", "language_other", "occult"],
                multiplier: 20,
                description: "大学の教員・研究者"
            },
            {
                name: "考古学者",
                skills: ["archaeology", "library_use", "history", "spot_hidden", "navigate", "photography", "language_other", "appraise"],
                multiplier: 20,
                description: "遺跡や遺物の調査研究者"
            },
            {
                name: "司書",
                skills: ["library_use", "accounting", "computer_use", "history", "psychology", "language_other", "spot_hidden", "persuade"],
                multiplier: 20,
                description: "図書館・文書館の専門職"
            }
        ],
        investigation: [
            {
                name: "私立探偵",
                skills: ["spot_hidden", "listen", "track", "psychology", "persuade", "photography", "hide", "law"],
                multiplier: 20,
                description: "独立系の調査員"
            },
            {
                name: "記者",
                skills: ["persuade", "psychology", "spot_hidden", "listen", "photography", "fast_talk", "library_use", "language_other"],
                multiplier: 20,
                description: "新聞記者・雑誌ライター"
            },
            {
                name: "警察官",
                skills: ["law", "spot_hidden", "listen", "intimidate", "handgun", "grapple", "drive_auto", "first_aid"],
                multiplier: 20,
                description: "法執行機関の職員"
            }
        ],
        combat: [
            {
                name: "軍人",
                skills: ["rifle", "handgun", "dodge", "first_aid", "intimidate", "survival", "navigate", "drive_auto"],
                multiplier: 20,
                description: "現役または元軍人"
            },
            {
                name: "格闘家",
                skills: ["martial_arts", "dodge", "kick", "grapple", "psychology", "intimidate", "jump", "first_aid"],
                multiplier: 20,
                description: "武道家・ボクサー等"
            }
        ],
        medical: [
            {
                name: "医師",
                skills: ["medicine", "first_aid", "biology", "pharmacy", "psychology", "credit_rating", "persuade", "language_other"],
                multiplier: 20,
                description: "医師・外科医"
            },
            {
                name: "看護師",
                skills: ["medicine", "first_aid", "biology", "psychology", "persuade", "listen", "spot_hidden", "pharmacy"],
                multiplier: 20,
                description: "医療スタッフ"
            }
        ],
        arts: [
            {
                name: "芸術家",
                skills: ["art", "psychology", "spot_hidden", "history", "persuade", "charm", "language_other", "appraise"],
                multiplier: 20,
                description: "画家・彫刻家・演者など"
            },
            {
                name: "作家",
                skills: ["language_own", "language_other", "library_use", "psychology", "history", "occult", "persuade", "spot_hidden"],
                multiplier: 20,
                description: "小説家・著述家"
            }
        ],
        others: [
            {
                name: "犯罪者",
                skills: ["hide", "sneak", "locksmith", "sleight_of_hand", "spot_hidden", "listen", "bargain", "disguise"],
                multiplier: 20,
                description: "常習犯・無法者"
            },
            {
                name: "コレクター",
                skills: ["credit_rating", "ride", "art", "language_other", "handgun", "history", "charm", "accounting"],
                multiplier: 20,
                description: "収集家・愛好家"
            }
        ]
    };

function initOccupationTemplates() {
        const categoryLinks = document.querySelectorAll('#occupationCategories a');
        categoryLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // アクティブクラスの切り替え
                categoryLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
                
                // カテゴリの職業を表示
                const category = this.dataset.category;
                displayOccupations(category);
            });
        });
        
        // 初期表示
        displayOccupations('academic');
    }

    // 職業リストを表示
    function displayOccupations(category) {
        const occupationList = document.getElementById('occupationList');
        const occupations = OCCUPATION_TEMPLATES[category] || [];
        
        let html = '<div class="list-group">';
        occupations.forEach(occ => {
            const skillDisplay = (occ.skills || [])
                .map(skillKey => ALL_SKILLS_6TH[skillKey]?.name || skillKey)
                .join(', ');
            html += `
                <a href="#" class="list-group-item list-group-item-action occupation-template-item" 
                   data-occupation='${JSON.stringify(occ)}'>
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">${occ.name}</h6>
                        <small>倍率: EDU x${occ.multiplier}</small>
                    </div>
                    <p class="mb-1 text-muted small">${occ.description}</p>
                    <small>推奨技能: ${skillDisplay}</small>
                </a>
            `;
        });
        html += '</div>';
        
        occupationList.innerHTML = html;
        
        // Occupation template click handlers
        document.querySelectorAll('.occupation-template-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const occupation = JSON.parse(this.dataset.occupation);
                applyOccupationTemplate(occupation);
            });
        });
    }

    // 職業テンプレートを適用
    function applyOccupationTemplate(occupation) {
        // 職業名をセット
        document.getElementById('occupation').value = occupation.name;
        
        // 職業ポイント計算方法を設定
        const methodSelect = document.getElementById('occupationMethod');
        if (methodSelect && occupation.multiplier === 20) {
            methodSelect.value = 'edu20';
        }
        
        // 職業技能をセット
        userTouchedOccupation = true;
        setOccupationSkills(occupation.skills || [], { persist: true });
        
        // モーダルを閉じる
        const modal = bootstrap.Modal.getInstance(document.getElementById('occupationTemplateModal'));
        modal.hide();
        
        // 技能ポイントを再計算
        calculateSkillPoints();
        updateSkillTotals();
    }

    // Bootstrap タブ初期化
    const triggerTabList = [].slice.call(document.querySelectorAll('#skillTabs button'));
    triggerTabList.forEach(function (triggerEl) {
        const tabTrigger = new bootstrap.Tab(triggerEl);
        
        triggerEl.addEventListener('click', function (event) {
            event.preventDefault();
            tabTrigger.show();
        });
    });
    
    // 画像アップロード機能
    function initImageUpload() {
        const imageInput = document.getElementById('character-images');
        const imagePreview = document.getElementById('image-preview');
        const previewImg = document.getElementById('preview-img');
        const removeBtn = document.getElementById('remove-image');
        
        if (!imageInput) return;
        
        // ファイル選択時のプレビュー表示
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // File size check (5MB limit)
                if (file.size > 5 * 1024 * 1024) {
                    alert('File size must be 5MB or less.');
                    imageInput.value = '';
                    return;
                }
                
                // File type check
                if (!file.type.match(/^image\/(jpeg|jpg|png|gif)$/)) {
                    alert('Please select a JPG, PNG, or GIF image.');
                    imageInput.value = '';
                    return;
                }
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImg.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
        
        // 画像を削除
        removeBtn?.addEventListener('click', function() {
            imageInput.value = '';
            previewImg.src = '';
            imagePreview.style.display = 'none';
        });
    }
    
    // 初期化
    updateGlobalDiceFormula();
    initAbilityDiceSettings();
    generateSkillsList();
    addSkillInputEvents();  // 技能リスト生成後にイベントリスナーを追加
    // アクティブな技能タブを初期描画
    refreshActiveSkillTab();
    initOccupationSkillControls();
    void initRecommendedSkillControls();

    initOccupationTemplates(); // 職業テンプレート機能を初期化
    initImageUpload(); // 画像アップロード機能を初期化

    window.addCustomSkill = addCustomSkill;
    window.removeCustomSkill = removeCustomSkill;
    window.updateCustomSkillName = updateCustomSkillName;
    window.createAddCustomSkillButton = createAddCustomSkillButton;
    window.createCustomSkillItemHTML = createCustomSkillItemHTML;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    function setValueById(id, value) {
        const el = document.getElementById(id);
        if (!el) return;
        el.value = value ?? '';
    }

    async function fetchJson(url, options = {}) {
        const response = await fetch(url, { credentials: 'same-origin', ...options });
        if (!response.ok) {
            let err;
            try {
                err = await response.json();
            } catch (_) {
                err = { error: `HTTP ${response.status}` };
            }
            throw err;
        }
        if (response.status === 204) return null;
        return response.json();
    }

    async function loadCharacterForEdit(characterId) {
        const titleEl = document.querySelector('h1.eldritch-font');
        if (titleEl) {
            titleEl.innerHTML = '<i class="fas fa-user-ninja text-primary"></i> クトゥルフ神話TRPG 6版探索者編集';
        }
        document.title = 'クトゥルフ神話TRPG 6版探索者編集 - タブレノ';
        const submitBtn = document.querySelector('#character-sheet-form button[type="submit"]');
        if (submitBtn) submitBtn.innerHTML = '<i class="fas fa-save"></i> 探索者を更新';
        const footerSaveBtnEl = document.getElementById('footerSaveCharacter');
        if (footerSaveBtnEl) footerSaveBtnEl.innerHTML = '<i class="fas fa-save"></i> 探索者を更新';
        const createVersionBtn = document.getElementById('createVersionButton');
        if (createVersionBtn) createVersionBtn.style.display = '';
        const footerCreateVersionBtn = document.getElementById('footerCreateVersion');
        if (footerCreateVersionBtn) footerCreateVersionBtn.style.display = '';

        const sheet = await fetchJson(`/accounts/character-sheets/${characterId}/`);
        if (sheet.edition !== '6th') {
            throw { error: 'この画面は6版キャラクター専用です。' };
        }

        // Basic info
        setValueById('character-name', sheet.name);
        setValueById('player-name', sheet.player_name);
        setValueById('age', sheet.age);
        setValueById('gender', sheet.gender);
        setValueById('occupation', sheet.occupation);
        setValueById('birthplace', sheet.birthplace);
        setValueById('residence', sheet.residence);
        setValueById('notes', sheet.notes);
        setRecommendedSkills(Array.isArray(sheet.recommended_skills) ? sheet.recommended_skills : [], { persist: false });
        setOccupationSkills(Array.isArray(sheet.occupation_skills) ? sheet.occupation_skills : [], { persist: false });

        // Abilities
        setValueById('str', sheet.str_value);
        setValueById('con', sheet.con_value);
        setValueById('pow', sheet.pow_value);
        setValueById('dex', sheet.dex_value);
        setValueById('app', sheet.app_value);
        setValueById('siz', sheet.siz_value);
        setValueById('int', sheet.int_value);
        setValueById('edu', sheet.edu_value);

        // Current status (do not overwrite on derived recalculation)
        setValueById('current_hp', sheet.hit_points_current);
        setValueById('current_mp', sheet.magic_points_current);
        setValueById('current_san', sheet.sanity_current);

        calculateDerivedStats({ setCurrentDefaults: false });

        // Financial data (6th)
        try {
            const fin = await fetchJson(`/accounts/character-sheets/${characterId}/financial_summary/`);
            setValueById('money', fin.cash);
            setValueById('assets', fin.assets);
            setValueById('income', fin.annual_income);
        } catch (_) {
            // optional
        }

        // Skills
        const nameToKey = new Map(
            Object.entries(ALL_SKILLS_6TH)
                .map(([key, skill]) => [skill?.name, key])
                .filter(([name]) => !!name)
        );

        const customSkillsToAdd = [];
        (sheet.skills || []).forEach(skill => {
            const skillKey = nameToKey.get(skill.skill_name);
            if (!skillKey) {
                customSkillsToAdd.push(skill);
                return;
            }

            const card = skillCardByKey.get(skillKey);
            if (!card) return;

            const occInput = card.querySelector('.occupation-skill');
            const intInput = card.querySelector('.interest-skill');
            const baseInput = card.querySelector('.skill-base');
            const otherInput = card.querySelector('.other-skill');

            if (occInput) occInput.value = skill.occupation_points ?? 0;
            if (intInput) intInput.value = skill.interest_points ?? 0;
            if (baseInput) baseInput.value = skill.base_value ?? 0;
            if (otherInput) otherInput.value = skill.other_points ?? 0;

            const defaultBase = (() => {
                const definitionBase = ALL_SKILLS_6TH[skillKey]?.base;
                if (typeof definitionBase === 'number') return definitionBase;
                if (definitionBase === 'DEX*2') {
                    const dex = parseInt(document.getElementById('dex')?.value) || 0;
                    return Math.min(dex * 2, 999);
                }
                if (definitionBase === 'EDU*5') {
                    const edu = parseInt(document.getElementById('edu')?.value) || 0;
                    return Math.min(edu * 5, 999);
                }
                return 0;
            })();

            if (skill.base_value != null && skill.base_value !== defaultBase) {
                window.customBaseValues = window.customBaseValues || {};
                window.customBaseValues[skillKey] = skill.base_value;
            } else if (window.customBaseValues && window.customBaseValues[skillKey] !== undefined) {
                delete window.customBaseValues[skillKey];
            }
        });

        if (customSkillsToAdd.length > 0) {
            customSkillsToAdd.forEach(customSkill => {
                addCustomSkill(CUSTOM_SKILL_DEFAULT_CATEGORY, {
                    name: customSkill.skill_name,
                    baseValue: customSkill.base_value,
                    occupationPoints: customSkill.occupation_points,
                    interestPoints: customSkill.interest_points,
                    otherPoints: customSkill.other_points,
                    render: false
                });
            });
            refreshActiveSkillTab();
            updateSkillTotals();
        }

        updateDynamicSkillBases();
        updateSkillTotals();
    }

    function collectApiDataFromForm(form) {
        const formData = new FormData(form);
        const data = {};

        for (let [key, value] of formData.entries()) {
            if (key !== 'character_images') {
                data[key] = value;
            }
        }

        if (!data.name) {
            throw { error: 'Character name is required.' };
        }

        const abilities = ['str_value', 'con_value', 'pow_value', 'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value'];
        let hasAbilities = false;
        for (const ability of abilities) {
            if (data[ability] && parseInt(data[ability]) > 0) {
                hasAbilities = true;
                break;
            }
        }
        if (!hasAbilities) {
            throw { error: 'Please set ability scores.' };
        }

        const apiData = {
            edition: '6th',
            name: data.name,
            player_name: data.player_name || '',
            age: data.age ? parseInt(data.age, 10) : null,
            gender: data.gender || '',
            occupation: data.occupation || '',
            birthplace: data.birthplace || '',
            residence: data.residence || '',

            str_value: parseInt(data.str_value, 10),
            con_value: parseInt(data.con_value, 10),
            pow_value: parseInt(data.pow_value, 10),
            dex_value: parseInt(data.dex_value, 10),
            app_value: parseInt(data.app_value, 10),
            siz_value: parseInt(data.siz_value, 10),
            int_value: parseInt(data.int_value, 10),
            edu_value: parseInt(data.edu_value, 10),

            notes: data.notes || ''
        };
        apiData.recommended_skills = Array.from(recommendedSkillKeys);
        apiData.occupation_skills = Array.from(occupationSkillKeys);
        const scenarioPayload = getScenarioRecommendedSkillPayload();
        const scenarioId = parseInt(scenarioPayload.scenarioId, 10);
        if (!Number.isNaN(scenarioId)) {
            apiData.scenario_id = scenarioId;
        }
        if (scenarioPayload.title) {
            apiData.scenario_title = scenarioPayload.title;
        }
        if (scenarioPayload.gameSystem) {
            apiData.game_system = scenarioPayload.gameSystem;
        }

        // 戦闘ステータス
        if (data.hit_points_current !== '' && data.hit_points_current != null) apiData.hit_points_current = parseInt(data.hit_points_current, 10) || 0;
        if (data.magic_points_current !== '' && data.magic_points_current != null) apiData.magic_points_current = parseInt(data.magic_points_current, 10) || 0;
        if (data.sanity_current !== '' && data.sanity_current != null) apiData.sanity_current = parseInt(data.sanity_current, 10) || 0;
        if (data.armor !== '' && data.armor != null) apiData.armor = parseInt(data.armor, 10) || 0;

        // 財産情報（保存時は update_financial_data を使用）
        if (data.money !== '' && data.money != null) apiData.money = parseInt(data.money, 10) || 0;
        if (data.assets !== '' && data.assets != null) apiData.assets = parseInt(data.assets, 10) || 0;
        if (data.income !== '' && data.income != null) apiData.income = parseInt(data.income, 10) || 0;

        // 背景情報をnotesに統合
        const backgroundNotes = [];
        if (data.backstory) backgroundNotes.push(`背景ストーリー:\n${data.backstory}`);
        if (data.appearance) backgroundNotes.push(`外見:\n${data.appearance}`);
        if (data.ideals) backgroundNotes.push(`信念・信条:\n${data.ideals}`);
        if (data.bonds) backgroundNotes.push(`重要な人物:\n${data.bonds}`);
        if (data.flaws) backgroundNotes.push(`弱点・恐怖症:\n${data.flaws}`);
        if (data.items) backgroundNotes.push(`所持品:\n${data.items}`);
        if (backgroundNotes.length > 0) {
            apiData.notes = (apiData.notes ? apiData.notes + '\n\n' : '') + backgroundNotes.join('\n\n');
        }

        // 技能データの収集
        const skills = [];
        skillCards.forEach(({ key: skillKey, card }) => {
            const occInput = card.querySelector('.occupation-skill');
            const intInput = card.querySelector('.interest-skill');
            const baseInput = card.querySelector('.skill-base');
            const otherInput = card.querySelector('.other-skill');

            const occValue = Math.min(parseInt(occInput?.value, 10) || 0, 999);
            const intValue = Math.min(parseInt(intInput?.value, 10) || 0, 999);
            const otherValue = Math.min(parseInt(otherInput?.value, 10) || 0, 999);

            const hasCustomBase = !!(window.customBaseValues && window.customBaseValues[skillKey] !== undefined);
            if (occValue > 0 || intValue > 0 || otherValue > 0 || hasCustomBase) {
                let baseValue = 0;
                if (window.customBaseValues && window.customBaseValues[skillKey] !== undefined) {
                    baseValue = window.customBaseValues[skillKey];
                } else {
                    baseValue = parseInt(baseInput?.value, 10) || 0;
                }
                baseValue = Math.min(baseValue, 999);

                skills.push({
                    skill_name: getSkillDisplayName(skillKey, card),
                    base_value: baseValue,
                    occupation_points: occValue,
                    interest_points: intValue,
                    other_points: otherValue
                });
            }
        });

        if (skills.length > 0) apiData.skills = skills;

        const imageFiles = formData
            .getAll('character_images')
            .filter(f => f instanceof File && f.size > 0 && f.name);

        return { apiData, data, formData, imageFiles };
    }

    async function updateFinancialData(characterId, data) {
        const payload = {};
        if (data.money !== '' && data.money != null) payload.cash = parseInt(data.money, 10) || 0;
        if (data.assets !== '' && data.assets != null) payload.assets = parseInt(data.assets, 10) || 0;
        if (data.income !== '' && data.income != null) payload.annual_income = parseInt(data.income, 10) || 0;
        if (Object.keys(payload).length === 0) return;

        await fetchJson(`/accounts/character-sheets/${characterId}/update_financial_data/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify(payload),
        });
    }

    async function syncSkills(characterId, desiredSkills) {
        const existingSkills = await fetchJson(`/accounts/character-sheets/${characterId}/skills/`);
        const existingByName = new Map((existingSkills || []).map(s => [s.skill_name, s]));
        const desiredByName = new Map((desiredSkills || []).map(s => [s.skill_name, s]));

        for (const desired of (desiredSkills || [])) {
            const existing = existingByName.get(desired.skill_name);
            const payload = {
                skill_name: desired.skill_name,
                base_value: desired.base_value,
                occupation_points: desired.occupation_points,
                interest_points: desired.interest_points,
                other_points: desired.other_points ?? 0,
            };

            if (existing?.id) {
                await fetchJson(`/accounts/character-sheets/${characterId}/skills/${existing.id}/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    body: JSON.stringify(payload),
                });
            } else {
                await fetchJson(`/accounts/character-sheets/${characterId}/skills/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    body: JSON.stringify(payload),
                });
            }
        }

        for (const [name, existing] of existingByName.entries()) {
            if (!desiredByName.has(name) && existing?.id) {
                await fetchJson(`/accounts/character-sheets/${characterId}/skills/${existing.id}/`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': csrfToken },
                });
            }
        }
    }

    async function replaceCharacterImages(characterId, imageFiles) {
        if (!Array.isArray(imageFiles) || imageFiles.length === 0) return;

        // Delete existing images first to avoid "main image" uniqueness conflicts
        try {
            const existing = await fetchJson(`/accounts/character-sheets/${characterId}/images/`);
            const existingResults = Array.isArray(existing) ? existing : (existing?.results || []);
            for (const img of existingResults) {
                if (!img?.id) continue;
                await fetchJson(`/accounts/character-sheets/${characterId}/images/${img.id}/`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': csrfToken },
                });
            }
        } catch (_) {
            // If listing/deleting fails, continue to try uploading new images
        }

        for (let index = 0; index < imageFiles.length; index++) {
            const file = imageFiles[index];
            const upload = new FormData();
            upload.append('image', file);
            upload.append('is_main', index === 0 ? 'true' : 'false');
            upload.append('order', String(index));

            await fetchJson(`/accounts/character-sheets/${characterId}/images/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: upload,
            });
        }
    }

    async function updateCharacterSheet(characterId, apiData, data, imageFiles = []) {
        const updatePayload = {
            name: apiData.name,
            player_name: apiData.player_name,
            gender: apiData.gender,
            occupation: apiData.occupation,
            birthplace: apiData.birthplace,
            residence: apiData.residence,
            recommended_skills: apiData.recommended_skills || [],
            occupation_skills: apiData.occupation_skills || [],
            str_value: apiData.str_value,
            con_value: apiData.con_value,
            pow_value: apiData.pow_value,
            dex_value: apiData.dex_value,
            app_value: apiData.app_value,
            siz_value: apiData.siz_value,
            int_value: apiData.int_value,
            edu_value: apiData.edu_value,
            notes: apiData.notes,
        };

        if (apiData.age != null) updatePayload.age = apiData.age;
        if (apiData.hit_points_current != null) updatePayload.hit_points_current = apiData.hit_points_current;
        if (apiData.magic_points_current != null) updatePayload.magic_points_current = apiData.magic_points_current;
        if (apiData.sanity_current != null) updatePayload.sanity_current = apiData.sanity_current;

        await fetchJson(`/accounts/character-sheets/${characterId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify(updatePayload),
        });

        await updateFinancialData(characterId, data);
        await syncSkills(characterId, apiData.skills || []);
        await replaceCharacterImages(characterId, imageFiles);
    }
    
    // Form submit handling
    const characterForm = document.getElementById('character-sheet-form');
    if (characterForm) {
        characterForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            let collected;
            try {
                collected = collectApiDataFromForm(this);
            } catch (error) {
                alert(error?.error || 'Invalid form data.');
                return;
            }

            const { apiData, data, formData, imageFiles } = collected;

            if (isEditMode) {
                try {
                    await updateCharacterSheet(editCharacterId, apiData, data, imageFiles);
                    alert('Character sheet updated successfully.');
                    window.location.href = `/accounts/character/${editCharacterId}/`;
                } catch (error) {
                    console.error('Error:', error);
                    alert(error?.error ? ('Error: ' + error.error) : 'Network error occurred.');
                }
                return;
            }

            if (imageFiles.length > 0) {
                const submitFormData = new FormData();

                Object.keys(apiData).forEach(key => {
                    if (key === 'skills' || key === 'equipment' || key === 'recommended_skills' || key === 'occupation_skills') {
                        submitFormData.append(key, JSON.stringify(apiData[key]));
                    } else {
                        submitFormData.append(key, apiData[key]);
                    }
                });

                imageFiles.forEach(file => submitFormData.append('character_images', file));

                // Send to API with multipart/form-data
                fetch('/accounts/character-sheets/create_6th_edition/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                    },
                    credentials: 'same-origin',
                    body: submitFormData,
                })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(err => Promise.reject(err));
                        }
                        return response.json();
                    })
                    .then(result => {
                        // Success: API returns CharacterSheet object
                        if (result.id) {
                            alert('Character sheet created successfully.');
                            window.location.href = '/accounts/character/list/';
                        } else {
                            alert('Error: unexpected response format.');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        if (error.error) {
                            alert('Error: ' + error.error);
                        } else {
                            alert('Network error occurred.');
                        }
                    });
            } else {
                // Send JSON payload without image
                fetch('/accounts/character-sheets/create_6th_edition/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify(apiData),
                })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(err => Promise.reject(err));
                        }
                        return response.json();
                    })
                    .then(result => {
                        // Success: API returns CharacterSheet object
                        if (result.id) {
                            alert('Character sheet created successfully.');
                            window.location.href = '/accounts/character/list/';
                        } else {
                            alert('Error: unexpected response format.');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        if (error.error) {
                            alert('Error: ' + error.error);
                        } else {
                            alert('Network error occurred.');
                        }
                    });
            }
        });
    }
    const footerSaveBtn = document.getElementById('footerSaveCharacter');
    if (footerSaveBtn && characterForm) {
        footerSaveBtn.addEventListener('click', () => {
            // Trigger submit with HTML5 validation
            characterForm.requestSubmit();
        });
    }

    async function handleCreateVersion() {
        if (!isEditMode || !characterForm) return;
        if (!confirm('現在の入力内容を「新しいバージョン」として保存します。\n（既存バージョンは更新しません）')) return;

        let collected;
        try {
            collected = collectApiDataFromForm(characterForm);
        } catch (error) {
            alert(error?.error || 'Invalid form data.');
            return;
        }

        try {
            const created = await fetchJson(`/accounts/character-sheets/${editCharacterId}/create_version/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
            });
            const newId = created?.id;
            if (!newId) throw { error: '新バージョンの作成に失敗しました。' };

            await updateCharacterSheet(newId, collected.apiData, collected.data, collected.imageFiles);

            alert('新バージョンを作成しました。');
            window.location.href = `/accounts/character/${newId}/`;
        } catch (error) {
            console.error('Error:', error);
            alert(error?.error ? ('Error: ' + error.error) : 'Network error occurred.');
        }
    }

    const createVersionBtn = document.getElementById('createVersionButton');
    if (createVersionBtn) createVersionBtn.addEventListener('click', handleCreateVersion);
    const footerCreateVersionBtn = document.getElementById('footerCreateVersion');
    if (footerCreateVersionBtn) footerCreateVersionBtn.addEventListener('click', handleCreateVersion);

    if (isEditMode) {
        loadCharacterForEdit(editCharacterId)
            .then(() => autosizeTextareas())
            .catch(error => {
                console.error('Failed to load character for edit:', error);
                alert(error?.error || 'Failed to load character data.');
            });
    } else {
        // 初期計算（常にロールして値を埋める）
        setTimeout(() => {
            rollAllAbilities();
        }, 0);
    }
});
