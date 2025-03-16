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
    const storedTheme = getStoredTheme();
    if (storedTheme) {
        return storedTheme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function setTheme(theme) {
    if (theme === "auto") {
        document.documentElement.setAttribute("data-bs-theme", (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
    }
    else {
        document.documentElement.setAttribute("data-bs-theme", theme);
    }
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
        const svgOfActiveBtn = btnToActive?.querySelector("svg use")?.getAttribute("href") ?? null;
        document.querySelectorAll("[data-bs-theme-value]").forEach(element => {
            element.classList.remove("active");
            element.setAttribute("aria-pressed", "false");
        });
        btnToActive.classList.add("active");
        btnToActive.setAttribute("aria-pressed", "true");
        if (svgOfActiveBtn) {
            activeThemeIcon?.setAttribute("href", svgOfActiveBtn);
        }
        if (themeSwitcherText) {
            const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset.bsThemeValue})`;
            themeSwitcher.setAttribute("aria-label", themeSwitcherLabel);
        }
        if (focus) {
            themeSwitcher.focus();
        }
    }
    ;
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
        const storedTheme = getStoredTheme();
        if (storedTheme !== "light" && storedTheme !== "dark") {
            setTheme(getPreferredTheme());
        }
    });
    showActiveTheme(getPreferredTheme());
    document.querySelectorAll("[data-bs-theme-value]").forEach(toggle => {
        toggle.addEventListener("click", () => {
            const theme = toggle.getAttribute("data-bs-theme-value");
            if (theme) {
                setStoredTheme(theme);
                setTheme(theme);
                showActiveTheme(theme, true);
            }
        });
    });
}
// Set the theme immediately, before the rest of the page loads. We need to come back later
// to invoke applyTheme(), as that will only work once the navbar has been drawn (with its
// dropdown theme selector.
setTheme(getPreferredTheme());
//
// HTML encoding
//
// It seems ridiculous that this isn't standard in JavaScript
// It is certainly ridiculous to involve the DOM, but on the other hand, the
// browser will implement this correctly, and any solution using .replace()
// will be buggy.  And this will be fast.  But still, this is weak.
let _domTextAreaForHaxxors = document.createElement("textarea");
// Convert text to HTML.
function textAsHTML(text) {
    _domTextAreaForHaxxors.textContent = text;
    return _domTextAreaForHaxxors.innerHTML;
}
// Convert HTML to text.
function htmlAsText(html) {
    _domTextAreaForHaxxors.innerHTML = html;
    return _domTextAreaForHaxxors.textContent;
}
const integerRegExp = /^\d+$/;
//
// URL substitution
//
function urlReplace(url) {
    if (eventID) {
        url = url.replace("<event_id>", eventID);
    }
    return url;
}
//
// Arrays
//
// Build an array from a range.
function range(start, end, step) {
    if (step == null) {
        step = 1;
    }
    else if (step === 0) {
        throw new RangeError("step = 0");
    }
    return Array(end - start)
        .join("a")
        .split("a")
        .map(function (val, i) { return (i * step) + start; });
}
function compareReportEntries(a, b) {
    if (a.created < b.created) {
        return -1;
    }
    if (a.created > b.created) {
        return 1;
    }
    if (a.system_entry && !b.system_entry) {
        return -1;
    }
    if (!a.system_entry && b.system_entry) {
        return 1;
    }
    if (a.text < b.text) {
        return -1;
    }
    if (a.text > b.text) {
        return 1;
    }
    return 0;
}
//
// Request making
//
async function fetchJsonNoThrow(url, init) {
    if (init == null) {
        init = {};
    }
    init.headers = new Headers(init.headers);
    init.headers.set("Accept", "application/json");
    if (init.body != null) {
        init.method = "POST";
        if (init.body.constructor.name === "FormData") {
            let size = 0;
            const fd = init.body;
            for (const [k, v] of fd.entries()) {
                size += k.length;
                if (v instanceof Blob) {
                    size += v.size;
                }
                else {
                    size += v.length;
                }
            }
            // Large file uploads are a problem, since the server locks up the Reactor thread
            // until the file is done uploading. Also, a large enough upload (multi-gig) can
            // cause the server to consume all the memory on the system and require a manual
            // restart. Yuck.
            if (size > 20 * 1024 * 1024) {
                return { resp: null, json: null, err: "Please keep data uploads small, " +
                        "ideally under 10 MB" };
            }
            // don't JSONify, don't set a Content-Type (fetch does it automatically for FormData)
        }
        else {
            // otherwise assume body is supposed to be json
            init.headers.set("Content-Type", "application/json");
            if (typeof init.body !== "string") {
                init.body = JSON.stringify(init.body);
            }
        }
    }
    let response = null;
    try {
        response = await fetch(url, init);
        if (!response.ok) {
            return { resp: response, json: null, err: `${response.statusText} (${response.status})` };
        }
        let json = null;
        if (response.headers.get("content-type") === "application/json") {
            json = await response.json();
        }
        return { resp: response, json: json, err: null };
    }
    catch (err) {
        return { resp: response, json: null, err: err.message };
    }
}
//
// Generic string formatting
//
// Pad a string representing an integer to two digits.
function padTwo(value) {
    if (value == null) {
        return "?";
    }
    const val = value.toString();
    if (val.length === 1) {
        return "0" + val;
    }
    return val;
}
// Convert a minute (0-60) into a value used by IMS form inputs.
// That is: round to the nearest multiple of 5 and pad to two digits.
function normalizeMinute(minute) {
    minute = Math.round(minute / 5) * 5;
    while (minute > 60) {
        minute -= 60;
    }
    return padTwo(minute);
}
// Apparently some implementations of Number.parseInt don't reliably use base
// 10 by default (eg. when encountering leading zeroes).
function parseInt(stringInt) {
    return Number.parseInt(stringInt, 10);
}
//
// Elements
//
// Create a <time> element from a date.
function timeElement(date) {
    const timeStampContainer = document.createElement("time");
    timeStampContainer.setAttribute("datetime", date.toISOString());
    timeStampContainer.textContent = fullDateTime.format(date);
    return timeStampContainer;
}
// Disable an element
function disable(elements) {
    for (const e of elements) {
        e.setAttribute("disabled", "");
    }
}
// Enable an element
function enable(elements) {
    for (const e of elements) {
        e.removeAttribute("disabled");
    }
}
// Disable editing for an element
function disableEditing() {
    disable(document.querySelectorAll(".form-control"));
    // these forms don't actually exist
    // disable(document.querySelectorAll("#entries-form input,select,textarea,button"));
    // disable(document.querySelectorAll("#attach-file-form input,select,textarea,button"));
    enable(document.querySelectorAll("input[type=search]")); // Don't disable search fields
    document.documentElement.classList.add("no-edit");
}
// Enable editing for an element
function enableEditing() {
    enable(document.querySelectorAll(".form-control"));
    // these forms don't actually exist
    // enable(document.querySelectorAll("#entries-form input,select,textarea,button"));
    // enable(document.querySelectorAll("#attach-file-form :input,select,textarea,button"));
    document.documentElement.classList.remove("no-edit");
}
// Add an error indication to a control
function controlHasError(element) {
    // @ts-ignore JQuery
    element.parent().addClass("is-invalid");
}
// Add a success indication to a control
function controlHasSuccess(element, clearTimeout) {
    element.addClass("is-valid");
    if (clearTimeout != null) {
        // @ts-ignore JQuery
        element.delay("1000").queue(function (next) {
            controlClear(element);
            next();
        });
    }
}
// Add an error indication to a control
function controlHasErrorNoJQuery(element) {
    element.classList.add("is-invalid");
}
// Add a success indication to a control
function controlHasSuccessNoJQuery(element, clearTimeout) {
    element.classList.add("is-valid");
    if (clearTimeout != null) {
        setTimeout(() => {
            controlClearNoJQuery(element);
        }, clearTimeout);
    }
}
// Clear error/success indication from a control
function controlClear(element) {
    element.removeClass("is-invalid");
    element.removeClass("is-valid");
}
function controlClearNoJQuery(element) {
    element.classList.remove("is-invalid");
    element.classList.remove("is-valid");
}
//
// Load HTML body template.
//
async function loadBody() {
    detectTouchDevice();
    // @ts-ignore since this requires es2024, which I can't get to work with IntelliJ...
    const { promise, resolve } = Promise.withResolvers();
    // @ts-ignore some JQuery nonsense
    $("body").load(pageTemplateURL, resolve);
    await promise;
    applyTheme();
    if (typeof eventID !== "undefined") {
        for (const eventLabel of document.getElementsByClassName("event-id")) {
            eventLabel.textContent = eventID;
            eventLabel.classList.add("active-event");
        }
        const activeEventIncidents = document.getElementById("active-event-incidents");
        if (activeEventIncidents != null) {
            activeEventIncidents.setAttribute("href", urlReplace(url_viewIncidents));
            activeEventIncidents.classList.remove("hidden");
            if (window.location.pathname.startsWith(urlReplace(url_viewIncidents))) {
                activeEventIncidents.classList.add("active");
            }
        }
        const activeEventFRs = document.getElementById("active-event-field-reports");
        if (activeEventFRs != null) {
            activeEventFRs.setAttribute("href", urlReplace(url_viewFieldReports));
            activeEventFRs.classList.remove("hidden");
            if (window.location.pathname.startsWith(urlReplace(url_viewFieldReports))) {
                activeEventFRs.classList.add("active");
            }
        }
    }
}
//
// Touch device detection
//
// Add .touch or .no-touch class to top-level element if the browser is or is
// not on a touch device, respectively.
function detectTouchDevice() {
    if ("ontouchstart" in document.documentElement) {
        document.documentElement.classList.add("touch");
    }
    else {
        document.documentElement.classList.add("no-touch");
    }
}
//
// Controls
//
// Select an option element with a given value from a given select element.
function selectOptionWithValue(select, value) {
    select
        .children("option")
        .prop("selected", false);
    select
        .children("option[value='" + value + "']")
        .prop("selected", true);
}
//
// Incident data
//
// Look up a state's name given its ID.
function stateNameFromID(stateID) {
    switch (stateID) {
        case "new": return "New";
        case "on_hold": return "On Hold";
        case "dispatched": return "Dispatched";
        case "on_scene": return "On Scene";
        case "closed": return "Closed";
        default:
            console.warn("Unknown incident state ID: " + stateID);
            return "Unknown";
    }
}
// Look up a state's sort key given its ID.
function stateSortKeyFromID(stateID) {
    switch (stateID) {
        case "new": return 1;
        case "on_hold": return 2;
        case "dispatched": return 3;
        case "on_scene": return 4;
        case "closed": return 5;
        default:
            console.warn("Unknown incident state ID: " + stateID);
            return undefined;
    }
}
// Look up a concentric street's name given its ID.
function concentricStreetFromID(streetID) {
    if (streetID == null || typeof concentricStreetNameByID === "undefined") {
        return "";
    }
    const name = concentricStreetNameByID[streetID];
    if (name == null) {
        console.warn("Unknown street ID: " + streetID);
        return "";
    }
    return name;
}
// Return the state ID for a given incident.
function stateForIncident(incident) {
    // Data from 2014+ should have incident.state set.
    if (incident.state !== undefined) {
        return incident.state;
    }
    console.warn("Unknown state for incident: " + incident);
    return "Unknown";
}
// Return a summary for a given incident.
function summarizeIncident(incident) {
    if (incident.summary) {
        return incident.summary;
    }
    // Get the first line of the first report entry.
    for (const reportEntry of incident.report_entries ?? []) {
        if (reportEntry.system_entry) {
            // Don't use a system-generated entry in the summary
            continue;
        }
        const lines = reportEntry.text.split("\n");
        for (const line of lines) {
            if (line) {
                return line;
            }
        }
    }
    return "";
}
// Return a summary for a given field report.
function summarizeFieldReport(report) {
    return summarizeIncident(report);
}
// Get author for incident
function incidentAuthor(incident) {
    for (const entry of incident.report_entries ?? []) {
        if (entry.author) {
            return entry.author;
        }
    }
    return "(none)";
}
// Get author for field report
function fieldReportAuthor(report) {
    return incidentAuthor(report);
}
// Render incident as a string
function incidentAsString(incident) {
    if (incident.number == null) {
        return "New Incident";
    }
    return `#${incident.number}: ${summarizeIncident(incident)} (${incident.event})`;
}
// Render field report as a string
function fieldReportAsString(report) {
    if (report.number == null) {
        return "New Field Report";
    }
    return `FR #${report.number} (${fieldReportAuthor(report)}): ` +
        `${summarizeFieldReport(report)} (${report.event})`;
}
let eventFieldReports = null;
// Return all user-entered report text for a given incident as a single string.
function reportTextFromIncident(incidentOrFR) {
    const texts = [];
    if (incidentOrFR.summary != null) {
        texts.push(incidentOrFR.summary);
    }
    for (const reportEntry of incidentOrFR.report_entries ?? []) {
        // Skip system entries
        if (reportEntry.system_entry) {
            continue;
        }
        const text = reportEntry.text;
        if (text != null) {
            texts.push(text);
        }
    }
    // Incidents page loads all field reports for the event
    if (eventFieldReports != null && "field_reports" in incidentOrFR) {
        for (const reportNumber of incidentOrFR.field_reports ?? []) {
            const report = eventFieldReports[reportNumber];
            const reportText = reportTextFromIncident(report);
            texts.push(reportText);
        }
    }
    return texts.join(" ");
}
// Return a short description for a given location.
function shortDescribeLocation(location) {
    if (location == null) {
        return undefined;
    }
    const locationBits = [];
    if (location.name != null) {
        locationBits.push(location.name);
    }
    switch (location.type) {
        case undefined:
        // Fall through to "text" case
        case "text":
            if (location.description != null) {
                locationBits.push(" ");
                locationBits.push(location.description);
            }
            break;
        case "garett":
            if (location.radial_hour || location.radial_minute || location.concentric) {
                locationBits.push(" (");
                locationBits.push(padTwo(location.radial_hour));
                locationBits.push(":");
                locationBits.push(padTwo(location.radial_minute));
                locationBits.push("@");
                locationBits.push(concentricStreetFromID(location.concentric));
                locationBits.push(")");
            }
            break;
        default:
            locationBits.push("Unknown location type:" + location.type);
            break;
    }
    return locationBits.join("");
}
//
// DataTables rendering
//
function renderSafeSorted(strings) {
    const safe = strings.map(s => textAsHTML(s));
    const copy = safe.toSorted((a, b) => a.localeCompare(b));
    return copy.join(", ");
}
function renderIncidentNumber(incidentNumber, type, incident) {
    switch (type) {
        case "display":
            return incidentNumber;
        case "filter":
            return incidentNumber;
        case "type":
        case "sort":
            return incidentNumber;
    }
    return undefined;
}
// e.g. "Wed, 8/28"
const shortDate = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "numeric",
    day: "2-digit",
    // timeZone not specified; will use user's timezone
});
// e.g. "19:21"
const shortTime = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    hour12: false,
    minute: "numeric",
    // timeZone not specified; will use user's timezone
});
// e.g. "19:21"
const shortTimeSec = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    hour12: false,
    minute: "numeric",
    second: "numeric",
    // timeZone not specified; will use user's timezone
});
// e.g. "Thu, Aug 29, 2024, 19:11:04 EDT"
const fullDateTime = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    hour12: false,
    minute: "numeric",
    second: "numeric",
    timeZoneName: "short",
    // timeZone not specified; will use user's timezone
});
function renderDate(date, type, incident) {
    const d = Date.parse(date);
    switch (type) {
        case "display":
            return shortDate.format(d) + "<wbr />@" + shortTime.format(d);
        case "filter":
            return shortDate.format(d) + " " + shortTime.format(d);
        case "type":
        case "sort":
            return d;
    }
    return undefined;
}
function renderState(state, type, incident) {
    if (state == null) {
        state = stateForIncident(incident);
    }
    switch (type) {
        case "display":
            return textAsHTML(stateNameFromID(state));
        case "filter":
            return stateNameFromID(state);
        case "type":
            return state;
        case "sort":
            return stateSortKeyFromID(state);
    }
    return undefined;
}
function renderLocation(data, type, incident) {
    if (data == null) {
        data = "";
    }
    switch (type) {
        case "display":
            return textAsHTML(shortDescribeLocation(data) ?? "");
        case "filter":
        case "sort":
            return shortDescribeLocation(data);
        case "type":
            return "";
    }
    return undefined;
}
function renderSummary(data, type, incident) {
    switch (type) {
        case "display":
            return textAsHTML(summarizeIncident(incident));
        case "sort":
            return summarizeIncident(incident);
        case "filter":
            return reportTextFromIncident(incident);
        case "type":
            return "";
    }
    return undefined;
}
//
// Populate report entry text
//
function reportEntryElement(entry) {
    // Build a container for the entry
    // @ts-ignore JQuery
    const entryContainer = $("<div />", { "class": "report_entry" });
    const strikable = !entry.system_entry;
    if (entry.system_entry) {
        entryContainer.addClass("report_entry_system");
    }
    else if (entry.stricken) {
        entryContainer.addClass("report_entry_stricken");
    }
    else {
        entryContainer.addClass("report_entry_user");
    }
    if (entry.merged) {
        entryContainer.addClass("report_entry_merged");
    }
    // Add the timestamp and author, with a Strike/Unstrike button
    // @ts-ignore JQuery
    const metaDataContainer = $("<p />", { "class": "report_entry_metadata" });
    if (strikable) {
        let onclick = "";
        if (typeof incidentNumber !== "undefined") {
            // we're on the incident page
            if (entry.merged) {
                // this is an entry from a field report, as shown on the incident page
                onclick = "setStrikeFieldReportEntry(" + entry.merged + ", " + entry.id + ", " + !entry.stricken + ");";
            }
            else {
                // this is an incident entry on the incident page
                onclick = "setStrikeIncidentEntry(" + incidentNumber + ", " + entry.id + ", " + !entry.stricken + ");";
            }
        }
        else if (typeof fieldReportNumber !== "undefined") {
            // we're on the field report page
            onclick = "setStrikeFieldReportEntry(" + fieldReportNumber + ", " + entry.id + ", " + !entry.stricken + ");";
        }
        // @ts-ignore JQuery
        const strikeContainer = $("<button />", { "onclick": onclick });
        strikeContainer.addClass("badge btn btn-danger remove-badge float-end");
        strikeContainer.text(entry.stricken ? "Unstrike" : "Strike");
        // TODO: it'd be nice to have a strikethrough icon rather than the word "Strike".
        //  The code below should almost do it, but I can't get the button to just show
        //  the icon by itself.
        // const iconContainer = $("<svg />", {"class": "bi"});
        // iconContainer.append($("<use />", {"href": "#strikethrough"}));
        // strikeContainer.append($("<span class='d-none'>Strike</span>", {"class": "d-none"}));
        // strikeContainer.append(iconContainer);
        metaDataContainer.append(strikeContainer);
    }
    const timeStampContainer = timeElement(new Date(entry.created));
    timeStampContainer.classList.add("report_entry_timestamp");
    metaDataContainer.append([timeStampContainer, ", "]);
    let author = entry.author;
    if (author == null) {
        author = "(unknown)";
    }
    // @ts-ignore JQuery
    const authorContainer = $("<span />");
    authorContainer.text(entry.author);
    authorContainer.addClass("report_entry_author");
    metaDataContainer.append(author);
    if (entry.merged) {
        metaDataContainer.append(" ");
        // @ts-ignore JQuery
        const link = $("<a />");
        link.text("field report #" + entry.merged);
        link.attr("href", urlReplace(url_viewFieldReports) + entry.merged);
        metaDataContainer.append("(via ");
        metaDataContainer.append(link);
        metaDataContainer.append(")");
        metaDataContainer.addClass("report_entry_source");
    }
    metaDataContainer.append(":");
    entryContainer.append(metaDataContainer);
    // Add report text
    const lines = entry.text.split("\n");
    for (const line of lines) {
        // @ts-ignore JQuery
        const textContainer = $("<p />", { "class": "report_entry_text" });
        textContainer.text(line);
        entryContainer.append(textContainer);
    }
    if (entry.has_attachment && incidentNumber != null) {
        const url = urlReplace(url_incidentAttachmentNumber)
            .replace("<incident_number>", incidentNumber.toString())
            .replace("<attachment_number>", entry.id.toString());
        // @ts-ignore JQuery
        const attachmentLink = $("<a />", { "href": url });
        attachmentLink.text("Attached file");
        entryContainer.append(attachmentLink);
    }
    // Add a horizontal line after each entry
    // @ts-ignore JQuery
    entryContainer.append($("<hr />", { "class": "m-1" }));
    return entryContainer;
}
function drawReportEntries(entries) {
    // @ts-ignore JQuery
    const container = $("#report_entries");
    container.empty();
    if (entries) {
        for (const entry of entries) {
            container.append(reportEntryElement(entry));
        }
        container.parent().parent().removeClass("hidden");
    }
    else {
        container.parent().parent().addClass("hidden");
    }
}
function reportEntryEdited() {
    // @ts-ignore JQuery
    const text = $("#report_entry_add").val().trim();
    // @ts-ignore JQuery
    const submitButton = $("#report_entry_submit");
    submitButton.removeClass("btn-default");
    submitButton.removeClass("btn-warning");
    submitButton.removeClass("btn-danger");
    if (!text) {
        submitButton.addClass("disabled");
        submitButton.addClass("btn-default");
    }
    else {
        submitButton.removeClass("disabled");
        submitButton.addClass("btn-warning");
    }
}
// The error callback for a report entry strike call.
// This function is designed to work from either the incident
// or the field report page.
function onStrikeError(err) {
    const message = `Failed to set report entry strike status: ${err}`;
    console.log(message);
    setErrorMessage(message);
}
let registerOnStrikeSuccess = null;
async function setStrikeIncidentEntry(incidentNumber, reportEntryId, strike) {
    const url = urlReplace(url_incident_reportEntry)
        .replace("<incident_number>", incidentNumber.toString())
        .replace("<report_entry_id>", reportEntryId.toString());
    const { err } = await fetchJsonNoThrow(url, {
        body: JSON.stringify({ "stricken": strike }),
    });
    if (err != null) {
        onStrikeError(err);
    }
    else {
        registerOnStrikeSuccess();
    }
}
async function setStrikeFieldReportEntry(fieldReportNumber, reportEntryId, strike) {
    const url = urlReplace(url_fieldReport_reportEntry)
        .replace("<field_report_number>", fieldReportNumber.toString())
        .replace("<report_entry_id>", reportEntryId.toString());
    const { err } = await fetchJsonNoThrow(url, {
        body: JSON.stringify({ "stricken": strike }),
    });
    if (err != null) {
        onStrikeError(err);
    }
    else {
        registerOnStrikeSuccess();
    }
}
let registerSendEdits = null;
async function submitReportEntry() {
    // @ts-ignore JQuery
    const text = $("#report_entry_add").val().trim();
    if (!text) {
        return;
    }
    console.log("New report entry:\n" + text);
    // Disable the submit button to prevent repeat submissions
    // @ts-ignore JQuery
    $("#report_entry_submit").addClass("disabled");
    // send a dummy ID to appease the JSON parser in the server
    const { err } = await registerSendEdits({ "report_entries": [{ "text": text, "id": -1 }] });
    if (err != null) {
        // @ts-ignore JQuery
        const submitButton = $("#report_entry_submit");
        submitButton.removeClass("disabled");
        submitButton.removeClass("btn-default");
        submitButton.removeClass("btn-warning");
        submitButton.addClass("btn-danger");
        // @ts-ignore JQuery
        controlHasError($("#report_entry_add"));
        return;
    }
    // @ts-ignore JQuery
    const $textArea = $("#report_entry_add");
    // Clear the report entry
    $textArea.val("");
    controlHasSuccess($textArea, 1000);
    // Reset the submit button and its "disabled" status
    reportEntryEdited();
}
//
// Generated history display
//
function toggleShowHistory() {
    // @ts-ignore JQuery
    if ($("#history_checkbox").is(":checked")) {
        // @ts-ignore JQuery
        $("#report_entries").removeClass("hide-history");
    }
    else {
        // @ts-ignore JQuery
        $("#report_entries").addClass("hide-history");
    }
}
async function editFromElement(element, jsonKey, transform) {
    let value = element.val();
    if (transform != null) {
        value = transform(value);
    }
    // Build a JSON object representing the requested edits
    const edits = {};
    const keyPath = jsonKey.split(".");
    const lastKey = keyPath.pop();
    let current = edits;
    for (const path of keyPath) {
        const next = {};
        current[path] = next;
        current = next;
    }
    current[lastKey] = value;
    // Location must include type
    if (edits.location != null && typeof edits.location !== "string") {
        edits.location.type = "garett"; // UI only supports one type
    }
    // Send request to server
    const { err } = await registerSendEdits(edits);
    if (err != null) {
        controlHasError(element);
    }
    else {
        controlHasSuccess(element, 1000);
    }
}
async function editFromElementNoJQuery(element, jsonKey, transform) {
    let value = element.value;
    if (transform != null) {
        value = transform(value);
    }
    // Build a JSON object representing the requested edits
    const edits = {};
    const keyPath = jsonKey.split(".");
    const lastKey = keyPath.pop();
    let current = edits;
    for (const path of keyPath) {
        const next = {};
        current[path] = next;
        current = next;
    }
    current[lastKey] = value;
    // Location must include type
    if (edits.location != null && typeof edits.location !== "string") {
        edits.location.type = "garett"; // UI only supports one type
    }
    // Send request to server
    const { err } = await registerSendEdits(edits);
    if (err != null) {
        controlHasErrorNoJQuery(element);
    }
    else {
        controlHasSuccessNoJQuery(element, 1000);
    }
}
//
// EventSource
//
const incidentChannelName = "incident_update";
const fieldReportChannelName = "field_report_update";
const reattemptMinTimeMillis = 10000;
const lastSseIDKey = "last_sse_id";
// Call this from each browsing context, so that it can queue up to become a leader
// to manage the EventSource.
async function requestEventSourceLock() {
    // The "navigator.locks" API is only available over secure browsing contexts.
    // Secure contexts include HTTPS as well as non-HTTPS via localhost, so this is
    // really only when you try to connect directly to another host without TLS.
    // https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts
    if (!window.isSecureContext && typeof setErrorMessage !== "undefined") {
        setErrorMessage("You're connected through an insecure browsing context. " +
            "Background SSE updates will not work!");
        return;
    }
    function tryAcquireLock() {
        // @ts-ignore withResolves needs es2024
        const { promise, resolve } = Promise.withResolvers();
        subscribeToUpdates(resolve);
        return promise;
    }
    function waitBeforeRetry(timeMillis) {
        return new Promise(r => setTimeout(r, Math.max(0, timeMillis)));
    }
    // Infinitely attempt to reconnect to the EventSource.
    // This addresses the following issue for when IMS lives on AWS:
    // https://github.com/burningmantech/ranger-ims-server/issues/1364
    while (true) {
        const start = Date.now();
        // Acquire the lock, set up the EventSource, and start
        // broadcasting events to other browsing contexts.
        await navigator.locks.request("ims_eventsource_lock", tryAcquireLock);
        const millisSinceStart = Date.now() - start;
        await waitBeforeRetry(reattemptMinTimeMillis - millisSinceStart);
    }
}
// This starts the EventSource call and configures event listeners to propagate
// updates to BroadcastChannels. The idea is that only one browsing context should
// have an EventSource connection at any given time.
//
// The "closed" param is a callback to notify the caller that the EventSource has
// been closed.
function subscribeToUpdates(closed) {
    const eventSource = new EventSource(url_eventSource, { withCredentials: true });
    eventSource.addEventListener("open", function () {
        console.log("Event listener opened");
    }, true);
    eventSource.addEventListener("error", function () {
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log("Event listener closed");
            eventSource.close();
            closed();
        }
        else {
            // This is likely a retriable error, and EventSource will automatically
            // attempt reconnection.
            console.log("Event listener error");
        }
    }, true);
    eventSource.addEventListener("InitialEvent", function (e) {
        const previousId = localStorage.getItem(lastSseIDKey);
        if (e.lastEventId === previousId) {
            return;
        }
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        const allChannels = [
            new BroadcastChannel(incidentChannelName),
            new BroadcastChannel(fieldReportChannelName),
        ];
        for (const ch of allChannels) {
            ch.postMessage({ update_all: true });
        }
    });
    eventSource.addEventListener("Incident", function (e) {
        const send = new BroadcastChannel(incidentChannelName);
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        send.postMessage(JSON.parse(e.data));
    }, true);
    eventSource.addEventListener("FieldReport", function (e) {
        const send = new BroadcastChannel(fieldReportChannelName);
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        send.postMessage(JSON.parse(e.data));
    }, true);
}
// Set the user-visible error information on the page to the provided string.
function setErrorMessage(msg) {
    msg = "Error: (Cause: " + msg + ")";
    const errText = document.getElementById("error_text");
    if (errText) {
        errText.textContent = msg;
    }
    const errInfo = document.getElementById("error_info");
    if (errInfo) {
        errInfo.classList.remove("hidden");
        errInfo.scrollIntoView();
    }
}
function clearErrorMessage() {
    const errText = document.getElementById("error_text");
    if (errText) {
        errText.textContent = "";
    }
    const errInfo = document.getElementById("error_info");
    if (errInfo) {
        errInfo.classList.add("hidden");
    }
}
// Delete everything in a DOM Node. This is the pure JS equivalent of
// JQuery's .empty() function.
function emptyNode(node) {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
}
// Remove the old LocalStorage caches that IMS no longer uses, so that
// they can't act against the ~5 MB per-domain limit of HTML5 LocalStorage.
// This can probably be removed after the 2025 event, when all the relevant
// computers have their caches purged.
function cleanupOldCaches() {
    localStorage.removeItem("lscache-ims.incident_types");
    localStorage.removeItem("lscache-ims.incident_types-cacheexpiration");
    localStorage.removeItem("lscache-ims.personnel");
    localStorage.removeItem("lscache-ims.personnel-cacheexpiration");
    localStorage.removeItem("ims.incident_types");
    localStorage.removeItem("ims.incident_types.deadline");
    localStorage.removeItem("ims.personnel");
    localStorage.removeItem("ims.personnel.deadline");
}
cleanupOldCaches();
