document.addEventListener("DOMContentLoaded", async () => {
  const loadingState = document.getElementById("loading-state");
  const missingState = document.getElementById("missing-state");
  const foundState = document.getElementById("found-state");

  const loginBtn = document.getElementById("login-udemy-btn");
  const connectBtn = document.getElementById("connect-btn");

  let extractedToken = null;
  const UDEMY_URL = "https://www.udemy.com";
  const TARGET_SA_URL = "https://udemy-saver.vercel.app";

  function switchState(stateEl) {
    [loadingState, missingState, foundState].forEach((el) =>
      el.classList.remove("active"),
    );
    stateEl.classList.add("active");
  }

  try {
    // Attempt to get the cookie
    const cookie = await chrome.cookies.get({
      url: UDEMY_URL,
      name: "access_token",
    });

    if (cookie && cookie.value) {
      extractedToken = cookie.value;
      switchState(foundState);
    } else {
      switchState(missingState);
    }
  } catch (err) {
    console.error("Cookie extraction error:", err);
    switchState(missingState);
  }

  // Handle Login to Udemy
  loginBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: UDEMY_URL });
  });

  // Handle Launch & Connect
  connectBtn.addEventListener("click", async () => {
    // 1. Find if the vercel app is already open
    const tabs = await chrome.tabs.query({
      url: "*://udemy-saver.vercel.app/*",
    });

    let targetTab = null;
    if (tabs.length > 0) {
      // Find the specific tab if possible
      targetTab =
        tabs.find((t) => t.url.includes("udemy-saver.vercel.app")) || tabs[0];
      await chrome.tabs.update(targetTab.id, { active: true });
    } else {
      // Create new tab
      targetTab = await chrome.tabs.create({
        url: `${TARGET_SA_URL}/app/index.html`,
      });
    }

    // 2. Inject the token directly into localStorage on the target tab
    // We execute a script in the context of the target tab.
    await chrome.scripting.executeScript({
      target: { tabId: targetTab.id },
      func: (token) => {
        const XOR_KEY = "lone_wolf_udemy_saver_2026";
        let result = "";
        for (let i = 0; i < token.length; i++) {
          result += String.fromCharCode(
            token.charCodeAt(i) ^ XOR_KEY.charCodeAt(i % XOR_KEY.length),
          );
        }
        localStorage.setItem("udemy_sec_data", btoa(result));
        localStorage.removeItem("udemy_token"); // Clean up old unencrypted token
        // Force reload so the app picks up the token immediately
        window.location.reload();
      },
      args: [extractedToken],
    });

    // 3. Close the popup
    window.close();
  });
});
