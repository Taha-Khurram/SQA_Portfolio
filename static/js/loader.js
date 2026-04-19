// Page Loader Script
(function() {
  const loader = document.getElementById('pageLoader');

  // Hide loader when page is fully loaded
  window.addEventListener('load', function() {
    setTimeout(function() {
      loader.classList.add('hidden');
      document.body.classList.add('page-transition');
    }, 300);
  });

  // Show loader on page navigation
  document.addEventListener('click', function(e) {
    const link = e.target.closest('a');

    if (link &&
        link.href &&
        !link.href.startsWith('#') &&
        !link.href.includes('javascript:') &&
        !link.hasAttribute('download') &&
        !link.target &&
        link.hostname === window.location.hostname) {

      e.preventDefault();
      loader.classList.remove('hidden');

      setTimeout(function() {
        window.location.href = link.href;
      }, 300);
    }
  });

  // Handle browser back/forward
  window.addEventListener('pageshow', function(e) {
    if (e.persisted) {
      loader.classList.add('hidden');
    }
  });
})();
