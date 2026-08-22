// Meta Pixel event tracking, shared by every page.
//
// The contact form is a cross-origin SimplePractice iframe, so the page cannot
// see submissions with certainty. The widget shows its own "message sent"
// screen inside the iframe and never navigates or posts a message out, so the
// page only ever learns that the visitor closed the modal. thank-you.html is
// the site's stand-in for a submission: closing the form after ten seconds or
// more is treated as one, and there is a manual "Sent your message? Continue"
// link under the form for anyone who takes another route. Loading that page
// is therefore the strongest conversion signal available, and it fires Lead.
//
// Intent and completion are deliberately split across two standard events, so
// one person who sends a message is counted once and not twice: opening the
// form fires Contact, reaching the confirmation page fires Lead. Optimize on
// Lead; read Contact as the top of that funnel.
//
// STANDARD events (what Meta can optimize and attribute against):
//
//   PageView    -> fired by the base pixel snippet in the page head
//   Contact     -> contact form opened (intent, no message sent yet)
//   Lead        -> confirmation page reached, phone click, email click
//                  (phone and email are completed contact attempts, so they
//                  belong with the conversion rather than with intent)
//   ViewContent -> Services / FAQ sections scrolled into view
//
// CUSTOM events (readable, one per thing a visitor can actually click, so
// Events Manager tells you WHAT was clicked and not just "a CTA was"):
//
//   schedule-consult        hero primary button
//   view-services           hero secondary button
//   nav-get-started         "Get Started" in the nav (desktop or mobile)
//   nav-services            nav -> Services
//   nav-about-me            nav -> About Me
//   nav-faq                 nav -> FAQ
//   nav-home                nav -> Home Base (about page only)
//   learn-more-individual   Individual Therapy card
//   learn-more-couples      Couples Counseling card
//   learn-more-family       Family Therapy card
//   open-contact-form       the button that actually opens the form
//   contact-form-opened     the form modal is now on screen (any path in)
//   contact-form-continue   the manual "Sent your message? Continue" link
//   contact-form-handoff    left the form for the confirmation page; detected_by
//                           says how (modal-closed in almost every case, or
//                           postMessage / iframe-navigation if the widget ever
//                           starts signalling)
//   contact-form-submitted  the confirmation page loaded
//   thank-you-home          confirmation page -> home
//   thank-you-about         confirmation page -> about
//   phone-click             tel: link
//   email-click             mailto: link
//   client-portal           existing client heading to SimplePractice
//   psychology-today        outbound profile link
//
// Every click event carries source_page ("home", "about" or "thank-you"), so
// the same name can be used on every page and still be broken down by where it
// happened.
//
// Names come from data-nq-event="..." in the markup. To track a new link or
// button, add that attribute - no change is needed in this file.
//
// Plus shallow engagement signals, all custom so they stay out of any
// conversion count:
//
//   scroll-25 / scroll-50 / scroll-75   how far down the page people get
//   engaged-15s / engaged-45s           visible time on page, tab-blur aware
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

    // Which page the action happened on, attached to every event so the shared
    // names ("phone-click", "nav-faq") stay breakdown-able.
    const path = window.location.pathname;
    const pageLabel = /about\.html$/.test(path) ? 'about'
        : /thank-you\.html$/.test(path) ? 'thank-you'
        : 'home';

    // Let the inline contact-modal code report the form opening.
    window.nqTrack = track;
    window.nqTrackCustom = trackCustom;

    // ---- Click tracking -------------------------------------------------
    // Delegated from the document so it covers both pages, survives markup
    // changes, and picks up keyboard activation (Enter on a link fires click).
    document.addEventListener('click', function (e) {
        if (!e.target.closest) return;
        const el = e.target.closest('a, button');
        if (!el) return;

        const href = el.getAttribute('href') || '';
        const name = el.getAttribute('data-nq-event');

        // Phone and email are real, completed contact attempts - our best
        // conversions. They fire Lead (so Meta can optimize on it) AND a
        // readable custom event (so you can read it in Events Manager).
        if (href.indexOf('tel:') === 0) {
            track('Lead', { content_name: 'phone-click', content_category: 'Contact' });
            trackCustom('phone-click', { source_page: pageLabel });
            return;
        }

        if (href.indexOf('mailto:') === 0) {
            track('Lead', { content_name: 'email-click', content_category: 'Contact' });
            trackCustom('email-click', { source_page: pageLabel });
            return;
        }

        if (name) {
            trackCustom(name, { source_page: pageLabel });
            return;
        }

        // Safety net: an untagged CTA pointing at the contact section still
        // reports something, labelled with its own text so it can be found
        // and given a proper data-nq-event.
        if (href.indexOf('#contact') !== -1 || href.indexOf('contact=open') !== -1) {
            trackCustom('contact-cta-untagged', {
                link_text: (el.textContent || '').trim().slice(0, 60) || 'unknown',
                source_page: pageLabel
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
        { pct: 25, event: 'scroll-25' },
        { pct: 50, event: 'scroll-50' },
        { pct: 75, event: 'scroll-75' }
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
                trackCustom(mark.event, { percent: mark.pct, source_page: pageLabel });
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
        { seconds: 15, event: 'engaged-15s' },
        { seconds: 45, event: 'engaged-45s' }
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
                trackCustom(mark.event, { seconds: mark.seconds, source_page: pageLabel });
            } else {
                remaining++;
            }
        });

        if (remaining === 0) window.clearInterval(timer);
    }, 1000);
})();
