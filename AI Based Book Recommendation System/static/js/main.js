// Basic client-side handlers for signup/login and recommendations
document.addEventListener("DOMContentLoaded", function () {
  // handle signup form if present
  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      const form = e.target;
      const data = {
        name: form.name.value,
        email: form.email.value,
        password: form.password.value
      };
      const msg = document.getElementById("signupMsg");
      msg.textContent = "Signing up...";
      try {
        const res = await fetch("/signup", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify(data)
        });
        const json = await res.json();
        if (json.success) {
          msg.textContent = "Registered. Redirecting...";
          window.location = "/";
        } else {
          msg.textContent = json.message || "Signup failed.";
        }
      } catch (err) {
        msg.textContent = "Network error.";
      }
    });
  }

  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      const form = e.target;
      const data = {
        email: form.email.value,
        password: form.password.value
      };
      const msg = document.getElementById("loginMsg");
      msg.textContent = "Signing in...";
      try {
        const res = await fetch("/login", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify(data)
        });
        const json = await res.json();
        if (json.success) {
          msg.textContent = "Logged in. Redirecting...";
          const params = new URLSearchParams(window.location.search);
          const next = params.get("next") || "/";
          window.location = next;
        } else {
          msg.textContent = json.message || "Login failed.";
        }
      } catch (err) {
        msg.textContent = "Network error.";
      }
    });
  }

  // recommend similar (placeholder)
  document.querySelectorAll(".recommend-btn").forEach(btn => {
    btn.addEventListener("click", function () {
      const id = btn.getAttribute("data-id");
      const recoList = document.getElementById("recoList");
      // placeholder logic - replace with call to your recommendation API later
      recoList.innerHTML = `<p>Books similar to book id ${id}:</p>
      <ul>
        <li>Suggested Book A</li>
        <li>Suggested Book B</li>
      </ul>`;
      window.scrollTo({top: recoList.offsetTop - 10, behavior: "smooth"});
    });
  });

  // optional: small auth-status check to update UI later
  fetch("/api/auth-status").then(r => r.json()).then(json => {
    // not used now but available for progressive enhancement
    console.log("auth", json);
  });
});
