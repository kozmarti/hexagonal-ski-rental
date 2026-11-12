// The light / dark button in the menu bar.
// Until it is clicked, the page follows the device setting (Pico.css, no data-theme).
// A click switches to the other mode and remembers it in this browser (localStorage), so the
// next pages keep it. The saved mode is applied in <head> already (base.html): no flash.
(function () {
  const deviceIsDark = window.matchMedia("(prefers-color-scheme: dark)");

  function current() {
    return document.documentElement.dataset.theme || (deviceIsDark.matches ? "dark" : "light");
  }

  // The icon shows where a click goes: ☾ in light mode, ☀ in dark mode.
  function render() {
    const dark = current() === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = dark ? "☀" : "☾";
      button.title = dark ? "Switch to light mode" : "Switch to dark mode";
      button.setAttribute("aria-label", button.title);
    });
  }

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-theme-toggle]")) return;
    const next = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch (error) {
      // Storage blocked (private window...): applied to this page only.
    }
    render();
  });

  // Not chosen yet: follow the device when its setting changes.
  deviceIsDark.addEventListener("change", render);
  render();
})();
