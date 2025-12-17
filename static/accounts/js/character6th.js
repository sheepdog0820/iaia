document.addEventListener('DOMContentLoaded', function() {

    
    // 6th edition skill data
    const SKILLS_6TH = {
        combat: {
            dodge: { base: "DEX*2", name: "\u56de\u907f" },
            martial_arts: { base: 1, name: "\u30de\u30fc\u30b7\u30e3\u30eb\u30a2\u30fc\u30c4" },
            throw: { base: 25, name: "\u6295\u64ae" },
            first_aid: { base: 30, name: "\u5fdc\u6025\u624b\u5f53" },
            fist_punch: { base: 50, name: "\u3053\u3076\u3057\uff08\u30d1\u30f3\u30c1\uff09" },
            head_butt: { base: 10, name: "\u982d\u6483\u304d" },
            kick: { base: 25, name: "\u30ad\u30c3\u30af" },
            grapple: { base: 25, name: "\u7d44\u307f\u4ed8\u304d" },
            knife: { base: 20, name: "\u30ca\u30a4\u30d5" },
            club: { base: 25, name: "\u3053\u3093\u68d2" },
            handgun: { base: 20, name: "\u62f3\u9283" },
            rifle: { base: 25, name: "\u30e9\u30a4\u30d5\u30eb" },
            shotgun: { base: 30, name: "\u30b7\u30e7\u30c3\u30c8\u30ac\u30f3" },
            submachine_gun: { base: 15, name: "\u30b5\u30d6\u30de\u30b7\u30f3\u30ac\u30f3" },
            machine_gun: { base: 15, name: "\u30de\u30b7\u30f3\u30ac\u30f3" },
            bow: { base: 15, name: "\u5f13" },
            sword: { base: 20, name: "\u5263" },
            spear: { base: 20, name: "\u69cd" },
            whip: { base: 5, name: "\u97a3" }
        },
        exploration: {
            spot_hidden: { base: 25, name: "\u76ee\u661f" },
            listen: { base: 25, name: "\u805e\u304d\u8033" },
            library_use: { base: 25, name: "\u56f3\u66f8\u9928" },
            track: { base: 10, name: "\u8ffd\u8de1" },
            navigate: { base: 10, name: "\u30ca\u30d3\u30b2\u30fc\u30c8" },
            photography: { base: 10, name: "\u5199\u771f\u8853" }
        },
        action: {
            climb: { base: 40, name: "\u767b\u6500" },
            jump: { base: 25, name: "\u8df3\u8e8d" },
            swim: { base: 25, name: "\u6c34\u6cf3" },
            sneak: { base: 10, name: "\u5fcd\u3073\u6b69\u304d" },
            hide: { base: 10, name: "\u96a0\u308c\u308b" },
            conceal: { base: 15, name: "\u96a0\u3059" },
            locksmith: { base: 1, name: "\u9375\u958b\u3051" },
            drive_auto: { base: 20, name: "\u904b\u8ee2" },
            pilot: { base: 1, name: "\u64ae\u7d71" },
            ride: { base: 5, name: "\u4e57\u99ac" },
            electrical_repair: { base: 10, name: "\u96fb\u6c17\u4fee\u7406" },
            electronics: { base: 1, name: "\u96fb\u5b50\u5de5\u5b66" },
            mechanical_repair: { base: 20, name: "\u6a5f\u68b0\u4fee\u7406" },
            operate_heavy_machine: { base: 1, name: "\u91cd\u6a5f\u68b0\u64cd\u4f5c" },
            disguise: { base: 1, name: "\u5909\u88c5" },
            sleight_of_hand: { base: 10, name: "\u624b\u3055\u3070\u304d" }
        },
        social: {
            persuade: { base: 15, name: "\u8aac\u5f97" },
            fast_talk: { base: 5, name: "\u8a00\u3044\u304f\u308b\u3081" },
            bargain: { base: 5, name: "\u5024\u5207\u308a" },
            psychology: { base: 5, name: "\u5fc3\u7406\u5b66" },
            psychoanalysis: { base: 1, name: "\u7cbe\u795e\u5206\u6790" },
            credit_rating: { base: 0, name: "\u4fe1\u7528" },
            language_own: { base: "EDU*5", name: "\u6bcd\u56fd\u8a9e" },
            language_other: { base: 1, name: "\u4ed6\u56fd\u8a9e" },
            intimidate: { base: 15, name: "\u5a01\u5687" },
            charm: { base: 15, name: "\u9b45\u60d1" }
        },
        knowledge: {
            occult: { base: 5, name: "\u30aa\u30ab\u30eb\u30c8" },
            cthulhu_mythos: { base: 0, name: "\u30af\u30c8\u30a5\u30eb\u30d5\u795e\u8a71" },
            archaeology: { base: 1, name: "\u8003\u53e4\u5b66" },
            anthropology: { base: 1, name: "\u4eba\u985e\u5b66" },
            history: { base: 20, name: "\u6b74\u53f2" },
            natural_world: { base: 10, name: "\u535a\u7269\u5b66" },
            geology: { base: 1, name: "\u5730\u8cea\u5b66" },
            astronomy: { base: 1, name: "\u5929\u6587\u5b66" },
            biology: { base: 1, name: "\u751f\u7269\u5b66" },
            chemistry: { base: 1, name: "\u5316\u5b66" },
            physics: { base: 1, name: "\u7269\u7406\u5b66" },
            pharmacy: { base: 1, name: "\u85ac\u5b66" },
            medicine: { base: 5, name: "\u533b\u5b66" },
            law: { base: 5, name: "\u6cd5\u5f8b" },
            accounting: { base: 10, name: "\u7d4c\u7406" },
            computer_use: { base: 1, name: "\u30b3\u30f3\u30d4\u30e5\u30fc\u30bf\u30fc" },
            appraise: { base: 5, name: "\u9271\u5b9a" },
            cryptography: { base: 1, name: "\u6697\u53f7" },
            forensics: { base: 1, name: "\u6cd5\u533b\u5b66" }
        },
        other: {
            art: { base: 5, name: "\u82b8\u8853" },
            craft: { base: 5, name: "\u5de5\u82b8" },
            sing: { base: 5, name: "\u6b4c\u5531" },
            play_instrument: { base: 5, name: "\u697d\u5668\u6f14\u594f" },
            dance: { base: 5, name: "\u30c0\u30f3\u30b9" },
            acting: { base: 5, name: "\u6f14\u6280" },
            teach: { base: 10, name: "\u6559\u80b2" },
            perform: { base: 5, name: "\u82b8\u80fd" },
            animal_handling: { base: 5, name: "\u52d5\u7269\u4f7f\u3044" },
            survival: { base: 10, name: "\u30b5\u30d0\u30a4\u30d0\u30eb" },
            hypnosis: { base: 1, name: "\u50ac\u7720\u8853" },
            occult_folklore: { base: 5, name: "\u6c11\u4fd7\u5b66" },
            gaming: { base: 5, name: "\u30ae\u30e3\u30f3\u30d6\u30eb" }
        }
    };
    
    // Combined skills map (backward compatibility)
    const ALL_SKILLS_6TH = {
        ...SKILLS_6TH.combat,
        ...SKILLS_6TH.exploration,
        ...SKILLS_6TH.action,
        ...SKILLS_6TH.social,
        ...SKILLS_6TH.knowledge,
        ...SKILLS_6TH.other
    };

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

    // 繝繧､繧ｹ繝ｭ繝ｼ繝ｫ髢｢謨ｰ
    function rollDice(count, sides, bonus) {
        let total = 0;
        for (let i = 0; i < count; i++) {
            total += Math.floor(Math.random() * sides) + 1;
        }
        return total + bonus;
    }

    // 蜈ｨ閭ｽ蜉帛､繝ｭ繝ｼ繝ｫ
    function rollAllAbilities() {
        const { count, sides, bonus } = updateGlobalDiceFormula();
        const abilities = ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'];
        
        abilities.forEach(abilityName => {
            let total = 0;
            for (let i = 0; i < count; i++) {
                total += Math.floor(Math.random() * sides) + 1;
            }
            total += bonus;
            
            const input = document.getElementById(abilityName);
            if (input) {
                input.value = total;
                
                // 繧ｨ繝輔ぉ繧ｯ繝郁ｿｽ蜉
                input.classList.add('dice-rolled');
                setTimeout(() => input.classList.remove('dice-rolled'), 1000);
            }
        });
        
        // Update derived values after rolling
        calculateDerivedStats();
    }

    // Derived stats auto calculation
    function calculateDerivedStats() {
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
        if (document.getElementById('current_hp')) document.getElementById('current_hp').value = hp;
        if (document.getElementById('current_mp')) document.getElementById('current_mp').value = mp;
        if (document.getElementById('current_san')) document.getElementById('current_san').value = san;
        
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
    function createSkillItemHTML(key, skill, category = 'all') {
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

        return `
            <div class="col-xl-3 col-lg-4 col-md-6 mb-3">
                <div class="skill-item border rounded p-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <label for="skill_${key}" class="form-label small fw-bold mb-0">${skill.name}</label>
                        <button type="button" class="btn btn-outline-secondary btn-sm" 
                                onclick="toggleSkillDiceSettings('${key}')" 
                                title="Dice settings">
                            <i class="fas fa-dice-d6"></i>
                        </button>
                    </div>
                    
                    <!-- 繝繧､繧ｹ險ｭ螳壹お繝ｪ繧｢・亥・譛滄撼陦ｨ遉ｺ・・-->
                    <div id="diceSettings_${key}" class="skill-dice-settings mt-2" style="display: none;">
                        <div class="bg-light p-2 rounded">
                            <div class="row g-1">
                                <div class="col-4">
                                    <label class="form-label small">蛟区焚</label>
                                    <input type="number" class="form-control form-control-sm" 
                                           id="skillDiceCount_${key}" min="1" max="10" value="3" 
                                           onchange="updateSkillDiceFormula('${key}')">
                                </div>
                                <div class="col-4">
                                    <label class="form-label small">髱｢謨ｰ</label>
                                    <input type="number" class="form-control form-control-sm" 
                                           id="skillDiceSides_${key}" min="2" max="100" value="6" 
                                           onchange="updateSkillDiceFormula('${key}')">
                                </div>
                                <div class="col-4">
                                    <label class="form-label small">繝懊・繝翫せ</label>
                                    <input type="number" class="form-control form-control-sm" 
                                           id="skillDiceBonus_${key}" min="-50" max="50" value="0" 
                                           onchange="updateSkillDiceFormula('${key}')">
                                </div>
                            </div>
                            <div class="row g-1 mt-1">
                                <div class="col-8">
                                    <span class="small text-muted">蠑・ <span id="skillDiceFormula_${key}">3d6+0</span></span>
                                </div>
                                <div class="col-4">
                                    <button type="button" class="btn btn-primary btn-sm w-100" 
                                            onclick="rollSkillValue('${key}')">
                                        <i class="fas fa-dice"></i> 繝ｭ繝ｼ繝ｫ
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row g-1 mt-2">
                        <div class="col-4">
                            <input type="number" class="form-control form-control-sm text-center skill-base" 
                                   id="base_${key}" value="${baseValue}" min="0" max="100" 
                                   data-skill="${key}" data-default="${skill.base}" 
                                   title="Base value (left click to edit, right click to reset)"
                                   data-bs-toggle="tooltip"
                                   data-bs-placement="top">
                        </div>
                        <div class="col-4">
                            <input type="number" class="form-control form-control-sm occupation-skill text-center" 
                                   id="occ_${key}" min="0" max="90" value="0" placeholder="閨ｷ" 
                                   data-skill="${key}" title="閨ｷ讌ｭ謚閭ｽ">
                        </div>
                        <div class="col-4">
                            <input type="number" class="form-control form-control-sm interest-skill text-center" 
                                   id="int_${key}" min="0" max="90" value="0" placeholder="雜｣" 
                                   data-skill="${key}" title="雜｣蜻ｳ謚閭ｽ">
                        </div>
                    </div>
                    <div class="row g-1 mt-1">
                        <div class="col-12">
                            <div class="skill-total fw-bold text-center" id="total_${key}">${baseValue}%</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    // Skill list generation (by category)
    function generateSkillsList() {
        const combatContainer = document.getElementById('combatSkills');
        const explorationContainer = document.getElementById('explorationSkills');
        const actionContainer = document.getElementById('actionSkills');
        const socialContainer = document.getElementById('socialSkills');
        const knowledgeContainer = document.getElementById('knowledgeSkills');
        const allContainer = document.getElementById('allSkills');

        // Build the full skill list once (source for other tabs)
        if (allContainer) {
            allContainer.innerHTML = '';
            Object.entries(ALL_SKILLS_6TH).forEach(([key, skill]) => {
                allContainer.innerHTML += createSkillItemHTML(key, skill, 'all');
            });
        }

        // Read-only notices for category tabs (use the All tab to edit values)
        const readOnlyNotice = `
            <div class="alert alert-secondary" role="alert">
                <i class="fas fa-info-circle"></i> Use the "All" tab to edit skills.
            </div>
        `;
        if (combatContainer) combatContainer.innerHTML = readOnlyNotice;
        if (explorationContainer) explorationContainer.innerHTML = readOnlyNotice;
        if (actionContainer) actionContainer.innerHTML = readOnlyNotice;
        if (socialContainer) socialContainer.innerHTML = readOnlyNotice;
        if (knowledgeContainer) knowledgeContainer.innerHTML = readOnlyNotice;
    }

    // Skill input event bindings
    function addSkillInputEvents() {
        try {
            document.querySelectorAll('.occupation-skill, .interest-skill').forEach(input => {
                input.addEventListener('input', updateSkillTotals);
            });

            document.querySelectorAll('.skill-base').forEach(input => {
                input.addEventListener('input', function() {
                    try {
                        const skillKey = this.dataset.skill;
                        const value = parseInt(this.value) || 0;

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

                        if (window.customBaseValues && window.customBaseValues[skillKey]) {
                            delete window.customBaseValues[skillKey];
                        }

                        const skill = ALL_SKILLS_6TH[skillKey];
                        if (!skill) {
                            console.warn(`Skill ${skillKey} not found in ALL_SKILLS_6TH`);
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
        } catch (error) {
            console.error('Error in addSkillInputEvents:', error);
        }
    }

    // Toggle skill dice settings panel
    function toggleSkillDiceSettings(skillKey) {
        const settingsDiv = document.getElementById(`diceSettings_${skillKey}`);
        if (settingsDiv) {
            if (settingsDiv.style.display === 'none') {
                settingsDiv.style.display = 'block';
                updateSkillDiceFormula(skillKey);
            } else {
                settingsDiv.style.display = 'none';
            }
        }
    }
    
    // 謚閭ｽ蛻･繝繧､繧ｹ蠑上・譖ｴ譁ｰ
    function updateSkillDiceFormula(skillKey) {
        const count = parseInt(document.getElementById(`skillDiceCount_${skillKey}`)?.value) || 3;
        const sides = parseInt(document.getElementById(`skillDiceSides_${skillKey}`)?.value) || 6;
        const bonus = parseInt(document.getElementById(`skillDiceBonus_${skillKey}`)?.value) || 0;
        
        const formula = `${count}d${sides}${bonus >= 0 ? '+' : ''}${bonus}`;
        const formulaSpan = document.getElementById(`skillDiceFormula_${skillKey}`);
        if (formulaSpan) {
            formulaSpan.textContent = formula;
        }
        
        return { count, sides, bonus };
    }
    
    // 謚閭ｽ蛟､縺ｮ繝繧､繧ｹ繝ｭ繝ｼ繝ｫ
    function rollSkillValue(skillKey) {
        const { count, sides, bonus } = updateSkillDiceFormula(skillKey);
        
        let total = 0;
        for (let i = 0; i < count; i++) {
            total += Math.floor(Math.random() * sides) + 1;
        }
        total += bonus;
        
        // 閨ｷ讌ｭ謚閭ｽ縺ｨ雜｣蜻ｳ謚閭ｽ縺ｮ蜈･蜉帶ｬ・↓蛟､繧定ｨｭ螳・        const occInput = document.getElementById(`occ_${skillKey}`);
        const intInput = document.getElementById(`int_${skillKey}`);
        
        // 謚閭ｽ蜷阪ｒ蜿門ｾ・        const skillName = ALL_SKILLS_6TH[skillKey]?.name || skillKey;
        
        const choice = confirm(
            `${skillName} roll result: ${total}\n\n` +
            'OK: set as occupation skill\n' +
            'Cancel: set as interest skill'
        );
        
        if (choice && occInput) {
            occInput.value = Math.min(total, 90);
            occInput.classList.add('dice-rolled');
            setTimeout(() => occInput.classList.remove('dice-rolled'), 1000);
        } else if (!choice && intInput) {
            intInput.value = Math.min(total, 90);
            intInput.classList.add('dice-rolled');
            setTimeout(() => intInput.classList.remove('dice-rolled'), 1000);
        }
        
        // 謚閭ｽ蜷郁ｨ医ｒ譖ｴ譁ｰ
        updateSkillTotals();
    }
    
    // 蜍慕噪蝓ｺ譛ｬ蛟､繧呈戟縺､謚閭ｽ縺ｮ譖ｴ譁ｰ
    function updateDynamicSkillBases() {
        try {
            // 蝗様�EDEX依存
            const dexEl = document.getElementById('dex');
            if (!dexEl) {
                console.warn('DEX element not found');
                return;
            }
            const dex = parseInt(dexEl.value) || 0;
            const dodgeBaseEl = document.getElementById('base_dodge');
            if (dodgeBaseEl && (!window.customBaseValues || window.customBaseValues['dodge'] === undefined)) {
                dodgeBaseEl.value = dex * 2;
            }
            
            // 母国語 = EDU依存
            const eduEl = document.getElementById('edu');
            if (!eduEl) {
                console.warn('EDU element not found');
                return;
            }
            const edu = parseInt(eduEl.value) || 0;
            const languageOwnBaseEl = document.getElementById('base_language_own');
            if (languageOwnBaseEl && (!window.customBaseValues || window.customBaseValues['language_own'] === undefined)) {
                languageOwnBaseEl.value = edu * 5;
            }
            
            // 謚閭ｽ蜷郁ｨ医ｂ譖ｴ譁ｰ
            updateSkillTotals();
        } catch (error) {
            console.error('Error in updateDynamicSkillBases:', error);
        }
    }
    
    // 繧ｰ繝ｭ繝ｼ繝舌Ν髢｢謨ｰ縺ｨ縺励※螳夂ｾｩ・・TML縺九ｉ蜻ｼ縺ｳ蜃ｺ縺吶◆繧・ｼ・    window.toggleSkillDiceSettings = toggleSkillDiceSettings;
    window.updateSkillDiceFormula = updateSkillDiceFormula;
    window.rollSkillValue = rollSkillValue;

    // 謚閭ｽ蜷郁ｨ域峩譁ｰ
    function updateSkillTotals() {
        // console.log('updateSkillTotals called');
        let occupationUsed = 0;
        let interestUsed = 0;
        let allocatedCount = 0;
        const allocatedSkills = [];
        
        
        Object.keys(ALL_SKILLS_6TH).forEach(key => {
            const occEl = document.getElementById(`occ_${key}`);
            const intEl = document.getElementById(`int_${key}`);
            const totalEl = document.getElementById(`total_${key}`);
            
            if (!occEl || !intEl || !totalEl) return;

            // Base value (prefer custom value if present)
            let base = 0;
            if (window.customBaseValues && window.customBaseValues[key] !== undefined) {
                base = window.customBaseValues[key];
            } else {
                const skill = ALL_SKILLS_6TH[key];
                let baseValue = skill?.base ?? 0;
                if (typeof baseValue === 'string') {
                    if (baseValue === 'DEX*2') {
                        const dex = parseInt(document.getElementById('dex')?.value) || 0;
                        baseValue = dex * 2;
                    } else if (baseValue === 'EDU*5') {
                        const edu = parseInt(document.getElementById('edu')?.value) || 0;
                        baseValue = edu * 5;
                    }
                }
                base = parseInt(baseValue) || 0;
            }

            const occ = parseInt(occEl.value) || 0;
            const int = parseInt(intEl.value) || 0;
            const total = Math.min(base + occ + int, 90);
            totalEl.textContent = `${total}%`;
            
            if (occ > 0 || int > 0) {
                allocatedCount++;
                allocatedSkills.push({
                    key,
                    skill: ALL_SKILLS_6TH[key],
                    base,
                    occ,
                    int,
                    total,
                });
            }
            
            occupationUsed += occ;
            interestUsed += int;
        });

updateAllocatedSkillsTab(allocatedSkills);
        
        // 謖ｯ繧雁・縺第ｸ医∩謚閭ｽ謨ｰ縺ｮ繝舌ャ繧ｸ譖ｴ譁ｰ
        const allocatedCountBadge = document.getElementById('allocatedCount');
        if (allocatedCountBadge) {
            allocatedCountBadge.textContent = allocatedCount;
        }
        
        // 繝昴う繝ｳ繝井ｽｿ逕ｨ迥ｶ豕∵峩譁ｰ
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
        
        // 繝輔ャ繧ｿ繝ｼ縺ｮ謚閭ｽ繝昴う繝ｳ繝郁｡ｨ遉ｺ繧よ峩譁ｰ
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
    
    // Update allocated skills tab
    function updateAllocatedSkillsTab(allocatedSkills) {
        const allocatedContainer = document.getElementById('allocatedSkills');
        
        if (!allocatedContainer) return;
        
        if (allocatedSkills.length === 0) {
            // Empty state message
            allocatedContainer.innerHTML = `
                <div class="col-12 text-center text-muted p-4" id="noAllocatedMessage">
                    <i class="fas fa-info-circle fa-2x mb-2"></i>
                    <p>No skills have been allocated yet.</p>
                </div>
            `;
        } else {
            // Render allocated skill summaries (read-only)
            allocatedContainer.innerHTML = '';
            allocatedSkills.forEach(item => {
                allocatedContainer.innerHTML += `
                    <div class="col-xl-4 col-lg-6 col-md-6 mb-3">
                        <div class="skill-item border rounded p-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="fw-bold">${item.skill.name || item.key}</span>
                                <span class="badge bg-primary">${item.total}%</span>
                            </div>
                            <div class="small text-muted mt-1">
                                ??: ${item.occupationPoints || 0}% / ??: ${item.interestPoints || 0}% / ???: ${item.skill.base}%
                            </div>
                        </div>
                    </div>
                `;
            });
        }
    }



    // 全能力値ダイス（ボタン）
    document.getElementById('rollAllAbilities')?.addEventListener('click', rollAllAbilities);
    
    // 蜈ｨ閭ｽ蜉帛､繝繧､繧ｹ險ｭ螳壹・螟画峩譎ゅ↓繝輔か繝ｼ繝溘Η繝ｩ繧呈峩譁ｰ
    document.getElementById('globalDiceCount')?.addEventListener('input', updateGlobalDiceFormula);
    document.getElementById('globalDiceSides')?.addEventListener('input', updateGlobalDiceFormula);
    document.getElementById('globalDiceBonus')?.addEventListener('input', updateGlobalDiceFormula);
    
    // Recalculate when occupation method changes
    document.getElementById('occupationMethod')?.addEventListener('change', function() {
        calculateSkillPoints();
        updateSkillTotals();
    });
    
    // 繝輔ャ繧ｿ繝ｼ繝懊ち繝ｳ縺ｮ繧､繝吶Φ繝医Μ繧ｹ繝翫・
    document.getElementById('footerRollDice')?.addEventListener('click', function() {
        document.getElementById('rollAllAbilities')?.click();
    });
    
    // 閭ｽ蜉帛､螟画峩譎ゅ↓蜑ｯ谺｡繧ｹ繝・・繧ｿ繧ｹ繧呈峩譁ｰ
    document.querySelectorAll('.ability-score').forEach(input => {
        input.addEventListener('input', calculateDerivedStats);
    });

    // 繝ｪ繧ｻ繝・ヨ繝ｻ險育ｮ励・繧ｿ繝ｳ
    document.getElementById('resetSkillPoints')?.addEventListener('click', function() {
        document.querySelectorAll('.occupation-skill, .interest-skill').forEach(input => {
            input.value = 0;
        });
        updateSkillTotals();
    });

    document.getElementById('calculateSkills')?.addEventListener('click', function() {
        calculateSkillPoints();
        updateSkillTotals();
    });

    // 閨ｷ讌ｭ繝・Φ繝励Ξ繝ｼ繝医ョ繝ｼ繧ｿ
    
    // Occupation template data (skill keys are mapped to display names later)
    const OCCUPATION_TEMPLATES = {
        academic: [
            {
                name: "Professor",
                skills: ["library_use", "psychology", "persuade", "credit_rating", "history", "natural_world", "language_other", "occult"],
                multiplier: 20,
                description: "University faculty or researcher"
            },
            {
                name: "Archaeologist",
                skills: ["archaeology", "library_use", "history", "spot_hidden", "navigate", "photography", "language_other", "appraise"],
                multiplier: 20,
                description: "Field researcher of ruins and artifacts"
            },
            {
                name: "Librarian",
                skills: ["library_use", "accounting", "computer_use", "history", "psychology", "language_other", "spot_hidden", "persuade"],
                multiplier: 20,
                description: "Library or archive specialist"
            }
        ],
        investigation: [
            {
                name: "Private Detective",
                skills: ["spot_hidden", "listen", "track", "psychology", "persuade", "photography", "hide", "law"],
                multiplier: 20,
                description: "Independent investigator"
            },
            {
                name: "Journalist",
                skills: ["persuade", "psychology", "spot_hidden", "listen", "photography", "fast_talk", "library_use", "language_other"],
                multiplier: 20,
                description: "Reporter or writer"
            },
            {
                name: "Police Officer",
                skills: ["law", "spot_hidden", "listen", "intimidate", "handgun", "grapple", "drive_auto", "first_aid"],
                multiplier: 20,
                description: "Law enforcement officer"
            }
        ],
        combat: [
            {
                name: "Soldier",
                skills: ["rifle", "handgun", "dodge", "first_aid", "intimidate", "survival", "navigate", "drive_auto"],
                multiplier: 20,
                description: "Active or former military"
            },
            {
                name: "Martial Artist",
                skills: ["martial_arts", "dodge", "kick", "grapple", "psychology", "intimidate", "jump", "first_aid"],
                multiplier: 20,
                description: "Fighter or boxer"
            }
        ],
        medical: [
            {
                name: "Doctor",
                skills: ["medicine", "first_aid", "biology", "pharmacy", "psychology", "credit_rating", "persuade", "language_other"],
                multiplier: 20,
                description: "Physician or surgeon"
            },
            {
                name: "Nurse",
                skills: ["medicine", "first_aid", "biology", "psychology", "persuade", "listen", "spot_hidden", "pharmacy"],
                multiplier: 20,
                description: "Medical staff"
            }
        ],
        arts: [
            {
                name: "Artist",
                skills: ["art", "psychology", "spot_hidden", "history", "persuade", "charm", "language_other", "appraise"],
                multiplier: 20,
                description: "Painter, sculptor, performer"
            },
            {
                name: "Writer",
                skills: ["language_own", "language_other", "library_use", "psychology", "history", "occult", "persuade", "spot_hidden"],
                multiplier: 20,
                description: "Author or novelist"
            }
        ],
        others: [
            {
                name: "Criminal",
                skills: ["hide", "sneak", "locksmith", "sleight_of_hand", "spot_hidden", "listen", "bargain", "disguise"],
                multiplier: 20,
                description: "Career criminal or outlaw"
            },
            {
                name: "Collector",
                skills: ["credit_rating", "ride", "art", "language_other", "handgun", "history", "charm", "accounting"],
                multiplier: 20,
                description: "Collector or enthusiast"
            }
        ]
    };

function initOccupationTemplates() {
        const categoryLinks = document.querySelectorAll('#occupationCategories a');
        categoryLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // 繧｢繧ｯ繝・ぅ繝悶け繝ｩ繧ｹ縺ｮ蛻・ｊ譖ｿ縺・                categoryLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
                
                // 繧ｫ繝・ざ繝ｪ繝ｼ縺ｮ閨ｷ讌ｭ繧定｡ｨ遉ｺ
                const category = this.dataset.category;
                displayOccupations(category);
            });
        });
        
        // 蛻晄悄陦ｨ遉ｺ
        displayOccupations('academic');
    }

    // 閨ｷ讌ｭ繝ｪ繧ｹ繝医・陦ｨ遉ｺ
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

    // 閨ｷ讌ｭ繝・Φ繝励Ξ繝ｼ繝医・驕ｩ逕ｨ
    function applyOccupationTemplate(occupation) {
        // 閨ｷ讌ｭ蜷阪ｒ險ｭ螳・        document.getElementById('occupation').value = occupation.name;
        
        // 閨ｷ讌ｭ蛟咲紫繧定ｨｭ螳・        const methodSelect = document.getElementById('occupationMethod');
        if (methodSelect && occupation.multiplier === 20) {
            methodSelect.value = 'edu20';
        }
        
        // 謗ｨ螂ｨ謚閭ｽ繧偵ワ繧､繝ｩ繧､繝茨ｼ亥ｮ溯｣・・逵∫払・・        // console.log('謗ｨ螂ｨ謚閭ｽ:', occupation.skills);
        
        // 繝｢繝ｼ繝繝ｫ繧帝哩縺倥ｋ
        const modal = bootstrap.Modal.getInstance(document.getElementById('occupationTemplateModal'));
        modal.hide();
        
        // 謚閭ｽ繝昴う繝ｳ繝医ｒ蜀崎ｨ育ｮ・        calculateSkillPoints();
        updateSkillTotals();
    }

    // Bootstrap 繧ｿ繝門・譛溷喧
    const triggerTabList = [].slice.call(document.querySelectorAll('#skillTabs button'));
    triggerTabList.forEach(function (triggerEl) {
        const tabTrigger = new bootstrap.Tab(triggerEl);
        
        triggerEl.addEventListener('click', function (event) {
            event.preventDefault();
            tabTrigger.show();
        });
    });
    
    // 逕ｻ蜒上い繝・・繝ｭ繝ｼ繝画ｩ溯・
    function initImageUpload() {
        const imageInput = document.getElementById('character-image');
        const imagePreview = document.getElementById('image-preview');
        const previewImg = document.getElementById('preview-img');
        const removeBtn = document.getElementById('remove-image');
        
        if (!imageInput) return;
        
        // 繝輔ぃ繧､繝ｫ驕ｸ謚樊凾縺ｮ繝励Ξ繝薙Η繝ｼ陦ｨ遉ｺ
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
        
        // 逕ｻ蜒丞炎髯､
        removeBtn?.addEventListener('click', function() {
            imageInput.value = '';
            previewImg.src = '';
            imagePreview.style.display = 'none';
        });
    }
    
    // ???
    updateGlobalDiceFormula();
    generateSkillsList();
    addSkillInputEvents();  // ????????????????????
    
    // ??????????????????
    setTimeout(() => {
        rollAllAbilities();
    }, 0);
    
    initOccupationTemplates(); // 閨ｷ讌ｭ繝・Φ繝励Ξ繝ｼ繝域ｩ溯・繧貞・譛溷喧
    initImageUpload(); // 逕ｻ蜒上い繝・・繝ｭ繝ｼ繝画ｩ溯・繧貞・譛溷喧
    
    // Form submit handling
    const characterForm = document.getElementById('character-sheet-form');
    if (characterForm) {
        characterForm.addEventListener('submit', function(e) {
            e.preventDefault();
        
            const formData = new FormData(this);
            const data = {};
            
            // Collect form data (except file)
            for (let [key, value] of formData.entries()) {
                if (key !== 'character_image') {
                    data[key] = value;
                }
            }
            
            // Validation
            if (!data.name) {
                alert('Character name is required.');
                return;
            }
            
            // Ability validation
            const abilities = ['str_value', 'con_value', 'pow_value', 'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value'];
            let hasAbilities = false;
            for (const ability of abilities) {
                if (data[ability] && parseInt(data[ability]) > 0) {
                    hasAbilities = true;
                    break;
                }
            }

            
            if (!hasAbilities) {
                alert('Please set ability scores.');
                return;
            }

            // 6迚育畑縺ｫAPI繧ｨ繝ｳ繝峨・繧､繝ｳ繝医↓騾∽ｿ｡
            const apiData = {
            edition: '6th',
            // 笨・name縺ｯ繝輔か繝ｼ繝縺ｮname="name"
            name: data.name,
            player_name: data.player_name || '',
            age: data.age ? parseInt(data.age, 10) : null,
            gender: data.gender || '',
            occupation: data.occupation || '',
            birthplace: data.birthplace || '',
            residence: data.residence || '',

            // 笨・ability縺ｯ繝輔か繝ｼ繝縺ｮname="xxx_value"
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
            
            // 謌ｦ髣倥せ繝・・繧ｿ繧ｹ
            if (data.current_hp) apiData.hit_points_current = parseInt(data.current_hp);
            if (data.current_mp) apiData.magic_points_current = parseInt(data.current_mp);
            if (data.current_san) apiData.sanity_points_current = parseInt(data.current_san);
            if (data.armor) apiData.armor = parseInt(data.armor) || 0;
            
            // 雋｡逕｣諠・ｱ
            if (data.money) apiData.money = parseInt(data.money) || 0;
            if (data.assets) apiData.assets = parseInt(data.assets) || 0;
            if (data.income) apiData.income = parseInt(data.income) || 0;
            
            // 閭梧勹諠・ｱ繧地otes縺ｫ邨ｱ蜷・            const backgroundNotes = [];
            if (data.backstory) backgroundNotes.push(`閭梧勹繧ｹ繝医・繝ｪ繝ｼ:\n${data.backstory}`);
            if (data.appearance) backgroundNotes.push(`螟冶ｦ・\n${data.appearance}`);
            if (data.ideals) backgroundNotes.push(`菫｡蠢ｵ繝ｻ菫｡譚｡:\n${data.ideals}`);
            if (data.bonds) backgroundNotes.push(`驥崎ｦ√↑莠ｺ迚ｩ:\n${data.bonds}`);
            if (data.flaws) backgroundNotes.push(`蠑ｱ轤ｹ繝ｻ諱先也裸:\n${data.flaws}`);
            if (data.items) backgroundNotes.push(`謇謖∝刀:\n${data.items}`);
            
            if (backgroundNotes.length > 0) {
                apiData.notes = (apiData.notes ? apiData.notes + '\n\n' : '') + backgroundNotes.join('\n\n');
            }
            
            // 謚閭ｽ繝・・繧ｿ縺ｮ蜿朱寔
            const skills = [];
            document.querySelectorAll('.occupation-skill').forEach(input => {
                const skillKey = input.dataset.skill;
                const occValue = parseInt(input.value) || 0;
                const intValue = parseInt(document.getElementById(`int_${skillKey}`)?.value) || 0;
                
                if (occValue > 0 || intValue > 0) {
                    // 繧ｫ繧ｹ繧ｿ繝蝓ｺ譛ｬ蛟､縺後≠繧後・菴ｿ逕ｨ縲√↑縺代ｌ縺ｰ繝・ヵ繧ｩ繝ｫ繝亥､繧剃ｽｿ逕ｨ
                    let baseValue = 0;
                    if (window.customBaseValues && window.customBaseValues[skillKey] !== undefined) {
                        baseValue = window.customBaseValues[skillKey];
                    } else {
                        const skillData = ALL_SKILLS_6TH[skillKey];
                        if (skillData) {
                            let defaultBase = skillData.base;
                            if (typeof defaultBase === 'string') {
                                if (defaultBase === 'DEX*2') {
                                    const dex = parseInt(document.getElementById('dex')?.value) || 0;
                                    defaultBase = dex * 2;
                                } else if (defaultBase === 'EDU*5') {
                                    const edu = parseInt(document.getElementById('edu')?.value) || 0;
                                    defaultBase = edu * 5;
                                }
                            }
                            baseValue = parseInt(defaultBase) || 0;
                        }
                    }
                    
                    skills.push({
                        skill_name: ALL_SKILLS_6TH[skillKey]?.name || skillKey,
                        base_value: baseValue,
                        occupation_points: occValue,
                        interest_points: intValue,
                        other_points: 0
                    });
                }
            });
            
            if (skills.length > 0) {
                apiData.skills = skills;
            }
            
            // Send image when present
            const imageFile = formData.get('character_image');
            if (imageFile && imageFile.size > 0) {
                const submitFormData = new FormData();

                Object.keys(apiData).forEach(key => {
                    if (key === 'skills' || key === 'equipment') {
                        submitFormData.append(key, JSON.stringify(apiData[key]));
                    } else {
                        submitFormData.append(key, apiData[key]);
                    }
                });

                submitFormData.append('character_image', imageFile);

                // Send to API with multipart/form-data
                fetch('/accounts/character-sheets/create_6th_edition/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    },
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
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    },
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
});
