// Register GSAP plugins
gsap.registerPlugin(ScrollTrigger);

// Hero animation on page load
gsap.from('#hero h1', {
    duration: 1,
    y: 50,
    opacity: 0,
    ease: 'power3.out'
});

gsap.from('.tagline', {
    duration: 1,
    y: 30,
    opacity: 0,
    ease: 'power3.out',
    delay: 0.3
});

// Animate sections on scroll
gsap.utils.toArray('section:not(#hero)').forEach(section => {
    gsap.from(section.children, {
        scrollTrigger: {
            trigger: section,
            start: 'top 80%',
            toggleActions: 'play none none reverse'
        },
        duration: 0.8,
        y: 50,
        opacity: 0,
        stagger: 0.2,
        ease: 'power2.out'
    });
});

// Smooth nav link highlighting
document.querySelectorAll('nav a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(link.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});
