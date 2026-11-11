// Scanning equipment QR codes: on the Scan page (opens the item's page) and on the counter
// page (ticks the item in the rental being prepared).
//
// A code can come from three places, all handled the same way:
// - a barcode scanner, which types the code like a keyboard and presses Enter;
// - the keyboard (typing or pasting an id or a sticker link, then Enter);
// - the camera, with the free html5-qrcode library (needs HTTPS, or localhost).
(function () {
  const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
  const CAMERA_LIBRARY = "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";

  const actions = {
    // Scan page: open the item's page (rent it, return its rental, finish its maintenance).
    goto(id, field) {
      window.location.href = field.dataset.scanUrl.replace(field.dataset.scanPlaceholder, id);
      return { ok: true, text: "Opening the item…" };
    },
    // Counter: tick the scanned item in the rental being prepared.
    tick(id) {
      const box = document.querySelector(`input[name="equipment"][value="${id}"]`);
      if (!box) return { ok: false, text: "Not in the list: not available, or already rented." };
      box.checked = true;
      box.closest("details")?.setAttribute("open", "");
      box.scrollIntoView({ block: "center" });
      return { ok: true, text: `Added: ${box.parentElement.textContent.trim()}` };
    },
  };

  // Messages are set as text, never as HTML: item names come from the database.
  function show(message, ok, text) {
    const element = document.createElement(ok ? "ins" : "del");
    element.textContent = text;
    message.replaceChildren(element);
  }

  function setUp(field) {
    const input = field.querySelector("input");
    const message = field.querySelector("[data-scan-message]");
    const action = actions[field.dataset.scan];
    let last = { id: null, at: 0 };

    function handle(text) {
      const match = UUID.exec(text);
      const id = match && match[0].toLowerCase();
      // The camera reads the same code many times per second: handle it once.
      if (id && id === last.id && Date.now() - last.at < 3000) return;
      last = { id, at: Date.now() };
      const result = id ? action(id, field) : { ok: false, text: "This is not an equipment code." };
      show(message, result.ok, result.text);
    }

    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      handle(input.value);
      input.value = "";
    });

    field.querySelector("[data-scan-camera]")?.addEventListener("click", () => startCamera(field, handle));
  }

  function startCamera(field, handle) {
    const message = field.querySelector("[data-scan-message]");
    if (!window.isSecureContext) {
      show(message, false, "The camera needs HTTPS (it works on this computer at localhost).");
      return;
    }
    const start = () => {
      const reader = field.querySelector("[data-scan-reader]");
      reader.hidden = false;
      const camera = new Html5Qrcode(reader.id);
      camera
        .start({ facingMode: "environment" }, { fps: 10, qrbox: 220 }, handle, () => {})
        .catch(() => show(message, false, "The camera could not be started."));
    };
    if (window.Html5Qrcode) return start();
    const script = document.createElement("script");
    script.src = CAMERA_LIBRARY;
    script.onload = start;
    script.onerror = () => show(message, false, "The camera library could not be loaded.");
    document.head.appendChild(script);
  }

  document.querySelectorAll("[data-scan]").forEach(setUp);
})();
