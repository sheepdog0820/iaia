document.addEventListener('DOMContentLoaded', function() {

    // 6迚亥渕譛ｬ謚閭ｽ繝・・繧ｿ・医き繝・ざ繝ｪ蛻・￠・・    const SKILLS_6TH = {
        // 謌ｦ髣倡ｳｻ謚閭ｽ
        "combat": {
            "dodge": { base: "DEXﾃ・", name: "蝗樣∩" },
            "martial_arts": { base: 1, name: "繝槭・繧ｷ繝｣繝ｫ繧｢繝ｼ繝・ },
            "throw": { base: 25, name: "謚墓憧" },
            "first_aid": { base: 30, name: "蠢懈･謇句ｽ・ },
            "fist_punch": { base: 50, name: "縺薙・縺暦ｼ医ヱ繝ｳ繝・ｼ・ },
            "head_butt": { base: 10, name: "鬆ｭ遯√″" },
            "kick": { base: 25, name: "繧ｭ繝・け" },
            "grapple": { base: 25, name: "邨・∩莉倥″" },
            "knife": { base: 20, name: "繝翫う繝・ },
            "club": { base: 25, name: "縺薙ｓ譽・ },
            "handgun": { base: 20, name: "諡ｳ驫・ },
            "rifle": { base: 25, name: "繝ｩ繧､繝輔Ν" },
            "shotgun": { base: 30, name: "繧ｷ繝ｧ繝・ヨ繧ｬ繝ｳ" },
            "submachine_gun": { base: 15, name: "繧ｵ繝悶・繧ｷ繝ｳ繧ｬ繝ｳ" },
            "machine_gun": { base: 15, name: "繝槭す繝ｳ繧ｬ繝ｳ" },
            "bow": { base: 15, name: "蠑・ },
            "sword": { base: 20, name: "蜑｣" },
            "spear": { base: 20, name: "讒・ },
            "whip": { base: 5, name: "髷ｭ" }
        },
        // 謗｢邏｢謚閭ｽ
        "exploration": {
            "spot_hidden": { base: 25, name: "逶ｮ譏・ },
            "listen": { base: 25, name: "閨槭″閠ｳ" },
            "library_use": { base: 25, name: "蝗ｳ譖ｸ鬢ｨ" },
            "track": { base: 10, name: "霑ｽ霍｡" },
            "navigate": { base: 10, name: "繝翫ン繧ｲ繝ｼ繝・ },
            "photography": { base: 10, name: "蜀咏悄陦・ }
        },
        // 陦悟虚謚閭ｽ
        "action": {
            "climb": { base: 40, name: "逋ｻ謾" },
            "jump": { base: 25, name: "霍ｳ霄・ },
            "swim": { base: 25, name: "豌ｴ豕ｳ" },
            "sneak": { base: 10, name: "蠢阪・豁ｩ縺・ },
            "hide": { base: 10, name: "髫繧後ｋ" },
            "conceal": { base: 15, name: "髫縺・ },
            "locksmith": { base: 1, name: "骰ｵ髢九￠" },
            "drive_auto": { base: 20, name: "驕玖ｻ｢" },
            "pilot": { base: 1, name: "謫咲ｸｦ" },
            "ride": { base: 5, name: "荵鈴ｦｬ" },
            "electrical_repair": { base: 10, name: "髮ｻ豌嶺ｿｮ逅・ },
            "electronics": { base: 1, name: "髮ｻ蟄仙ｷ･蟄ｦ" },
            "mechanical_repair": { base: 20, name: "讖滓｢ｰ菫ｮ逅・ },
            "operate_heavy_machine": { base: 1, name: "驥肴ｩ滓｢ｰ謫堺ｽ・ },
            "disguise": { base: 1, name: "螟芽｣・ },
            "sleight_of_hand": { base: 10, name: "謇九＆縺ｰ縺・ }
        },
        // 莠､貂画橿閭ｽ
        "social": {
            "persuade": { base: 15, name: "隱ｬ蠕・ },
            "fast_talk": { base: 5, name: "險縺・￥繧九ａ" },
            "bargain": { base: 5, name: "蛟､蛻・ｊ" },
            "psychology": { base: 5, name: "蠢・炊蟄ｦ" },
            "psychoanalysis": { base: 1, name: "邊ｾ逾槫・譫・ },
            "credit_rating": { base: 0, name: "菫｡逕ｨ" },
            "language_own": { base: "EDUﾃ・", name: "豈榊嵜隱・ },
            "language_other": { base: 1, name: "莉門嵜隱・ },
            "intimidate": { base: 15, name: "螽∝嚊" },
            "charm": { base: 15, name: "鬲・ヱ" }
        },
        // 遏･隴俶橿閭ｽ
        "knowledge": {
            "occult": { base: 5, name: "繧ｪ繧ｫ繝ｫ繝・ },
            "cthulhu_mythos": { base: 0, name: "繧ｯ繝医ぇ繝ｫ繝慕･櫁ｩｱ" },
            "archaeology": { base: 1, name: "閠・商蟄ｦ" },
            "anthropology": { base: 1, name: "莠ｺ鬘槫ｭｦ" },
            "history": { base: 20, name: "豁ｴ蜿ｲ" },
            "natural_world": { base: 10, name: "蜊夂黄蟄ｦ" },
            "geology": { base: 1, name: "蝨ｰ雉ｪ蟄ｦ" },
            "astronomy": { base: 1, name: "螟ｩ譁・ｭｦ" },
            "biology": { base: 1, name: "逕溽黄蟄ｦ" },
            "chemistry": { base: 1, name: "蛹門ｭｦ" },
            "physics": { base: 1, name: "迚ｩ逅・ｭｦ" },
            "pharmacy": { base: 1, name: "阮ｬ蟄ｦ" },
            "medicine": { base: 5, name: "蛹ｻ蟄ｦ" },
            "law": { base: 5, name: "豕募ｾ・ },
            "accounting": { base: 10, name: "邨檎炊" },
            "computer_use": { base: 1, name: "繧ｳ繝ｳ繝斐Η繝ｼ繧ｿ繝ｼ" },
            "appraise": { base: 5, name: "髑大ｮ・ },
            "cryptography": { base: 1, name: "證怜捷" },
            "forensics": { base: 1, name: "髑題ｭ・ }
        },
        // 縺昴・莉匁橿閭ｽ
        "other": {
            "art": { base: 5, name: "闃ｸ陦・ },
            "craft": { base: 5, name: "蟾･闃ｸ" },
            "sing": { base: 5, name: "豁悟罰" },
            "play_instrument": { base: 5, name: "讌ｽ蝎ｨ貍泌･・ },
            "dance": { base: 5, name: "繝繝ｳ繧ｹ" },
            "acting": { base: 5, name: "貍疲橿" },
            "teach": { base: 10, name: "謨呵ご" },
            "perform": { base: 5, name: "闃ｸ閭ｽ" },
            "animal_handling": { base: 5, name: "蜍慕黄菴ｿ縺・ },
            "survival": { base: 10, name: "繧ｵ繝舌う繝舌Ν" },
            "hypnosis": { base: 1, name: "蛯ｬ逵陦・ },
            "occult_folklore": { base: 5, name: "豌台ｿ怜ｭｦ" },
            "gaming": { base: 5, name: "繧ｮ繝｣繝ｳ繝悶Ν" }
        }
    };
    
    // 蜈ｨ謚閭ｽ縺ｮ邨ｱ蜷医が繝悶ず繧ｧ繧ｯ繝茨ｼ亥ｾ梧婿莠呈鋤諤ｧ縺ｮ縺溘ａ・・    const ALL_SKILLS_6TH = {
        ...SKILLS_6TH.combat,
        ...SKILLS_6TH.exploration,
        ...SKILLS_6TH.action,
        ...SKILLS_6TH.social,
        ...SKILLS_6TH.knowledge,
        ...SKILLS_6TH.other
    };

    // 蜈ｨ閭ｽ蜉帛､繝繧､繧ｹ險ｭ螳壹・譖ｴ譁ｰ
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
        
        // 閾ｪ蜍戊ｨ育ｮ怜ｮ溯｡・        calculateDerivedStats();
    }

    // 蜑ｯ谺｡繧ｹ繝・・繧ｿ繧ｹ閾ｪ蜍戊ｨ育ｮ・    function calculateDerivedStats() {
        const str = parseInt(document.getElementById('str')?.value) || 0;
        const con = parseInt(document.getElementById('con')?.value) || 0;
        const pow = parseInt(document.getElementById('pow')?.value) || 0;
        const dex = parseInt(document.getElementById('dex')?.value) || 0;
        const int = parseInt(document.getElementById('int')?.value) || 0;
        const edu = parseInt(document.getElementById('edu')?.value) || 0;
        const siz = parseInt(document.getElementById('siz')?.value) || 0;
        
        // 6迚郁ｨ育ｮ怜ｼ上↓蝓ｺ縺･縺擾ｼ育ｫｯ謨ｰ蛻・ｊ荳翫￡・・        const hp = Math.ceil((con + siz) / 2);
        const mp = pow;  // MP = POW
        const san = pow * 5;  // SAN = POW ﾃ・5
        
        if (document.getElementById('hp')) document.getElementById('hp').value = hp;
        if (document.getElementById('mp')) document.getElementById('mp').value = mp;
        if (document.getElementById('san')) document.getElementById('san').value = san;
        
        // 迴ｾ蝨ｨ蛟､繧ょ・譛溷､縺ｨ縺励※險ｭ螳・        if (document.getElementById('current_hp')) document.getElementById('current_hp').value = hp;
        if (document.getElementById('current_mp')) document.getElementById('current_mp').value = mp;
        if (document.getElementById('current_san')) document.getElementById('current_san').value = san;
        
        // 譛螟ｧSAN繧りｨｭ螳夲ｼ・迚医〒縺ｯ蛻晄悄蛟､縺ｨ蜷後§・・        if (document.getElementById('sanity_max')) document.getElementById('sanity_max').value = san;
        
        // ????????
        const updateDisplay = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };
        updateDisplay('hp_display', hp);
        updateDisplay('mp_display', mp);
        updateDisplay('san_display', san);
        
        // 6迚亥崋譛峨・險育ｮ・        calculateDerivedStats6th(str, con, pow, dex, int, edu, siz);
        
        // 謚閭ｽ繝昴う繝ｳ繝郁ｨ育ｮ・        calculateSkillPoints();
        
        // 蜍慕噪蝓ｺ譛ｬ蛟､縺ｮ謚閭ｽ繧呈峩譁ｰ・・EX繧ЕDU縺ｮ螟画峩譎ゑｼ・        updateDynamicSkillBases();
    }
    
    function calculateDerivedStats6th(str, con, pow, dex, int, edu, siz) {
        // 繧｢繧､繝・い = INT ﾃ・5
        if (document.getElementById('idea')) {
            document.getElementById('idea').value = int * 5;
        }
        
        // 蟷ｸ驕・= POW ﾃ・5
        if (document.getElementById('luck')) {
            document.getElementById('luck').value = pow * 5;
        }
        
        // 遏･隴・= EDU ﾃ・5
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

        // 繝繝｡繝ｼ繧ｸ繝懊・繝翫せ險育ｮ暦ｼ・迚茨ｼ・        const total = str + siz;
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

    // 閨ｷ讌ｭ謚閭ｽ繝昴う繝ｳ繝郁ｨ育ｮ玲婿蠑・    function calculateOccupationSkillPoints(method) {
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
    
    // 謚閭ｽ繝昴う繝ｳ繝郁ｨ育ｮ・    function calculateSkillPoints() {
        const int = parseInt(document.getElementById('int')?.value) || 0;
        const method = document.getElementById('occupationMethod')?.value || 'edu20';
        
        // 閨ｷ讌ｭ謚閭ｽ繝昴う繝ｳ繝・ 驕ｸ謚槭＆繧後◆險育ｮ玲婿蠑上↓繧医ｋ
        const occupationPoints = calculateOccupationSkillPoints(method);
        
        // 雜｣蜻ｳ謚閭ｽ繝昴う繝ｳ繝・ INT ﾃ・10
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



    // 謚閭ｽ繧｢繧､繝・ΒHTML逕滓・
    function createSkillItemHTML(key, skill, category = 'all') {
        let baseValue = skill.base;
        if (typeof baseValue === 'string') {
            // 蜍慕噪蝓ｺ譛ｬ蛟､險育ｮ・            if (baseValue === 'DEXﾃ・') {
                const dex = parseInt(document.getElementById('dex')?.value) || 0;
                baseValue = dex * 2;
            } else if (baseValue === 'EDUﾃ・') {
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
                                title="繝繧､繧ｹ險ｭ螳・>
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
                                   title="蝓ｺ譛ｬ蛟､・医け繝ｪ繝・け縺ｧ邱ｨ髮・∝承繧ｯ繝ｪ繝・け縺ｧ繝ｪ繧ｻ繝・ヨ・・
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
    
    // 謚閭ｽ繝ｪ繧ｹ繝育函謌撰ｼ医き繝・ざ繝ｪ蛻･・・    function generateSkillsList() {
        // 蜷・き繝・ざ繝ｪ縺ｮ繧ｳ繝ｳ繝・リ繧貞叙蠕暦ｼ育ｷｨ髮・・蜈ｨ陦ｨ遉ｺ繧ｿ繝悶ｒ蜚ｯ荳縺ｮ繧ｽ繝ｼ繧ｹ縺ｫ縺吶ｋ・・        const combatContainer = document.getElementById('combatSkills');
        const explorationContainer = document.getElementById('explorationSkills');
        const actionContainer = document.getElementById('actionSkills');
        const socialContainer = document.getElementById('socialSkills');
        const knowledgeContainer = document.getElementById('knowledgeSkills');
        const allContainer = document.getElementById('allSkills');

        // 邱ｨ髮・畑縺ｮ謚閭ｽ陦後・蜈ｨ陦ｨ遉ｺ繧ｿ繝悶・縺ｿ逕滓・縺励！D驥崎､・ｒ髦ｲ縺・        if (allContainer) {
            allContainer.innerHTML = '';
            Object.entries(ALL_SKILLS_6TH).forEach(([key, skill]) => {
                allContainer.innerHTML += createSkillItemHTML(key, skill, 'all');
            });
        }

        // 繧ｫ繝・ざ繝ｪ繧ｿ繝悶↓縺ｯ邱ｨ髮・ｸ榊庄縺ｮ譯亥・縺縺代ｒ陦ｨ遉ｺ
        const readOnlyNotice = `
            <div class="alert alert-secondary" role="alert">
                <i class="fas fa-info-circle"></i> 蜷・橿閭ｽ縺ｮ邱ｨ髮・・縲悟・陦ｨ遉ｺ縲阪ち繝悶〒陦後▲縺ｦ縺上□縺輔＞縲・            </div>
        `;
        if (combatContainer) combatContainer.innerHTML = readOnlyNotice;
        if (explorationContainer) explorationContainer.innerHTML = readOnlyNotice;
        if (actionContainer) actionContainer.innerHTML = readOnlyNotice;
        if (socialContainer) socialContainer.innerHTML = readOnlyNotice;
        if (knowledgeContainer) knowledgeContainer.innerHTML = readOnlyNotice;
        
        // 謚閭ｽ蜈･蜉帙う繝吶Φ繝郁ｿｽ蜉・亥・陦ｨ遉ｺ繧ｿ繝悶・縺ｿ・・        addSkillInputEvents();
        
        // 繝・・繝ｫ繝√ャ繝励・蛻晄悄蛹・        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }

    // 謚閭ｽ蜈･蜉帙う繝吶Φ繝・    function addSkillInputEvents() {
        try {
            document.querySelectorAll('.occupation-skill, .interest-skill').forEach(input => {
                input.addEventListener('input', updateSkillTotals);
            });
            
            // 蝓ｺ譛ｬ蛟､蜈･蜉帙う繝吶Φ繝医ｒ霑ｽ蜉
            document.querySelectorAll('.skill-base').forEach(input => {
                input.addEventListener('input', function() {
                    try {
                        const skillKey = this.dataset.skill;
                        const value = parseInt(this.value) || 0;
                        
                        // 繧ｫ繧ｹ繧ｿ繝蝓ｺ譛ｬ蛟､繧剃ｿ晏ｭ・                        if (!window.customBaseValues) {
                            window.customBaseValues = {};
                        }
                        window.customBaseValues[skillKey] = value;
                        
                        // 繧ｫ繧ｹ繧ｿ繝槭う繧ｺ縺輔ｌ縺溘％縺ｨ繧堤､ｺ縺吶け繝ｩ繧ｹ繧定ｿｽ蜉
                        this.classList.add('customized');
                        
                        // 謚閭ｽ蜷郁ｨ医ｒ譖ｴ譁ｰ
                        updateSkillTotals();
                    } catch (error) {
                        console.error('Error in skill base input handler:', error);
                    }
                });
            
            // 蜿ｳ繧ｯ繝ｪ繝・け縺ｧ繝・ヵ繧ｩ繝ｫ繝亥､縺ｫ繝ｪ繧ｻ繝・ヨ
            input.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                try {
                    const skillKey = this.dataset.skill;
                    const defaultValue = this.dataset.default;
                    
                    // 繧ｫ繧ｹ繧ｿ繝蝓ｺ譛ｬ蛟､繧偵け繝ｪ繧｢
                    if (window.customBaseValues && window.customBaseValues[skillKey]) {
                        delete window.customBaseValues[skillKey];
                    }
                    
                    // 繧ｫ繧ｹ繧ｿ繝槭う繧ｺ繧ｯ繝ｩ繧ｹ繧貞炎髯､
                    this.classList.remove('customized');
                    
                    // 繝・ヵ繧ｩ繝ｫ繝亥､縺ｫ謌ｻ縺・                    const skill = ALL_SKILLS_6TH[skillKey];
                    if (!skill) {
                        console.warn(`Skill ${skillKey} not found in ALL_SKILLS_6TH`);
                        return;
                    }
                    let baseValue = skill.base;
                    if (typeof baseValue === 'string') {
                        if (baseValue === 'DEXﾃ・') {
                            const dex = parseInt(document.getElementById('dex')?.value) || 0;
                            baseValue = dex * 2;
                        } else if (baseValue === 'EDUﾃ・') {
                            const edu = parseInt(document.getElementById('edu')?.value) || 0;
                            baseValue = edu * 5;
                        }
                    }
                    this.value = baseValue;
                    
                    // 謚閭ｽ蜷郁ｨ医ｒ譖ｴ譁ｰ
                    updateSkillTotals();
                    
                    // 繝輔ぅ繝ｼ繝峨ヰ繝・け陦ｨ遉ｺ
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
    
    // 謚閭ｽ蛻･繝繧､繧ｹ險ｭ螳壹・陦ｨ遉ｺ/髱櫁｡ｨ遉ｺ蛻・ｊ譖ｿ縺・    function toggleSkillDiceSettings(skillKey) {
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
        
        // 繝繧､繧｢繝ｭ繧ｰ縺ｧ謖ｯ繧雁・縺代ｒ驕ｸ謚・        const choice = confirm(
            `${skillName}縺ｮ繝繧､繧ｹ繝ｭ繝ｼ繝ｫ邨先棡: ${total}\n\n` +
            'OK: 閨ｷ讌ｭ謚閭ｽ縺ｫ險ｭ螳喀n' +
            '繧ｭ繝｣繝ｳ繧ｻ繝ｫ: 雜｣蜻ｳ謚閭ｽ縺ｫ險ｭ螳・
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
            // 蝗樣∩・・EXﾃ・・・            const dexEl = document.getElementById('dex');
            if (!dexEl) {
                console.warn('DEX element not found');
                return;
            }
            const dex = parseInt(dexEl.value) || 0;
            const dodgeBaseEl = document.getElementById('base_dodge');
            if (dodgeBaseEl && (!window.customBaseValues || window.customBaseValues['dodge'] === undefined)) {
                dodgeBaseEl.value = dex * 2;
            }
            
            // 豈榊嵜隱橸ｼ・DUﾃ・・・            const eduEl = document.getElementById('edu');
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
            
            if (occEl && intEl && totalEl) {
                // 蝓ｺ譛ｬ蛟､繧貞叙蠕暦ｼ医き繧ｹ繧ｿ繝蛟､縺後≠繧句ｴ蜷医・縺昴ｌ繧剃ｽｿ逕ｨ・・                let base = 0;
                if (window.customBaseValues && window.customBaseValues[key] !== undefined) {
                    base = window.customBaseValues[key];
                } else {
                    // 繝・ヵ繧ｩ繝ｫ繝医・蝓ｺ譛ｬ蛟､繧貞虚逧・↓險育ｮ・                    const skill = ALL_SKILLS_6TH[key];
                    let baseValue = skill.base;
                    if (typeof baseValue === 'string') {
                        if (baseValue === 'DEXﾃ・') {
                            const dex = parseInt(document.getElementById('dex')?.value) || 0;
                            baseValue = dex * 2;
                        } else if (baseValue === 'EDUﾃ・') {
                            const edu = parseInt(document.getElementById('edu')?.value) || 0;
                            baseValue = edu * 5;
                        }
                    }
                    base = parseInt(baseValue) || 0;
                }
                const occ = parseInt(occEl.value) || 0;
                const int = parseInt(intEl.value) || 0;
                
                const total = Math.min(base + occ + int, 90);
                totalEl.textContent = total + '%';
                
                // 繝昴う繝ｳ繝医′謖ｯ繧雁・縺代ｉ繧後※縺・ｋ謚閭ｽ繧定ｨ倬鹸
                if (occ > 0 || int > 0) {
                    allocatedCount++;
                    allocatedSkills.push({
                    key: key,
                    skill: ALL_SKILLS_6TH[key], // 竊・縺薙％繧剃ｿｮ豁｣・域悴螳夂ｾｩskill繧剃ｽｿ繧上↑縺・ｼ・                    base: base,
                    occ: occ,
                    int: int,
                    total: total
                    });
                }
                
                occupationUsed += occ;
                interestUsed += int;
            }
        });
        
        // 謖ｯ繧雁・縺第ｸ医∩謚閭ｽ繧ｿ繝悶・譖ｴ譁ｰ
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
    
    // 謖ｯ繧雁・縺第ｸ医∩謚閭ｽ繧ｿ繝悶・譖ｴ譁ｰ
    function updateAllocatedSkillsTab(allocatedSkills) {
        const allocatedContainer = document.getElementById('allocatedSkills');
        
        if (!allocatedContainer) return;
        
        if (allocatedSkills.length === 0) {
            // 謖ｯ繧雁・縺代ｉ繧後◆謚閭ｽ縺後↑縺・ｴ蜷・            allocatedContainer.innerHTML = `
                <div class="col-12 text-center text-muted p-4" id="noAllocatedMessage">
                    <i class="fas fa-info-circle fa-2x mb-2"></i>
                    <p>縺ｾ縺繝昴う繝ｳ繝医ｒ謖ｯ繧雁・縺代◆謚閭ｽ縺後≠繧翫∪縺帙ｓ縲・/p>
                </div>
            `;
        } else {
            // 謖ｯ繧雁・縺代ｉ繧後◆謚閭ｽ繧偵し繝槭Μ繝ｼ陦ｨ遉ｺ・磯㍾隍⑩D繧帝∩縺代ｋ縺溘ａ蜈･蜉帶ｬ・・菴懊ｉ縺ｪ縺・ｼ・            allocatedContainer.innerHTML = '';
            allocatedSkills.forEach(item => {
                allocatedContainer.innerHTML += `
                    <div class="col-xl-4 col-lg-6 col-md-6 mb-3">
                        <div class="skill-item border rounded p-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="fw-bold">${item.skill.name || item.key}</span>
                                <span class="badge bg-primary">${item.total}%</span>
                            </div>
                            <div class="small text-muted mt-1">
                                蝓ｺ譛ｬ:${item.base}% / 閨ｷ:${item.occ}% / 雜｣:${item.int}%
                            </div>
                        </div>
                    </div>
                `;
            });
        }
    }


    // 繧､繝吶Φ繝医Μ繧ｹ繝翫・險ｭ螳・    document.getElementById('rollAllAbilities')?.addEventListener('click', rollAllAbilities);
    
    // 蜈ｨ閭ｽ蜉帛､繝繧､繧ｹ險ｭ螳壹・螟画峩譎ゅ↓繝輔か繝ｼ繝溘Η繝ｩ繧呈峩譁ｰ
    document.getElementById('globalDiceCount')?.addEventListener('input', updateGlobalDiceFormula);
    document.getElementById('globalDiceSides')?.addEventListener('input', updateGlobalDiceFormula);
    document.getElementById('globalDiceBonus')?.addEventListener('input', updateGlobalDiceFormula);
    
    // 閨ｷ讌ｭ謚閭ｽ繝昴う繝ｳ繝郁ｨ育ｮ玲婿蠑丞､画峩譎ゅ・繧､繝吶Φ繝・    document.getElementById('occupationMethod')?.addEventListener('change', function() {
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
    const OCCUPATION_TEMPLATES = {
        academic: [
            {
                name: "謨呎肢",
                skills: ["蝗ｳ譖ｸ鬢ｨ", "蠢・炊蟄ｦ", "隱ｬ蠕・, "菫｡逕ｨ", "豁ｴ蜿ｲ", "蜊夂黄蟄ｦ", "莉門嵜隱・, "繧ｪ繧ｫ繝ｫ繝・],
                multiplier: 20,
                description: "螟ｧ蟄ｦ謨呎肢繧・皮ｩｶ閠・
            },
            {
                name: "閠・商蟄ｦ閠・, 
                skills: ["閠・商蟄ｦ", "蝗ｳ譖ｸ鬢ｨ", "豁ｴ蜿ｲ", "逶ｮ譏・, "繝翫ン繧ｲ繝ｼ繝・, "蜀咏悄陦・, "莉門嵜隱・, "髑大ｮ・],
                multiplier: 20,
                description: "驕ｺ霍｡繧・商莉｣譁・・縺ｮ遐皮ｩｶ閠・
            },
            {
                name: "蝗ｳ譖ｸ鬢ｨ蜿ｸ譖ｸ",
                skills: ["蝗ｳ譖ｸ鬢ｨ", "邨檎炊", "繧ｳ繝ｳ繝斐Η繝ｼ繧ｿ繝ｼ", "豁ｴ蜿ｲ", "蠢・炊蟄ｦ", "莉門嵜隱・, "逶ｮ譏・, "隱ｬ蠕・],
                multiplier: 20,
                description: "蝗ｳ譖ｸ鬢ｨ繧・ｳ・侭鬢ｨ縺ｮ邂｡逅・・
            }
        ],
        investigation: [
            {
                name: "遘∫ｫ区爾蛛ｵ",
                skills: ["逶ｮ譏・, "閨槭″閠ｳ", "霑ｽ霍｡", "蠢・炊蟄ｦ", "隱ｬ蠕・, "蜀咏悄陦・, "髫繧後ｋ", "豕募ｾ・],
                multiplier: 20,
                description: "豌鷹俣縺ｮ隱ｿ譟ｻ蜩｡"
            },
            {
                name: "繧ｸ繝｣繝ｼ繝翫Μ繧ｹ繝・,
                skills: ["隱ｬ蠕・, "蠢・炊蟄ｦ", "逶ｮ譏・, "閨槭″閠ｳ", "蜀咏悄陦・, "險縺・￥繧九ａ", "蝗ｳ譖ｸ鬢ｨ", "莉門嵜隱・],
                multiplier: 20,
                description: "譁ｰ閨櫁ｨ倩・ｄ蝣ｱ驕馴未菫り・
            },
            {
                name: "隴ｦ蟇溷ｮ・,
                skills: ["豕募ｾ・, "逶ｮ譏・, "閨槭″閠ｳ", "螽∝嚊", "諡ｳ驫・, "邨・∩莉倥″", "驕玖ｻ｢", "蠢懈･謇句ｽ・],
                multiplier: 20,
                description: "豕募濤陦悟ｮ・
            }
        ],
        combat: [
            {
                name: "霆堺ｺｺ",
                skills: ["繝ｩ繧､繝輔Ν", "諡ｳ驫・, "蝗樣∩", "蠢懈･謇句ｽ・, "螽∝嚊", "繧ｵ繝舌う繝舌Ν", "繝翫ン繧ｲ繝ｼ繝・, "驕玖ｻ｢"],
                multiplier: 20,
                description: "迴ｾ蠖ｹ縺ｾ縺溘・騾蠖ｹ霆堺ｺｺ"
            },
            {
                name: "譬ｼ髣伜ｮｶ",
                skills: ["繝槭・繧ｷ繝｣繝ｫ繧｢繝ｼ繝・, "蝗樣∩", "繧ｭ繝・け", "邨・∩莉倥″", "蠢・炊蟄ｦ", "螽∝嚊", "霍ｳ霄・, "蠢懈･謇句ｽ・],
                multiplier: 20,
                description: "豁ｦ驕灘ｮｶ繧・・繧ｯ繧ｵ繝ｼ"
            }
        ],
        medical: [
            {
                name: "蛹ｻ蟶ｫ",
                skills: ["蛹ｻ蟄ｦ", "蠢懈･謇句ｽ・, "逕溽黄蟄ｦ", "阮ｬ蟄ｦ", "蠢・炊蟄ｦ", "菫｡逕ｨ", "隱ｬ蠕・, "莉門嵜隱・],
                multiplier: 20,
                description: "蛹ｻ閠・ｄ螟也ｧ大現"
            },
            {
                name: "逵玖ｭｷ蟶ｫ",
                skills: ["蛹ｻ蟄ｦ", "蠢懈･謇句ｽ・, "逕溽黄蟄ｦ", "蠢・炊蟄ｦ", "隱ｬ蠕・, "閨槭″閠ｳ", "逶ｮ譏・, "阮ｬ蟄ｦ"],
                multiplier: 20,
                description: "蛹ｻ逋ょｾ謎ｺ玖・
            }
        ],
        arts: [
            {
                name: "闃ｸ陦灘ｮｶ",
                skills: ["闃ｸ陦・, "蠢・炊蟄ｦ", "逶ｮ譏・, "豁ｴ蜿ｲ", "隱ｬ蠕・, "鬲・ヱ", "莉門嵜隱・, "髑大ｮ・],
                multiplier: 20,
                description: "逕ｻ螳ｶ縲∝ｽｫ蛻ｻ螳ｶ縺ｪ縺ｩ"
            },
            {
                name: "菴懷ｮｶ",
                skills: ["豈榊嵜隱・, "莉門嵜隱・, "蝗ｳ譖ｸ鬢ｨ", "蠢・炊蟄ｦ", "豁ｴ蜿ｲ", "繧ｪ繧ｫ繝ｫ繝・, "隱ｬ蠕・, "逶ｮ譏・],
                multiplier: 20,
                description: "蟆剰ｪｬ螳ｶ繧・・譛ｬ螳ｶ"
            }
        ],
        others: [
            {
                name: "迥ｯ鄂ｪ閠・,
                skills: ["髫繧後ｋ", "蠢阪・豁ｩ縺・, "骰ｵ髢九￠", "謇九＆縺ｰ縺・, "逶ｮ譏・, "閨槭″閠ｳ", "蛟､蛻・ｊ", "螟芽｣・],
                multiplier: 20,
                description: "蜈・官鄂ｪ閠・ｄ陬冗､ｾ莨壹・莠ｺ髢・
            },
            {
                name: "繝・ぅ繝ｬ繝・ち繝ｳ繝・,
                skills: ["菫｡逕ｨ", "荵鈴ｦｬ", "闃ｸ陦・, "莉門嵜隱・, "諡ｳ驫・, "豁ｴ蜿ｲ", "鬲・ヱ", "邨檎炊"],
                multiplier: 20,
                description: "雉・肇螳ｶ縲・％讌ｽ閠・
            }
        ]
    };

    // 閨ｷ讌ｭ繝・Φ繝励Ξ繝ｼ繝域ｩ溯・縺ｮ蛻晄悄蛹・    function initOccupationTemplates() {
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
            html += `
                <a href="#" class="list-group-item list-group-item-action occupation-template-item" 
                   data-occupation='${JSON.stringify(occ)}'>
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">${occ.name}</h6>
                        <small>蛟咲紫: EDUﾃ・{occ.multiplier}</small>
                    </div>
                    <p class="mb-1 text-muted small">${occ.description}</p>
                    <small>謗ｨ螂ｨ謚閭ｽ: ${occ.skills.join(', ')}</small>
                </a>
            `;
        });
        html += '</div>';
        
        occupationList.innerHTML = html;
        
        // 繧ｯ繝ｪ繝・け繧､繝吶Φ繝医・險ｭ螳・        document.querySelectorAll('.occupation-template-item').forEach(item => {
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
                // 繝輔ぃ繧､繝ｫ繧ｵ繧､繧ｺ繝√ぉ繝・け・・MB・・                if (file.size > 5 * 1024 * 1024) {
                    alert('繝輔ぃ繧､繝ｫ繧ｵ繧､繧ｺ縺ｯ5MB莉･荳九↓縺励※縺上□縺輔＞縲・);
                    imageInput.value = '';
                    return;
                }
                
                // 繝輔ぃ繧､繝ｫ繧ｿ繧､繝励メ繧ｧ繝・け
                if (!file.type.match(/^image\/(jpeg|jpg|png|gif)$/)) {
                    alert('JPG縲￣NG縲；IF蠖｢蠑上・逕ｻ蜒上ヵ繧｡繧､繝ｫ繧帝∈謚槭＠縺ｦ縺上□縺輔＞縲・);
                    imageInput.value = '';
                    return;
                }
                
                // 繝励Ξ繝薙Η繝ｼ陦ｨ遉ｺ
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
    
    // 蛻晄悄蛹・    updateGlobalDiceFormula();
    generateSkillsList();
    addSkillInputEvents();  // 謚閭ｽ繝ｪ繧ｹ繝育函謌仙ｾ後↓繧､繝吶Φ繝医Μ繧ｹ繝翫・繧定ｿｽ蜉
    
    // 謚閭ｽ繝ｪ繧ｹ繝医′逕滓・縺輔ｌ縺溷ｾ後↓豢ｾ逕溘せ繝・・繧ｿ繧ｹ繧定ｨ育ｮ・    setTimeout(() => {
        calculateDerivedStats();
        updateSkillTotals();    // 蛻晄悄險育ｮ励ｒ螳溯｡・    }, 0);
    
    initOccupationTemplates(); // 閨ｷ讌ｭ繝・Φ繝励Ξ繝ｼ繝域ｩ溯・繧貞・譛溷喧
    initImageUpload(); // 逕ｻ蜒上い繝・・繝ｭ繝ｼ繝画ｩ溯・繧貞・譛溷喧
    
    // 繝輔か繝ｼ繝騾∽ｿ｡蜃ｦ逅・    const characterForm = document.getElementById('character-sheet-form');
    if (characterForm) {
        characterForm.addEventListener('submit', function(e) {
            e.preventDefault();
        
            const formData = new FormData(this);
            const data = {};
            
            // FormData縺九ｉ繝・・繧ｿ繧貞叙蠕暦ｼ医ヵ繧｡繧､繝ｫ莉･螟厄ｼ・            for (let [key, value] of formData.entries()) {
                if (key !== 'character_image') {
                    data[key] = value;
                }
            }
            
            // 繝舌Μ繝・・繧ｷ繝ｧ繝ｳ
            if (!data.name) {
                alert('謗｢邏｢閠・錐縺ｯ蠢・医〒縺吶・);
                return;
            }
            
            // 閭ｽ蜉帛､繝舌Μ繝・・繧ｷ繝ｧ繝ｳ・医ヵ繧｣繝ｼ繝ｫ繝牙錐繧剃ｿｮ豁｣・・            const abilities = ['str_value', 'con_value', 'pow_value', 'dex_value', 'app_value', 'siz_value', 'int_value', 'edu_value'];
            let hasAbilities = false;
            for (const ability of abilities) {
                if (data[ability] && parseInt(data[ability]) > 0) {
                    hasAbilities = true;
                    break;
                }
            }
            
            if (!hasAbilities) {
                alert('閭ｽ蜉帛､繧定ｨｭ螳壹＠縺ｦ縺上□縺輔＞縲・);
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
                                if (defaultBase === 'DEXﾃ・') {
                                    const dex = parseInt(document.getElementById('dex')?.value) || 0;
                                    defaultBase = dex * 2;
                                } else if (defaultBase === 'EDUﾃ・') {
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
            
            // 逕ｻ蜒上ヵ繧｡繧､繝ｫ縺後≠繧句ｴ蜷医・FormData縺ｧ騾∽ｿ｡
            const imageFile = formData.get('character_image');
            if (imageFile && imageFile.size > 0) {
                // FormData繧剃ｽｿ逕ｨ縺励※逕ｻ蜒上ｒ蜷ｫ繧√※騾∽ｿ｡
                const submitFormData = new FormData();
                
                // API繝・・繧ｿ縺ｮ蜷・ヵ繧｣繝ｼ繝ｫ繝峨ｒFormData縺ｫ霑ｽ蜉
                Object.keys(apiData).forEach(key => {
                    if (key === 'skills' || key === 'equipment') {
                        submitFormData.append(key, JSON.stringify(apiData[key]));
                    } else {
                        submitFormData.append(key, apiData[key]);
                    }
                });
                
                // 逕ｻ蜒上ヵ繧｡繧､繝ｫ繧定ｿｽ蜉
                submitFormData.append('character_image', imageFile);
                
                // API縺ｫ騾∽ｿ｡・・ultipart/form-data・・                fetch('/accounts/character-sheets/create_6th_edition/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: submitFormData
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => Promise.reject(err));
                    }
                    return response.json();
                })
                .then(result => {
                    // 謌仙粥譎ゅ・蜃ｦ逅・ｼ・PI縺ｯCharacterSheet繧ｪ繝悶ず繧ｧ繧ｯ繝医ｒ霑斐☆・・                    if (result.id) {
                        alert('謗｢邏｢閠・す繝ｼ繝医′豁｣蟶ｸ縺ｫ菴懈・縺輔ｌ縺ｾ縺励◆・・);
                        window.location.href = '/accounts/character/list/';
                    } else {
                        alert('繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: 莠域悄縺励↑縺・Ξ繧ｹ繝昴Φ繧ｹ蠖｢蠑・);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (error.error) {
                        alert('繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: ' + error.error);
                    } else {
                        alert('繝阪ャ繝医Ρ繝ｼ繧ｯ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆縲・);
                    }
                });
            } else {
                // 逕ｻ蜒上↑縺励・蝣ｴ蜷医・JSON縺ｧ騾∽ｿ｡
                fetch('/accounts/character-sheets/create_6th_edition/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify(apiData)
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => Promise.reject(err));
                    }
                    return response.json();
                })
                .then(result => {
                    // 謌仙粥譎ゅ・蜃ｦ逅・ｼ・PI縺ｯCharacterSheet繧ｪ繝悶ず繧ｧ繧ｯ繝医ｒ霑斐☆・・                    if (result.id) {
                        alert('謗｢邏｢閠・す繝ｼ繝医′豁｣蟶ｸ縺ｫ菴懈・縺輔ｌ縺ｾ縺励◆・・);
                        window.location.href = '/accounts/character/list/';
                    } else {
                        alert('繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: 莠域悄縺励↑縺・Ξ繧ｹ繝昴Φ繧ｹ蠖｢蠑・);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (error.error) {
                        alert('繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: ' + error.error);
                    } else {
                        alert('繝阪ャ繝医Ρ繝ｼ繧ｯ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆縲・);
                    }
                });
            }
        });
    }
    const footerSaveBtn = document.getElementById('footerSaveCharacter');
    if (footerSaveBtn && characterForm) {
    footerSaveBtn.addEventListener('click', () => {
        // HTML5繝舌Μ繝・・繧ｷ繝ｧ繝ｳ繧りｵｰ繧峨○縺､縺､submit繧､繝吶Φ繝医ｒ逋ｺ轣ｫ
        characterForm.requestSubmit();
    });
    }
});
