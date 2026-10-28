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

function assertOther(html, value) {
    assert.match(html, new RegExp(`skill-breakdown-other"> <span class="skill-breakdown-label">その他</span> <span class="skill-breakdown-value">${value}</span>`));
    assert.ok(!html.includes('skill-breakdown-bonus'));
}

test('legacy split adjustments are shown together as other points', () => {
    const html = render([{ skill_name: '説得', base_value: 15, bonus_points: 30, other_points: 5, current_value: 50 }]);
    assertOther(html, 35);
    assert.ok(html.includes('説得 合計 50'));
});

test('HO adjustments appear as other points with the persisted totals', () => {
    for (const [skill_name, base_value, occupation_points, other_points, current_value] of [
        ['重機械操作', 1, 40, 30, 71],
        ['電気修理', 10, 35, 20, 65],
        ['説得', 15, 25, 30, 70],
    ]) {
        const html = render([{ skill_name, base_value, occupation_points, other_points, current_value }]);
        assertOther(html, other_points);
        assert.ok(html.includes(`${skill_name} 合計 ${current_value}`));
    }
});

test('a skill trained only through other points remains visible', () => {
    const html = render([{ skill_name: '重機械操作', base_value: 1, other_points: 30, current_value: 31 }]);
    assertOther(html, 30);
    assert.ok(html.includes('重機械操作 合計 31'));
});

test('missing and zero adjustments do not add empty breakdown chips', () => {
    for (const adjustment of [{}, { other_points: 0, bonus_points: 0 }]) {
        const html = render([{ skill_name: '目星', base_value: 25, occupation_points: 20, current_value: 45, ...adjustment }]);
        assert.ok(!html.includes('skill-breakdown-bonus'));
        assert.ok(!html.includes('skill-breakdown-other'));
        assert.ok(html.includes('目星 合計 45'));
    }
    assert.ok(!render([{ skill_name: '目星', base_value: 25, bonus_points: 0, current_value: 25 }]).includes('skill-card'));
    assert.match(render([]), /技能ポイントを振った技能がありません。/);
});

test('consolidated other points appear once and totals are not recomputed', () => {
    const html = render([{ skill_name: '目星', base_value: 25, occupation_points: 40, interest_points: 20, bonus_points: 0, other_points: 15, current_value: 99 }]);
    assertOther(html, 15);
    assert.equal((html.match(/skill-breakdown-other/g) || []).length, 1);
    assert.ok(html.includes('目星 合計 99'));
});
