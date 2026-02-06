/**
 * Mermaid diagram lightbox with zoom & pan support.
 *
 * - Click any .mermaid element to open the lightbox overlay.
 * - Mouse wheel to zoom in/out (centered on cursor position).
 * - Click + drag to pan.
 * - Click backdrop or press Escape to close.
 */
(function () {
  var overlay = document.getElementById("mermaid-overlay");
  var content = document.getElementById("mermaid-overlay-content");
  if (!overlay || !content) return;

  var scale = 1;
  var translateX = 0;
  var translateY = 0;
  var isDragging = false;
  var dragStartX = 0;
  var dragStartY = 0;
  var dragStartTX = 0;
  var dragStartTY = 0;

  function applyTransform() {
    var svg = content.querySelector("svg");
    if (svg)
      svg.style.transform =
        "translate(" +
        translateX +
        "px," +
        translateY +
        "px) scale(" +
        scale +
        ")";
  }

  function resetTransform() {
    scale = 1;
    translateX = 0;
    translateY = 0;
  }

  // Use event delegation so it works even after mermaid replaces DOM nodes
  document.addEventListener("click", function (e) {
    var target = e.target.closest(".mermaid");
    if (target) {
      var svg = target.querySelector("svg");
      if (svg) {
        content.innerHTML = "";
        var clone = svg.cloneNode(true);
        // Ensure viewBox exists so SVG scales properly when we resize it
        if (!clone.getAttribute("viewBox")) {
          var w = svg.getAttribute("width") || svg.getBoundingClientRect().width;
          var h =
            svg.getAttribute("height") || svg.getBoundingClientRect().height;
          w = parseFloat(w) || 800;
          h = parseFloat(h) || 600;
          clone.setAttribute("viewBox", "0 0 " + w + " " + h);
        }
        clone.removeAttribute("width");
        clone.removeAttribute("height");
        clone.removeAttribute("style");
        clone.style.width = "100%";
        clone.style.height = "auto";
        clone.style.maxHeight = "85vh";
        clone.style.transformOrigin = "center center";
        clone.style.transition = "transform 0.15s ease";
        content.appendChild(clone);
        resetTransform();
        overlay.classList.add("visible");
      }
    }
  });

  // Mouse wheel zoom inside the overlay
  content.addEventListener(
    "wheel",
    function (e) {
      e.preventDefault();
      var delta = e.deltaY > 0 ? -0.1 : 0.1;
      var newScale = Math.min(Math.max(scale + delta, 0.2), 10);
      // Zoom toward cursor position
      var rect = content.getBoundingClientRect();
      var cx = e.clientX - rect.left - rect.width / 2;
      var cy = e.clientY - rect.top - rect.height / 2;
      var ratio = newScale / scale;
      translateX = cx - ratio * (cx - translateX);
      translateY = cy - ratio * (cy - translateY);
      scale = newScale;
      applyTransform();
    },
    { passive: false }
  );

  // Mouse drag to pan inside the overlay
  content.addEventListener("mousedown", function (e) {
    if (e.button !== 0) return;
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartTX = translateX;
    dragStartTY = translateY;
    content.style.cursor = "grabbing";
    e.preventDefault();
  });
  document.addEventListener("mousemove", function (e) {
    if (!isDragging) return;
    translateX = dragStartTX + (e.clientX - dragStartX);
    translateY = dragStartTY + (e.clientY - dragStartY);
    applyTransform();
  });
  document.addEventListener("mouseup", function () {
    if (isDragging) {
      isDragging = false;
      content.style.cursor = "";
    }
  });

  // Close overlay when clicking on the backdrop (not on the content)
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) {
      overlay.classList.remove("visible");
      resetTransform();
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      overlay.classList.remove("visible");
      resetTransform();
    }
  });
})();
