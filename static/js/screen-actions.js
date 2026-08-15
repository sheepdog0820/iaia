(function () {
    'use strict';

    function closeActionBar(actionBar) {
        if (!actionBar) return;
        actionBar.classList.remove('screen-actions-open');
        actionBar.querySelector('[data-screen-actions-toggle]')?.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('screen-actions-sheet-open');
    }

    function openActionBar(actionBar) {
        if (!actionBar) return;
        actionBar.classList.add('screen-actions-open');
        actionBar.querySelector('[data-screen-actions-toggle]')?.setAttribute('aria-expanded', 'true');
        document.body.classList.add('screen-actions-sheet-open');
        actionBar.querySelector('[data-screen-action-sheet] .btn, [data-screen-action-sheet] a')?.focus();
    }

    function initializeActionBar(actionBar) {
        const toggle = actionBar.querySelector('[data-screen-actions-toggle]');
        const sheet = actionBar.querySelector('[data-screen-action-sheet]');
        const page = actionBar.closest('[data-screen-actions-page]');
        const primary = actionBar.querySelector('.screen-action-primary');

        if (page && primary?.querySelector('.btn, a, button')) {
            page.classList.add('has-screen-primary-action');
        }

        if (!toggle || !sheet) return;

        const actionItems = sheet.querySelectorAll(
            '.btn:not(.screen-action-sheet-close), a, button:not(.screen-action-sheet-close)'
        );
        if (actionItems.length === 0) {
            toggle.classList.add('d-none');
            return;
        }

        toggle.addEventListener('click', () => {
            if (actionBar.classList.contains('screen-actions-open')) {
                closeActionBar(actionBar);
            } else {
                openActionBar(actionBar);
            }
        });

        actionBar.querySelectorAll('[data-screen-actions-close]').forEach(element => {
            element.addEventListener('click', () => closeActionBar(actionBar));
        });

        sheet.addEventListener('click', event => {
            if (event.target.closest('[data-screen-actions-keep-open]')) return;
            if (event.target.closest('.btn, a, button')) {
                closeActionBar(actionBar);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-screen-actions]').forEach(initializeActionBar);

        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                document.querySelectorAll('[data-screen-actions].screen-actions-open').forEach(closeActionBar);
            }
        });
    });
})();
