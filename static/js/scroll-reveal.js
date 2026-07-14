/* ============================================================
   Scroll Reveal — site-wide reveal-on-scroll + progress bar.
   Auto-tags common elements so no per-page markup is needed.
   Pairs with css/scroll-animations.css.

   The `js-reveal` class is added to <html> by a tiny inline
   script in header.html BEFORE paint, so elements hide without
   a flash. This file then observes them and reveals on scroll.
   ============================================================ */
(function () {
  "use strict";

  // Bail entirely if the user prefers reduced motion — the inline
  // head script already skips adding `.js-reveal`, so nothing is hidden.
  var prefersReduced =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReduced) return;

  /* ---- Which elements reveal, and how ----
     Each rule maps a CSS selector to a reveal direction. First match
     wins (an element already tagged .reveal is skipped). Order matters:
     more specific selectors go first. */
  var RULES = [
    // Home page
    { sel: ".hero-content > *", dir: "up", stagger: true },
    { sel: ".about-image", dir: "left" },
    { sel: ".about-content", dir: "right" },
    { sel: ".about-highlights .highlight-card", dir: "up", stagger: true },
    { sel: ".services-heading, .services-desc", dir: "up", stagger: true },
    { sel: ".services-cards .service-card", dir: "up", stagger: true },
    { sel: ".collab-container > *", dir: "zoom", stagger: true },
    { sel: ".testimonials-heading", dir: "up" },
    { sel: ".testimonials-container .testimonial-card", dir: "up", stagger: true },
    // Generic fallbacks — cover about / services / portfolio / contact pages
    { sel: "section [class*='-heading'], section [class*='-title']", dir: "up" },
    { sel: "[class*='-card']", dir: "up", stagger: true },
    { sel: ".project-detail section, .project-detail article", dir: "up", stagger: true },
  ];

  // Group selector used to compute per-group stagger delays.
  var STAGGER_STEP = 60; // ms between siblings
  var STAGGER_MAX = 5; // cap so long lists don't lag far behind

  function tag() {
    RULES.forEach(function (rule) {
      var nodes = document.querySelectorAll(rule.sel);
      var staggerIndex = 0;
      nodes.forEach(function (el) {
        if (el.classList.contains("reveal")) return; // already claimed
        el.classList.add("reveal");
        if (rule.dir && rule.dir !== "up") {
          el.setAttribute("data-reveal", rule.dir);
        }
        if (rule.stagger) {
          var step = Math.min(staggerIndex, STAGGER_MAX);
          el.style.setProperty("--reveal-delay", step * STAGGER_STEP + "ms");
          staggerIndex++;
        }
      });
    });
  }

  function observe() {
    var targets = document.querySelectorAll(".reveal");
    if (!targets.length) return;

    // No IntersectionObserver (very old browsers): just show everything.
    if (!("IntersectionObserver" in window)) {
      targets.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target); // reveal once, then stop watching
          }
        });
      },
      {
        threshold: 0.12,
        rootMargin: "0px 0px -8% 0px", // trigger slightly before fully in view
      }
    );

    targets.forEach(function (el) {
      io.observe(el);
    });
  }

  /* ---- Scroll progress bar ---- */
  function progressBar() {
    var bar = document.createElement("div");
    bar.className = "scroll-progress";
    document.body.appendChild(bar);

    var ticking = false;
    function update() {
      var doc = document.documentElement;
      var scrollable = doc.scrollHeight - doc.clientHeight;
      var ratio = scrollable > 0 ? window.scrollY / scrollable : 0;
      bar.style.transform = "scaleX(" + Math.min(ratio, 1) + ")";
      ticking = false;
    }
    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) {
          window.requestAnimationFrame(update);
          ticking = true;
        }
      },
      { passive: true }
    );
    update();
  }

  function init() {
    tag();
    observe();
    progressBar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
