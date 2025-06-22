/**
 * シンプルな技能フィルタリングシステム
 * DOM要素を再生成せず、CSSクラスで表示/非表示を制御
 */

// 技能フィルタリングマネージャー
const SkillFilterManager = {
    // 現在の検索条件
    currentSearch: '',
    currentTab: 'all',
    
    // 初期化
    init() {
        this.setupEventListeners();
        this.initializeSkills();
    },
    
    // イベントリスナーの設定
    setupEventListeners() {
        // 検索入力
        const searchInput = document.getElementById('skill-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.currentSearch = e.target.value.toLowerCase();
                this.applyFilters();
            });
        }
        
        // タブ切り替え
        const tabButtons = document.querySelectorAll('[data-skill-tab]');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                // アクティブタブの更新
                tabButtons.forEach(b => b.classList.remove('active'));
                button.classList.add('active');
                
                // フィルタ適用
                this.currentTab = button.dataset.skillTab;
                this.applyFilters();
            });
        });
    },
    
    // 技能の初期化（一度だけ実行）
    initializeSkills() {
        const skillItems = document.querySelectorAll('.skill-item-wrapper');
        
        skillItems.forEach(item => {
            // data属性の設定（既に設定されていない場合）
            if (!item.dataset.skillName) {
                const skillTitle = item.querySelector('.skill-title')?.textContent?.trim() || '';
                const cleanName = skillTitle.replace(/\s*カスタム\s*/g, '').trim();
                item.dataset.skillName = cleanName.toLowerCase();
                
                // カテゴリも設定
                const category = item.dataset.skillCategory || this.detectCategory(cleanName);
                item.dataset.skillCategory = category;
            }
        });
    },
    
    // カテゴリ検出（必要に応じて）
    detectCategory(skillName) {
        // カテゴリ判定ロジック
        const combatSkills = ['回避', 'キック', 'ナイフ', '拳銃', 'マシンガン', 'ライフル'];
        const searchSkills = ['目星', '聞き耳', '図書館', '追跡'];
        const knowledgeSkills = ['医学', '精神分析', '心理学', 'オカルト', '博物学', '物理学', '生物学', '地質学', '考古学', '人類学', '歴史', '法律'];
        
        if (combatSkills.includes(skillName)) return 'combat';
        if (searchSkills.includes(skillName)) return 'search';
        if (knowledgeSkills.includes(skillName)) return 'knowledge';
        return 'other';
    },
    
    // フィルタ適用
    applyFilters() {
        const skillItems = document.querySelectorAll('.skill-item-wrapper');
        let visibleCount = 0;
        
        skillItems.forEach(item => {
            const skillName = item.dataset.skillName || '';
            const category = item.dataset.skillCategory || 'other';
            
            // 検索条件チェック
            const matchesSearch = !this.currentSearch || skillName.includes(this.currentSearch);
            
            // タブ条件チェック
            const matchesTab = this.currentTab === 'all' || category === this.currentTab;
            
            // 表示/非表示の制御
            if (matchesSearch && matchesTab) {
                item.classList.remove('hidden', 'search-hidden', 'tab-hidden');
                visibleCount++;
            } else {
                item.classList.add('hidden');
                if (!matchesSearch) item.classList.add('search-hidden');
                if (!matchesTab) item.classList.add('tab-hidden');
            }
        });
        
        // 結果なしメッセージの表示/非表示
        this.updateNoResultsMessage(visibleCount);
        
        // カウンター更新
        this.updateCounters();
    },
    
    // 結果なしメッセージ
    updateNoResultsMessage(visibleCount) {
        const containers = ['all-skills-container', 'combat-skills-container', 'search-skills-container', 'knowledge-skills-container', 'other-skills-container'];
        
        containers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (!container) return;
            
            // 既存のメッセージを削除
            const existingMessage = container.querySelector('.no-results-message');
            if (existingMessage) existingMessage.remove();
            
            // 該当タブで結果がない場合
            if (visibleCount === 0 && (this.currentTab === 'all' || containerId.includes(this.currentTab))) {
                const message = document.createElement('div');
                message.className = 'no-results-message';
                message.innerHTML = `
                    <i class="fas fa-search text-muted"></i>
                    <p>検索条件に一致する技能がありません</p>
                `;
                container.appendChild(message);
            }
        });
    },
    
    // カウンター更新
    updateCounters() {
        const categories = ['all', 'combat', 'search', 'knowledge', 'other'];
        
        categories.forEach(category => {
            const count = this.getVisibleCount(category);
            const badge = document.getElementById(`${category}-count`);
            if (badge) {
                badge.textContent = count;
            }
        });
    },
    
    // カテゴリ別の表示数取得
    getVisibleCount(category) {
        let selector = '.skill-item-wrapper:not(.hidden)';
        if (category !== 'all') {
            selector = `.skill-item-wrapper[data-skill-category="${category}"]:not(.hidden)`;
        }
        return document.querySelectorAll(selector).length;
    }
};

// DOM読み込み完了時に初期化
document.addEventListener('DOMContentLoaded', () => {
    SkillFilterManager.init();
});

// グローバルに公開（必要に応じて）
window.SkillFilterManager = SkillFilterManager;