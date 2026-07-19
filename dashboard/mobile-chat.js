// Wiring giao diện chat trên điện thoại (mobile-only, <=860px):
//  - dời chip model (#mbOpen + #mbPop) lên header khi mobile, trả về model-bar khi desktop
//  - nút + = hội thoại mới (dùng lại #resetBtn)
//  - ngăn kéo điều hướng: ☰ mở/đóng, backdrop / Esc / chọn mục thì đóng
(function () {
  function init() {
    var mq = window.matchMedia("(max-width: 860px)");

    // 1) Chip model: mobile đưa lên giữa header, desktop trả về .model-bar.
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
    placeModelChip();

    // 2) Nút + = hội thoại mới (ủy quyền sang nút reset sẵn có).
    var newChat = document.getElementById("newChatBtn");
    var reset = document.getElementById("resetBtn");
    if (newChat && reset) newChat.addEventListener("click", function () { reset.click(); });

    // 3) Ngăn kéo điều hướng.
    var toggle = document.getElementById("navToggle");
    var backdrop = document.getElementById("navBackdrop");
    var rail = document.querySelector(".rail");
    function openNav() { document.body.classList.add("nav-open"); if (backdrop) backdrop.hidden = false; }
    function closeNav() { document.body.classList.remove("nav-open"); if (backdrop) backdrop.hidden = true; }
    if (toggle) toggle.addEventListener("click", function () {
      document.body.classList.contains("nav-open") ? closeNav() : openNav();
    });
    if (backdrop) backdrop.addEventListener("click", closeNav);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeNav(); });
    if (rail) rail.addEventListener("click", function (e) {
      if (e.target.closest(".rail-item") && mq.matches) closeNav();
    });

    // Đổi kích thước / xoay màn: đặt lại chỗ chip + đóng ngăn kéo cho gọn.
    var onChange = function () { placeModelChip(); closeNav(); };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
