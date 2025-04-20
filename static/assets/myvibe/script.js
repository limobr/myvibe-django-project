// Theme switching with localStorage persistence
document.addEventListener('DOMContentLoaded', () => {
    const themeSwitcher = document.querySelector('.theme-switcher');
    if (!themeSwitcher) return;

    const themeIcon = themeSwitcher.querySelector('i');
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    document.body.setAttribute('data-theme', currentTheme);
    themeIcon.className = currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';

    themeSwitcher.addEventListener('click', () => {
        const isDark = document.body.getAttribute('data-theme') === 'dark';
        const newTheme = isDark ? 'light' : 'dark';
        
        document.body.setAttribute('data-theme', newTheme);
        themeIcon.className = isDark ? 'fas fa-moon' : 'fas fa-sun';
        localStorage.setItem('theme', newTheme);
    });

    // Mobile menu active state using event delegation
    document.querySelector('.mobile-nav')?.addEventListener('click', (e) => {
        const icon = e.target.closest('i');
        if (!icon) return;
        
        document.querySelectorAll('.mobile-nav i').forEach(i => 
            i.classList.remove('active')
        );
        icon.classList.add('active');
    });

    // Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const container = document.querySelector('.container');
    const sidebar = document.querySelector('.sidebar');
    const mobileSearchIcon = document.querySelector('.mobile-search-icon');
    const searchBar = document.querySelector('.search-bar');

    sidebarToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        if (window.innerWidth > 1024) {
            container.classList.toggle('large-sidebar-collapsed');
        } else if (window.innerWidth > 768) {
            container.classList.toggle('semi-sidebar-expanded');
        } else {
            sidebar.classList.toggle('sidebar-active');
        }
    });

    // Mobile Search Toggle
    mobileSearchIcon.addEventListener('click', (e) => {
        e.stopPropagation();
        searchBar.classList.toggle('active');
    });

    // Close sidebar and search bar on outside click
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
            sidebar.classList.remove('sidebar-active');
        }
        if (!searchBar.contains(e.target) && e.target !== mobileSearchIcon) {
            searchBar.classList.remove('active');
        }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 1024) {
            container.classList.remove('semi-sidebar-expanded');
            sidebar.classList.remove('sidebar-active');
        } else if (window.innerWidth > 768) {
            container.classList.remove('large-sidebar-collapsed');
            sidebar.classList.remove('sidebar-active');
        } else {
            container.classList.remove('large-sidebar-collapsed', 'semi-sidebar-expanded');
        }
    });
});

// Profile Tab Navigation with error handling
document.querySelector('.profile-nav')?.addEventListener('click', (e) => {
    const button = e.target.closest('.nav-button');
    if (!button || button.classList.contains('active')) return;

    const targetId = button.dataset.target;
    if (!targetId) return;

    document.querySelectorAll('.nav-button, .profile-section').forEach(el => 
        el.classList.remove('active')
    );

    button.classList.add('active');
    document.getElementById(targetId)?.classList.add('active');
});

// Post Modal Handling with cleanup
let modalOpen = false;

function openPostModal(postId) {
    if (modalOpen) return;
    modalOpen = true;

    const modal = document.getElementById('postModal');
    const modalContent = document.getElementById('modalContent');
    
    modal.style.display = 'block';
    modal.classList.add('active');
    modalContent.innerHTML = '<div class="loader"></div>';

    fetch(`/post/${postId}/details/`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.text();
        })
        .then(html => {
            modalContent.innerHTML = html;
            initializeModalControls(postId);
        })
        .catch(error => {
            console.error('Post modal error:', error);
            modalContent.innerHTML = `
                <div class="error-message">
                    Failed to load post. Please try again later.
                </div>
            `;
        })
        .finally(() => modalOpen = false);
}

function initializeModalControls(postId) {
    const closeModal = () => {
        const modal = document.getElementById('postModal');
        modal.classList.remove('active');
        modal.style.display = 'none';
        window.removeEventListener('click', outsideClickHandler);
    };

    const outsideClickHandler = (e) => {
        if (e.target === document.getElementById('postModal')) closeModal();
    };

    document.querySelector('.close-modal')?.addEventListener('click', closeModal);
    window.addEventListener('click', outsideClickHandler);

    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.onsubmit = async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const commentInput = commentForm.querySelector('input[type="text"]');
            const commentText = commentInput.value.trim();

            if (!commentText) {
                commentInput.focus();
                return;
            }

            try {
                const response = await fetch('/add-comment/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        post_id: postId,
                        text: commentText
                    })
                });

                if (!response.ok) throw new Error('Comment submission failed');

                const data = await response.json();
                if (data.success) {
                    const commentsSection = document.getElementById('commentsSection');
                    commentsSection.appendChild(createCommentElement(data.comment));
                    commentInput.value = '';
                } else {
                    throw new Error(data.error || 'Unknown error');
                }
            } catch (error) {
                console.error('Comment error:', error);
                alert('Failed to post comment. Please try again.');
            }
        };
    }
}

// Media Dialog with accessibility improvements
function openMediaDialog(url, type) {
    const dialog = document.getElementById('mediaDialog');
    const content = dialog.querySelector('.media-dialog-content');
    
    content.innerHTML = type === 'image' 
        ? `<img src="${url}" alt="Full screen content" tabindex="0">` 
        : `<video src="${url}" controls tabindex="0"></video>`;
    
    dialog.showModal();
    dialog.querySelector('video')?.focus();
}

function closeMediaDialog() {
    document.getElementById('mediaDialog')?.close();
}

// Generic comment handler using event delegation
var csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '{{ csrf_token }}';
document.addEventListener('submit', async (e) => {
    const form = e.target.closest('.comment-form');
    if (!form) return;
    e.preventDefault();

    const input = form.querySelector('.comment-input');
    const loader = form.querySelector('.comment-loader');
    const postId = form.dataset.postId;
    const commentText = input.value.trim();

    if (!commentText) {
        input.focus();
        return;
    }

    try {
        loader.style.display = 'block';

        const response = await fetch('/add-comment/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                post_id: postId,
                text: commentText
            })
        });

        if (!response.ok) throw new Error('Network response was not ok');

        const data = await response.json();
        if (data.success) {
            const comment = createCommentElement(data.comment);
            form.closest('.comments-section')
                ?.querySelector('.comments-list')
                ?.appendChild(comment);
            input.value = '';
        } else {
            throw new Error(data.error || 'Unknown error');
        }
    } catch (error) {
        console.error('Comment submission error:', error);
        alert('Failed to post comment. Please try again.');
    } finally {
        loader.style.display = 'none';
    }
});

// Helper function to create comment element
function createCommentElement(comment) {
    const div = document.createElement('div');
    div.className = 'comment card';
    div.innerHTML = `
        <div class="comment-header">
            <strong>${comment.user}</strong>
            <time datetime="${comment.created_at}">
                ${new Date(comment.created_at).toLocaleString()}
            </time>
        </div>
        <p class="comment-text">${comment.text}</p>
    `;
    return div;
}


// 00000000000000000000000000000 create event scripts 000000000000000000 

$(document).ready(function () {
    // Step navigation setup
    var navListItems = $('div.setup-panel div a'),
        allWells = $('.setup-content'),
        allNextBtn = $('.nextBtn');

    allWells.hide();

    navListItems.click(function (e) {
        e.preventDefault();
        var $target = $($(this).attr('href')),
            $item = $(this);

        if (!$item.hasClass('disabled')) {
            navListItems.removeClass('btn-success').addClass('btn-default');
            $item.addClass('btn-success');
            allWells.hide();
            $target.show();
            $target.find('input:eq(0)').focus();
        }
    });

    allNextBtn.click(function () {
        var curStep = $(this).closest(".setup-content"),
            curStepBtn = curStep.attr("id"),
            nextStepWizard = $('div.setup-panel div a[href="#' + curStepBtn + '"]').parent().next().children("a"),
            curInputs = curStep.find("input[type='text'], input[type='url'], input[type='number'], input[type='datetime-local'], textarea, select"),
            isValid = true;

        $(".form-group").removeClass("has-error");
        for (var i = 0; i < curInputs.length; i++) {
            if (!curInputs[i].validity.valid) {
                isValid = false;
                $(curInputs[i]).closest(".form-group").addClass("has-error");
            }
        }

        if (isValid) nextStepWizard.removeAttr('disabled').trigger('click');
    });

    $('div.setup-panel div a.btn-success').trigger('click');

    // Leaflet Map for Step 3
    var map, marker;

    // Initialize map when Step 3 is shown
    $('div.setup-panel div a[href="#step-3"]').on('click', function () {
        if (!map) {
            // Center on Kenya (approx coordinates: -1.286389, 36.817223)
            map = L.map('map').setView([-1.286389, 36.817223], 6); // Zoom level 6 shows Kenya well

            // Add OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            // Add a draggable marker
            marker = L.marker([-1.286389, 36.817223], { draggable: true }).addTo(map);

            // Update form fields on marker drag
            marker.on('dragend', function (e) {
                var coords = e.target.getLatLng();
                $('input[name="latitude"]').val(coords.lat.toFixed(6));
                $('input[name="longitude"]').val(coords.lng.toFixed(6));
            });

            // Update form fields on map click
            map.on('click', function (e) {
                var coords = e.latlng;
                marker.setLatLng(coords);
                $('input[name="latitude"]').val(coords.lat.toFixed(6));
                $('input[name="longitude"]').val(coords.lng.toFixed(6));
            });

            // Set initial form values
            var initialCoords = marker.getLatLng();
            $('input[name="latitude"]').val(initialCoords.lat.toFixed(6));
            $('input[name="longitude"]').val(initialCoords.lng.toFixed(6));
        }
    });

    // Search bar functionality (now static in HTML)
    var searchInput = $('#location-search');
    var suggestionsDropdown = $('#suggestions');

    // Trigger search on input
    searchInput.on('input', function () {
        var query = $(this).val();
        if (query.length < 3) {
            suggestionsDropdown.hide();
            return;
        }

        $.ajax({
            url: 'https://nominatim.openstreetmap.org/search',
            data: {
                q: query + ', Kenya', // Restrict search to Kenya
                format: 'json',
                limit: 5,
                countrycodes: 'ke' // ISO code for Kenya
            },
            success: function (data) {
                suggestionsDropdown.empty();
                if (data.length > 0) {
                    data.forEach(function (place) {
                        var suggestion = $('<a class="dropdown-item" href="#">' + place.display_name + '</a>');
                        suggestion.on('click', function (e) {
                            e.preventDefault();
                            var lat = parseFloat(place.lat);
                            var lon = parseFloat(place.lon);
                            map.setView([lat, lon], 15); // Zoom in to selected location
                            marker.setLatLng([lat, lon]);
                            $('input[name="latitude"]').val(lat.toFixed(6));
                            $('input[name="longitude"]').val(lon.toFixed(6));
                            suggestionsDropdown.hide();
                            searchInput.val(place.display_name);
                        });
                        suggestionsDropdown.append(suggestion);
                    });
                    suggestionsDropdown.show();
                } else {
                    suggestionsDropdown.hide();
                }
            },
            error: function () {
                suggestionsDropdown.hide();
            }
        });
    });

    // Hide suggestions when clicking outside
    $(document).on('click', function (e) {
        if (!searchInput.is(e.target) && !suggestionsDropdown.is(e.target) && suggestionsDropdown.has(e.target).length === 0) {
            suggestionsDropdown.hide();
        }
    });
});