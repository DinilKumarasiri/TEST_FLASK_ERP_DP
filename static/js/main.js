// static/js/main.js

// CSRF Token Setup
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            const csrfToken = $('meta[name="csrf-token"]').attr('content');
            if (csrfToken) {
                xhr.setRequestHeader("X-CSRFToken", csrfToken);
            }
        }
    }
});

// Toast Notification Function
function showToast(message, type = 'info') {
    const toast = $(`
        <div class="toast alert alert-${type} position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999;">
            ${message}
            <button type="button" class="btn-close ms-3" onclick="$(this).parent().remove()"></button>
        </div>
    `);
    $('body').append(toast);
    setTimeout(() => toast.remove(), 5000);
}

// Form Validation Helper
function validateForm(formId) {
    const form = $(`#${formId}`);
    let isValid = true;
    
    form.find('[required]').each(function() {
        const $this = $(this);
        if (!$this.val().trim()) {
            $this.addClass('is-invalid');
            isValid = false;
        } else {
            $this.removeClass('is-invalid');
        }
    });
    
    return isValid;
}

// Format Currency
function formatCurrency(amount) {
    return '₹' + parseFloat(amount).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}

// Format Date
function formatDate(date, format = 'YYYY-MM-DD') {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    
    if (format === 'YYYY-MM-DD') {
        return `${year}-${month}-${day}`;
    } else if (format === 'DD/MM/YYYY') {
        return `${day}/${month}/${year}`;
    }
    return date;
}

// Debounce Function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Mobile Menu Toggle
function initMobileMenu() {
    const menuToggle = $('#mobileMenuToggle');
    const navOverlay = $('#mobileNavOverlay');
    const navContainer = $('#mobileNavContainer');
    const navClose = $('#mobileNavClose');
    
    if (menuToggle.length) {
        menuToggle.on('click', function(e) {
            e.stopPropagation();
            $(this).toggleClass('active');
            navOverlay.toggleClass('show');
            navContainer.toggleClass('show');
            $('body').css('overflow', 'hidden');
        });
        
        function closeMenu() {
            menuToggle.removeClass('active');
            navOverlay.removeClass('show');
            navContainer.removeClass('show');
            $('body').css('overflow', 'auto');
        }
        
        navOverlay.on('click', closeMenu);
        navClose.on('click', closeMenu);
        
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape') closeMenu();
        });
    }
}

// Document Ready
$(document).ready(function() {
    // Initialize mobile menu
    initMobileMenu();
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(() => {
        $('.alert:not(.alert-permanent)').fadeOut(300, function() {
            $(this).remove();
        });
    }, 5000);
    
    // Tooltip initialization
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Popover initialization
    $('[data-bs-toggle="popover"]').popover();
    
    // Confirm delete buttons
    $('.confirm-delete').on('click', function(e) {
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
            return false;
        }
    });
});