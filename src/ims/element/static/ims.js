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
const getStoredTheme = () => localStorage.getItem("theme");
const setStoredTheme = theme => localStorage.setItem("theme", theme);
const getPreferredTheme = () => {
    const storedTheme = getStoredTheme();
    if (storedTheme) {
        return storedTheme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};
const setTheme = theme => {
    if (theme === "auto") {
        document.documentElement.setAttribute("data-bs-theme", (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
    } else {
        document.documentElement.setAttribute("data-bs-theme", theme);
    }
};
function applyTheme() {
    "use strict";

    setTheme(getPreferredTheme());

    const showActiveTheme = (theme, focus = false) => {
        const themeSwitcher = document.querySelector("#bd-theme");

        if (!themeSwitcher) {
            return;
        }

        const themeSwitcherText = document.querySelector("#bd-theme-text");
        const activeThemeIcon = document.querySelector(".theme-icon-active use");
        const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`);
        const svgOfActiveBtn = btnToActive.querySelector("svg use").getAttribute("href");

        document.querySelectorAll("[data-bs-theme-value]").forEach(element => {
            element.classList.remove("active");
            element.setAttribute("aria-pressed", "false");
        })

        btnToActive.classList.add("active");
        btnToActive.setAttribute("aria-pressed", "true");
        activeThemeIcon.setAttribute('href', svgOfActiveBtn);
        const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset.bsThemeValue})`;
        themeSwitcher.setAttribute("aria-label", themeSwitcherLabel);

        if (focus) {
            themeSwitcher.focus();
        }
    };

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
            setStoredTheme(theme);
            setTheme(theme);
            showActiveTheme(theme, true);
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

let _domTextAreaForHaxxors = document.createElement("textarea")

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
// Errors
///

function ValueError(message) {
    this.name = "ValueError";
    this.message = message || "Invalid Value";
    this.stack = (new Error()).stack;
}
ValueError.prototype = Object.create(Error.prototype);
ValueError.prototype.constructor = ValueError;


//
// Arrays
//

// Build an array from a range.
function range(start, end, step) {
    if (step == null) {
        step = 1;
    } else if (step === 0) {
        throw new ValueError("step = 0");
    }

    return Array(end - start)
        .join(0)
        .split(0)
        .map(function(val, i) { return (i * step) + start} )
        ;
}


function compareReportEntries(a, b) {
    if (a.created < b.created) { return -1; }
    if (a.created > b.created) { return  1; }

    if (a.system_entry && ! b.system_entry) { return -1; }
    if (! a.system_entry && b.system_entry) { return  1; }

    if (a.text < b.text) { return -1; }
    if (a.text > b.text) { return  1; }

    return 0;
}


//
// Request making
//

function jsonRequest(url, jsonOut, success, error) {
    function ok(data, status, xhr) {
        if (success) {
            success(data, status, xhr);
        }
    }

    function fail(xhr, status, requestError) {
        // Intentionally empty response is not an error.
        if (
            status === "parsererror" &&
            xhr.status === 201 &&
            xhr.responseText === ""
        ) {
            ok("", "", xhr);
            return;
        }

        if (error) {
            error(requestError, status, xhr);
        }
    }

    const args = {
        "url": url,
        "method": "GET",
        "dataType": "json",
        "success": ok,
        "error": fail,
    };

    if (jsonOut) {
        const jsonText = JSON.stringify(jsonOut);

        args["method"] = "POST";
        args["contentType"] = "application/json";
        args["data"] = jsonText;
    }

    $.ajax(args);
}



//
// Generic string formatting
//

// Pad a string representing an integer to two digits.
function padTwo(value) {
    if (value == null) {
        return "?";
    }

    value = value.toString();

    if (value.length === 1) {
        return "0" + value;
    }

    return value;
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
    const timeStampContainer = jQuery(
        "<time />", {"datetime": date.toISOString()}
    );
    timeStampContainer.text(fullDateTime.format(date));
    return timeStampContainer;
}


// Disable an element
function disable(element) {
    element.attr("disabled", "");
}


// Enable an element
function enable(element) {
    element.removeAttr("disabled");
}


// Disable editing for an element
function disableEditing() {
    disable($(".form-control"));
    enable($(":input[type=search]"));  // Don't disable search fields
    $(document.documentElement).addClass("no-edit");
}


// Enable editing for an element
function enableEditing() {
    enable($(".form-control"));
    $(document.documentElement).removeClass("no-edit");
}


// Add an error indication to a control
function controlHasError(element) {
    element.parent().addClass("is-invalid");
}


// Add a success indication to a control
function controlHasSuccess(element, clearTimeout) {
    element.addClass("is-valid");
    if (clearTimeout != null) {
        element.delay("1000").queue(function(next) {
            controlClear(element);
            next();
        });
    }
}


// Clear error/success indication from a control
function controlClear(element) {
    element.removeClass("is-invalid");
    element.removeClass("is-valid");
}


//
// Load HTML body template.
//

function loadBody(success) {
    function complete() {
        applyTheme();

        if (typeof eventID !== "undefined") {
            $(".event-id").text(eventID);
            $(".event-id").addClass("active-event");
        }

        if (success) {
            success();
        }
    }

    detectTouchDevice();
    $("body").load(pageTemplateURL, complete);
}


//
// Touch device detection
//

// Add .touch or .no-touch class to top-level element if the browser is or is
// not on a touch device, respectively.
function detectTouchDevice() {
    if ("ontouchstart" in document.documentElement) {
        $(document.documentElement).addClass("touch");
    } else {
        $(document.documentElement).addClass("no-touch");
    }
}


//
// Controls
//

// Select an option element with a given value from a given select element.
function selectOptionWithValue(select, value) {
    select
        .children("option")
        .prop("selected", false)
        ;

    select
        .children("option[value='" + value + "']")
        .prop("selected", true)
        ;
}


//
// Incident data
//

// Look up the name of a priority given its number (1-5).
function priorityNameFromNumber(number) {
    switch (number) {
        case 1: return "High";
        case 2: return "High";
        case 3: return "Normal";
        case 4: return "Low";
        case 5: return "Low︎";
        default:
            console.warn("Unknown incident priority number: " + number);
            return undefined;
    }
}


// Look up the glyph for a priority given its number (1-5).
function priorityIconFromNumber(number) {
    switch (number) {
        case 1: return '↑';
        case 2: return '↑';
        case 3: return '';
        case 4: return '↓';
        case 5: return '↓';
        default:
            console.warn("Unknown incident priority number: " + number);
            return undefined;
  }
}


// Look up a state's name given its ID.
function stateNameFromID(stateID) {
    switch (stateID) {
        case "new"       : return "New";
        case "on_hold"   : return "On Hold";
        case "dispatched": return "Dispatched";
        case "on_scene"  : return "On Scene";
        case "closed"    : return "Closed";
        default:
            console.warn("Unknown incident state ID: " + stateID);
            return undefined;
    }
}


// Look up a state's sort key given its ID.
function stateSortKeyFromID(stateID) {
    switch (stateID) {
        case "new"       : return 1;
        case "on_hold"   : return 2;
        case "dispatched": return 3;
        case "on_scene"  : return 4;
        case "closed"    : return 5;
        default:
            console.warn("Unknown incident state ID: " + stateID);
            return undefined;
    }
}


// Look up a concentric street's name given its ID.
function concentricStreetFromID(streetID) {
    if (streetID == null) {
        return undefined;
    }

    const name = concentricStreetNameByID[streetID];
    if (name == null) {
        console.warn("Unknown street ID: " + streetID);
        return undefined;
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
    return undefined;
}


// Return a summary for a given incident.
function summarizeIncident(incident) {
    const summary = incident.summary;
    const reportEntries = incident.report_entries;

    if (!summary) {
        if (!reportEntries) {
            return "";
        }
        // Get the first line of the first report entry.
        for (const reportEntry of reportEntries) {
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

    return summary;
}


// Return a summary for a given field report.
function summarizeFieldReport(report) {
    return summarizeIncident(report);
}


// Get author for incident
function incidentAuthor(incident) {
    for (const entry of incident.report_entries??[]) {
        if (entry.author) {
            return entry.author;
        }
    }

    return undefined;
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
    return (
        "IMS #" + incident.number + ": " +
        summarizeIncident(incident)
    );
}


// Render field report as a string
function fieldReportAsString(report) {
    if (report.number == null) {
        return "New Field Report";
    }
    return (
        "FR #" + report.number +
        " (" + fieldReportAuthor(report) + "): " +
        summarizeFieldReport(report)
    );
}


// Return all user-entered report text for a given incident.
function reportTextFromIncident(incident) {
    const texts = [];

    if (incident.summary != null) {
        texts.push(incident.summary);
    }

    for (const reportEntry of incident.report_entries??[]) {

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
    if (typeof eventFieldReports !== "undefined" && incident.field_reports) {
        for (const reportNumber of incident.field_reports) {
            const report = eventFieldReports[reportNumber];
            const reportText = reportTextFromIncident(report);

            texts.push(reportText);
        }
    }

    return texts.join("");
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
            locationBits.push(
                "Unknown location type:" + location.type
            );
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
    return copy.join(", ")
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

function renderPriority(priorityNumber, type, incident) {
    switch (type) {
        case "display":
            return priorityIconFromNumber(priorityNumber);
        case "filter":
            return priorityNameFromNumber(priorityNumber);
        case "type":
        case "sort":
            return priorityNumber;
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
            return textAsHTML(shortDescribeLocation(data));
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

    const entryContainer = $("<div />", {"class": "report_entry"});

    const strikable = !entry.system_entry;

    if (entry.system_entry) {
        entryContainer.addClass("report_entry_system");
    } else if (entry.stricken) {
        entryContainer.addClass("report_entry_stricken");
    } else {
        entryContainer.addClass("report_entry_user");
    }

    if (entry.merged) {
        entryContainer.addClass("report_entry_merged");
    }

    // Add the timestamp and author, with a Strike/Unstrike button

    const metaDataContainer = $("<p />", {"class": "report_entry_metadata"})

    if (strikable) {
        let onclick = "";

        if (typeof incidentNumber !== "undefined") {
            // we're on the incident page
            if (entry.merged) {
                // this is an entry from a field report, as shown on the incident page
                onclick = "setStrikeFieldReportEntry(" + entry.merged + ", " + entry.id + ", " + !entry.stricken + ");"
            } else {
                // this is an incident entry on the incident page
                onclick = "setStrikeIncidentEntry(" + incidentNumber + ", " + entry.id + ", " + !entry.stricken + ");"
            }
        } else if (typeof fieldReportNumber !== "undefined") {
            // we're on the field report page
            onclick = "setStrikeFieldReportEntry(" + fieldReportNumber + ", " + entry.id + ", " + !entry.stricken + ");"
        }
        const strikeContainer = $("<button />", {"onclick": onclick});
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
    timeStampContainer.addClass("report_entry_timestamp");

    metaDataContainer.append([timeStampContainer, ", "]);

    let author = entry.author;
    if (author == null) {
        author = "(unknown)";
    }
    const authorContainer = $("<span />");
    authorContainer.text(entry.author);
    authorContainer.addClass("report_entry_author");

    metaDataContainer.append(author);

    if (entry.merged) {
        metaDataContainer.append(" ");

        const link = $("<a />");
        link.text("field report #" + entry.merged);
        link.attr("href", urlReplace(url_viewFieldReports) + entry.merged)

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
        const textContainer = $("<p />", {"class": "report_entry_text"});
        textContainer.text(line);

        entryContainer.append(textContainer);
    }

    // Add a horizontal line after each entry

    entryContainer.append( $("<hr />", {"class": "m-1"}) );

    return entryContainer;
}

function drawReportEntries(entries) {
    const container = $("#report_entries");
    container.empty();

    if (entries) {
        for (const entry of entries) {
            container.append(reportEntryElement(entry));
        }
        container.parent().parent().removeClass("hidden");
    } else {
        container.parent().parent().addClass("hidden");
    }
}

function reportEntryEdited() {
    const text = $("#report_entry_add").val().trim();
    const submitButton = $("#report_entry_submit");

    submitButton.removeClass("btn-default");
    submitButton.removeClass("btn-warning");
    submitButton.removeClass("btn-danger");

    if (!text) {
        submitButton.addClass("disabled");
        submitButton.addClass("btn-default");
    } else {
        submitButton.removeClass("disabled");
        submitButton.addClass("btn-warning");
    }
}

// The success callback for a report entry strike call.
// This function is designed to work from either the incident
// or the field report page.
function onStrikeSuccess() {
    if (typeof loadAndDisplayFieldReport !== "undefined") {
        loadAndDisplayFieldReport();
    }
    if (typeof loadAndDisplayIncident !== "undefined") {
        loadAndDisplayIncident();
    }
    if (typeof loadAndDisplayFieldReports !== "undefined") {
        loadAndDisplayFieldReports();
    }
    clearErrorMessage();
}

// The error callback for a report entry strike call.
// This function is designed to work from either the incident
// or the field report page.
function onStrikeError(xhr, status, requestError) {
    const message = "Failed to set report entry strike status";
    console.log(message + ": " + JSON.stringify(requestError));
    setErrorMessage(message);
}

function setStrikeIncidentEntry(incidentNumber, reportEntryId, strike) {
    const url = urlReplace(url_incident_reportEntry)
        .replace("<incident_number>", incidentNumber)
        .replace("<report_entry_id>", reportEntryId);
    jsonRequest(url, {"stricken": strike}, onStrikeSuccess, onStrikeError);
}

function setStrikeFieldReportEntry(fieldReportNumber, reportEntryId, strike) {
    const url = urlReplace(url_fieldReport_reportEntry)
        .replace("<field_report_number>", fieldReportNumber)
        .replace("<report_entry_id>", reportEntryId);
    jsonRequest(url, {"stricken": strike}, onStrikeSuccess, onStrikeError);
}

function submitReportEntry() {
    const text = $("#report_entry_add").val().trim();

    if (!text) {
        return;
    }

    console.log("New report entry:\n" + text);

    function ok() {
        const $textArea = $("#report_entry_add");
        // Clear the report entry
        $textArea.val("");
        controlHasSuccess($textArea, 1000);
        // Reset the submit button
        reportEntryEdited();
    }

    function fail() {
        const submitButton = $("#report_entry_submit");
        submitButton.removeClass("btn-default");
        submitButton.removeClass("btn-warning");
        submitButton.addClass("btn-danger");
        controlHasError($("#report_entry_add"), 1000);
    }

    sendEdits({"report_entries": [{"text": text}]}, ok, fail);
}

//
// Generated history display
//

function toggleShowHistory() {
    if ($("#history_checkbox").is(":checked")) {
        $("#report_entries").removeClass("hide-history");
    } else {
        $("#report_entries").addClass("hide-history");
    }
}

function editFromElement(element, jsonKey, transform) {
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

    if (edits.location != null) {
        edits.location.type = "garett";  // UI only supports one type
    }

    // Send request to server

    function ok() {
        controlHasSuccess(element, 1000);
    }

    function fail() {
        controlHasError(element);
    }

    sendEdits(edits, ok, fail);
}


//
// EventSource
//

const incidentChannelName = "incident_update";
const fieldReportChannelName= "field_report_update";
const reattemptMinTimeMillis = 10000;
const lastSseIDKey = "last_sse_id";

// Call this from each browsing context, so that it can queue up to become a leader
// to manage the EventSource.
async function requestEventSourceLock() {
    // Infinitely attempt to reconnect to the EventSource.
    // This addresses the following issue for when IMS lives on AWS:
    // https://github.com/burningmantech/ranger-ims-server/issues/1364
    while (true) {
        const start = Date.now();
        // Acquire the lock, set up the EventSource, and start
        // broadcasting events to other browsing contexts.
        await navigator.locks.request("ims_eventsource_lock", () => {
            const {promise, resolve} = Promise.withResolvers();
            subscribeToUpdates(resolve);
            return promise;
        });
        const millisSinceStart = Date.now() - start;
        await new Promise(r => setTimeout(r, Math.max(0, reattemptMinTimeMillis-millisSinceStart)));
    }
}

// This starts the EventSource call and configures event listeners to propagate
// updates to BroadcastChannels. The idea is that only one browsing context should
// have an EventSource connection at any given time.
//
// The "closed" param is a callback to notify the caller that the EventSource has
// been closed.
function subscribeToUpdates(closed) {
    const eventSource = new EventSource(
        url_eventSource, { withCredentials: true }
    );

    eventSource.addEventListener("open", function() {
        console.log("Event listener opened");
    }, true);

    eventSource.addEventListener("error", function() {
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log("Event listener closed");
            eventSource.close();
            closed();
        } else {
            // This is likely a retriable error, and EventSource will automatically
            // attempt reconnection.
            console.log("Event listener error");
        }
    }, true);

    eventSource.addEventListener("InitialEvent", function(e) {
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
            ch.postMessage({update_all: true});
        }
    })

    eventSource.addEventListener("Incident", function(e) {
        const send = new BroadcastChannel(incidentChannelName);
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        send.postMessage(JSON.parse(e.data));
    }, true);

    // TODO: this will never receive any events currently, since the server isn't configured to
    //  fire events for FieldReports. See
    //  https://github.com/burningmantech/ranger-ims-server/blob/954498eb125bb9a83d2b922361abef4935f228ba/src/ims/application/_eventsource.py#L113-L135
    eventSource.addEventListener("FieldReport", function(e) {
        const send = new BroadcastChannel(fieldReportChannelName);
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        send.postMessage(JSON.parse(e.data));
    }, true);
}
