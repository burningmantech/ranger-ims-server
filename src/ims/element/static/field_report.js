"use strict";
///<reference path="ims.ts"/>
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
// Initialize UI
let fieldReport = null;
async function initFieldReportPage() {
    await loadBody();
    disableEditing();
    await loadAndDisplayFieldReport();
    // for a new field report
    if (fieldReport.number == null) {
        document.getElementById("field_report_summary").focus();
    }
    // Warn the user if they're about to navigate away with unsaved text.
    window.addEventListener("beforeunload", function (e) {
        if (document.getElementById("report_entry_add").value !== "") {
            e.preventDefault();
        }
    });
    // Fire-and-forget this promise, since it tries forever to acquire a lock
    requestEventSourceLock();
    newFieldReportChannel().onmessage = async function (e) {
        const number = e.data.field_report_number;
        const event = e.data.event_id;
        const updateAll = e.data.update_all;
        if (updateAll || (event === eventID && number === fieldReportNumber)) {
            console.log("Got field report update: " + number);
            await loadAndDisplayFieldReport();
        }
    };
    const helpModal = new bootstrap.Modal(document.getElementById("helpModal"));
    // Keyboard shortcuts
    document.addEventListener("keydown", function (e) {
        // No shortcuts when an input field is active
        if (document.activeElement !== document.body) {
            return;
        }
        // No shortcuts when ctrl, alt, or meta is being held down
        if (e.altKey || e.ctrlKey || e.metaKey) {
            return;
        }
        // ? --> show help modal
        if (e.key === "?") {
            helpModal.toggle();
        }
        // a --> jump to add a new report entry
        if (e.key === "a") {
            e.preventDefault();
            // Scroll to report_entry_add field
            document.getElementById("report_entry_add").focus();
            document.getElementById("report_entry_add").scrollIntoView(true);
        }
        // h --> toggle showing system entries
        if (e.key.toLowerCase() === "h") {
            document.getElementById("history_checkbox").click();
        }
        // n --> new field report
        if (e.key.toLowerCase() === "n") {
            window.open("./new", '_blank').focus();
        }
    });
    document.getElementById("helpModal").addEventListener("keydown", function (e) {
        if (e.key === "?") {
            helpModal.toggle();
        }
    });
    document.getElementById("report_entry_add").addEventListener("keydown", function (e) {
        const submitEnabled = !document.getElementById("report_entry_submit").classList.contains("disabled");
        if (submitEnabled && (e.ctrlKey || e.altKey) && e.key === "Enter") {
            submitReportEntry();
        }
    });
}
//
// Load field report
//
async function loadFieldReport() {
    let number = null;
    if (fieldReport == null) {
        // First time here.  Use page JavaScript initial value.
        number = fieldReportNumber ?? null;
    }
    else {
        // We have an incident already.  Use that number.
        number = fieldReport.number ?? null;
    }
    if (number == null) {
        fieldReport = {
            "number": null,
            "created": null,
        };
    }
    else {
        const { json, err } = await fetchJsonNoThrow(urlReplace(url_fieldReports) + number, null);
        if (err != null) {
            disableEditing();
            const message = "Failed to load field report: " + err;
            console.error(message);
            setErrorMessage(message);
            return { err: message };
        }
        fieldReport = json;
    }
    return { err: null };
}
async function loadAndDisplayFieldReport() {
    const { err } = await loadFieldReport();
    if (fieldReport == null || err != null) {
        const message = "Field report failed to load";
        console.log(message);
        setErrorMessage(message);
        return;
    }
    drawTitle();
    drawNumber();
    drawIncident();
    drawSummary();
    toggleShowHistory();
    drawReportEntries(fieldReport.report_entries);
    clearErrorMessage();
    document.getElementById("report_entry_add").addEventListener("input", reportEntryEdited);
    if (editingAllowed) {
        enableEditing();
    }
}
//
// Populate page title
//
function drawTitle() {
    document.title = fieldReportAsString(fieldReport);
}
//
// Populate field report number
//
function drawNumber() {
    let number = fieldReport.number;
    if (number == null) {
        number = "(new)";
    }
    document.getElementById("field_report_number").textContent = number.toString();
}
//
// Populate incident number or show "create incident" button
//
function drawIncident() {
    document.getElementById("incident_number").textContent = "Please include in Summary";
    // New Field Report. There can be no Incident
    if (fieldReport.number == null) {
        return;
    }
    // If there's an attached Incident, then show a link to it
    const incident = fieldReport.incident;
    if (incident != null) {
        const incidentURL = urlReplace(url_viewIncidentNumber).replace("<number>", incident.toString());
        const link = document.createElement("a");
        link.href = incidentURL;
        link.text = incident.toString();
        const incidentField = document.getElementById("incident_number");
        incidentField.textContent = "";
        incidentField.append(link);
    }
    // If there's no attached Incident, show a button for making
    // a new Incident
    if (incident == null && canWriteIncidents) {
        document.getElementById("create_incident").classList.remove("hidden");
    }
    else {
        document.getElementById("create_incident").classList.add("hidden");
    }
}
//
// Populate field report summary
//
function drawSummary() {
    const summaryInput = document.getElementById("field_report_summary");
    if (fieldReport.summary) {
        summaryInput.value = fieldReport.summary;
        summaryInput.removeAttribute("placeholder");
        return;
    }
    summaryInput.value = "";
    const summarized = summarizeIncident(fieldReport);
    if (summarized) {
        // only replace the placeholder if it would be nonempty
        summaryInput.setAttribute("placeholder", summarized);
    }
}
//
// Editing
//
async function frSendEdits(edits) {
    if (fieldReport == null) {
        return { err: "fieldReport is null!" };
    }
    const number = fieldReport.number;
    let url = urlReplace(url_fieldReports);
    if (number == null) {
        // No fields are required for a new FR, nothing to do here
    }
    else {
        // We're editing an existing field report.
        edits.number = number;
        url += number;
    }
    const { resp, err } = await fetchJsonNoThrow(url, {
        body: JSON.stringify(edits),
    });
    if (err != null) {
        const message = `Failed to apply edit: ${err}`;
        console.log(message);
        await loadAndDisplayFieldReport();
        setErrorMessage(message);
        return { err: message };
    }
    if (number == null) {
        // We created a new field report.
        // We need to find out the created field report number so that
        // future edits don't keep creating new resources.
        const newNumber = resp?.headers.get("X-IMS-Field-Report-Number") ?? null;
        // Check that we got a value back
        if (newNumber == null) {
            return { err: "No X-IMS-Field-Report-Number header provided." };
        }
        const newAsNumber = parseInt(newNumber);
        // Check that the value we got back is valid
        if (isNaN(newAsNumber)) {
            return { err: "Non-integer X-IMS-Field-Report-Number header provided: " + newAsNumber };
        }
        // Store the new number in our field report object
        fieldReportNumber = fieldReport.number = newAsNumber;
        // Update browser history to update URL
        drawTitle();
        window.history.pushState(null, document.title, urlReplace(url_viewFieldReports) + newNumber);
    }
    await loadAndDisplayFieldReport();
    return { err: null };
}
registerSendEdits = frSendEdits;
async function editSummary() {
    const summaryInput = document.getElementById("field_report_summary");
    await editFromElement(summaryInput, "summary");
}
//
// Make a new incident and attach this Field Report to it
//
async function makeIncident() {
    // Create the new incident
    const incidentsURL = urlReplace(url_incidents);
    if (fieldReport == null) {
        setErrorMessage("fieldReport is null!");
        return;
    }
    const authors = [];
    if (fieldReport.report_entries) {
        authors.push(fieldReport.report_entries[0].author ?? "null");
    }
    const { resp, err } = await fetchJsonNoThrow(incidentsURL, {
        body: JSON.stringify({
            "summary": fieldReport.summary,
            "ranger_handles": authors,
        }),
    });
    if (err != null || resp == null) {
        disableEditing();
        setErrorMessage(`Failed to create incident: ${err}`);
        return;
    }
    const newNum = resp.headers.get("X-IMS-Incident-Number");
    if (newNum == null) {
        disableEditing();
        setErrorMessage("Failed to create incident: no IMS Incident Number provided");
        return;
    }
    fieldReport.incident = parseInt(newNum);
    // Attach this FR to that new incident
    const attachToIncidentUrl = `${urlReplace(url_fieldReports)}${fieldReport.number}` +
        `?action=attach;incident=${fieldReport.incident}`;
    const { err: attachErr } = await fetchJsonNoThrow(attachToIncidentUrl, {
        body: JSON.stringify({}),
    });
    if (attachErr != null) {
        disableEditing();
        setErrorMessage(`Failed to attach field report: ${attachErr}`);
        return;
    }
    console.log("Created and attached to new incident " + fieldReport.incident);
    await loadAndDisplayFieldReport();
}
// The success callback for a report entry strike call.
async function frOnStrikeSuccess() {
    await loadAndDisplayFieldReport();
    clearErrorMessage();
}
registerOnStrikeSuccess = frOnStrikeSuccess;
