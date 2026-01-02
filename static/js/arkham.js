// タブレノ - Main JavaScript File

// CSRFトークンの設定
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Axiosのデフォルト設定
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';

// グローバル設定
const ARKHAM = {
    apiBase: '/api',
    currentUser: null,
    
    // APIエンドポイント
    endpoints: {
        sessions: '/api/schedules/sessions/',
        scenarios: '/api/scenarios/scenarios/',
        groups: '/api/accounts/groups/',
        users: '/api/accounts/users/',
        calendar: '/api/schedules/calendar/',
        statistics: '/api/schedules/sessions/statistics/'
    },
    
    // 日付フォーマット
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    // 時間フォーマット（分→時間）
    formatDuration: function(minutes) {
        if (!minutes) return '0分';
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        
        if (hours === 0) return `${mins}分`;
        if (mins === 0) return `${hours}時間`;
        return `${hours}時間${mins}分`;
    },
    
    // エラーハンドリング
    handleError: function(error) {
        console.error('API Error:', error);
        
        let message = 'エラーが発生しました';
        if (error.response && error.response.data) {
            if (error.response.data.detail) {
                message = error.response.data.detail;
            } else if (error.response.data.error) {
                message = error.response.data.error;
            }
        }
        
        this.showAlert(message, 'danger');
    },
    
    // アラート表示
    showAlert: function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // 5秒後に自動で消去
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    },
    
    // 成功メッセージ表示
    showSuccess: function(message) {
        this.showAlert(message, 'success');
    },
    
    // エラーメッセージ表示
    showError: function(message) {
        this.showAlert(message, 'danger');
    },
    
    // ローディング表示
    showLoading: function(element) {
        element.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    },
    
    // モーダル作成
    createModal: function(title, body, footer = '') {
        return `
            <div class="modal fade" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${body}
                        </div>
                        ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }
};

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    // ナビゲーションの設定
    setupNavigation();
    
    // クイックアクションボタンの設定
    setupQuickActions();
    
    // エルドリッチエフェクトの初期化
    initEldritchEffects();
});

// ナビゲーション設定
function setupNavigation() {
    // カレンダーリンク
    const calendarLink = document.getElementById('calendar-link');
    if (calendarLink) {
        calendarLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadCalendarView();
        });
    }
    
    // セッションリンク
    const sessionsLink = document.getElementById('sessions-link');
    if (sessionsLink) {
        sessionsLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadSessionsView();
        });
    }
    
    // シナリオリンク
    const scenariosLink = document.getElementById('scenarios-link');
    if (scenariosLink) {
        scenariosLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadScenariosView();
        });
    }
    
    // グループリンク
    const groupsLink = document.getElementById('groups-link');
    if (groupsLink) {
        groupsLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadGroupsView();
        });
    }
    
    // 統計リンク
    const statisticsLink = document.getElementById('statistics-link');
    if (statisticsLink) {
        statisticsLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadStatisticsView();
        });
    }
}

// クイックアクション設定
function setupQuickActions() {
    // セッション作成ボタン
    const createSessionBtn = document.getElementById('create-session-btn');
    if (createSessionBtn) {
        const isAnchor = createSessionBtn.tagName === 'A' && createSessionBtn.getAttribute('href');
        if (!isAnchor) {
            createSessionBtn.addEventListener('click', function() {
            if (createSessionBtn.dataset.arkhamAction === 'modal') {
                showCreateSessionModal();
                return;
            }
            loadCalendarView();
            });
        }
    }
    
    // セッション参加ボタン
    const joinSessionBtn = document.getElementById('join-session-btn');
    if (joinSessionBtn) {
        const isAnchor = joinSessionBtn.tagName === 'A' && joinSessionBtn.getAttribute('href');
        if (!isAnchor) {
            joinSessionBtn.addEventListener('click', function() {
            if (joinSessionBtn.dataset.arkhamAction === 'modal') {
                showJoinSessionModal();
                return;
            }
            loadSessionsView();
            });
        }
    }
    
    // シナリオ追加ボタン
    const addScenarioBtn = document.getElementById('add-scenario-btn');
    if (addScenarioBtn) {
        const isAnchor = addScenarioBtn.tagName === 'A' && addScenarioBtn.getAttribute('href');
        if (!isAnchor) {
            addScenarioBtn.addEventListener('click', function() {
            if (addScenarioBtn.dataset.arkhamAction === 'modal') {
                showAddScenarioModal();
                return;
            }
            loadScenariosView();
            });
        }
    }
}

// エルドリッチエフェクト初期化
function initEldritchEffects() {
    // ランダムに要素を光らせる
    setInterval(() => {
        const elements = document.querySelectorAll('.fas');
        if (elements.length > 0) {
            const randomElement = elements[Math.floor(Math.random() * elements.length)];
            randomElement.style.filter = 'drop-shadow(0 0 5px currentColor)';
            setTimeout(() => {
                randomElement.style.filter = '';
            }, 1000);
        }
    }, 5000);
}

// ビュー読み込み関数群
function loadCalendarView() {
    // カレンダービューの実装
    window.location.href = '/api/schedules/calendar/view/';
}

function loadSessionsView() {
    // セッションビューの実装
    window.location.href = '/api/schedules/sessions/view/';
}

function loadScenariosView() {
    // シナリオビューの実装
    window.location.href = '/api/scenarios/archive/view/';
}

function loadGroupsView() {
    // グループビューの実装
    window.location.href = '/accounts/groups/view/';
}

function loadStatisticsView() {
    // 統計ビューの実装
    window.location.href = '/accounts/statistics/view/';
}

// モーダル表示関数群
function showCreateSessionModal() {
    const modalHtml = ARKHAM.createModal(
        'セッション作成',
        `
        <form id="create-session-form">
            <div class="mb-3">
                <label class="form-label">セッションタイトル</label>
                <input type="text" class="form-control" name="title" required>
            </div>
            <div class="mb-3">
                <label class="form-label">日時</label>
                <input type="datetime-local" class="form-control" name="date" required>
            </div>
            <div class="mb-3">
                <label class="form-label">場所</label>
                <input type="text" class="form-control" name="location">
            </div>
            <div class="mb-3">
                <label class="form-label">説明</label>
                <textarea class="form-control" name="description" rows="3"></textarea>
            </div>
        </form>
        `,
        `
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
        <button type="button" class="btn btn-primary" onclick="submitCreateSession()">作成</button>
        `
    );
    
    const modalElement = document.createElement('div');
    modalElement.innerHTML = modalHtml;
    document.body.appendChild(modalElement.firstElementChild);
    
    const modal = new bootstrap.Modal(modalElement.firstElementChild);
    modal.show();
    
    // モーダルが閉じられたときに要素を削除
    modalElement.firstElementChild.addEventListener('hidden.bs.modal', function() {
        modalElement.remove();
    });
}

function showJoinSessionModal() {
    ARKHAM.showAlert('セッション参加機能は開発中です', 'warning');
}

function showAddScenarioModal() {
    ARKHAM.showAlert('シナリオ追加機能は開発中です', 'warning');
}

// セッション作成送信
function submitCreateSession() {
    const form = document.getElementById('create-session-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // グループIDをダミーで設定（後で実装）
    data.group = 1;
    data.visibility = 'group';
    
    axios.post(ARKHAM.endpoints.sessions, data)
        .then(response => {
            ARKHAM.showAlert('セッションが作成されました！', 'success');
            bootstrap.Modal.getInstance(form.closest('.modal')).hide();
            // ページリロードまたは動的更新
            setTimeout(() => location.reload(), 1000);
        })
        .catch(error => {
            ARKHAM.handleError(error);
        });
}

// ユーティリティ関数
function truncateText(text, maxLength = 100) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function getStatusBadge(status) {
    const statusMap = {
        'planned': { class: 'bg-primary', text: '予定' },
        'ongoing': { class: 'bg-warning', text: '進行中' },
        'completed': { class: 'bg-success', text: '完了' },
        'cancelled': { class: 'bg-danger', text: 'キャンセル' }
    };
    
    const statusInfo = statusMap[status] || { class: 'bg-secondary', text: status };
    return `<span class="badge ${statusInfo.class}">${statusInfo.text}</span>`;
}

function getRoleBadge(role) {
    const roleMap = {
        'gm': { class: 'bg-warning', text: 'GM' },
        'player': { class: 'bg-info', text: 'PL' }
    };
    
    const roleInfo = roleMap[role] || { class: 'bg-secondary', text: role };
    return `<span class="badge ${roleInfo.class}">${roleInfo.text}</span>`;
}
