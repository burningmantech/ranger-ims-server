"use strict";
// See the file COPYRIGHT for copyright information.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// Set the theme immediately, before the rest of the page loads, so that there's
// no flickering. We'll then come back later to applyTheme, which sets the navbar
// dropdown icons.
setTheme(getPreferredTheme());
document.addEventListener("DOMContentLoaded", applyTheme);
//
// Apply the HTML theme, light or dark or default.
//
// Adapted from https://getbootstrap.com/docs/5.3/customize/color-modes/#javascript
// Under Creative Commons Attribution 3.0 Unported License
function getStoredTheme() {
    return localStorage.getItem("theme");
}
function setStoredTheme(theme) {
    localStorage.setItem("theme", theme);
}
function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored != null) {
        return stored;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function setTheme(theme) {
    if (theme === "auto") {
        theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.setAttribute("data-bs-theme", theme);
}
function applyTheme() {
    setTheme(getPreferredTheme());
    function showActiveTheme(theme, focus = false) {
        const themeSwitcher = document.querySelector("#bd-theme");
        if (!themeSwitcher) {
            return;
        }
        const themeSwitcherText = document.querySelector("#bd-theme-text");
        const activeThemeIcon = document.querySelector(".theme-icon-active use");
        const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`);
        const svgOfActiveBtn = btnToActive.querySelector("svg use").href.baseVal;
        document.querySelectorAll("[data-bs-theme-value]").forEach((element) => {
            element.classList.remove("active");
            element.setAttribute("aria-pressed", "false");
        });
        btnToActive.classList.add("active");
        btnToActive.setAttribute("aria-pressed", "true");
        if (svgOfActiveBtn) {
            activeThemeIcon.href.baseVal = svgOfActiveBtn;
        }
        if (themeSwitcherText) {
            const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset["bsThemeValue"]})`;
            themeSwitcher.setAttribute("aria-label", themeSwitcherLabel);
        }
        if (focus) {
            themeSwitcher.focus();
        }
    }
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
        const storedTheme = getStoredTheme();
        if (storedTheme !== "light" && storedTheme !== "dark") {
            setTheme(getPreferredTheme());
        }
    });
    showActiveTheme(getPreferredTheme());
    document.querySelectorAll("[data-bs-theme-value]").forEach((toggle) => {
        toggle.addEventListener("click", function (_e) {
            const theme = toggle.getAttribute("data-bs-theme-value");
            if (theme) {
                setStoredTheme(theme);
                setTheme(theme);
                showActiveTheme(theme, true);
            }
        });
    });
}
