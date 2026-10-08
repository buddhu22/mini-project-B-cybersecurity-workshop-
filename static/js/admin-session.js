(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  window.setInterval(() => {
    fetch("/admin/refresh", { method: "POST", headers: { "X-CSRFToken": csrf }, credentials: "same-origin" })
      .then(response => { if (!response.ok || response.redirected || response.url.includes("/admin/login")) window.location.assign("/admin/login"); })
      .catch(() => {});
  }, 10 * 60 * 1000);
})();
