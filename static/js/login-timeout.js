(() => {
  const page = document.querySelector("[data-login-timeout]");
  const warning = document.getElementById("login-timeout-warning");
  if (!page || !warning) return;

  const timeoutMs = Number(page.dataset.loginTimeout) * 1000;
  let lastActivity = Date.now();
  let timer;

  function checkTimeout() {
    const remaining = timeoutMs - (Date.now() - lastActivity);
    if (remaining <= 0) {
      warning.hidden = false;
      page.querySelectorAll("input, button").forEach(control => { control.disabled = true; });
      return;
    }
    timer = window.setTimeout(checkTimeout, Math.min(remaining, 1000));
  }

  function recordActivity() {
    if (!warning.hidden) return;
    lastActivity = Date.now();
    window.clearTimeout(timer);
    checkTimeout();
  }

  ["pointerdown", "keydown", "touchstart", "click", "input"].forEach(eventName => {
    document.addEventListener(eventName, recordActivity, { passive: true });
  });
  checkTimeout();
})();
