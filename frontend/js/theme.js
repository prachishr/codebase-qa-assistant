(function () {
    const savedTheme = localStorage.getItem("codebase_qa_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);

    function updateIcons() {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
        const toggles = document.querySelectorAll(".theme-toggle");
        toggles.forEach((toggle) => {
            const icon = toggle.querySelector(".theme-icon") || toggle;
            if (currentTheme === "light") {
                icon.textContent = "🌙";
                toggle.setAttribute("title", "Switch to Dark Theme");
                toggle.setAttribute("aria-label", "Switch to Dark Theme");
            } else {
                icon.textContent = "☀️";
                toggle.setAttribute("title", "Switch to Light Theme");
                toggle.setAttribute("aria-label", "Switch to Light Theme");
            }
        });
    }

    window.toggleTheme = function () {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
        const nextTheme = currentTheme === "light" ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", nextTheme);
        localStorage.setItem("codebase_qa_theme", nextTheme);
        updateIcons();
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            updateIcons();
            document.querySelectorAll(".theme-toggle").forEach((btn) => {
                btn.addEventListener("click", window.toggleTheme);
            });
        });
    } else {
        updateIcons();
        document.querySelectorAll(".theme-toggle").forEach((btn) => {
            btn.addEventListener("click", window.toggleTheme);
        });
    }
})();
