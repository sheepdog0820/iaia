'use strict';

const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const template = readFileSync(resolve(__dirname, '../../templates/accounts/character_detail.html'), 'utf8');
const start = template.indexOf('    function displaySkills(skills) {');
const end = template.indexOf('    function displayBackgroundInfo(', start);
assert.ok(start >= 0 && end > start, 'The character detail skill renderer must exist');
const escapeHtml = template.match(/    function escapeHtml\(value\) \{[\s\S]*?\n    \}/)[0];

function render(skills) {
    const container = { innerHTML: '' };
    const context = vm.createContext({ document: { getElementById: () => container }, skills });
    vm.runInContext(escapeHtml + '\n' + template.slice(start, end) + '\ndisplaySkills(skills);', context);
    return container.innerHTML.replace(/\s+/g, ' ');
}

function assertBonus(html, value) {
    assert.match(html, new RegExp(`skill-breakdown-bonus"> <span class="skill-breakdown-label">ボーナス</span> <span class="skill-breakdown-value">${value}</span>`));
}

test('HO bonuses appear separately with the persisted totals', () => {
    for (const [skill_name, base_value, occupation_points, bonus_points, current_value] of [
        ['重機械操作', 1, 40, 30, 71],
        ['電気修理', 10, 35, 20, 65],
        ['説得', 15, 25, 30, 70],
    ]) {
        const html = render([{ skill_name, base_value, occupation_points, bonus_points, current_value }]);
        assertBonus(html, bonus_points);
        assert.ok(html.includes(`${skill_name} 合計 ${current_value}`));
    }
});

test('a skill trained only through a bonus remains visible', () => {
    const html = render([{ skill_name: '重機械操作', base_value: 1, bonus_points: 30, current_value: 31 }]);
    assertBonus(html, 30);
    assert.ok(html.includes('重機械操作 合計 31'));
});

test('missing and zero bonuses do not add empty breakdown chips', () => {
    for (const bonus of [{}, { bonus_points: 0 }]) {
        const html = render([{ skill_name: '目星', base_value: 25, occupation_points: 20, current_value: 45, ...bonus }]);
        assert.ok(!html.includes('skill-breakdown-bonus'));
        assert.ok(html.includes('目星 合計 45'));
    }
    assert.ok(!render([{ skill_name: '目星', base_value: 25, bonus_points: 0, current_value: 25 }]).includes('skill-card'));
    assert.match(render([]), /技能ポイントを振った技能がありません。/);
});

test('bonus and other points stay distinct and totals are not recomputed', () => {
    const html = render([{ skill_name: '目星', base_value: 25, occupation_points: 40, interest_points: 20, bonus_points: 10, other_points: 5, current_value: 99 }]);
    assertBonus(html, 10);
    assert.match(html, /skill-breakdown-other"> <span class="skill-breakdown-label">その他<\/span> <span class="skill-breakdown-value">5<\/span>/);
    assert.ok(html.includes('目星 合計 99'));
});
