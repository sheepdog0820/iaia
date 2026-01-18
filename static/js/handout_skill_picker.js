(function () {
    'use strict';

    const COC_BASE_SKILL_NAMES = [
        'こぶし（パンチ）',
        'オカルト',
        'キック',
        'クトゥルフ神話',
        'コンピューター',
        'サバイバル',
        'サブマシンガン',
        'ショットガン',
        'ナビゲート',
        'マシンガン',
        'マーシャルアーツ',
        'ライフル',
        '乗馬',
        '人類学',
        '他の言語',
        '信用',
        '値切り',
        '写真術',
        '化学',
        '医学',
        '博物学',
        '回避',
        '図書館',
        '地質学',
        '変装',
        '天文学',
        '威圧',
        '心理学',
        '忍び歩き',
        '応急手当',
        '手さばき',
        '投擲',
        '拳銃',
        '操縦',
        '機械修理',
        '歴史',
        '母国語',
        '水泳',
        '法律',
        '物理学',
        '生物学',
        '登攀',
        '目星',
        '精神分析',
        '組み付き',
        '経理',
        '考古学',
        '聞き耳',
        '芸術',
        '薬学',
        '製作',
        '言いくるめ',
        '説得',
        '跳躍',
        '追跡',
        '運転',
        '重機械操作',
        '鍵開け',
        '鑑定',
        '隠す',
        '隠れる',
        '電子工学',
        '電気修理',
        '頭突き',
        '魅惑',
    ];

    function normalizeToken(value) {
        if (value == null) return '';
        return String(value)
            .replace(/\u3000/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function tokenizeSkills(rawText) {
        if (!rawText) return [];
        return String(rawText)
            .replace(/、/g, ',')
            .replace(/\r\n/g, '\n')
            .replace(/\n/g, ',')
            .split(',')
            .map(normalizeToken)
            .filter(Boolean);
    }

    function uniquePreserveOrder(values) {
        const seen = new Set();
        const result = [];
        (values || []).forEach(value => {
            const token = normalizeToken(value);
            if (!token) return;
            const key = token.toLowerCase();
            if (seen.has(key)) return;
            seen.add(key);
            result.push(token);
        });
        return result;
    }

    function mergeSkillCandidates(...lists) {
        const merged = [];
        (lists || []).forEach(list => {
            (list || []).forEach(item => merged.push(item));
        });
        return uniquePreserveOrder(merged).sort((a, b) => a.localeCompare(b, 'ja'));
    }

    function clearElement(element) {
        if (!element) return;
        while (element.firstChild) element.removeChild(element.firstChild);
    }

    function buildDatalist(datalistEl, options) {
        if (!datalistEl) return;
        clearElement(datalistEl);
        (options || []).forEach(name => {
            const optionEl = document.createElement('option');
            optionEl.value = name;
            datalistEl.appendChild(optionEl);
        });
    }

    function renderSelectedChips(containerEl, skills, onRemove) {
        if (!containerEl) return;
        clearElement(containerEl);

        if (!skills || skills.length === 0) {
            const emptyEl = document.createElement('span');
            emptyEl.className = 'text-muted';
            emptyEl.textContent = '推奨技能はまだ設定されていません。';
            containerEl.appendChild(emptyEl);
            return;
        }

        const fragment = document.createDocumentFragment();
        skills.forEach(skillName => {
            const badge = document.createElement('span');
            badge.className = 'badge bg-info text-dark me-1 mb-1';
            badge.dataset.skill = skillName;
            badge.textContent = skillName;

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-link btn-sm p-0 ms-1 text-dark';
            removeBtn.setAttribute('aria-label', '削除');
            removeBtn.innerHTML = '&times;';
            removeBtn.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                onRemove?.(skillName);
            });

            badge.appendChild(removeBtn);
            fragment.appendChild(badge);
        });
        containerEl.appendChild(fragment);
    }

    function renderSuggestedChips(containerEl, suggestions, onAdd) {
        if (!containerEl) return;
        clearElement(containerEl);

        const list = uniquePreserveOrder(suggestions);
        if (!list.length) return;

        const fragment = document.createDocumentFragment();
        list.forEach(name => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-secondary btn-sm';
            btn.textContent = name;
            btn.addEventListener('click', () => onAdd?.(name));
            fragment.appendChild(btn);
        });
        containerEl.appendChild(fragment);
    }

    function resolveElement(value) {
        if (!value) return null;
        if (value instanceof HTMLElement) return value;
        return document.getElementById(String(value));
    }

    function createPicker(config) {
        const textarea = resolveElement(config?.textarea);
        const input = resolveElement(config?.input);
        const datalist = resolveElement(config?.datalist);
        const chips = resolveElement(config?.chips);
        const suggestions = resolveElement(config?.suggestions);
        const clearButton = resolveElement(config?.clearButton);

        if (!textarea || !input || !datalist || !chips) return null;

        const gameSystem = normalizeToken(config?.gameSystem).toLowerCase();
        const scenarioRecommended = tokenizeSkills(config?.scenarioRecommendedSkills);
        const available = gameSystem === 'coc'
            ? mergeSkillCandidates(COC_BASE_SKILL_NAMES, scenarioRecommended)
            : mergeSkillCandidates(scenarioRecommended);

        buildDatalist(datalist, available);

        const state = {
            skills: [],
        };

        function writeTextarea(skillsList) {
            textarea.value = (skillsList || []).join(', ');
        }

        function setSkills(nextSkills, { syncTextarea = true } = {}) {
            state.skills = uniquePreserveOrder(nextSkills);
            renderSelectedChips(chips, state.skills, (skillName) => {
                setSkills(state.skills.filter(s => s !== skillName));
            });
            if (syncTextarea) writeTextarea(state.skills);
        }

        function syncFromTextarea({ normalize = false } = {}) {
            const parsed = tokenizeSkills(textarea.value);
            if (normalize) {
                setSkills(parsed, { syncTextarea: true });
            } else {
                setSkills(parsed, { syncTextarea: false });
            }
        }

        function addFromText(raw) {
            const incoming = tokenizeSkills(raw);
            if (!incoming.length) return;
            setSkills(state.skills.concat(incoming));
        }

        function addFromInput() {
            const raw = input.value;
            if (!normalizeToken(raw)) return;
            addFromText(raw);
            input.value = '';
            input.focus();
        }

        function clearAll() {
            setSkills([]);
            input.value = '';
            input.focus();
        }

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ',' || event.key === '、') {
                event.preventDefault();
                addFromInput();
            }
        });

        const addButton = resolveElement(config?.addButton);
        if (addButton) {
            addButton.addEventListener('click', (event) => {
                event.preventDefault();
                addFromInput();
            });
        }

        if (clearButton) {
            clearButton.addEventListener('click', (event) => {
                event.preventDefault();
                clearAll();
            });
        }

        textarea.addEventListener('input', () => {
            syncFromTextarea({ normalize: false });
        });

        textarea.addEventListener('blur', () => {
            syncFromTextarea({ normalize: true });
        });

        renderSuggestedChips(suggestions, scenarioRecommended, (name) => {
            addFromText(name);
        });

        const modalEl = resolveElement(config?.modal);
        if (modalEl) {
            modalEl.addEventListener('shown.bs.modal', () => {
                syncFromTextarea({ normalize: false });
            });
        }

        syncFromTextarea({ normalize: false });

        return {
            syncFromTextarea,
            setSkillsFromText: (raw) => {
                textarea.value = raw || '';
                syncFromTextarea({ normalize: false });
            },
            clear: clearAll,
        };
    }

    window.HandoutSkillPicker = {
        attach: createPicker,
        tokenize: tokenizeSkills,
        COC_BASE_SKILL_NAMES,
    };
})();
