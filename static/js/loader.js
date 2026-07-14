// Page Loader Script — optimized for perceived speed.
(function () {
  const loader = document.getElementById('pageLoader');
  if (!loader) return;

  // Hide the loader as soon as the DOM is ready — don't wait for every
  // image/font (window.load) and don't add an artificial delay.
  function hideLoader() {
    loader.classList.add('hidden');
    document.body.classList.add('page-transition');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideLoader);
  } else {
    hideLoader();
  }

  // Show the loader during navigation, but DON'T block it with a timeout.
  // The browser keeps painting the current page (with the loader) while it
  // fetches the next one, so navigation starts instantly.
  document.addEventListener('click', function (e) {
    const link = e.target.closest('a');

    if (link &&
        link.href &&
        !link.href.startsWith('#') &&
        !link.getAttribute('href').startsWith('#') &&
        !link.href.includes('javascript:') &&
        !link.hasAttribute('download') &&
        !link.target &&
        link.hostname === window.location.hostname) {
      loader.classList.remove('hidden');
      // Let the default navigation proceed immediately — no preventDefault,
      // no setTimeout. This removes the old ~300ms per-click stall.
    }
  });

  // Handle browser back/forward from bfcache.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      loader.classList.add('hidden');
    }
  });
})();
