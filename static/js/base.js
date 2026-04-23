document.addEventListener('DOMContentLoaded', function () {

    /* ═══════════════════════════════════════════════════════════
       SPA NAVIGATION — Only reload content, not sidebar/header
    ═══════════════════════════════════════════════════════════ */
    const mainContent = document.getElementById('mainContent');
    const loadingIndicator = document.getElementById('navLoadingIndicator');
    let isNavigating = false;

    // Intercept all internal navigation links
    function enableSmoothNavigation() {
        // Select sidebar links AND content area links
        const navLinks = document.querySelectorAll('.sidebar-link, #mainContent a');

        navLinks.forEach(link => {
            // Skip if already processed
            if (link.hasAttribute('data-spa-enabled')) return;
            link.setAttribute('data-spa-enabled', 'true');

            const href = link.getAttribute('href');

            // Skip SPA navigation if data-spa-reload="false" is set (force full reload)
            if (link.getAttribute('data-spa-reload') === 'false') {
                return;
            }

            // Skip external links, anchors, javascript links
            if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('javascript:') || href.startsWith('mailto:')) {
                return;
            }

            // Only intercept internal links
            if (href) {
                link.addEventListener('click', function(e) {
                    // Allow default behavior for Ctrl/Cmd/Shift clicks (open in new tab)
                    if (e.ctrlKey || e.metaKey || e.shiftKey) return;

                    e.preventDefault();
                    navigateToPage(href, link);
                });
            }
        });
    }

    // Navigate to a new page via AJAX
    async function navigateToPage(url, clickedLink) {
        if (isNavigating) return;
        isNavigating = true;

        // Show loading state
        if (mainContent) mainContent.classList.add('page-loading');
        if (loadingIndicator) loadingIndicator.classList.add('active');

        // Scroll to top immediately so the new page doesn't appear to slide up
        window.scrollTo(0, 0);

        try {
            // Fetch the new page
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error('Navigation failed');
            }

            // If session expired and redirected to login, do full page redirect
            if (response.url.includes('/login/')) {
                window.location.href = response.url;
                return;
            }

            const html = await response.text();

            // Parse the HTML
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            // Extract the new content
            const newContent = doc.querySelector('#mainContent');

            if (newContent && mainContent) {
                // 1. Abort old page listeners / destroy charts — but do NOT remove CSS yet.
                //    Removing CSS before the swap causes the old content (still visible at
                //    30% opacity) to lose its styles, which makes the topbar/header jump.
                cleanupOldPageResources();

                // 2. Pre-load new styles (tagged data-new-page-style) while old CSS stays.
                //    Awaiting here means new CSS is already parsed before we swap content.
                await loadPageStyles(doc);

                // 3. Swap content, then immediately flush old CSS and promote new CSS.
                //    Both happen in the same synchronous block so the browser sees exactly
                //    one layout: new content + new styles, no intermediate unstyled frame.
                mainContent.innerHTML = newContent.innerHTML;
                mainContent.setAttribute('data-url', url);
                flushOldPageStyles();

                // Update page title
                const newTitle = doc.querySelector('title');
                if (newTitle) document.title = newTitle.textContent;

                // Update URL
                window.history.pushState({url: url}, '', url);

                // Store current SPA URL for visibility/bfcache restoration
                window.currentSPAUrl = url;

                // Update active nav state
                updateActiveNav(url);

                // 4. Execute page-specific scripts
                executePageScripts(doc);

                // Restore scroll position in next frame (layout is stable by then)
                const targetScrollY = window._restoreScrollY || 0;
                window._restoreScrollY = null;

                requestAnimationFrame(() => {
                    window.scrollTo(0, targetScrollY);
                });
            } else {
                // Fallback to full page load
                window.location.href = url;
            }
        } catch (error) {
            console.error('Navigation error:', error);
            // Fallback to full page load
            window.location.href = url;
        } finally {
            // Hide loading state
            if (mainContent) mainContent.classList.remove('page-loading');
            if (loadingIndicator) loadingIndicator.classList.remove('active');
            isNavigating = false;
        }
    }

    // Clean up old page-specific resources
    function cleanupOldPageResources() {
        const popup = document.getElementById('monthPickerPopup');
        if (popup) {
            popup.classList.remove('show');
            popup.style.display = 'none';
            popup.remove(); // ✅ fully remove it from DOM
        }
        // Abort all page-specific event listeners registered via AbortController
        if (window._pageAbortController) {
            window._pageAbortController.abort();
            window._pageAbortController = null;
        }
        if (window.Chart) {
            Object.values(Chart.instances).forEach(chart => {
                try { chart.destroy(); } catch(e) {}
            });
        }

        delete window._voucherListScriptLoaded;
        delete window._popstateListenerAdded;
        delete window._escapeListenerAdded;
        delete window._modalClickListenersAdded;
        delete window._searchUIInitialized;

        // CSS cleanup intentionally omitted here — deferred to flushOldPageStyles()
        // which is called AFTER content injection to prevent layout shifts.
        // Only scripts are removed now so stale JS doesn't linger.
        document.querySelectorAll('script[data-page-specific]').forEach(el => el.remove());
    }

    // Swap CSS in one shot: remove old page styles, promote newly loaded styles.
    // Called synchronously right after mainContent.innerHTML is set, so the browser
    // paints new content + new CSS together without an unstyled intermediate frame.
    function flushOldPageStyles() {
        // Remove old page-specific styles
        document.querySelectorAll('style[data-page-specific]').forEach(el => el.remove());
        document.querySelectorAll('link[data-page-specific]').forEach(el => el.remove());
        // Remove any unmarked inline styles (but not base styles or newly loaded styles)
        document.querySelectorAll('head style:not([data-base]):not([data-new-page-style])').forEach(el => el.remove());

        // Promote newly loaded styles to page-specific so they're cleaned up next navigation
        document.querySelectorAll('[data-new-page-style]').forEach(el => {
            el.removeAttribute('data-new-page-style');
            el.setAttribute('data-page-specific', 'true');
        });
    }

    // Load page-specific CSS from the fetched document.
    // Returns a Promise that resolves once all new <link> stylesheets have loaded,
    // so callers can await it before injecting content (prevents FOUC).
    async function loadPageStyles(doc) {
        // Inject inline <style> tags synchronously (instant, no network round-trip)
        // Tagged data-new-page-style so flushOldPageStyles() can promote them later.
        const styleTags = doc.querySelectorAll('head style');
        styleTags.forEach(style => {
            if (style.textContent.includes('FINVAULT DESIGN SYSTEM')) return;
            if (style.textContent.includes('Prevent white flash')) return;

            const newStyle = document.createElement('style');
            newStyle.textContent = style.textContent;
            newStyle.setAttribute('data-new-page-style', 'true');
            document.head.appendChild(newStyle);
        });

        // Load external stylesheets and collect load promises
        const linkPromises = [];
        const linkTags = doc.querySelectorAll('head link[rel="stylesheet"]');
        linkTags.forEach(link => {
            const href = link.getAttribute('href');
            if (!href) return;

            // Skip global bootstrap
            if (href.includes('bootstrap') && !href.includes('dataTables')) return;

            // Match by filename only, not full path
            const fileName = href.split('/').pop().split('?')[0];
            const alreadyLoaded = Array.from(
                document.querySelectorAll('link[rel="stylesheet"]')
            ).some(l => {
                const existingFile = l.getAttribute('href')?.split('/').pop().split('?')[0];
                return existingFile === fileName;
            });

            if (!alreadyLoaded) {
                const newLink = document.createElement('link');
                newLink.rel = 'stylesheet';
                newLink.href = href;
                newLink.setAttribute('data-new-page-style', 'true');
                const p = new Promise(resolve => {
                    newLink.onload = resolve;
                    newLink.onerror = resolve;   // Don't block on CSS error
                    setTimeout(resolve, 2000);   // Safety timeout
                });
                linkPromises.push(p);
                document.head.appendChild(newLink);
            }
        });

        if (linkPromises.length > 0) {
            await Promise.all(linkPromises);
        }
    }

    // Execute page-specific scripts from the fetched document
function executePageScripts(doc) {
    const scripts = doc.querySelectorAll('body script');
    const externalScripts = [];
    const inlineScripts = [];

    scripts.forEach(oldScript => {
        const src = oldScript.getAttribute('src');
        if (src) {
            if (src.includes('bootstrap.bundle')) return;
            // Always reload Chart.js to ensure it's available
            if (src.includes('chart.umd')) {
                // Remove old Chart.js if it exists
                const oldChart = document.querySelector('script[src*="chart.umd"]');
                if (oldChart) oldChart.remove();
            }
            externalScripts.push(src);
        } else {
            inlineScripts.push(oldScript.textContent);
        }
    });

    // Load all external scripts first, THEN run inline scripts in order
    function loadScriptsSequentially(srcs, index, callback) {
        if (index >= srcs.length) {
            callback();
            return;
        }
        const src = srcs[index];
        const existing = document.querySelector(`script[src="${src}"]`);
        if (existing && !src.includes('chart.umd')) {
            // Skip if already loaded (except Chart.js which we always reload)
            loadScriptsSequentially(srcs, index + 1, callback);
            return;
        }

        const s = document.createElement('script');
        s.src = src;
        s.setAttribute('data-page-specific', 'true');

        let scriptLoaded = false;
        const timeout = setTimeout(() => {
            if (!scriptLoaded) {
                console.warn(`Script loading timeout: ${src}`);
                loadScriptsSequentially(srcs, index + 1, callback);
            }
        }, 10000); // 10 second timeout

        s.onload = () => {
            scriptLoaded = true;
            clearTimeout(timeout);
            // Wait a bit for Chart.js to fully initialize
            if (src.includes('chart.umd')) {
                setTimeout(() => {
                    loadScriptsSequentially(srcs, index + 1, callback);
                }, 300);
            } else {
                loadScriptsSequentially(srcs, index + 1, callback);
            }
        };

        s.onerror = () => {
            scriptLoaded = true;
            clearTimeout(timeout);
            console.error(`Failed to load script: ${src}`);
            loadScriptsSequentially(srcs, index + 1, callback);
        };

        document.body.appendChild(s);
    }

    loadScriptsSequentially(externalScripts, 0, function () {
        inlineScripts.forEach(code => {
            var _origAddEvt = document.addEventListener.bind(document);
            var _origReady;
            try {
                // Patch document.addEventListener BEFORE creating the script element
                // so DOMContentLoaded listeners inside the script fire immediately
                document.addEventListener = function(type, fn, opts) {
                    if (type === 'DOMContentLoaded') {
                        // Execute immediately since DOM is already loaded
                        setTimeout(fn, 0);
                        return;
                    }
                    return _origAddEvt(type, fn, opts);
                };

                // Shim jQuery ready if jQuery exists
                if (window.jQuery) {
                    _origReady = jQuery.fn.ready;
                    jQuery.fn.ready = function(fn) {
                        setTimeout(fn, 0);
                        return this;
                    };
                }

                const s = document.createElement('script');
                s.textContent = code;  // run directly, no IIFE wrapper
                s.setAttribute('data-page-specific', 'true');
                document.body.appendChild(s);
            } catch (e) {
                console.error('Script execution error during SPA navigation:', e);
                console.error('Failed script preview:', code.substring(0, 200));
            } finally {
                // Always restore — even if the script threw on execution
                document.addEventListener = _origAddEvt;
                if (window.jQuery && _origReady) {
                    jQuery.fn.ready = _origReady;
                }
            }
        });

        // Trigger custom event after all scripts are executed
        setTimeout(() => {
            window.dispatchEvent(new Event('spa-navigation-complete'));
        }, 300);
    });
}

    // Update active navigation highlight
    function updateActiveNav(url) {
        document.querySelectorAll('.sidebar-link').forEach(link => {
            link.classList.remove('active');
            const linkPath = new URL(link.href, window.location.origin).pathname;
            const currentPath = new URL(url, window.location.origin).pathname;

            if (linkPath === currentPath || (linkPath !== '/' && currentPath.startsWith(linkPath))) {
                link.classList.add('active');

                // Update topbar title
                const navLabel = link.querySelector('.nav-label');
                const titleEl = document.getElementById('topbarPageTitle');
                if (navLabel && titleEl) {
                    titleEl.textContent = navLabel.textContent.trim();
                }
            }
        });
    }


    // Expose navigateToPage globally so other scripts (e.g. voucher_list.js) can use SPA navigation
    window.navigateToPage = navigateToPage;

    // Handle browser back/forward buttons — all navigation goes through SPA
    window.addEventListener('popstate', function(event) {
        const url = (event.state && event.state.url) ? event.state.url : window.location.href;
        // Check if we have a saved scroll position for the target URL
        try {
            const saved = JSON.parse(sessionStorage.getItem('pvListScroll') || 'null');
            const targetPath = url.replace(/^https?:\/\/[^/]+/, ''); // strip origin if present
            if (saved && saved.url === targetPath && saved.scrollY) {
                sessionStorage.removeItem('pvListScroll');
                window._restoreScrollY = saved.scrollY;
            }
        } catch(e) {}
        navigateToPage(url);
    });

    // Initialize smooth navigation on page load
    enableSmoothNavigation();

    // Re-enable smooth navigation after SPA navigation completes
    window.addEventListener('spa-navigation-complete', function() {
        enableSmoothNavigation();
        // Re-initialize mobile navigation toggle
        if (typeof initMobileNav === 'function') {
            initMobileNav();
        }
    });

    // Store initial state for back button
    if (mainContent) {
        const initialUrl = mainContent.getAttribute('data-url') || window.location.pathname;
        window.history.replaceState({url: initialUrl}, '', initialUrl);
    }

    /* ── Sidebar collapse (desktop) ── */
    const sidebar        = document.getElementById('sidebar');
    const contentWrapper = document.getElementById('contentWrapper');
    const topbar         = document.getElementById('topbar');
    const toggleBtn      = document.getElementById('sidebarToggle');
    const toggleIcon     = document.getElementById('toggleIcon');
    const COLLAPSED_KEY  = 'sidebar_collapsed';
    const PINNED_KEY     = 'sidebar_pinned';
    const IDLE_TIMEOUT   = 5 * 60 * 1000; // 5 minutes

    let idleTimer = null;
    let wasAutoCollapsed = false;

    function applyCollapsed(collapsed) {
        if (!sidebar) return;

        // Apply collapsed state
        sidebar.classList.toggle('collapsed', collapsed);
        contentWrapper && contentWrapper.classList.toggle('sidebar-collapsed', collapsed);
        topbar         && topbar.classList.toggle('sidebar-collapsed', collapsed);
        if (toggleIcon) {
            toggleIcon.className = collapsed ? 'bi bi-chevron-right' : 'bi bi-chevron-left';
        }

        // Force layout recalculation to prevent ghost spacing
        requestAnimationFrame(() => {
            // Force reflow by reading offsetHeight
            if (sidebar) {
                const h = sidebar.offsetHeight;
                const brandElement = sidebar.querySelector('.sidebar-brand');
                const navElement = sidebar.querySelector('.sidebar-nav');

                if (brandElement) {
                    const brandHeight = brandElement.offsetHeight;
                }
                if (navElement) {
                    const navHeight = navElement.offsetHeight;
                }
            }
        });
    }

    // Restore saved state
    applyCollapsed(localStorage.getItem(COLLAPSED_KEY) === 'true');

    // Manual toggle button
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            const isCollapsed = sidebar.classList.contains('collapsed');
            applyCollapsed(!isCollapsed);
            localStorage.setItem(COLLAPSED_KEY, !isCollapsed);

            // If user manually toggles, mark as pinned to prevent auto-collapse
            localStorage.setItem(PINNED_KEY, 'true');
            wasAutoCollapsed = false;

            // Restart idle timer
            resetIdleTimer();
        });
    }

    /* ═══════════════════════════════════════════════════════════
       AUTO-COLLAPSE SIDEBAR AFTER 5 MINUTES OF INACTIVITY
    ═══════════════════════════════════════════════════════════ */

    function autoCollapseSidebar() {
        // Don't auto-collapse if user manually pinned it open
        const isPinned = localStorage.getItem(PINNED_KEY) === 'true';
        if (isPinned) return;

        // Don't auto-collapse if already collapsed
        if (sidebar && sidebar.classList.contains('collapsed')) return;

        // Don't auto-collapse if user is typing in input
        const activeElement = document.activeElement;
        if (activeElement && (
            activeElement.tagName === 'INPUT' ||
            activeElement.tagName === 'TEXTAREA' ||
            activeElement.isContentEditable
        )) {
            resetIdleTimer(); // Restart timer if typing
            return;
        }

        // Auto-collapse
        applyCollapsed(true);
        wasAutoCollapsed = true;
    }

    function autoExpandSidebar() {
        // Only expand if it was auto-collapsed (not manually collapsed)
        if (wasAutoCollapsed && sidebar && sidebar.classList.contains('collapsed')) {
            applyCollapsed(false);
            wasAutoCollapsed = false;
        }
        resetIdleTimer();
    }

    function resetIdleTimer() {
        // Clear existing timer
        if (idleTimer) {
            clearTimeout(idleTimer);
        }

        // Set new timer
        idleTimer = setTimeout(autoCollapseSidebar, IDLE_TIMEOUT);
    }

    // Track user activity to reset idle timer
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

    activityEvents.forEach(event => {
        document.addEventListener(event, function(e) {
            // Don't reset timer for sidebar hover (we want to allow expansion)
            if (event === 'mousemove' && e.target.closest('#sidebar')) {
                return;
            }

            // If user clicks anywhere and sidebar was auto-collapsed, expand it
            if (event === 'click' && wasAutoCollapsed) {
                autoExpandSidebar();
            } else {
                resetIdleTimer();
            }
        }, { passive: event !== 'click' });
    });

    // Expand sidebar on hover (if auto-collapsed)
    if (sidebar) {
        sidebar.addEventListener('mouseenter', function() {
            autoExpandSidebar();
        });

        // Optional: Re-collapse on mouse leave if was auto-collapsed
        sidebar.addEventListener('mouseleave', function() {
            if (wasAutoCollapsed) {
                // Give a short delay before re-collapsing
                setTimeout(() => {
                    if (wasAutoCollapsed && !sidebar.matches(':hover')) {
                        applyCollapsed(true);
                    }
                }, 300);
            }
        });
    }

    // Start idle timer on page load
    resetIdleTimer();

    // Reset pinned state on page load (optional - remove if you want pin to persist across sessions)
    // localStorage.removeItem(PINNED_KEY);

    /* ── Mobile sidebar ── */
    function openMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        sidebar  && sidebar.classList.add('mobile-open');
        overlay  && overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        sidebar  && sidebar.classList.remove('mobile-open');
        overlay  && overlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    function toggleMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && sidebar.classList.contains('mobile-open')) {
            closeMobileSidebar();
        } else {
            openMobileSidebar();
        }
    }

    // Initialize mobile navigation toggle
    function initMobileNav() {
        const mobileToggle = document.getElementById('mobileToggle');
        const overlay = document.getElementById('sidebarOverlay');

        // Remove existing listeners to prevent duplicates
        if (mobileToggle) {
            const newMobileToggle = mobileToggle.cloneNode(true);
            mobileToggle.parentNode.replaceChild(newMobileToggle, mobileToggle);
            newMobileToggle.addEventListener('click', toggleMobileSidebar);
        }

        if (overlay) {
            const newOverlay = overlay.cloneNode(true);
            overlay.parentNode.replaceChild(newOverlay, overlay);
            newOverlay.addEventListener('click', closeMobileSidebar);
        }
    }

    // Initialize on page load
    initMobileNav();

    /* ═══════════════════════════════════════════════════════════
       FIX HEADER POSITION AFTER IDLE/INACTIVITY
       When page is idle for long time, header can get cut off
    ═══════════════════════════════════════════════════════════ */
    function fixHeaderPosition() {
        // Reset scroll to top
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;

        // Force layout recalculation
        requestAnimationFrame(() => {
            const topbar = document.querySelector('.topbar');
            const sidebar = document.querySelector('.sidebar');
            const contentWrapper = document.querySelector('.content-wrapper');

            // Force reflow by reading dimensions
            if (topbar) {
                const h = topbar.offsetHeight;
                topbar.style.top = '0';
                topbar.style.position = 'fixed';
            }
            if (sidebar) {
                const w = sidebar.offsetWidth;
                sidebar.style.top = '0';
            }
            if (contentWrapper) {
                const h = contentWrapper.offsetHeight;
                contentWrapper.style.marginTop = 'var(--topbar-h)';
            }

            // Dispatch events to recalculate everything
            requestAnimationFrame(() => {
                window.dispatchEvent(new Event('resize'));
                window.dispatchEvent(new Event('scroll'));
            });
        });
    }

    // Fix header when page becomes visible again after being hidden
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            // Only fix header position, no auto-reload
            fixHeaderPosition();
        }
    });

    // Fix header when returning from browser back/forward (bfcache restoration)
    // Page restored from bfcache means stale state - force full reload
    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            // Page was restored from bfcache - reload to get fresh state
            console.log('Page restored from bfcache - reloading for fresh state');
            window.location.reload();
        }
    });

    /* ═══════════════════════════════════════════════════════════
       GLOBAL CLICK HANDLER — Handles all topbar interactions
       Using event delegation for reliability across SPA navigation
    ═══════════════════════════════════════════════════════════ */
    function closeAllDropdowns() {
        const notifDropdown = document.getElementById('notifDropdown');
        const userDropdown = document.getElementById('userDropdown');
        notifDropdown && notifDropdown.classList.remove('show');
        userDropdown  && userDropdown.classList.remove('show');
    }
    // Close month picker when clicking outside
    document.addEventListener('click', function(e) {
        const popup = document.getElementById('monthPickerPopup');
        if (!popup) return;
        if (
            !popup.contains(e.target) &&
            !e.target.closest('.filter-year-btn') &&
            !e.target.closest('.fiscal-year-btn') &&
            !e.target.closest('[data-month-picker]')
        ) {
            popup.classList.remove('show');
            popup.style.display = 'none';
        }
    });

    // Close month picker on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const popup = document.getElementById('monthPickerPopup');
            if (popup) {
                popup.classList.remove('show');
                popup.style.display = 'none';
            }
        }
    });

    /* ── Alert toast management: dedup · cap · auto-dismiss ── */
    (function () {
        const container = document.querySelector('.alert-container');
        if (!container) return;

        const MAX_TOASTS = 3;

        // 1. Remove duplicate messages (keep first occurrence of each text)
        const seen = new Set();
        container.querySelectorAll('.modern-alert').forEach(function (alert) {
            const text = (alert.querySelector('.alert-content') || alert).textContent.trim();
            if (seen.has(text)) {
                alert.remove();
            } else {
                seen.add(text);
            }
        });

        // 2. Cap at MAX_TOASTS — remove oldest excess alerts
        const remaining = Array.from(container.querySelectorAll('.modern-alert'));
        if (remaining.length > MAX_TOASTS) {
            remaining.slice(MAX_TOASTS).forEach(function (a) { a.remove(); });
        }

        // 3. Auto-dismiss each visible toast after 4 s (stagger by 300 ms so they don't all vanish at once)
        container.querySelectorAll('.modern-alert').forEach(function (alert, idx) {
            setTimeout(function () {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                if (bsAlert) bsAlert.close();
            }, 4000 + idx * 300);
        });
    })();

    /* ── Active link highlight ── */
    const path = window.location.pathname;
    document.querySelectorAll('.sidebar-link').forEach(function (link) {
        if (link.href && link.getAttribute('href') !== '#') {
            try {
                const linkPath = new URL(link.href).pathname;
                if (path === linkPath || (linkPath !== '/' && path.startsWith(linkPath))) {
                    link.classList.add('active');
                }
            } catch(e) {}
        }
    });

    /* ── Dynamic topbar page title (breadcrumb) ── */
    const titleEl = document.getElementById('topbarPageTitle');
    if (titleEl) {
        const activeLink = document.querySelector('.sidebar-link.active .nav-label');
        if (activeLink) titleEl.textContent = activeLink.textContent.trim();
    }

    /* ═══════════════════════════════════════════════════════════
       THEME TOGGLE — Light/Dark Mode
    ═══════════════════════════════════════════════════════════ */
    const body = document.body;

    // Initialize theme from localStorage or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    body.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Update icon based on theme
    function updateThemeIcon(theme) {
        const themeIcon = document.getElementById('themeIcon');
        const themeToggle = document.getElementById('themeToggle');
        if (themeIcon && themeToggle) {
            if (theme === 'light') {
                themeIcon.className = 'bi bi-sun-fill';
                themeToggle.title = 'Switch to dark mode';
            } else {
                themeIcon.className = 'bi bi-moon-fill';
                themeToggle.title = 'Switch to light mode';
            }
        }
    }

    function handleThemeToggle() {
        const currentTheme = body.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        document.documentElement.setAttribute('data-theme', newTheme);
        body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    }

});

/* ═══════════════════════════════════════════════════════════
   GLOBAL TOPBAR FUNCTIONS
   Attached directly to window object so onclick handlers work
   Cannot be blocked by page-specific scripts
═══════════════════════════════════════════════════════════ */

// Theme toggle function
window.toggleTheme = function(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    document.documentElement.setAttribute('data-theme', newTheme);
    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Update icon
    const themeIcon = document.getElementById('themeIcon');
    const themeToggle = document.getElementById('themeToggle');
    if (themeIcon && themeToggle) {
        if (newTheme === 'light') {
            themeIcon.className = 'bi bi-sun-fill';
            themeToggle.title = 'Switch to dark mode';
        } else {
            themeIcon.className = 'bi bi-moon-fill';
            themeToggle.title = 'Switch to light mode';
        }
    }
};

// Notification dropdown toggle function
window.toggleNotifDropdown = function(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    const notifDropdown = document.getElementById('notifDropdown');
    const userDropdown = document.getElementById('userDropdown');

    const isOpen = notifDropdown && notifDropdown.classList.contains('show');

    // Close all first
    notifDropdown && notifDropdown.classList.remove('show');
    userDropdown && userDropdown.classList.remove('show');

    // Toggle notification dropdown
    if (!isOpen && notifDropdown) {
        notifDropdown.classList.add('show');
    }
};

// User dropdown toggle function
window.toggleUserDropdown = function(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    const notifDropdown = document.getElementById('notifDropdown');
    const userDropdown = document.getElementById('userDropdown');

    const isOpen = userDropdown && userDropdown.classList.contains('show');

    // Close all first
    notifDropdown && notifDropdown.classList.remove('show');
    userDropdown && userDropdown.classList.remove('show');

    // Toggle user dropdown
    if (!isOpen && userDropdown) {
        userDropdown.classList.add('show');
    }
};

// Close dropdowns when clicking outside
document.addEventListener('click', function(e) {
    // Don't close if clicking on buttons (handled by onclick)
    if (e.target.closest('#notifBtn') || e.target.closest('#userBtn') || e.target.closest('#themeToggle')) {
        return;
    }

    // Don't close if clicking inside a dropdown
    if (e.target.closest('#notifDropdown') || e.target.closest('#userDropdown')) {
        return;
    }

    // Close all dropdowns
    const notifDropdown = document.getElementById('notifDropdown');
    const userDropdown = document.getElementById('userDropdown');
    notifDropdown && notifDropdown.classList.remove('show');
    userDropdown && userDropdown.classList.remove('show');
});

// ============================================================================
// CSRF TOKEN KEEP-ALIVE SYSTEM
// Prevents CSRF token staleness after page idle periods
// ============================================================================

(function() {
    'use strict';

    // Configuration
    const KEEP_ALIVE_INTERVAL = 4 * 60 * 1000; // 4 minutes in milliseconds
    const KEEP_ALIVE_URL = '/keep-alive/';

    let keepAliveTimer = null;

    /**
     * Updates all CSRF tokens on the page with a fresh token
     * @param {string} newToken - Fresh CSRF token from server
     */
    function updateCSRFTokens(newToken) {
        // Update all hidden CSRF input fields
        document.querySelectorAll('[name=csrfmiddlewaretoken]').forEach(input => {
            input.value = newToken;
        });

        // Update CSRF cookie if it exists
        document.cookie = `csrftoken=${newToken}; path=/; SameSite=Lax`;

        // Update any global csrfToken variables used in inline scripts
        if (typeof window.csrfToken !== 'undefined') {
            window.csrfToken = newToken;
        }
    }

    /**
     * Pings the keep-alive endpoint to refresh session and CSRF token
     */
    function pingKeepAlive() {
        fetch(KEEP_ALIVE_URL, {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'ok' && data.csrf_token) {
                updateCSRFTokens(data.csrf_token);
                console.debug('[Keep-Alive] Session and CSRF token refreshed at', data.timestamp);
            }
        })
        .catch(error => {
            // Silent fail - don't alert user for network errors
            console.debug('[Keep-Alive] Ping failed:', error.message);
        });
    }

    /**
     * Starts the keep-alive timer
     */
    function startKeepAlive() {
        // Clear any existing timer
        if (keepAliveTimer) {
            clearInterval(keepAliveTimer);
        }

        // Ping immediately on start
        pingKeepAlive();

        // Set up periodic pings
        keepAliveTimer = setInterval(pingKeepAlive, KEEP_ALIVE_INTERVAL);
    }

    /**
     * Handles tab visibility changes
     * Refreshes CSRF token when user returns to the tab
     */
    function handleVisibilityChange() {
        if (!document.hidden) {
            // User returned to tab - refresh token immediately
            console.debug('[Keep-Alive] Tab became visible, refreshing token');
            pingKeepAlive();
        }
    }

    // Initialize keep-alive system when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startKeepAlive);
    } else {
        startKeepAlive();
    }

    // Refresh token when user returns to tab after being away
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup on page unload (pagehide is bfcache-compatible unlike beforeunload)
    window.addEventListener('pagehide', function() {
        if (keepAliveTimer) {
            clearInterval(keepAliveTimer);
            keepAliveTimer = null;
        }
    });

    // Restart keep-alive when page is restored from bfcache
    window.addEventListener('pageshow', function(e) {
        if (e.persisted && !keepAliveTimer) {
            startKeepAlive();
        }
    });
})();
