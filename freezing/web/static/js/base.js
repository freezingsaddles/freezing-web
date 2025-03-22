$(document).ready(function ($) {

  // delegate calls to data-toggle="lightbox"
  $(document).delegate('*[data-toggle="lightbox"]:not([data-gallery="navigateTo"])', 'click', function(event) {
    event.preventDefault();
    return $(this).ekkoLightbox({
      onShown: function() {
        if (window.console) {
          return console.log('Checking our the events huh?');
        }
      },
      onNavigate: function(direction, itemIndex) {
        if (window.console) {
          return console.log('Navigating '+direction+'. Current item: '+itemIndex);
        }
      }
    });
  });

  // https://stackoverflow.com/a/75065536
  // Set theme to the user's preferred color scheme
  function updateTheme() {
    const colorMode = window.matchMedia("(prefers-color-scheme: dark)").matches ?
      "dark" :
      "light";
    document.querySelector("html").setAttribute("data-bs-theme", colorMode);
    // Persist the theme to avoid light-mode always flashing in first
    const date = new Date();
    date.setDate(date.getDate() + 30);
    document.cookie = "theme=" + colorMode + "; expires=" + date.toUTCString() + "; path=/";
  }

  // Set theme on load
  updateTheme()

  // Update theme when the preferred scheme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateTheme)

});
