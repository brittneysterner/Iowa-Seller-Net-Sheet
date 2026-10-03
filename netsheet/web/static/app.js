// Small helpers for the editing screen: add/remove rows, contract side panel,
// and a reminder if you try to leave with unsaved changes.
(function () {
  let dirty = false;
  const form = document.getElementById("main-form");

  function newId() {
    return Math.random().toString(36).slice(2, 12).replace(/[^a-z0-9]/g, "x");
  }

  document.addEventListener("click", function (e) {
    const add = e.target.closest("[data-add]");
    if (add) {
      e.preventDefault();
      const tpl = document.getElementById("tpl-" + add.dataset.add);
      const list = document.getElementById("list-" + add.dataset.add);
      const html = tpl.innerHTML.replaceAll("__ID__", newId());
      list.insertAdjacentHTML("beforeend", html);
      const row = list.lastElementChild;
      if (add.dataset.label) {
        const lbl = row.querySelector("[data-role=label]");
        if (lbl) lbl.value = add.dataset.label;
      }
      const first = row.querySelector("input[type=text]");
      if (first) first.focus();
      dirty = true;
      updateMethods(row);
    }
    const rm = e.target.closest("[data-remove]");
    if (rm) {
      e.preventDefault();
      if (confirm("Remove this line? (It is removed when you click Save.)")) {
        rm.closest(".row-item").remove();
        dirty = true;
      }
    }
    const toggle = e.target.closest("[data-toggle-pdf]");
    if (toggle) {
      e.preventDefault();
      document.querySelector(".layout").classList.toggle("with-pdf");
    }
  });

  function updateMethods(scope) {
    (scope || document).querySelectorAll("select[data-method]").forEach(function (sel) {
      const row = sel.closest(".row-item");
      const m = sel.value;
      row.querySelector("[data-pct]").style.display = m === "flat" ? "none" : "";
      row.querySelector("[data-flat]").style.display = m === "percent" ? "none" : "";
    });
  }
  document.addEventListener("change", function (e) {
    if (e.target.matches("select[data-method]")) updateMethods(e.target.closest(".row-item"));
  });
  updateMethods();

  if (form) {
    form.addEventListener("input", function () { dirty = true; });
    form.addEventListener("submit", function () { dirty = false; });
    window.addEventListener("beforeunload", function (e) {
      if (dirty) { e.preventDefault(); e.returnValue = ""; }
    });
  }
})();
