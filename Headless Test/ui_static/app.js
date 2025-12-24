let avatars = Array.isArray(window.AVATARS) ? [...window.AVATARS] : [];

const projectName = document.getElementById("projectName");
const avatarSelect = document.getElementById("avatarSelect");
const avatarList = document.getElementById("avatarList");
const avatarInput = document.getElementById("avatarInput");
const avatarAddBtn = document.getElementById("avatarAddBtn");
const qualitySelect = document.getElementById("qualitySelect");
const fpsSelect = document.getElementById("fpsSelect");
const subtitlesSelect = document.getElementById("subtitlesSelect");
const cardsContainer = document.getElementById("cards");
const addCardBtn = document.getElementById("addCardBtn");
const startBtn = document.getElementById("startBtn");
const statusBox = document.getElementById("statusBox");
const cardCount = document.getElementById("cardCount");

function wordCount(text) {
  const cleaned = text.trim();
  if (!cleaned) {
    return 0;
  }
  return cleaned.split(/\s+/).length;
}

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.style.borderColor = isError ? "#e0b4b4" : "#e1e1dd";
  statusBox.style.background = isError ? "#fff4f4" : "#f4f4f1";
}

function renderAvatarSelect(selectedValue = null) {
  const previous = selectedValue || avatarSelect.value;
  avatarSelect.innerHTML = "";

  if (avatars.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No avatars saved";
    avatarSelect.appendChild(option);
    return;
  }

  avatars.forEach((avatar) => {
    const option = document.createElement("option");
    option.value = avatar;
    option.textContent = avatar;
    avatarSelect.appendChild(option);
  });

  if (previous && avatars.includes(previous)) {
    avatarSelect.value = previous;
  }
}

function renderAvatarList() {
  avatarList.innerHTML = "";

  if (avatars.length === 0) {
    const empty = document.createElement("div");
    empty.className = "helper";
    empty.textContent = "No avatars yet. Add one below.";
    avatarList.appendChild(empty);
    return;
  }

  avatars.forEach((avatar) => {
    const row = document.createElement("div");
    row.className = "avatar-item";

    const name = document.createElement("div");
    name.textContent = avatar;

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "ghost small";
    removeBtn.textContent = "Delete";
    removeBtn.addEventListener("click", () => deleteAvatar(avatar));

    row.appendChild(name);
    row.appendChild(removeBtn);
    avatarList.appendChild(row);
  });
}

async function refreshAvatars(selectedValue = null) {
  try {
    const response = await fetch("/avatars");
    const data = await response.json();
    avatars = data.avatars || [];
    renderAvatarSelect(selectedValue);
    renderAvatarList();
  } catch (error) {
    setStatus("Could not load avatars.", true);
  }
}

async function addAvatar() {
  const name = avatarInput.value.trim();
  if (!name) {
    setStatus("Enter an avatar name.", true);
    return;
  }

  try {
    const response = await fetch("/avatars", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Failed to add avatar.");
    }

    avatars = data.avatars || [];
    avatarInput.value = "";
    renderAvatarSelect(name);
    renderAvatarList();
    setStatus("Avatar saved.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function deleteAvatar(name) {
  try {
    const response = await fetch("/avatars", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Failed to delete avatar.");
    }

    avatars = data.avatars || [];
    renderAvatarSelect();
    renderAvatarList();
    setStatus("Avatar removed.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

function updateCardCount() {
  const count = cardsContainer.querySelectorAll(".video-card").length;
  cardCount.textContent = `${count} card${count === 1 ? "" : "s"}`;
}

function updateCardTitles() {
  const cards = cardsContainer.querySelectorAll(".video-card");
  cards.forEach((card, index) => {
    const label = card.querySelector(".card-title");
    label.textContent = `Video ${index + 1}`;
  });
}

function updateScriptStats(card) {
  const scriptInput = card.querySelector(".scriptInput");
  const stats = card.querySelector(".scriptStats");
  const words = wordCount(scriptInput.value);
  const chars = scriptInput.value.length;
  stats.textContent = `${words} words · ${chars} chars`;
}

function addCard(title = "", script = "") {
  const card = document.createElement("div");
  card.className = "video-card";

  const head = document.createElement("div");
  head.className = "card-head";

  const label = document.createElement("div");
  label.className = "card-title";

  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "ghost small";
  removeBtn.textContent = "Remove";
  removeBtn.addEventListener("click", () => {
    card.remove();
    if (cardsContainer.querySelectorAll(".video-card").length === 0) {
      addCard();
    }
    updateCardTitles();
    updateCardCount();
  });

  head.appendChild(label);
  head.appendChild(removeBtn);

  const titleField = document.createElement("label");
  titleField.className = "field";
  const titleLabel = document.createElement("span");
  titleLabel.textContent = "Title";
  const titleInput = document.createElement("input");
  titleInput.type = "text";
  titleInput.className = "titleInput";
  titleInput.placeholder = "Example: Intro Scene";
  titleInput.value = title;
  titleField.appendChild(titleLabel);
  titleField.appendChild(titleInput);

  const scriptField = document.createElement("label");
  scriptField.className = "field";
  const scriptLabel = document.createElement("span");
  scriptLabel.textContent = "Script";
  const scriptInput = document.createElement("textarea");
  scriptInput.className = "scriptInput";
  scriptInput.placeholder = "Paste your script here...";
  scriptInput.value = script;
  const stats = document.createElement("div");
  stats.className = "helper scriptStats";

  scriptInput.addEventListener("input", () => updateScriptStats(card));

  scriptField.appendChild(scriptLabel);
  scriptField.appendChild(scriptInput);
  scriptField.appendChild(stats);

  card.appendChild(head);
  card.appendChild(titleField);
  card.appendChild(scriptField);

  cardsContainer.appendChild(card);
  updateScriptStats(card);
  updateCardTitles();
  updateCardCount();
}

addCardBtn.addEventListener("click", () => {
  addCard();
  setStatus("Added a new video card.");
});

avatarAddBtn.addEventListener("click", addAvatar);
avatarInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    addAvatar();
  }
});

startBtn.addEventListener("click", async () => {
  const avatar = avatarSelect.value.trim();
  if (!avatar) {
    setStatus("Select an avatar before starting.", true);
    return;
  }

  const cards = Array.from(cardsContainer.querySelectorAll(".video-card"));
  const items = cards.map((card, index) => {
    const title = card.querySelector(".titleInput").value.trim();
    const script = card.querySelector(".scriptInput").value.trim();
    return {
      title: title || `Video ${index + 1}`,
      script,
    };
  });

  const emptyScripts = items.filter((item) => !item.script);
  if (emptyScripts.length > 0) {
    setStatus("Every card needs a script before starting.", true);
    return;
  }

  const payload = {
    project_name: projectName.value.trim() || "Pasted Scripts",
    avatar,
    config: {
      quality: qualitySelect.value,
      fps: fpsSelect.value,
      subtitles: subtitlesSelect.value,
    },
    items,
  };

  startBtn.disabled = true;
  startBtn.textContent = "Starting...";
  setStatus("Launching automation. Keep this page open.");

  try {
    const response = await fetch("/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Failed to start automation.");
    }

    setStatus("Automation started. Check the terminal for progress.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    startBtn.disabled = false;
    startBtn.textContent = "Start automation";
  }
});

addCard();
renderAvatarSelect();
renderAvatarList();
refreshAvatars();
