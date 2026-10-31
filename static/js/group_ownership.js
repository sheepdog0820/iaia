/* Consent-based group ownership. Names are always rendered as text. */
(function () {
    'use strict';

    function element(tag, text, className = '') {
        const node = document.createElement(tag);
        node.textContent = text;
        node.className = className;
        return node;
    }

    async function mount(container, { group, currentUserId, onChanged }) {
        container.replaceChildren();
        container.append(element('h6', '所有権の移譲'));
        container.append(element('p', `現在の所有者: ${group.owner_name}`, 'mb-2 text-break'));
        if (!group.is_member) return;
        const endpoint = `/api/accounts/groups/${group.id}/ownership-transfer/`;
        const status = element('p', '申請を確認しています。', 'small mb-2');
        status.setAttribute('role', 'status');
        container.append(status);
        const attached = () => container.isConnected;
        let busy = false;

        async function submit(button, action, data, confirmation) {
            if (busy || !attached()) return;
            busy = true;
            button.disabled = true;
            try {
                const confirmed = await ARKHAM.confirm(confirmation, { title: '所有権の移譲', confirmText: button.textContent });
                if (!confirmed || !attached()) return;
                try {
                    await axios.post(endpoint + action, data);
                } catch (error) {
                    // A lost response may follow a successful commit. Refresh the
                    // current state; never retry a mutation automatically.
                    ARKHAM.showError(error.response?.data?.error || '処理結果を確認できませんでした。最新の状態を確認してください。');
                    await onChanged();
                    return;
                }
                ARKHAM.showSuccess('所有権の申請状態を更新しました');
                await onChanged();
            } finally {
                busy = false;
                if (attached()) button.disabled = false;
            }
        }

        function action(label, path, data, confirmation) {
            const button = element('button', label, 'btn btn-outline-primary');
            button.type = 'button';
            button.addEventListener('click', () => {
                submit(button, path, data, confirmation).catch(() => {
                    if (attached()) status.textContent = '最新の状態を取得できませんでした。画面を再読み込みしてください。';
                });
            });
            return button;
        }

        try {
            const { data } = await axios.get(endpoint);
            if (!attached()) return;
            const request = data.transfer;
            const isOwner = currentUserId === group.owner;
            const active = request && !request.expired;
            const controls = element('div', '', 'd-flex flex-wrap gap-2');
            if (request) {
                const expiry = new Date(request.expires_at).toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' });
                status.textContent = request.expired
                    ? `申請の有効期限が切れています（${expiry} 日本時間）。`
                    : `${isOwner ? '承諾待ち' : 'あなた宛ての申請'}: ${request.target_name}（期限: ${expiry} 日本時間）`;
                if (isOwner) {
                    controls.append(action('申請を取り消す', 'cancel/', { request_id: request.id }, 'この所有権の移譲申請を取り消しますか？'));
                } else if (active && request.target === currentUserId) {
                    controls.append(action('承諾して引き継ぐ', 'accept/', { request_id: request.id }, 'グループの所有権を引き継ぎますか？ 新旧所有者は管理者になります。探索者・GM・課金契約は自動移譲されません。'));
                    controls.append(action('辞退する', 'decline/', { request_id: request.id }, 'この所有権の移譲申請を辞退しますか？'));
                }
            } else {
                status.textContent = isOwner ? '移譲先の本人が承諾すると所有者が変わります。申請の有効期限は7日間です。' : '所有権の申請・取消は現在の所有者が行います。';
            }
            if (isOwner && !active) {
                const candidates = data.candidates || [];
                if (candidates.length) {
                    const label = element('label', '移譲先のメンバー', 'form-label w-100');
                    const select = element('select', '', 'form-select');
                    label.append(select);
                    for (const candidate of candidates) {
                        const option = element('option', `${candidate.name}（ユーザー名: ${candidate.username}）`);
                        option.value = String(candidate.id);
                        select.append(option);
                    }
                    container.append(label);
                    const start = element('button', '移譲を申請', 'btn btn-outline-primary');
                    start.type = 'button';
                    start.addEventListener('click', () => {
                        const target = select.selectedOptions[0].textContent;
                        submit(start, '', { target_user_id: Number(select.value) }, `「${target}」へ所有権の移譲を申請しますか？ 本人の承諾が必要です。`).catch(() => {
                            if (attached()) status.textContent = '最新の状態を取得できませんでした。画面を再読み込みしてください。';
                        });
                    });
                    controls.append(start);
                } else {
                    container.append(element('p', '移譲先に指定できる有効な登録メンバーがいません。', 'small mb-2'));
                }
                container.append(element('p', '所有者は、移譲または明示的なグループ削除を済ませてから退会してください。探索者・GM・課金契約は自動移譲されません。', 'small text-muted'));
            }
            container.append(controls);
        } catch (error) {
            if (attached()) status.textContent = '所有権の申請を取得できませんでした。画面を再読み込みしてください。';
        }
    }

    window.GroupOwnership = { mount };
})();
