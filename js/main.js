// Register GSAP plugins
gsap.registerPlugin(ScrollTrigger);

// Reset all animated elements to initial state
gsap.set('#about-me', { opacity: 0, y: 50 });
gsap.set('#about-me .about-title', { opacity: 0, y: 20 });
gsap.set('#about-me .about-content', { opacity: 0, y: 20 });
gsap.set('.hero-name', { y: 0 });
gsap.set('.hero-content', { opacity: 0, y: 0 });
gsap.set('.scroll-hint', { opacity: 0 });
gsap.set('header', { opacity: 0, y: '-100%' });

// Splash screen animation
const splashTimeline = gsap.timeline();

// Fade in splash text
splashTimeline
    .from('#splash h1', {
        duration: 0.8,
        y: 30,
        opacity: 0,
        ease: 'power2.out'
    })
    .from('#splash p', {
        duration: 0.6,
        y: 20,
        opacity: 0,
        ease: 'power2.out'
    }, '-=0.4')
    // Hold for a moment, then fade out splash + deblur background
    .to('#splash', {
        duration: 0.8,
        opacity: 0,
        delay: 1,
        ease: 'power2.inOut',
        onComplete: () => {
            document.getElementById('splash').style.display = 'none';
            document.body.classList.remove('no-scroll');
        }
    })
    .to('.background-image', {
        duration: 1.2,
        filter: 'blur(0px)',
        scale: 1,
        ease: 'power2.out',
        onComplete: () => {
            document.querySelector('.background-image').classList.remove('blurred');
        }
    }, '-=0.6');

// Set initial states for animation
gsap.set('#galleries', { opacity: 0, y: 100 });
gsap.set('#galleries .gallery-card', { opacity: 0, y: 40 });

// Hero animation - timed sequence after splash
splashTimeline.add(() => {
    const heroTimeline = gsap.timeline();

    // 1. Name fades in at center
    heroTimeline.to('.hero-content', {
        duration: 1,
        opacity: 1,
        ease: 'power2.out'
    })
    // 2. Name moves up + header slides in
    .to('.hero-content', {
        duration: 1.2,
        y: -80,
        ease: 'power2.inOut',
        delay: 0.5
    })
    .to('header', {
        duration: 0.8,
        opacity: 1,
        y: 0,
        ease: 'power2.out'
    }, '-=0.8')
    // 3. "View Work" fades in
    .to('.scroll-hint', {
        duration: 0.8,
        opacity: 1,
        ease: 'power2.out'
    }, '-=0.4')
    // 4. Shelf slides up
    .to('#galleries', {
        duration: 1,
        opacity: 1,
        y: 0,
        ease: 'power2.out'
    }, '-=0.4')
    // 5. Gallery cards fade in
    .to('#galleries .gallery-card', {
        duration: 0.8,
        opacity: 1,
        y: 0,
        stagger: 0.1,
        ease: 'power2.out',
        clearProps: 'transform'
    }, '-=0.6');
});

// Hero-fade elements fade out as shelf covers them, fade back in when scrolling up
gsap.to('.hero-fade', {
    scrollTrigger: {
        trigger: '#galleries',
        start: 'top 75%',
        end: 'top 55%',
        scrub: true
    },
    opacity: 0,
    ease: 'none'
});

// Sticky name behavior - moves up as shelf approaches, stops above letters
gsap.to('.hero-name', {
    scrollTrigger: {
        trigger: '#galleries',
        start: 'top 75%',
        end: 'top 55%',
        scrub: 0.5
    },
    y: -120,
    ease: 'none'
});

// Name fades out when shelf covers it, fades back in when scrolling up
gsap.to('.hero-name', {
    scrollTrigger: {
        trigger: '#galleries',
        start: 'top 45%',
        end: 'top 30%',
        scrub: true
    },
    opacity: 0,
    ease: 'none'
});

// About Me section scroll animation
ScrollTrigger.create({
    trigger: '#about-me',
    start: 'top 85%',
    onEnter: () => {
        const aboutTimeline = gsap.timeline();

        // Section fades in
        aboutTimeline.to('#about-me', {
            duration: 0.8,
            opacity: 1,
            y: 0,
            ease: 'power2.out'
        })
        // Title animates in
        .to('#about-me .about-title', {
            duration: 0.6,
            opacity: 1,
            y: 0,
            ease: 'power2.out'
        }, '-=0.4')
        // Content animates in
        .to('#about-me .about-content', {
            duration: 0.6,
            opacity: 1,
            y: 0,
            ease: 'power2.out'
        }, '-=0.3');
    },
    once: true
});

// Function to scroll galleries into view (showing first row + peek of second row)
function scrollToGalleriesCenter() {
    const target = document.getElementById('galleries');
    const header = document.querySelector('header');
    const headerHeight = header.offsetHeight;
    const targetTop = target.getBoundingClientRect().top + window.scrollY;

    // Scroll so shelf top is just below header (small gap)
    const scrollTo = targetTop - headerHeight - 20;

    window.scrollTo({ top: Math.max(0, scrollTo), behavior: 'smooth' });
}

// Smooth scroll for nav links
document.querySelectorAll('nav a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(link.getAttribute('href'));
        if (target) {
            // For galleries, center it on screen
            if (link.getAttribute('href') === '#galleries') {
                scrollToGalleriesCenter();
            } else {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
});

// "View Work" button scrolls to galleries
const scrollHint = document.querySelector('.scroll-hint');
scrollHint.addEventListener('click', scrollToGalleriesCenter);

// 3D tilt effect for "View Work" button
(function() {
    let isHovering = false;
    let currentX = 0;
    let currentY = 0;
    let targetX = 0;
    let targetY = 0;

    function animate() {
        if (!isHovering) {
            currentX += (0 - currentX) * 0.1;
            currentY += (0 - currentY) * 0.1;
        } else {
            currentX += (targetX - currentX) * 0.15;
            currentY += (targetY - currentY) * 0.15;
        }

        const scale = isHovering ? 1.05 : 1;
        scrollHint.style.transform = `perspective(800px) rotateX(${currentY}deg) rotateY(${currentX}deg) scale(${scale})`;

        if (Math.abs(currentX) > 0.01 || Math.abs(currentY) > 0.01 || isHovering) {
            requestAnimationFrame(animate);
        } else {
            scrollHint.style.transform = '';
        }
    }

    scrollHint.addEventListener('mouseenter', () => {
        isHovering = true;
        requestAnimationFrame(animate);
    });

    scrollHint.addEventListener('mousemove', (e) => {
        const rect = scrollHint.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        targetX = (x - centerX) / 20;
        targetY = (centerY - y) / 20;
    });

    scrollHint.addEventListener('mouseleave', () => {
        isHovering = false;
    });
})();


// ===================
// GALLERY SYSTEM
// ===================

// Cloudinary configuration
const CLOUDINARY_BASE = 'https://res.cloudinary.com/deihjpq8s/image/upload';

// Image URLs - just the base paths (without transforms)
const galleryImages = {
    sorrento: [
        'v1768430959/sorrento_01.jpg',
        'v1768430959/sorrento_02.jpg',
        'v1768430959/sorrento_03.jpg',
        'v1768430959/sorrento_04.jpg',
        'v1768430959/sorrento_05.jpg',
        'v1768430959/sorrento_06.jpg',
        'v1768430959/sorrento_07.jpg',
        'v1768430959/sorrento_08.jpg',
        'v1768430959/sorrento_09.jpg',
        'v1768430959/sorrento_10.jpg',
        'v1768430959/sorrento_11.jpg',
        'v1768430959/sorrento_12.jpg',
        'v1768430959/sorrento_13.jpg',
        'v1768430959/sorrento_14.jpg',
        'v1768430959/sorrento_15.jpg',
        'v1768430959/sorrento_16.jpg',
        'v1768430959/sorrento_17.jpg',
        'v1768430959/sorrento_18.jpg',
        'v1768430959/sorrento_19.jpg',
        'v1768430959/sorrento_20.jpg',
        'v1768430959/sorrento_21.jpg',
    ],
    venice: [
        'v1768430959/venice_01.jpg',
        'v1768430959/venice_02.jpg',
        'v1768430959/venice_03.jpg',
        'v1768430959/venice_04.jpg',
        'v1768430959/venice_05.jpg',
        'v1768430959/venice_06.jpg',
        'v1768430959/venice_07.jpg',
        'v1768430959/venice_08.jpg',
        'v1768430959/venice_09.jpg',
        'v1768430959/venice_10.jpg',
        'v1768430959/venice_11.jpg',
        'v1768430959/venice_12.jpg',
        'v1768430959/venice_13.jpg',
        'v1768430959/venice_15.jpg',
        'v1768430959/venice_16.jpg',
        'v1768430959/venice_17.jpg',
        'v1768430959/venice_19.jpg',
        'v1768430959/venice_20.jpg',
        'v1768430959/venice_21.jpg',
        'v1768430959/venice_22.jpg',
        'v1768430959/venice_24.jpg',
        'v1768430959/venice_25.jpg',
        'v1768430959/venice_26.jpg',
        'v1768430959/venice_27.jpg',
        'v1768430959/venice_28.jpg',
    ],
    bermuda: [
        'v1768435273/bermuda_01.jpg',
        'v1768435273/bermuda_02.jpg',
        'v1768435273/bermuda_03.jpg',
        'v1768435273/bermuda_04.jpg',
        'v1768435273/bermuda_05.jpg',
        'v1768435273/bermuda_06.jpg',
        'v1768435273/bermuda_07.jpg',
        'v1768435273/bermuda_08.jpg',
        'v1768435273/bermuda_09.jpg',
        'v1768435273/bermuda_10.jpg',
        'v1768435273/bermuda_11.jpg',
        'v1768435273/bermuda_12.jpg',
        'v1768435273/bermuda_13.jpg',
        'v1768435273/bermuda_14.jpg',
        'v1768435273/bermuda_15.jpg',
        'v1768435273/bermuda_16.jpg',
        'v1768435273/bermuda_17.jpg',
        'v1768435273/bermuda_18.jpg',
        'v1768435273/bermuda_19.jpg',
        'v1768435273/bermuda_20.jpg',
        'v1768435273/bermuda_21.jpg',
        'v1768435273/bermuda_22.jpg',
        'v1768435273/bermuda_23.jpg',
        'v1768435273/bermuda_24.jpg',
        'v1768435273/bermuda_25.jpg',
    ],
    nj: [
        'v1768435273/nj_01.jpg',
        'v1768435273/nj_02.jpg',
        'v1768435273/nj_03.jpg',
        'v1768435273/nj_04.jpg',
        'v1768435273/nj_05.jpg',
        'v1768435273/nj_06.jpg',
        'v1768435273/nj_07.jpg',
        'v1768435273/nj_08.jpg',
        'v1768435273/nj_09.jpg',
        'v1768435273/nj_10.jpg',
        'v1768435273/nj_11.jpg',
        'v1768435273/nj_12.jpg',
        'v1768435273/nj_13.jpg',
        'v1768435273/nj_14.jpg',
        'v1768435273/nj_15.jpg',
        'v1768435273/nj_16.jpg',
        'v1768435273/nj_17.jpg',
    ],
    nyc: [
        'v1768435712/nyc_01.jpg',
        'v1768435712/nyc_02.jpg',
        'v1768435712/nyc_03.jpg',
        'v1768435712/nyc_04.jpg',
        'v1768435712/nyc_05.jpg',
        'v1768435712/nyc_06.jpg',
    ],
    rome: [
        'v1768435712/rome_01.jpg',
        'v1768435712/rome_02.jpg',
        'v1768435712/rome_03.jpg',
        'v1768435712/rome_04.jpg',
        'v1768435712/rome_05.jpg',
        'v1768435712/rome_06.jpg',
        'v1768435712/rome_07.jpg',
        'v1768435712/rome_08.jpg',
        'v1768435712/rome_09.jpg',
        'v1768435712/rome_10.jpg',
    ],
};

// Gallery display names
const galleryTitles = {
    sorrento: 'Sorrento',
    venice: 'Venice',
    bermuda: 'Bermuda',
    nj: 'New Jersey',
    nyc: 'New York City',
    rome: 'Rome',
};

// Build optimized URLs (capped at 1600px to protect full resolution)
function thumbUrl(path) {
    return `${CLOUDINARY_BASE}/f_auto,q_auto,w_800/${path}`;
}
function fullUrl(path) {
    return `${CLOUDINARY_BASE}/f_auto,q_auto,w_1600/${path}`;
}

// State
let currentGalleryImages = [];
let currentIndex = 0;

// DOM elements
const galleryView = document.getElementById('gallery-view');
const galleryViewTitle = galleryView.querySelector('.gallery-view-title');
const galleryViewGrid = galleryView.querySelector('.gallery-view-grid');
const lightbox = document.getElementById('lightbox');
const lightboxImg = lightbox.querySelector('.lightbox-content img');
const lightboxCounter = lightbox.querySelector('.lightbox-counter');

// Open gallery view (grid of thumbnails)
function openGalleryView(galleryName) {
    const images = galleryImages[galleryName];
    if (!images || images.length === 0) return;

    currentGalleryImages = images;
    galleryViewTitle.textContent = galleryTitles[galleryName] || galleryName;

    // Build grid
    galleryViewGrid.innerHTML = '';
    images.forEach((path, index) => {
        const img = document.createElement('img');
        img.dataset.index = index;
        img.alt = `${galleryName} photo ${index + 1}`;
        img.loading = 'lazy';

        // Fade in when loaded
        img.onload = () => img.classList.add('loaded');
        img.src = thumbUrl(path);

        img.addEventListener('click', () => openLightbox(index));
        galleryViewGrid.appendChild(img);
    });

    galleryView.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close gallery view
function closeGalleryView() {
    galleryView.classList.remove('active');
    document.body.style.overflow = '';
}

// Open lightbox (fullscreen single image)
function openLightbox(index) {
    currentIndex = index;
    updateLightboxImage();
    lightbox.classList.add('active');
}

// Close lightbox
function closeLightbox() {
    lightbox.classList.remove('active');
}

// Update lightbox image
function updateLightboxImage() {
    lightboxImg.src = fullUrl(currentGalleryImages[currentIndex]);
    lightboxCounter.textContent = `${currentIndex + 1} / ${currentGalleryImages.length}`;
}

// Navigate
function nextImage() {
    currentIndex = (currentIndex + 1) % currentGalleryImages.length;
    updateLightboxImage();
}

function prevImage() {
    currentIndex = (currentIndex - 1 + currentGalleryImages.length) % currentGalleryImages.length;
    updateLightboxImage();
}

// Event listeners - Gallery cards open gallery view
document.querySelectorAll('.gallery-card').forEach(card => {
    card.addEventListener('click', () => {
        openGalleryView(card.dataset.gallery);
    });
});

// Gallery view close
galleryView.querySelector('.gallery-view-close').addEventListener('click', closeGalleryView);

// Lightbox controls
lightbox.querySelector('.lightbox-close').addEventListener('click', closeLightbox);
lightbox.querySelector('.lightbox-prev').addEventListener('click', prevImage);
lightbox.querySelector('.lightbox-next').addEventListener('click', nextImage);

// Close lightbox on background click (back to grid)
lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) closeLightbox();
});

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    if (lightbox.classList.contains('active')) {
        if (e.key === 'Escape') closeLightbox();
        if (e.key === 'ArrowRight') nextImage();
        if (e.key === 'ArrowLeft') prevImage();
    } else if (galleryView.classList.contains('active')) {
        if (e.key === 'Escape') closeGalleryView();
    }
});

// Protect images from easy downloading
document.addEventListener('contextmenu', (e) => {
    if (e.target.tagName === 'IMG') {
        e.preventDefault();
    }
});

document.addEventListener('dragstart', (e) => {
    if (e.target.tagName === 'IMG') {
        e.preventDefault();
    }
});

// 3D tilt effect for gallery cards (iPadOS style)
document.querySelectorAll('.gallery-card').forEach(card => {
    let isHovering = false;
    let currentX = 0;
    let currentY = 0;
    let targetX = 0;
    let targetY = 0;

    function animate() {
        if (!isHovering) {
            // Ease back to center
            currentX += (0 - currentX) * 0.1;
            currentY += (0 - currentY) * 0.1;
        } else {
            // Ease toward target
            currentX += (targetX - currentX) * 0.15;
            currentY += (targetY - currentY) * 0.15;
        }

        const scale = isHovering ? 1.03 : 1;
        card.style.transform = `perspective(1000px) rotateX(${currentY}deg) rotateY(${currentX}deg) scale(${scale})`;

        // Keep animating if there's still movement
        if (Math.abs(currentX) > 0.01 || Math.abs(currentY) > 0.01 || isHovering) {
            requestAnimationFrame(animate);
        } else {
            card.style.transform = '';
        }
    }

    card.addEventListener('mouseenter', () => {
        isHovering = true;
        requestAnimationFrame(animate);
    });

    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        // More subtle: divide by larger numbers
        targetX = (x - centerX) / 25;
        targetY = (centerY - y) / 25;
    });

    card.addEventListener('mouseleave', () => {
        isHovering = false;
    });
});

// 3D tilt effect for nav buttons (same as gallery cards)
document.querySelectorAll('nav a').forEach(btn => {
    let isHovering = false;
    let currentX = 0;
    let currentY = 0;
    let targetX = 0;
    let targetY = 0;

    function animate() {
        if (!isHovering) {
            currentX += (0 - currentX) * 0.1;
            currentY += (0 - currentY) * 0.1;
        } else {
            currentX += (targetX - currentX) * 0.15;
            currentY += (targetY - currentY) * 0.15;
        }

        const scale = isHovering ? 1.05 : 1;
        btn.style.transform = `perspective(800px) rotateX(${currentY}deg) rotateY(${currentX}deg) scale(${scale})`;

        if (Math.abs(currentX) > 0.01 || Math.abs(currentY) > 0.01 || isHovering) {
            requestAnimationFrame(animate);
        } else {
            btn.style.transform = '';
        }
    }

    btn.addEventListener('mouseenter', () => {
        isHovering = true;
        requestAnimationFrame(animate);
    });

    btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        targetX = (x - centerX) / 15;
        targetY = (centerY - y) / 15;
    });

    btn.addEventListener('mouseleave', () => {
        isHovering = false;
    });
});

// ===================
// MOBILE BURGER MENU
// ===================
const burgerMenu = document.querySelector('.burger-menu');
const navLinks = document.querySelector('.nav-links');

burgerMenu.addEventListener('click', () => {
    burgerMenu.classList.toggle('active');
    navLinks.classList.toggle('active');
});

// Close menu when a nav link is clicked
navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        burgerMenu.classList.remove('active');
        navLinks.classList.remove('active');
    });
});

// ===================
// FORM SUBMISSION (AJAX)
// ===================
const contactForm = document.getElementById('contact-form');
if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const form = e.target;
        const submitBtn = form.querySelector('.submit-btn');
        const originalText = submitBtn.textContent;
        
        // Show loading state
        submitBtn.textContent = 'Sending...';
        submitBtn.disabled = true;
        
        try {
            const formData = new FormData(form);
            await fetch('/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams(formData).toString()
            });
            
            // Animate out form fields, show success
            gsap.to(form.querySelectorAll('.form-group, .submit-btn'), {
                opacity: 0,
                y: -20,
                duration: 0.3,
                stagger: 0.05,
                onComplete: () => {
                    form.innerHTML = '<div class="form-success"><h3>Message Sent!</h3><p>Thanks for reaching out. I\'ll get back to you soon.</p></div>';
                    gsap.from('.form-success', {
                        opacity: 0,
                        y: 20,
                        duration: 0.5,
                        ease: 'power2.out'
                    });
                }
            });
        } catch (error) {
            submitBtn.textContent = 'Error - Try Again';
            submitBtn.disabled = false;
            setTimeout(() => {
                submitBtn.textContent = originalText;
            }, 2000);
        }
    });
}
