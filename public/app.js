const DOM = {
  overlay: document.getElementById("login-overlay"),
  form: document.getElementById("login-form"),
  tokenInput: document.getElementById("access-token"),
  loginBtn: document.getElementById("login-btn"),
  btnText: document.querySelector(".btn-text"),
  spinner: document.querySelector(".spinner"),
  errorMsg: document.getElementById("login-error"),

  appContainer: document.getElementById("app-container"),
  dashView: document.getElementById("dashboard-view"),
  detailView: document.getElementById("course-detail-view"),

  coursesGrid: document.getElementById("courses-grid"),
  searchInput: document.getElementById("course-search"),
  logoutBtn: document.getElementById("logout-btn"),

  backBtn: document.getElementById("back-btn"),
  detailTitle: document.getElementById("detail-course-title"),
  currContainer: document.getElementById("curriculum-container"),
};

let state = {
  token: localStorage.getItem("udemy_token") || null,
  courses: [],
  currentCourse: null,
};

// --- Initialization ---
function init() {
  if (state.token) {
    verifyTokenAndLoad();
  }

  DOM.form.addEventListener("submit", handleLogin);
  DOM.logoutBtn.addEventListener("click", handleLogout);
  DOM.backBtn.addEventListener("click", () => switchView(DOM.dashView));
  DOM.searchInput.addEventListener("input", handleSearch);
}

// --- JS API Wrapper ---
async function api(endpoint, options = {}) {
  const headers = { Authorization: state.token, ...options.headers };
  const res = await fetch(`/api/${endpoint}`, { ...options, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "API Error");
  return data;
}

// --- Auth Handling ---
async function handleLogin(e) {
  if (e) e.preventDefault();
  const token = DOM.tokenInput.value.trim();
  if (!token) return;

  setLoading(true);
  DOM.errorMsg.classList.add("hidden");

  try {
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_token: token }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail);

    state.token = token;
    localStorage.setItem("udemy_token", token);
    loadCourses();
  } catch (err) {
    DOM.errorMsg.textContent = err.message;
    DOM.errorMsg.classList.remove("hidden");
    setLoading(false);
  }
}

async function verifyTokenAndLoad() {
  DOM.tokenInput.value = state.token;
  handleLogin();
}

function handleLogout() {
  state.token = null;
  localStorage.removeItem("udemy_token");
  DOM.appContainer.classList.add("hidden");
  DOM.overlay.classList.add("active");
  DOM.tokenInput.value = "";
}

function switchView(view) {
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.remove("active"));
  view.classList.remove("hidden");
  // slight delay for css transitions
  setTimeout(() => view.classList.add("active"), 10);
}

function setLoading(isLoading) {
  if (isLoading) {
    DOM.btnText.classList.add("hidden");
    DOM.spinner.classList.remove("hidden");
    DOM.loginBtn.disabled = true;
  } else {
    DOM.btnText.classList.remove("hidden");
    DOM.spinner.classList.add("hidden");
    DOM.loginBtn.disabled = false;
  }
}

// --- Courses Flow ---
async function loadCourses() {
  try {
    const data = await api("courses");
    state.courses = data.courses;
    renderCourses(state.courses);

    DOM.overlay.classList.remove("active");
    DOM.appContainer.classList.remove("hidden");
    switchView(DOM.dashView);
  } catch (err) {
    handleLogout();
    DOM.errorMsg.textContent = "Session expired. Please login again.";
    DOM.errorMsg.classList.remove("hidden");
  } finally {
    setLoading(false);
  }
}

function renderCourses(courses) {
  DOM.coursesGrid.innerHTML = "";
  if (courses.length === 0) {
    DOM.coursesGrid.innerHTML =
      '<p style="color:var(--text-sec); grid-column: 1/-1;">No courses found.</p>';
    return;
  }

  courses.forEach((course) => {
    const card = document.createElement("div");
    card.className = "course-card";
    card.innerHTML = `
            <div class="course-title">${course.title}</div>
            <div class="course-meta">ID: ${course.id}</div>
        `;
    card.addEventListener("click", () => loadCurriculum(course));
    DOM.coursesGrid.appendChild(card);
  });
}

function handleSearch(e) {
  const term = e.target.value.toLowerCase();
  const filtered = state.courses.filter((c) =>
    c.title.toLowerCase().includes(term),
  );
  renderCourses(filtered);
}

// --- Curriculum Flow ---
async function loadCurriculum(course) {
  state.currentCourse = course;
  DOM.detailTitle.textContent = course.title;
  switchView(DOM.detailView);

  DOM.currContainer.innerHTML = `
        <div class="curr-loading">
            <div class="spinner large"></div>
            <p>Fetching curriculum chapters...</p>
        </div>
    `;

  try {
    const data = await api(`curriculum/${course.id}`);
    renderCurriculum(data.curriculum);
  } catch (err) {
    DOM.currContainer.innerHTML = `<p class="error-msg">Error: ${err.message}</p>`;
  }
}

function getIcon(type) {
  if (type === "Video") return "▶️";
  if (type === "Article") return "📄";
  if (type === "Quiz" || type === "practice") return "❓";
  return "📎";
}

function renderCurriculum(items) {
  DOM.currContainer.innerHTML = "";

  let currentChapterDiv = null;
  let lectureList = null;

  items.forEach((item) => {
    if (item._class === "chapter") {
      currentChapterDiv = document.createElement("div");
      currentChapterDiv.className = "chapter-box";

      const title = document.createElement("h3");
      title.className = "chapter-title";
      title.textContent = `Chapter ${item.object_index || "*"}: ${item.title}`;
      currentChapterDiv.appendChild(title);

      lectureList = document.createElement("ul");
      lectureList.className = "lecture-list";
      currentChapterDiv.appendChild(lectureList);

      DOM.currContainer.appendChild(currentChapterDiv);
    } else if (
      (item._class === "lecture" ||
        item._class === "quiz" ||
        item._class === "practice") &&
      lectureList
    ) {
      const li = document.createElement("li");
      li.className = "lecture-item";

      const type = item.asset
        ? item.asset.asset_type
        : item._class === "quiz"
          ? "Quiz"
          : "Article";
      const icon = getIcon(type);

      let actionHtml = "";
      let hasAttachments =
        item.supplementary_assets && item.supplementary_assets.length > 0;

      // Render Video Download Button
      if (type === "Video") {
        actionHtml += `<button class="dl-btn" onclick="downloadLecture(${state.currentCourse.id}, ${item.id}, '${(item.title || "Video").replace(/'/g, "\\'")}')">⬇️ Video</button>`;
      } else if (type === "Article" || type === "Quiz") {
        actionHtml += `<span class="badge-locked">${type}</span>`;
      }

      // Render Attachment Download Buttons
      if (hasAttachments) {
        item.supplementary_assets.forEach((supp) => {
          actionHtml += `<button class="dl-btn badge-attachment" onclick="downloadAttachment(${state.currentCourse.id}, ${item.id}, ${supp.id}, '${(supp.filename || supp.title || "Asset").replace(/'/g, "\\'")}')">📎 ${supp.title || "Asset"}</button>`;
        });
      }

      li.innerHTML = `
                <div class="lecture-info">
                    <span class="lecture-icon">${icon}</span>
                    <span>${item.object_index || "*"}. ${item.title}</span>
                </div>
                <div class="lecture-actions">
                    ${actionHtml}
                </div>
            `;
      lectureList.appendChild(li);
    }
  });
}

// Global Download Functions
window.downloadLecture = async function (courseId, lectureId, title) {
  const btn = event.currentTarget;
  const originalText = btn.innerHTML;

  try {
    btn.disabled = true;
    btn.innerHTML = "⏳ Resolving...";

    const data = await api(`resolve-download/${courseId}/${lectureId}`);

    if (data.status === "drm_locked") {
      btn.outerHTML = `<span class="badge-locked">🔒 DRM Protected</span>`;
      return;
    }

    if (data.status === "success" && data.url) {
      btn.innerHTML = "⬇️ Starting...";
      window.open(data.url, "_blank");
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      }, 2000);
    }
  } catch (err) {
    alert(err.message);
    btn.innerHTML = "❌ Failed";
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }, 3000);
  }
};

window.downloadAttachment = async function (
  courseId,
  lectureId,
  assetId,
  filename,
) {
  const btn = event.currentTarget;
  const originalText = btn.innerHTML;

  try {
    btn.disabled = true;
    btn.innerHTML = "⏳ ...";

    const data = await api(
      `resolve-attachment/${courseId}/${lectureId}/${assetId}`,
    );

    if (data.status === "success" && data.url) {
      btn.innerHTML = "✅ Launching...";
      window.open(data.url, "_blank");
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      }, 2000);
    }
  } catch (err) {
    alert(err.message);
    btn.innerHTML = "❌ Failed";
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }, 3000);
  }
};

// Start app
init();
