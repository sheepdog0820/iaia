(function () {
    'use strict';

    const viewer = document.getElementById('sessionScenarioImageViewer');
    if (!viewer) {
        return;
    }

    // The template nests the dialog in the scenario card; place it at the page
    // root so fixed positioning is not clipped by card/container styles.
    document.body.appendChild(viewer);

    const openers = Array.from(document.querySelectorAll('[data-scenario-image-open]'));
    const image = viewer.querySelector('[data-scenario-viewer-image]');
    const title = viewer.querySelector('[data-scenario-viewer-title]');
    const count = viewer.querySelector('[data-scenario-viewer-count]');
    const closeButton = viewer.querySelector('[data-scenario-viewer-close]');
    const previousButton = viewer.querySelector('[data-scenario-viewer-previous]');
    const nextButton = viewer.querySelector('[data-scenario-viewer-next]');
    let currentIndex = 0;
    let lastOpener = null;
    let previousBodyOverflow = '';

    function showImage(index) {
        currentIndex = (index + openers.length) % openers.length;
        const opener = openers[currentIndex];
        const imageTitle = opener.dataset.imageTitle || opener.querySelector('img')?.alt || 'シナリオ画像';

        image.src = opener.dataset.imageUrl;
        image.alt = imageTitle;
        title.textContent = imageTitle;
        count.textContent = `${currentIndex + 1} / ${openers.length}`;
        previousButton.hidden = openers.length < 2;
        nextButton.hidden = openers.length < 2;
    }

    function openViewer(index, opener) {
        if (!openers.length) {
            return;
        }

        lastOpener = opener;
        showImage(index);
        previousBodyOverflow = document.body.style.overflow;
        viewer.hidden = false;
        viewer.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        closeButton.focus();
    }

    function closeViewer() {
        viewer.hidden = true;
        viewer.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = previousBodyOverflow;
        image.removeAttribute('src');
        if (lastOpener) {
            lastOpener.focus();
        }
    }

    openers.forEach((opener, index) => {
        opener.addEventListener('click', () => openViewer(index, opener));
    });
    closeButton.addEventListener('click', closeViewer);
    previousButton.addEventListener('click', () => showImage(currentIndex - 1));
    nextButton.addEventListener('click', () => showImage(currentIndex + 1));

    viewer.addEventListener('click', (event) => {
        if (event.target === viewer) {
            closeViewer();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (viewer.hidden) {
            return;
        }

        if (event.key === 'Escape') {
            event.preventDefault();
            closeViewer();
        } else if (event.key === 'ArrowLeft' && openers.length > 1) {
            event.preventDefault();
            showImage(currentIndex - 1);
        } else if (event.key === 'ArrowRight' && openers.length > 1) {
            event.preventDefault();
            showImage(currentIndex + 1);
        } else if (event.key === 'Tab') {
            const focusableButtons = [closeButton, previousButton, nextButton]
                .filter((button) => !button.hidden);
            const firstButton = focusableButtons[0];
            const lastButton = focusableButtons[focusableButtons.length - 1];

            if (event.shiftKey && document.activeElement === firstButton) {
                event.preventDefault();
                lastButton.focus();
            } else if (!event.shiftKey && document.activeElement === lastButton) {
                event.preventDefault();
                firstButton.focus();
            }
        }
    });
})();
