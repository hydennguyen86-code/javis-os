// Wiring giao diện chat trên điện thoại (mobile-only, <=860px):
//  - dời chip model (#mbOpen + #mbPop) lên header khi mobile, trả về model-bar khi desktop
//  - dời nhóm Hệ thống (chọn brain, cài đặt, đổi tông, Studio, loa, dải HỆ THỐNG) vào đáy ngăn kéo
//  - nút + = hội thoại mới (dùng lại #resetBtn)
//  - ngăn kéo điều hướng: ☰ mở/đóng, backdrop / Esc / chọn mục thì đóng
//  - rút gọn placeholder ô nhập cho vừa bề ngang điện thoại
(function () {
  function init() {
    var mq = window.matchMedia("(max-width: 860px)");
    var railEl = document.querySelector(".rail");

    // ---- 1) Chip model: mobile đưa lên giữa header, desktop trả về .model-bar ----
    var mbOpen = document.getElementById("mbOpen");
    var mbPop = document.getElementById("mbPop");
    var modelBar = document.getElementById("modelBar");
    var headerRoot = document.querySelector(".hud-top");
    var headerCenter = document.querySelector(".hud-center-title");
    function placeModelChip() {
      if (!mbOpen || !modelBar || !headerRoot) return;
      if (mq.matches) {
        if (mbOpen.parentElement !== headerRoot) {
          if (headerCenter && headerCenter.parentElement === headerRoot) {
            headerRoot.insertBefore(mbOpen, headerCenter.nextSibling);
          } else {
            headerRoot.appendChild(mbOpen);
          }
          if (mbPop) headerRoot.insertBefore(mbPop, mbOpen.nextSibling);
        }
      } else if (mbOpen.parentElement !== modelBar) {
        modelBar.insertBefore(mbOpen, modelBar.firstChild);
        if (mbPop) modelBar.insertBefore(mbPop, mbOpen.nextSibling);
      }
    }

    // ---- 2) Nhóm Hệ thống: mobile dời vào đáy ngăn kéo, desktop trả về chỗ cũ ----
    var sysHost = null, sysBtns = null, moved = [];
    function ensureSysHost() {
      if (sysHost || !railEl) return;
      sysHost = document.createElement("div");
      sysHost.className = "rail-sys";
      var lbl = document.createElement("div");
      lbl.className = "rail-sys-lbl";
      lbl.textContent = "Hệ thống";
      sysHost.appendChild(lbl);
      sysBtns = document.createElement("div");
      sysBtns.className = "rail-sys-btns";
      sysHost.appendChild(sysBtns);
      var foot = railEl.querySelector(".rail-foot");
      railEl.insertBefore(sysHost, foot || null);
    }
    function moveEl(el, toBtns) {
      if (!el) return;
      ensureSysHost();
      if (!sysHost) return;
      moved.push({ el: el, parent: el.parentElement, next: el.nextSibling });
      (toBtns ? sysBtns : sysHost).appendChild(el);
    }
    function placeSystem() {
      if (mq.matches) {
        if (!moved.length) {
          moveEl(document.querySelector(".navbar-brain"), false);
          moveEl(document.getElementById("settingsBtn"), true);
          moveEl(document.getElementById("themeToggle"), true);
          moveEl(document.getElementById("ttsToggle"), true);
          moveEl(document.getElementById("sysBar"), false);
        }
      } else if (moved.length) {
        moved.forEach(function (m) {
          if (m.next && m.next.parentElement === m.parent) m.parent.insertBefore(m.el, m.next);
          else m.parent.appendChild(m.el);
        });
        moved = [];
      }
    }

    // ---- 3) Placeholder ngắn cho ô nhập trên mobile ----
    var chatInput = document.getElementById("chatInput");
    var longPh = chatInput ? chatInput.getAttribute("placeholder") : "";
    function setPlaceholder() {
      if (chatInput) chatInput.setAttribute("placeholder", mq.matches ? "Nói hoặc gõ cho Javis…" : longPh);
    }

    // ---- 4) Nút + = hội thoại mới ----
    var newChat = document.getElementById("newChatBtn");
    var reset = document.getElementById("resetBtn");
    if (newChat && reset) newChat.addEventListener("click", function () { reset.click(); });

    // ---- 5) Ngăn kéo điều hướng ----
    var toggle = document.getElementById("navToggle");
    var backdrop = document.getElementById("navBackdrop");
    function openNav() { document.body.classList.add("nav-open"); if (backdrop) backdrop.hidden = false; }
    function closeNav() { document.body.classList.remove("nav-open"); if (backdrop) backdrop.hidden = true; }
    if (toggle) toggle.addEventListener("click", function () {
      document.body.classList.contains("nav-open") ? closeNav() : openNav();
    });
    if (backdrop) backdrop.addEventListener("click", closeNav);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeNav(); });
    if (railEl) railEl.addEventListener("click", function (e) {
      if (e.target.closest(".rail-item") && mq.matches) closeNav();  // chọn mục điều hướng -> đóng
    });

    function applyAll() { placeModelChip(); placeSystem(); setPlaceholder(); }
    applyAll();

    var onChange = function () { applyAll(); closeNav(); };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
