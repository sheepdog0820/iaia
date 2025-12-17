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
                
                // エフェクト追加
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

    function calculateDerivedStats6th(str, con, pow, dex, int, edu, siz) {
        // アイチE�� = INT ÁE5
        if (document.getElementById('idea')) {
            document.getElementById('idea').value = int * 5;
        }
        
        // 幸遁E= POW ÁE5
        if (document.getElementById('luck')) {
            document.getElementById('luck').value = pow * 5;
        }
        
        // 知譁E= EDU ÁE5
        if (document.getElementById('know')) {
            document.getElementById('know').value = edu * 5;
        }

        // ????????
        const setDisplay = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };
        setDisplay('idea_display', int * 5);
        setDisplay('luck_display', pow * 5);
        setDisplay('know_display', edu * 5);

        // ダメージボ�Eナス計算！E版！E        const total = str + siz;
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
            'edu20': edu * 20,
            'edu10app10': edu * 10 + app * 10,
            'edu10dex10': edu * 10 + dex * 10,
            'edu10pow10': edu * 10 + pow * 10,
            'edu10str10': edu * 10 + str * 10,
            'edu10con10': edu * 10 + con * 10,
            'edu10siz10': edu * 10 + siz * 10
        };
        
        return calculationMethods[method] || edu * 20;
    }
    // Total skill points calculation
    function calculateSkillPoints() {
        const int = parseInt(document.getElementById('int')?.value) || 0;
        const method = document.getElementById('occupationMethod')?.value || 'edu20';
        
        // 職業技能ポインチE 選択された計算方式による
        const occupationPoints = calculateOccupationSkillPoints(method);
        
        // 趣味技能ポインチE INT ÁE10
        const interestPoints = int * 10;
        
        if (document.getElementById('occupationTotal')) {
            document.getElementById('occupationTotal').value = occupationPoints;
        }
        const occupationPointsDisplay = document.getElementById('occupation_points_display');
        if (occupationPointsDisplay) {
            occupationPointsDisplay.textContent = occupationPoints;
        }
        if (document.getElementById('interestTotal')) {
            document.getElementById('interestTotal').value = interestPoints;
        }
    }



    // 技能アイチE��HTML生�E
    function createSkillItemHTML(key, skill, category = 'all') {
        let baseValue = skill.base;
        if (typeof baseValue === 'string') {
            // 動的基本値計箁E            if (baseValue === 'DEX*2') {
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
                                title="ダイス設宁E>
                            <i class="fas fa-dice-d6"></i>
                        </button>
                    </div>
                    
                    <!-- ダイス設定エリア�E��E期非表示�E�E-->
                    <div id="diceSettings_${key}" class="skill-dice-settings mt-2" style="display: none;">
                        <div class="bg-light p-2 rounded">
                            <div class="row g-1">
                                <div class="col-4">
                                    <label class="form-label small">個数</label>
                                    <input type="number" class="form-control form-control-sm" 
                                           id="skillDiceCount_${key}" min="1" max="10" value="3" 
                                           onchange="updateSkillDiceFormula('${key}')">
                                </div>
                                <div class="col-4">
                                    <label class="form-label small">面数</label>
                                    <input type="number" class="form-control form-control-sm" 
                                           id="skillDiceSides_${key}" min="2" max="100" value="6" 
                                           onchange="updateSkillDiceFormula('${key}')">
                                </div>
                                <div class="col-4">
                                    <label class="form-label small">ボ�Eナス</label>
                                    <input type="number" class="form-control form-control-sm" 
                                           id="skillDiceBonus_${key}" min="-50" max="50" value="0" 
                                           onchange="updateSkillDiceFormula('${key}')">
                                </div>
                            </div>
                            <div class="row g-1 mt-1">
                                <div class="col-8">
                                    <span class="small text-muted">弁E <span id="skillDiceFormula_${key}">3d6+0</span></span>
                                </div>
                                <div class="col-4">
                                    <button type="button" class="btn btn-primary btn-sm w-100" 
                                            onclick="rollSkillValue('${key}')">
                                        <i class="fas fa-dice"></i> ロール
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
                                   id="occ_${key}" min="0" max="90" value="0" placeholder="職" 
                                   data-skill="${key}" title="職業技能">
                        </div>
                        <div class="col-4">
                            <input type="number" class="form-control form-control-sm interest-skill text-center" 
                                   id="int_${key}" min="0" max="90" value="0" placeholder="趣" 
                                   data-skill="${key}" title="趣味技能">
                        </div>
                    </div>
                    <div class="row g-1 mt-1">
                        <div class="col-12">
