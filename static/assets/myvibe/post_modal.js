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