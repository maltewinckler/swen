/* Screenshot gallery — initialised on every MkDocs Material page navigation */
(function () {
  function initGalleries() {
    document.querySelectorAll(".swen-gallery").forEach(function (gallery) {
      /* Skip if already initialised */
      if (gallery.dataset.galleryReady) return;
      gallery.dataset.galleryReady = "1";

      var track = gallery.querySelector(".swen-gallery__track");
      var slides = gallery.querySelectorAll(".swen-gallery__slide");
      var dots = gallery.querySelectorAll(".swen-gallery__dot");
      var captionEl = gallery.nextElementSibling;
      if (captionEl && !captionEl.classList.contains("swen-gallery__caption")) {
        captionEl = null;
      }

      var captions = Array.from(slides).map(function (s) {
        return s.dataset.caption || "";
      });
      var total = slides.length;
      var current = 0;

      function adjustHeight() {
        var img = slides[current].querySelector("img");
        if (!img) return;
        if (img.complete && img.naturalHeight > 0) {
          gallery.style.height = img.offsetHeight + "px";
        } else {
          img.addEventListener("load", function () {
            gallery.style.height = img.offsetHeight + "px";
          }, { once: true });
        }
      }

      function goTo(n) {
        current = ((n % total) + total) % total;
        track.style.transform = "translateX(-" + current * 100 + "%)";
        dots.forEach(function (d, i) {
          d.classList.toggle("active", i === current);
        });
        if (captionEl) captionEl.textContent = captions[current];
        adjustHeight();
      }

      window.addEventListener("resize", function () {
        /* suppress the height transition during resize for a snappier feel */
        gallery.style.transition = "none";
        adjustHeight();
        requestAnimationFrame(function () {
          gallery.style.transition = "";
        });
      });

      gallery
        .querySelector(".swen-gallery__btn--prev")
        .addEventListener("click", function () {
          goTo(current - 1);
        });
      gallery
        .querySelector(".swen-gallery__btn--next")
        .addEventListener("click", function () {
          goTo(current + 1);
        });

      dots.forEach(function (dot, i) {
        dot.addEventListener("click", function () {
          goTo(i);
        });
      });

      /* Keyboard support when gallery is focused */
      gallery.setAttribute("tabindex", "0");
      gallery.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") goTo(current - 1);
        if (e.key === "ArrowRight") goTo(current + 1);
      });

      goTo(0);
    });
  }

  /* MkDocs Material exposes document$ (RxJS observable) for SPA navigation */
  if (typeof document$ !== "undefined") {
    document$.subscribe(initGalleries);
  } else {
    document.addEventListener("DOMContentLoaded", initGalleries);
  }
})();
