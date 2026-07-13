(function() {
    'use strict';

    function toAbsoluteUrl(url) {
        if (!url) return '';
        if (url.startsWith('http://') || url.startsWith('https://')) return url;
        return window.location.origin + url;
    }

    async function copyTextToClipboard(text) {
        if (!text) return;
        let clipboardError = null;

        if (navigator.clipboard?.writeText && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(text);
                return;
            } catch (error) {
                clipboardError = error;
            }
        }

        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'fixed';
        textarea.style.top = '0';
        textarea.style.left = '-9999px';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        textarea.setSelectionRange(0, textarea.value.length);

        let copied = false;
        try {
            copied = document.execCommand('copy');
        } finally {
            document.body.removeChild(textarea);
        }

        if (!copied) {
            throw clipboardError || new Error('Clipboard copy was rejected by the browser.');
        }
    }

    function toNumber(value, fallback = 0) {
        const num = Number(value);
        return Number.isFinite(num) ? num : fallback;
    }

    const COC6_DEFAULT_SKILLS = [
        { name: '回避', base: 'DEX*2' },
        { name: 'キック', base: 25 },
        { name: '組み付き', base: 25 },
        { name: 'こぶし（パンチ）', base: 50 },
        { name: '頭突き', base: 10 },
        { name: '投擲', base: 25 },
        { name: 'マーシャルアーツ', base: 1 },
        { name: '拳銃', base: 20 },
        { name: 'サブマシンガン', base: 15 },
        { name: 'ショットガン', base: 30 },
        { name: 'マシンガン', base: 15 },
        { name: 'ライフル', base: 25 },
        { name: '応急手当', base: 30 },
        { name: '鍵開け', base: 1 },
        { name: '隠す', base: 15 },
        { name: '隠れる', base: 10 },
        { name: '聞き耳', base: 25 },
        { name: '忍び歩き', base: 10 },
        { name: '写真術', base: 10 },
        { name: '精神分析', base: 1 },
        { name: '追跡', base: 10 },
        { name: '登攀', base: 40 },
        { name: '図書館', base: 25 },
        { name: '目星', base: 25 },
        { name: '運転', base: 20 },
        { name: '機械修理', base: 20 },
        { name: '重機械操作', base: 1 },
        { name: '乗馬', base: 5 },
        { name: '水泳', base: 25 },
        { name: '製作', base: 5 },
        { name: '操縦', base: 1 },
        { name: '跳躍', base: 25 },
        { name: '電気修理', base: 10 },
        { name: 'ナビゲート', base: 10 },
        { name: '変装', base: 1 },
        { name: '言いくるめ', base: 5 },
        { name: '信用', base: 15 },
        { name: '説得', base: 15 },
        { name: '値切り', base: 5 },
        { name: '他の言語', base: 1 },
        { name: '母国語', base: 'EDU*5' },
        { name: '医学', base: 5 },
        { name: 'オカルト', base: 5 },
        { name: '化学', base: 1 },
        { name: 'クトゥルフ神話', base: 0 },
        { name: '芸術', base: 5 },
        { name: '経理', base: 10 },
        { name: '考古学', base: 1 },
        { name: 'コンピューター', base: 1 },
        { name: '心理学', base: 5 },
        { name: '人類学', base: 1 },
        { name: '生物学', base: 1 },
        { name: '地質学', base: 1 },
        { name: '電子工学', base: 1 },
        { name: '天文学', base: 1 },
        { name: '博物学', base: 10 },
        { name: '物理学', base: 1 },
        { name: '法律', base: 5 },
        { name: '薬学', base: 1 },
        { name: '歴史', base: 20 },
    ];

    const COC7_DEFAULT_SKILLS = [
        { name: '回避', base: 'DEX/2' },
        { name: '近接戦闘（格闘）', base: 25 },
        { name: '投擲', base: 20 },
        { name: '射撃（拳銃）', base: 20 },
        { name: '射撃（ライフル／ショットガン）', base: 25 },
        { name: '応急手当', base: 30 },
        { name: '鍵開け', base: 1 },
        { name: '鑑定', base: 5 },
        { name: '隠密', base: 20 },
        { name: '聞き耳', base: 20 },
        { name: '精神分析', base: 1 },
        { name: '追跡', base: 10 },
        { name: '登攀', base: 20 },
        { name: '図書館', base: 20 },
        { name: '目星', base: 25 },
        { name: '手さばき', base: 10 },
        { name: '運転（自動車）', base: 20 },
        { name: '機械修理', base: 10 },
        { name: '重機械操作', base: 1 },
        { name: '乗馬', base: 5 },
        { name: '水泳', base: 20 },
        { name: '芸術／製作', base: 5 },
        { name: '操縦', base: 1 },
        { name: '跳躍', base: 20 },
        { name: '電気修理', base: 10 },
        { name: '電子工学', base: 1 },
        { name: 'ナビゲート', base: 10 },
        { name: 'サバイバル', base: 10 },
        { name: '変装', base: 5 },
        { name: '言いくるめ', base: 5 },
        { name: '魅惑', base: 15 },
        { name: '信用', base: 0 },
        { name: '説得', base: 10 },
        { name: '威圧', base: 15 },
        { name: 'ほかの言語', base: 1 },
        { name: '母国語', base: 'EDU' },
        { name: '医学', base: 1 },
        { name: 'オカルト', base: 5 },
        { name: '科学', base: 1 },
        { name: 'クトゥルフ神話', base: 0 },
        { name: '経理', base: 5 },
        { name: '考古学', base: 1 },
        { name: 'コンピューター', base: 5 },
        { name: '心理学', base: 10 },
        { name: '人類学', base: 1 },
        { name: '自然', base: 10 },
        { name: '法律', base: 5 },
        { name: '歴史', base: 5 },
    ];

    const COC7_SKILL_NAME_ALIASES = new Map([
        ['隠れる', '隠密'],
        ['忍び歩き', '隠密'],
        ['隠す', '手さばき'],
        ['近接戦闘', '近接戦闘（格闘）'],
        ['格闘技', '近接戦闘（格闘）'],
        ['キック', '近接戦闘（格闘）'],
        ['組み付き', '近接戦闘（格闘）'],
        ['こぶし（パンチ）', '近接戦闘（格闘）'],
        ['頭突き', '近接戦闘（格闘）'],
        ['マーシャルアーツ', '近接戦闘（格闘）'],
        ['拳銃', '射撃（拳銃）'],
        ['ショットガン', '射撃（ライフル／ショットガン）'],
        ['ライフル', '射撃（ライフル／ショットガン）'],
        ['運転', '運転（自動車）'],
        ['芸術', '芸術／製作'],
        ['製作', '芸術／製作'],
        ['他の言語', 'ほかの言語'],
        ['化学', '科学'],
        ['生物学', '科学'],
        ['地質学', '科学'],
        ['天文学', '科学'],
        ['物理学', '科学'],
        ['薬学', '科学'],
        ['博物学', '自然'],
    ]);

    function resolveSkillBase(base, abilities) {
        if (base === 'DEX*2') return Math.min(abilities.DEX * 2, 999);
        if (base === 'DEX/2') return Math.floor(abilities.DEX / 2);
        if (base === 'EDU*5') return Math.min(abilities.EDU * 5, 999);
        if (base === 'EDU') return abilities.EDU;
        return toNumber(base);
    }

    function collectSkills(character, abilities) {
        const edition = character?.edition || '6th';
        const defaultSkills = edition === '7th' ? COC7_DEFAULT_SKILLS : COC6_DEFAULT_SKILLS;
        const skillValues = new Map();

        defaultSkills.forEach(skill => {
            skillValues.set(skill.name, resolveSkillBase(skill.base, abilities));
        });

        const customSkills = new Map();
        (Array.isArray(character.skills) ? character.skills : []).forEach(skill => {
            if (!skill?.skill_name || !Number.isFinite(Number(skill.current_value))) return;
            const skillName = String(skill.skill_name);
            const normalizedSkillName = edition === '7th' ? (COC7_SKILL_NAME_ALIASES.get(skillName) || skillName) : skillName;
            const skillValue = toNumber(skill.current_value);
            if (skillValues.has(normalizedSkillName)) {
                const value = normalizedSkillName === skillName ? skillValue : Math.max(skillValues.get(normalizedSkillName), skillValue);
                skillValues.set(normalizedSkillName, value);
            } else {
                customSkills.set(skillName, skillValue);
            }
        });

        return [
            ...defaultSkills.map(skill => ({
                skill_name: skill.name,
                current_value: skillValues.get(skill.name),
            })),
            ...Array.from(customSkills, ([skill_name, current_value]) => ({ skill_name, current_value })),
        ];
    }

    function getSixthValue(sixth, key, fallback) {
        const value = toNumber(sixth?.[key], 0);
        return value || fallback;
    }

    function buildCharacterClipboard(character, detailUrl) {
        const abilityLabels = [
            ['STR', 'str_value'],
            ['CON', 'con_value'],
            ['POW', 'pow_value'],
            ['DEX', 'dex_value'],
            ['APP', 'app_value'],
            ['SIZ', 'siz_value'],
            ['INT', 'int_value'],
            ['EDU', 'edu_value'],
        ];
        const abilities = Object.fromEntries(
            abilityLabels.map(([label, key]) => [label, toNumber(character[key])])
        );
        const sixth = character.sixth_edition_data || character.character_6th || {};
        const skillCommands = collectSkills(character, abilities)
            .map(skill => `CCB<=${toNumber(skill.current_value)} 【${skill.skill_name}】`);
        const abilityCommands = abilityLabels.map(([label]) => (
            `CCB<=${abilities[label] * 5} 【${label}】`
        ));
        const derivedCommands = [
            getSixthValue(sixth, 'luck_roll', abilities.POW * 5) ? `CCB<=${getSixthValue(sixth, 'luck_roll', abilities.POW * 5)} 【幸運】` : '',
            getSixthValue(sixth, 'idea_roll', abilities.INT * 5) ? `CCB<=${getSixthValue(sixth, 'idea_roll', abilities.INT * 5)} 【アイデア】` : '',
            getSixthValue(sixth, 'know_roll', abilities.EDU * 5) ? `CCB<=${getSixthValue(sixth, 'know_roll', abilities.EDU * 5)} 【知識】` : '',
            character.sanity_current ? `CCB<=${toNumber(character.sanity_current)} 【SANチェック】` : '',
        ].filter(Boolean);
        const params = [
            ...abilityLabels.map(([label]) => ({ label, value: String(abilities[label]) })),
            { label: '職業', value: character.occupation || '-' },
            { label: '年齢', value: character.age ? String(character.age) : '-' },
            sixth.damage_bonus ? { label: 'DB', value: String(sixth.damage_bonus) } : null,
        ].filter(Boolean);
        return {
            kind: 'character',
            data: {
                name: character.name || '無名の探索者',
                memo: character.name_kana ? `読み仮名: ${character.name_kana}` : '',
                initiative: abilities.DEX || 0,
                externalUrl: toAbsoluteUrl(detailUrl),
                status: [
                    {
                        label: 'HP',
                        value: toNumber(character.hit_points_current ?? character.hp_current),
                        max: toNumber(character.hit_points_max ?? character.hp_current),
                    },
                    {
                        label: 'MP',
                        value: toNumber(character.magic_points_current ?? character.mp_current),
                        max: toNumber(character.magic_points_max ?? character.mp_current),
                    },
                    {
                        label: 'SAN',
                        value: toNumber(character.sanity_current ?? character.san_current),
                        max: toNumber(character.sanity_max ?? character.san_current),
                    },
                ],
                params,
                commands: [...derivedCommands, ...abilityCommands, ...skillCommands].join('\n'),
            },
        };
    }

    window.CCFOLIACharacterCopy = {
        buildCharacterClipboard,
        copyTextToClipboard,
        stringifyCharacter(character, detailUrl) {
            return JSON.stringify(buildCharacterClipboard(character, detailUrl));
        },
    };
})();
