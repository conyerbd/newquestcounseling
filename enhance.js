// Scroll-reveal enhancement. Progressive: without JS (or with reduced motion)
// everything is visible, because the hiding styles only apply under .nq-reveal.
(function () {
    if (!('IntersectionObserver' in window)) return;

    document.documentElement.classList.add('nq-reveal');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('in-view');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.05, rootMargin: '0px 0px -5% 0px' });

    document.querySelectorAll('section').forEach((section) => {
        // Sections already on screen at load appear instantly
        const rect = section.getBoundingClientRect();
        if (rect.top < window.innerHeight * 0.9) {
            section.classList.add('in-view');
        } else {
            observer.observe(section);
        }
    });
})();
