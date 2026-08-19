// Meta Pixel event tracking, shared by every page.
//
// The contact form is a cross-origin SimplePractice iframe, so the page cannot
// see submissions. That means there is no true "form submitted" signal to send.
// Instead we treat the strongest measurable contact actions as the conversion:
//
//   Lead        -> phone click, email click, contact form opened
//                  (segmented by content_name so you can still tell them apart)
//   CTAClick    -> custom; any "Schedule Consult" / "Get Started" / "Learn More"
//                  click. Intent only, kept OFF the standard events so it can't
//                  inflate the conversion count.
//   PortalLogin -> custom; existing clients heading to the client portal.
//   ViewContent -> scroll depth through the Services and FAQ sections.
//
// Plus shallow engagement signals, all custom so they stay out of the
// conversion count:
//
//   Scroll25/50/75          -> how far down the page people actually get
//   Engaged15s / Engaged45s -> visible time on page, tab-blur aware
//
// These exist because ViewContent only fires once the Services section is on
// screen, which is over two phone screens down. Without a shallower signal an
// instant bounce and someone who read the whole hero look identical.
//
// Deliberately NOT used: Schedule. In Meta's taxonomy that means an appointment
// was actually booked, which nothing on this site can confirm.

(function () {
    'use strict';

    function track(event, params) {
        if (typeof window.fbq !== 'function') return;
        window.fbq('track', event, params || {});
    }

    function trackCustom(event, params) {
        if (typeof window.fbq !== 'function') return;
        window.fbq('trackCustom', event, params || {});
    }

    // Let the inline contact-modal code report the form opening.
    window.nqTrack = track;
    window.nqTrackCustom = trackCustom;

    // ---- Click tracking -------------------------------------------------
    // Delegated from the document so it covers both pages, survives markup
    // changes, and picks up keyboard activation (Enter on a link fires click).
    document.addEventListener('click', function (e) {
        const link = e.target.closest && e.target.closest('a');
        if (!link) return;
        const href = link.getAttribute('href') || '';

        if (href.indexOf('tel:') === 0) {
            // A phone call is a real, completed contact - our best conversion.
            track('Lead', { content_name: 'Phone Call', content_category: 'Contact' });
            return;
        }

        if (href.indexOf('mailto:') === 0) {
            track('Lead', { content_name: 'Email', content_category: 'Contact' });
            return;
        }

        if (href.indexOf('clientsecure.me/sign-in') !== -1) {
            // Existing clients, not new leads - keep it out of the conversion count.
            trackCustom('PortalLogin');
            return;
        }

        // Any CTA pointing at the contact section, on either page
        // ("#contact" here, "index.html#contact" from the about page).
        if (href.indexOf('#contact') !== -1 || href.indexOf('contact=open') !== -1) {
            trackCustom('CTAClick', {
                content_name: (link.textContent || '').trim().slice(0, 60) || 'Contact CTA',
                source_page: document.title
            });
        }
    }, true);

    // ---- Section views --------------------------------------------------
    // Fires once per section, per page view. Observers are held in this array
    // for the life of the page rather than left to the callback closure alone.
    const observers = [];

    if ('IntersectionObserver' in window) {
        [
            { id: 'services', name: 'Services' },
            { id: 'wiki', name: 'FAQ' }
        ].forEach(function (section) {
            const el = document.getElementById(section.id);
            if (!el) return;
            const observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        track('ViewContent', { content_name: section.name });
                        observer.disconnect();
                    }
                });
            }, { threshold: 0.3 });
            observer.observe(el);
            observers.push(observer);
        });
    }

    // ---- Scroll depth ---------------------------------------------------
    // Percentage of the total scrollable distance, matching the health bar at
    // the top of the page. Each milestone fires at most once per page view.
    const scrollMarks = [
        { pct: 25, event: 'Scroll25' },
        { pct: 50, event: 'Scroll50' },
        { pct: 75, event: 'Scroll75' }
    ];

    let scrollQueued = false;

    function checkScrollDepth() {
        scrollQueued = false;
        const doc = document.documentElement;
        const scrollable = doc.scrollHeight - doc.clientHeight;
        if (scrollable <= 0) return;   // page shorter than the viewport

        const pct = (window.scrollY / scrollable) * 100;
        let remaining = 0;

        scrollMarks.forEach(function (mark) {
            if (mark.fired) return;
            if (pct >= mark.pct) {
                mark.fired = true;
                trackCustom(mark.event, { percent: mark.pct });
            } else {
                remaining++;
            }
        });

        if (remaining === 0) window.removeEventListener('scroll', onScroll);
    }

    function onScroll() {
        if (scrollQueued) return;      // coalesce to one check per frame
        scrollQueued = true;
        window.requestAnimationFrame(checkScrollDepth);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    checkScrollDepth();                // a page opened partway down still counts

    // ---- Time on page ---------------------------------------------------
    // Counts only seconds where the tab is actually visible, so a page left
    // open in a background tab doesn't read as someone reading it.
    const timeMarks = [
        { seconds: 15, event: 'Engaged15s' },
        { seconds: 45, event: 'Engaged45s' }
    ];

    let visibleSeconds = 0;

    const timer = window.setInterval(function () {
        if (document.visibilityState !== 'visible') return;
        visibleSeconds++;

        let remaining = 0;
        timeMarks.forEach(function (mark) {
            if (mark.fired) return;
            if (visibleSeconds >= mark.seconds) {
                mark.fired = true;
                trackCustom(mark.event, { seconds: mark.seconds });
            } else {
                remaining++;
            }
        });

        if (remaining === 0) window.clearInterval(timer);
    }, 1000);
})();
