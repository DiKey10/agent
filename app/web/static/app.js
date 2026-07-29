// Dodawanie rolek bez przeladowania strony + odpytywanie o postep zadania.
// Formularz dziala takze bez tego skryptu (POST /add), to jest tylko wygoda.

const form = document.getElementById("add-form");
const input = document.getElementById("url-input");
const jobsList = document.getElementById("jobs");

const LABELS = {
  pending: "W kolejce…",
  downloading: "Pobieram rolkę…",
  transcribing: "Rozpoznaję mowę…",
  extracting: "Układam przepis…",
  done: "Gotowe",
  rejected: "To nie przepis",
  failed: "Nie wyszło",
};

const TERMINAL = new Set(["done", "rejected", "failed"]);

function renderJob(jobId, state) {
  let node = document.getElementById(`job-${jobId}`);
  if (!node) {
    node = document.createElement("li");
    node.id = `job-${jobId}`;
    node.className = "job";
    jobsList.prepend(node);
  }

  node.className = `job is-${state.status}`;
  const label = LABELS[state.status] || state.status;
  const detail = state.message ? ` — ${state.message}` : "";

  node.innerHTML = "";

  const dot = document.createElement("span");
  dot.className = "dot";
  node.append(dot);

  const text = document.createElement("span");
  text.textContent = label + detail;
  node.append(text);

  if (state.recipe_id) {
    const link = document.createElement("a");
    link.href = `/recipe/${state.recipe_id}`;
    link.textContent = "Otwórz →";
    node.append(link);
  }
}

async function poll(jobId) {
  // Odpytujemy co 2 s. Przetwarzanie rolki trwa minuty, więc częstsze
  // sprawdzanie to tylko ruch bez korzyści.
  while (true) {
    let state;
    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state = await response.json();
    } catch (error) {
      renderJob(jobId, { status: "failed", message: "Utracono kontakt z serwerem." });
      return;
    }

    renderJob(jobId, state);

    if (TERMINAL.has(state.status)) {
      // Nowy przepis pojawi się na liście dopiero po odświeżeniu.
      if (state.status === "done") setTimeout(() => location.reload(), 1200);
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}

if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const url = input.value.trim();
    if (!url) return;

    const button = form.querySelector("button");
    button.disabled = true;

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();

      if (!response.ok) {
        alert(data.detail || "Nie udało się dodać rolki.");
        return;
      }

      input.value = "";
      renderJob(data.job_id, { status: "pending" });
      poll(data.job_id);
    } finally {
      button.disabled = false;
    }
  });
}

// Wejście z przekierowania formularza (bez JS): /?job=<id>
const jobFromUrl = new URLSearchParams(location.search).get("job");
if (jobFromUrl) poll(jobFromUrl);
