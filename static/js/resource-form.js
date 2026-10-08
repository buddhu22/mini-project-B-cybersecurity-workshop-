(() => {
  const choice = document.getElementById("session-choice");
  const title = document.getElementById("session-title");
  const day = document.getElementById("session-day");
  if (!choice || !title || !day) return;
  function update() {
    const option = choice.options[choice.selectedIndex];
    title.value = option?.dataset.title || "";
    day.value = option?.dataset.day || "";
  }
  choice.addEventListener("change", update);
  update();
})();
