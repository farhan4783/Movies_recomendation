/**
 * Movie Maverick - Animation Utilities
 * Advanced JavaScript utilities for scroll animations, stagger effects, and interactive features
 */

// ==================== SCROLL ANIMATIONS ====================

class ScrollAnimationObserver {
    constructor(options = {}) {
        this.options = {
            threshold: options.threshold || 0.1,
            rootMargin: options.rootMargin || '0px 0px -100px 0px',
            ...options
        };

        this.observer = new IntersectionObserver(
            this.handleIntersection.bind(this),
            this.options
        );

        this.init();
    }

    init() {
        // Observe all elements with data-animate attribute
        const elements = document.querySelectorAll('[data-animate]');
        elements.forEach(el => this.observer.observe(el));
    }

    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const animation = entry.target.dataset.animate;
                const delay = entry.target.dataset.delay || 0;

                setTimeout(() => {
                    entry.target.classList.add(`animate-${animation}`);
                    entry.target.style.opacity = '1';
                }, delay);

                // Unobserve after animation
                if (!entry.target.dataset.repeat) {
                    this.observer.unobserve(entry.target);
                }
            }
        });
    }

    observe(element) {
        this.observer.observe(element);
    }

    unobserve(element) {
        this.observer.unobserve(element);
    }
}

// ==================== STAGGER ANIMATIONS ====================

function staggerAnimation(selector, animationClass, delayIncrement = 100) {
    const elements = document.querySelectorAll(selector);

    elements.forEach((el, index) => {
        el.style.opacity = '0';
        setTimeout(() => {
            el.classList.add(animationClass);
            el.style.opacity = '1';
        }, index * delayIncrement);
    });
}

// ==================== PARALLAX SCROLL ====================

class ParallaxController {
    constructor(selector, speed = 0.5) {
        this.elements = document.querySelectorAll(selector);
        this.speed = speed;
        this.init();
    }

    init() {
        if (this.elements.length === 0) return;

        window.addEventListener('scroll', () => this.update(), { passive: true });
        this.update();
    }

    update() {
        const scrolled = window.pageYOffset;

        this.elements.forEach(el => {
            const yPos = -(scrolled * this.speed);
            el.style.transform = `translateY(${yPos}px)`;
        });
    }
}

// ==================== TOAST NOTIFICATIONS ====================

class ToastManager {
    constructor() {
        this.container = this.createContainer();
    }

    createContainer() {
        let container = document.querySelector('.toast-container');

        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        return container;
    }

    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icon = this.getIcon(type);
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <span style="font-size: 1.25rem;">${icon}</span>
                <span>${message}</span>
            </div>
        `;

        this.container.appendChild(toast);

        // Auto remove
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);

        return toast;
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// ==================== MODAL MANAGER ====================

class ModalManager {
    constructor() {
        this.activeModal = null;
    }

    open(content, options = {}) {
        this.close(); // Close any existing modal

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.onclick = (e) => {
            if (e.target === overlay && !options.persistent) {
                this.close();
            }
        };

        const modal = document.createElement('div');
        modal.className = 'modal';

        const header = document.createElement('div');
        header.className = 'modal-header';
        header.innerHTML = `
            <h2 style="margin: 0;">${options.title || ''}</h2>
            ${!options.persistent ? '<button class="modal-close">&times;</button>' : ''}
        `;

        const body = document.createElement('div');
        body.className = 'modal-body';

        if (typeof content === 'string') {
            body.innerHTML = content;
        } else {
            body.appendChild(content);
        }

        modal.appendChild(header);
        modal.appendChild(body);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        const closeBtn = header.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.onclick = () => this.close();
        }

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        this.activeModal = overlay;

        // ESC key to close
        if (!options.persistent) {
            this.escHandler = (e) => {
                if (e.key === 'Escape') this.close();
            };
            document.addEventListener('keydown', this.escHandler);
        }

        return overlay;
    }

    close() {
        if (this.activeModal) {
            this.activeModal.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                this.activeModal.remove();
                this.activeModal = null;
                document.body.style.overflow = '';
            }, 300);

            if (this.escHandler) {
                document.removeEventListener('keydown', this.escHandler);
                this.escHandler = null;
            }
        }
    }
}

// ==================== LOADING MANAGER ====================

class LoadingManager {
    constructor() {
        this.activeLoaders = new Set();
    }

    show(target = 'body', text = 'Loading...') {
        const container = typeof target === 'string'
            ? document.querySelector(target)
            : target;

        if (!container) return null;

        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 1rem;">
                <div class="spinner spinner-lg"></div>
                <p style="color: var(--text-secondary);">${text}</p>
            </div>
        `;
        loader.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(5px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            animation: fadeIn 0.3s ease;
        `;

        container.style.position = 'relative';
        container.appendChild(loader);
        this.activeLoaders.add(loader);

        return loader;
    }

    hide(loader) {
        if (loader && this.activeLoaders.has(loader)) {
            loader.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                loader.remove();
                this.activeLoaders.delete(loader);
            }, 300);
        }
    }

    hideAll() {
        this.activeLoaders.forEach(loader => this.hide(loader));
    }
}

// ==================== SCROLL PROGRESS ====================

class ScrollProgress {
    constructor(selector = '.scroll-progress') {
        this.element = document.querySelector(selector);
        if (this.element) {
            this.init();
        }
    }

    init() {
        window.addEventListener('scroll', () => this.update(), { passive: true });
        this.update();
    }

    update() {
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        const scrollPercent = (scrollTop / (documentHeight - windowHeight)) * 100;

        if (this.element) {
            this.element.style.width = `${Math.min(scrollPercent, 100)}%`;
        }
    }
}

// ==================== CONFETTI EFFECT ====================

function createConfetti(x, y, count = 50) {
    const colors = ['#e50914', '#ff6b72', '#667eea', '#f093fb', '#ffd700'];

    for (let i = 0; i < count; i++) {
        const confetti = document.createElement('div');
        confetti.style.cssText = `
            position: fixed;
            width: 10px;
            height: 10px;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            left: ${x}px;
            top: ${y}px;
            border-radius: 50%;
            pointer-events: none;
            z-index: 9999;
        `;

        document.body.appendChild(confetti);

        const angle = (Math.random() * 360) * (Math.PI / 180);
        const velocity = Math.random() * 5 + 5;
        const vx = Math.cos(angle) * velocity;
        const vy = Math.sin(angle) * velocity - 5;

        animateConfetti(confetti, vx, vy);
    }
}

function animateConfetti(element, vx, vy) {
    let x = parseFloat(element.style.left);
    let y = parseFloat(element.style.top);
    let velocityX = vx;
    let velocityY = vy;
    const gravity = 0.3;
    let opacity = 1;

    function update() {
        velocityY += gravity;
        x += velocityX;
        y += velocityY;
        opacity -= 0.01;

        element.style.left = x + 'px';
        element.style.top = y + 'px';
        element.style.opacity = opacity;

        if (opacity > 0 && y < window.innerHeight) {
            requestAnimationFrame(update);
        } else {
            element.remove();
        }
    }

    requestAnimationFrame(update);
}

// ==================== RIPPLE EFFECT ====================

function addRippleEffect(selector) {
    const elements = document.querySelectorAll(selector);

    elements.forEach(element => {
        element.style.position = 'relative';
        element.style.overflow = 'hidden';

        element.addEventListener('click', function (e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.5);
                left: ${x}px;
                top: ${y}px;
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;

            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    });
}

// ==================== SMOOTH SCROLL ====================

function smoothScrollTo(target, duration = 1000) {
    const targetElement = typeof target === 'string'
        ? document.querySelector(target)
        : target;

    if (!targetElement) return;

    const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset;
    const startPosition = window.pageYOffset;
    const distance = targetPosition - startPosition;
    let startTime = null;

    function animation(currentTime) {
        if (startTime === null) startTime = currentTime;
        const timeElapsed = currentTime - startTime;
        const run = ease(timeElapsed, startPosition, distance, duration);
        window.scrollTo(0, run);
        if (timeElapsed < duration) requestAnimationFrame(animation);
    }

    function ease(t, b, c, d) {
        t /= d / 2;
        if (t < 1) return c / 2 * t * t + b;
        t--;
        return -c / 2 * (t * (t - 2) - 1) + b;
    }

    requestAnimationFrame(animation);
}

// ==================== INITIALIZE ====================

// Global instances
const toast = new ToastManager();
const modal = new ModalManager();
const loading = new LoadingManager();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize scroll animations
    const scrollAnimations = new ScrollAnimationObserver();

    // Initialize scroll progress if element exists
    const scrollProgress = new ScrollProgress();

    // Add ripple effect to buttons
    addRippleEffect('.primary-btn, .secondary-btn');

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                smoothScrollTo(target);
            }
        });
    });

    // Add scroll class to navbar
    const navbar = document.querySelector('.sticky-nav');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }, { passive: true });
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ScrollAnimationObserver,
        ParallaxController,
        ToastManager,
        ModalManager,
        LoadingManager,
        ScrollProgress,
        staggerAnimation,
        createConfetti,
        addRippleEffect,
        smoothScrollTo,
        toast,
        modal,
        loading
    };
}
