document.addEventListener('DOMContentLoaded', () => {
    // Theme switching with localStorage persistence
    const themeSwitcher = document.querySelector('.theme-switcher');
    if (themeSwitcher) {
        const themeIcon = themeSwitcher.querySelector('i');
        const currentTheme = localStorage.getItem('theme') || 'light';
        
        document.body.setAttribute('data-theme', currentTheme);
        if (themeIcon) {
            themeIcon.className = currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        } else {
            console.warn('Theme icon not found inside theme-switcher');
        }

        themeSwitcher.addEventListener('click', () => {
            const isDark = document.body.getAttribute('data-theme') === 'dark';
            const newTheme = isDark ? 'light' : 'dark';
            
            document.body.setAttribute('data-theme', newTheme);
            if (themeIcon) {
                themeIcon.className = isDark ? 'fas fa-moon' : 'fas fa-sun';
            }
            localStorage.setItem('theme', newTheme);
        });
    } else {
        console.warn('Theme switcher element not found');
    }

    // Mobile menu active state using event delegation
    const mobileNav = document.querySelector('.mobile-nav');
    if (mobileNav) {
        mobileNav.addEventListener('click', (e) => {
            const icon = e.target.closest('i');
            if (!icon) return;
            
            document.querySelectorAll('.mobile-nav i').forEach(i => 
                i.classList.remove('active')
            );
            icon.classList.add('active');
        });
    } else {
        console.warn('Mobile nav element not found');
    }

    // Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const container = document.querySelector('.container');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const mobileSearchIcon = document.querySelector('.mobile-search-icon');
    const searchBar = document.querySelector('.search-bar');

    // Debugging: Log to confirm elements are selected
    console.log('Sidebar Toggle:', sidebarToggle);
    console.log('Container:', container);
    console.log('Sidebar:', sidebar);
    console.log('Main Content:', mainContent);
    console.log('Mobile Search Icon:', mobileSearchIcon);
    console.log('Search Bar:', searchBar);

    if (sidebarToggle && container && sidebar && mainContent) {
        sidebarToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Toggle clicked, window.innerWidth:', window.innerWidth); // Debugging
            if (window.innerWidth > 1024) {
                // Large screens: Toggle between full and icon-only sidebar
                console.log('Applying sidebar-collapsed for large screens');
                container.classList.toggle('sidebar-collapsed');
                sidebar.classList.toggle('sidebar-collapsed');
            } else if (window.innerWidth > 768) {
                // Medium screens: Toggle between icon-only and expanded sidebar
                console.log('Applying sidebar-expanded for medium screens');
                container.classList.toggle('sidebar-expanded');
                sidebar.classList.toggle('sidebar-expanded');
            } else {
                // Small screens: Slide in/out sidebar and push main content
                console.log('Applying sidebar-active for small screens');
                sidebar.classList.toggle('sidebar-active');
                mainContent.classList.toggle('sidebar-active');
            }
        });
    } else {
        console.error('One or more required elements for sidebar toggle not found:', {
            sidebarToggle, container, sidebar, mainContent
        });
    }

    // Mobile Search Toggle
    if (mobileSearchIcon && searchBar) {
        mobileSearchIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            searchBar.classList.toggle('active');
        });
    } else {
        console.warn('Mobile search icon or search bar not found:', { mobileSearchIcon, searchBar });
    }

    // Close sidebar and search bar on outside click
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768) {
            if (sidebar && !sidebar.contains(e.target) && e.target !== sidebarToggle && !e.target.closest('#sidebarToggle')) {
                sidebar.classList.remove('sidebar-active');
                mainContent.classList.remove('sidebar-active');
            }
            if (searchBar && !searchBar.contains(e.target) && e.target !== mobileSearchIcon && !e.target.closest('.mobile-search-icon')) {
                searchBar.classList.remove('active');
            }
        }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        if (!container || !sidebar || !mainContent || !searchBar) return;
        
        if (window.innerWidth > 1024) {
            // Large screens: Reset to default state
            container.classList.remove('sidebar-expanded');
            sidebar.classList.remove('sidebar-active', 'sidebar-expanded');
            mainContent.classList.remove('sidebar-active');
        } else if (window.innerWidth > 768) {
            // Medium screens: Start collapsed, allow expansion
            container.classList.remove('sidebar-collapsed');
            sidebar.classList.remove('sidebar-active', 'sidebar-collapsed');
            mainContent.classList.remove('sidebar-active');
            container.classList.add('sidebar-expanded');
            sidebar.classList.remove('sidebar-expanded');
        } else {
            // Small screens: Reset to hidden sidebar
            container.classList.remove('sidebar-collapsed', 'sidebar-expanded');
            sidebar.classList.remove('sidebar-collapsed', 'sidebar-expanded');
            mainContent.classList.remove('sidebar-active');
        }
        searchBar.classList.remove('active');
    });

    // Highlight active sidebar menu item
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.menu-item');
    if (menuItems) {
        menuItems.forEach(item => {
            const link = item.querySelector('a');
            if (link && link.getAttribute('href') === currentPath) {
                item.classList.add('active');
            }
        });
    } else {
        console.warn('Menu items not found');
    }

    // Message handling
    const messages = document.querySelectorAll('.message');
    if (messages) {
        messages.forEach(message => {
            setTimeout(() => {
                message.classList.remove('animate-in');
                setTimeout(() => message.remove(), 300);
            }, 5000);

            const closeButton = message.querySelector('.close-message');
            if (closeButton) {
                closeButton.addEventListener('click', () => {
                    message.classList.remove('animate-in');
                    setTimeout(() => message.remove(), 300);
                });
            }

            const progressBar = message.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.addEventListener('click', () => {
                    message.classList.remove('animate-in');
                    setTimeout(() => message.remove(), 300);
                });
            }
        });
    } else {
        console.log('No messages found');
    }
});

// Profile section navigation with tabs (for myprofile.html)
const profileNav = document.querySelector('.profile-nav');
if (profileNav) {
    const tabs = document.querySelectorAll('.nav-tab');
    const sections = document.querySelectorAll('.profile-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and sections
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            // Add active class to clicked tab and corresponding section
            tab.classList.add('active');
            const targetId = tab.getAttribute('data-target');
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });
}