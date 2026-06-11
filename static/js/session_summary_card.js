(function() {
    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getStatusLabel(status) {
        const labels = {
            planned: '予定',
            ongoing: '進行中',
            completed: '完了',
            cancelled: 'キャンセル',
        };
        return labels[status] || (status ? escapeHtml(status) : '未設定');
    }

    function getStatusBadgeClass(status) {
        const classes = {
            planned: 'text-bg-info',
            ongoing: 'text-bg-warning',
            completed: 'text-bg-success',
            cancelled: 'text-bg-danger',
        };
        return classes[status] || 'text-bg-secondary';
    }

    function getVisibilityLabel(visibility) {
        const labels = {
            private: 'プライベート',
            group: 'グループ内',
            public: '公開',
        };
        return labels[visibility] || '';
    }

    function getDateDisplay(session) {
        if (session.date_display) return escapeHtml(session.date_display);
        if (session.date_formatted) return escapeHtml(session.date_formatted);
        if (session.date) {
            try {
                return escapeHtml(new Date(session.date).toLocaleString('ja-JP'));
            } catch (error) {
                return escapeHtml(session.date);
            }
        }
        return '未定';
    }

    function getDurationDisplay(session) {
        if (session.duration_display) return escapeHtml(session.duration_display);
        const minutes = Number(session.duration_minutes || 0);
        if (Number.isFinite(minutes) && minutes > 0) {
            return `${minutes}分`;
        }
        return '';
    }

    function getGmName(session) {
        return escapeHtml(
            session.gm_detail?.nickname ||
            session.gm_detail?.username ||
            session.gm_name ||
            'GM'
        );
    }

    function renderParticipants(session) {
        const memberCount = Number(session.participant_count || 0);
        const guestCount = Number(session.guest_count || 0);
        const totalSuffix = `${memberCount}人${guestCount ? ` +ゲスト${guestCount}人` : ''}`;

        if (session.participants_summary) {
            return `<strong>${escapeHtml(session.participants_summary)}</strong> <span class="text-muted ms-1">(${escapeHtml(totalSuffix)})</span>`;
        }

        return `<strong>${escapeHtml(totalSuffix)}</strong>`;
    }

    function renderMetaItem(iconClass, content) {
        return `
            <div class="session-summary-card__meta-item">
                <i class="${iconClass}"></i>
                <div class="session-summary-card__meta-text">${content}</div>
            </div>
        `;
    }

    function renderRoleBadge(session, showRoleBadge) {
        if (!showRoleBadge || !session.my_role) return '';
        const isGm = session.my_role === 'gm';
        return `
            <div class="session-summary-card__role-badge">
                <span class="badge ${isGm ? 'bg-primary' : 'bg-secondary'}">${isGm ? 'GM' : 'PL'}</span>
            </div>
        `;
    }

    function render(session, options = {}) {
        const {
            actionHtml = '',
            clickable = false,
            compact = false,
            detailUrl = `/api/schedules/sessions/${session.id}/detail/`,
            footerHint = '',
            showRoleBadge = false,
            showYoutube = true,
        } = options;

        const durationDisplay = getDurationDisplay(session);
        const location = session.location ? escapeHtml(session.location) : '';
        const groupName = session.group_name ? escapeHtml(session.group_name) : '';
        const youtubeUrl = session.youtube_url ? escapeHtml(session.youtube_url) : '';
        const visibilityLabel = session.visibility_display || getVisibilityLabel(session.visibility);
        const titleTag = compact ? 'h6' : 'h5';

        const metaItems = [
            renderMetaItem(
                'fas fa-calendar-alt',
                `<strong>${getDateDisplay(session)}</strong>${durationDisplay ? `<span class="ms-2 text-muted">(${durationDisplay})</span>` : ''}`
            ),
            renderMetaItem('fas fa-user-tie', `GM: <strong>${getGmName(session)}</strong>`),
            renderMetaItem('fas fa-users', `参加者: ${renderParticipants(session)}`),
            location ? renderMetaItem('fas fa-map-marker-alt', location) : '',
            groupName ? renderMetaItem('fas fa-users-cog', `グループ: ${groupName}`) : '',
            visibilityLabel ? renderMetaItem('fas fa-eye', `公開設定: ${escapeHtml(visibilityLabel)}`) : '',
            showYoutube && youtubeUrl
                ? renderMetaItem(
                    'fab fa-youtube',
                    `<a href="${youtubeUrl}" target="_blank" rel="noopener noreferrer">配信を見る</a>`
                )
                : '',
        ].filter(Boolean).join('');

        const footer = footerHint || actionHtml
            ? `
                <div class="session-summary-card__footer">
                    <div class="session-summary-card__footer-hint">${footerHint ? `<i class="fas fa-arrow-right me-1"></i>${escapeHtml(footerHint)}` : ''}</div>
                    <div class="session-summary-card__actions">${actionHtml}</div>
                </div>
            `
            : '';

        const clickableAttributes = clickable
            ? ` role="button" tabindex="0" onclick="window.location.href='${detailUrl}'" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();window.location.href='${detailUrl}';}"`
            : '';

        return `
            <div class="card session-summary-card session-summary-card--${escapeHtml(session.status || 'planned')} ${clickable ? 'session-summary-card--clickable' : ''} mb-3"${clickableAttributes}>
                <div class="card-body">
                    <div class="session-summary-card__header">
                        <div class="session-summary-card__title-wrap">
                            ${renderRoleBadge(session, showRoleBadge)}
                            <${titleTag} class="session-summary-card__title ${compact ? 'session-summary-card__title--compact' : ''}">
                                ${escapeHtml(session.title || '無題セッション')}
                            </${titleTag}>
                        </div>
                        <span class="badge ${getStatusBadgeClass(session.status)}">${getStatusLabel(session.status)}</span>
                    </div>
                    <div class="session-summary-card__meta-list">
                        ${metaItems}
                    </div>
                    ${footer}
                </div>
            </div>
        `;
    }

    window.TablenoSessionCards = {
        escapeHtml,
        getStatusLabel,
        render,
    };
})();
