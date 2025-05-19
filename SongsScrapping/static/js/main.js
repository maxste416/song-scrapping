// Main JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize scrape button functionality
    const scrapeBtn = document.getElementById('scrape-button');
    if (scrapeBtn) {
        scrapeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            initiateScrape();
        });
    }
    
    // Initialize search form
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('search-input');
            if (!searchInput.value.trim()) {
                e.preventDefault();
                showNotification('Please enter a search term', 'warning');
            }
        });
    }
    
    // Format song content to highlight chords
    formatSongContent();
});

/**
 * Format song content to highlight chords
 */
function formatSongContent() {
    const songContent = document.querySelector('.song-content');
    if (!songContent) return;
    
    // Simple chord detection regex
    // This is a basic implementation and might need refinement based on actual content
    const chordRegex = /\b[A-G][#b]?(?:maj|min|m|sus|aug|dim)?[0-9]?(?:\/[A-G][#b]?)?\b/g;
    
    // Get the text content
    let content = songContent.textContent;
    
    // Replace chords with marked spans
    content = content.replace(chordRegex, match => `<span class="chord">${match}</span>`);
    
    // Update the content
    songContent.innerHTML = content;
}

/**
 * Initiate the scraping process
 */
function initiateScrape() {
    const scrapeBtn = document.getElementById('scrape-button');
    const scrapeStatus = document.getElementById('scrape-status');
    
    if (!scrapeBtn || !scrapeStatus) return;
    
    // Update UI to show scraping in progress
    scrapeBtn.disabled = true;
    scrapeBtn.classList.add('running');
    scrapeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scraping...';
    scrapeStatus.innerHTML = 'Scraping in progress. This may take several minutes...';
    scrapeStatus.classList.remove('d-none');
    
    // Get the URL from the input field
    const scrapeUrl = document.getElementById('scrape-url').value.trim();
    
    // Get the follow links option
    const followLinks = document.getElementById('follow-links').checked;
    
    // Validate URL
    if (!scrapeUrl) {
        showNotification('Please enter a valid URL', 'warning');
        scrapeBtn.disabled = false;
        scrapeBtn.classList.remove('running');
        scrapeBtn.innerHTML = 'Scrape Songs';
        return;
    }
    
    // Make API request to start scraping
    fetch('/api/scrape', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: scrapeUrl,
            follow_links: followLinks
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json().catch(err => {
            console.error('JSON parsing error:', err);
            throw new Error('Failed to parse response from server');
        });
    })
    .then(data => {
        // Update UI with scraping results
        if (data.success) {
            scrapeStatus.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            showNotification('Scraping completed successfully!', 'success');
            // Redirect to results page if available, otherwise reload
            if (data.redirect_url) {
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 1500);
            } else {
                // Fallback to reload if redirect URL isn't provided
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            }
        } else {
            // More informative error message
            scrapeStatus.innerHTML = `
                <div class="alert alert-danger">
                    <h5><i class="fas fa-exclamation-triangle me-2"></i> Scraping failed</h5>
                    <p>${data.message}</p>
                    <p class="mb-0 mt-2">Tips:</p>
                    <ul class="mb-0">
                        <li>Make sure the URL is from songsofpraise.in</li>
                        <li>Try using a more specific page URL (e.g. a category page)</li>
                        <li>Check your internet connection</li>
                    </ul>
                </div>`;
            showNotification('Scraping failed', 'danger');
        }
    })
    .catch(error => {
        console.error('Scraping error:', error);
        scrapeStatus.innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle me-2"></i> Scraping failed</h5>
                <p>Error: ${error.message}</p>
                <p class="mb-0 mt-2">Tips:</p>
                <ul class="mb-0">
                    <li>Try using a more specific URL from songsofpraise.in</li>
                    <li>Try scraping a category page instead of the main page</li>
                    <li>Scraping large pages may cause timeouts</li>
                </ul>
            </div>`;
        showNotification('Scraping failed', 'danger');
    })
    .finally(() => {
        // Reset button state
        scrapeBtn.disabled = false;
        scrapeBtn.classList.remove('running');
        scrapeBtn.innerHTML = 'Scrape Songs';
    });
}

/**
 * Show a notification toast
 */
function showNotification(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">Song Scraper</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}
