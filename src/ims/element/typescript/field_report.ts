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

import * as ims from "./ims.ts";

declare let url_incidents: string;
declare let url_viewFieldReports: string;
declare let url_fieldReports: string;
declare let url_viewIncidentNumber: string;

declare global {
    interface Window {
        makeIncident: ()=>Promise<void>;
        editSummary: ()=>Promise<void>;
        toggleShowHistory: ()=>void;
        reportEntryEdited: ()=>void;
        submitReportEntry: ()=>Promise<void>;
    }
}

let fieldReport: ims.FieldReport|null = null;

//
// Initialize UI
//

initFieldReportPage();

async function initFieldReportPage(): Promise<void> {
    const initResult = await ims.commonPageInit();
    if (!initResult.authInfo.authenticated) {
        ims.redirectToLogin();
        return;
    }

    window.makeIncident = makeIncident;
    window.editSummary = editSummary;
    window.toggleShowHistory = ims.toggleShowHistory;
    window.reportEntryEdited = ims.reportEntryEdited;
    window.submitReportEntry = ims.submitReportEntry;

    ims.disableEditing();
    await loadAndDisplayFieldReport();

    if (fieldReport == null) {
        return;
    }

    // for a new field report
    if (fieldReport.number == null) {
        // assume that Rangers without Incident access ought to see the instructions by default
        if (!ims.eventAccess?.readIncidents && !ims.eventAccess?.writeIncidents) {
            document.getElementById("fr-instructions")!.click();
        }
        document.getElementById("field_report_summary")!.focus();
    }

    // Warn the user if they're about to navigate away with unsaved text.
    window.addEventListener("beforeunload", function (e: BeforeUnloadEvent): void {
        if ((document.getElementById("report_entry_add") as HTMLTextAreaElement).value !== "") {
            e.preventDefault();
        }
    });

    ims.requestEventSourceLock();

    ims.newFieldReportChannel().onmessage = async function (e: MessageEvent<ims.FieldReportBroadcast>): Promise<void> {
        const number = e.data.field_report_number;
        const event = e.data.event_id;
        const updateAll = e.data.update_all;

        if (updateAll || (event === ims.pathIds.eventID && number === ims.pathIds.fieldReportNumber)) {
            console.log("Got field report update: " + number);
            await loadAndDisplayFieldReport();
        }
    };

    const helpModal = ims.bsModal(document.getElementById("helpModal")!);

    // Keyboard shortcuts
    document.addEventListener("keydown", function(e: KeyboardEvent): void {
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
            document.getElementById("report_entry_add")!.focus();
            document.getElementById("report_entry_add")!.scrollIntoView(true);
        }
        // h --> toggle showing system entries
        if (e.key.toLowerCase() === "h") {
            (document.getElementById("history_checkbox") as HTMLInputElement).click();
        }
        // n --> new field report
        if (e.key.toLowerCase() === "n") {
            (window.open("./new", '_blank') as Window).focus();
        }
    });
    (document.getElementById("helpModal") as HTMLDivElement).addEventListener("keydown", function(e: KeyboardEvent): void {
        if (e.key === "?") {
            helpModal.toggle();
        }
    });
    document.getElementById("report_entry_add")!.addEventListener("keydown", function (e: KeyboardEvent): void {
        const submitEnabled = !document.getElementById("report_entry_submit")!.classList.contains("disabled");
        if (submitEnabled && (e.ctrlKey || e.altKey) && e.key === "Enter") {
            ims.submitReportEntry();
        }
    });
}

//
// Load field report
//

async function loadFieldReport(): Promise<{err: string|null}> {
    let number: number|null = null;
    if (fieldReport == null) {
        // First time here.  Use page JavaScript initial value.
        number = ims.pathIds.fieldReportNumber??null;
    } else {
        // We have an incident already.  Use that number.
        number = fieldReport.number??null;
    }

    if (number == null) {
        fieldReport = {
            "number": null,
            "created": null,
        };
    } else {
        const {json, err} = await ims.fetchJsonNoThrow<ims.FieldReport>(
            ims.urlReplace(url_fieldReports) + number, null);
        if (err != null) {
            ims.disableEditing();
            const message = "Failed to load field report: " + err;
            console.error(message);
            ims.setErrorMessage(message);
            return {err: message};
        }
        fieldReport = json;
    }
    return {err: null};
}

async function loadAndDisplayFieldReport(): Promise<void> {
    const {err} = await loadFieldReport();

    if (fieldReport == null || err != null) {
        console.log(err);
        ims.setErrorMessage(err??"");
        return;
    }

    drawTitle();
    drawNumber();
    drawIncident();
    drawSummary();
    ims.toggleShowHistory();
    ims.drawReportEntries(fieldReport.report_entries??[]);
    ims.clearErrorMessage();

    document.getElementById("report_entry_add")!.addEventListener("input", ims.reportEntryEdited);

    if (ims.eventAccess?.writeFieldReports) {
        ims.enableEditing();
    }
}


//
// Populate page title
//

function drawTitle(): void {
    document.title = ims.fieldReportAsString(fieldReport!);
}


//
// Populate field report number
//

function drawNumber(): void {
    let number: number|string|null|undefined = fieldReport!.number;
    if (number == null) {
        number = "(new)";
    }
    document.getElementById("field_report_number")!.textContent = number.toString();
}

//
// Populate incident number or show "create incident" button
//

function drawIncident(): void {
    document.getElementById("incident_number")!.textContent = "Please include in Summary";
    // New Field Report. There can be no Incident
    if (fieldReport!.number == null) {
        return;
    }
    // If there's an attached Incident, then show a link to it
    const incident = fieldReport!.incident;
    if (incident != null) {
        const incidentURL = ims.urlReplace(url_viewIncidentNumber).replace("<number>", incident.toString());
        const link: HTMLAnchorElement = document.createElement("a");
        link.href = incidentURL;
        link.text = incident.toString();

        const incidentField = document.getElementById("incident_number")!;
        incidentField.textContent = "";
        incidentField.append(link);
    }
    // If there's no attached Incident, show a button for making
    // a new Incident
    if (incident == null && ims.eventAccess?.writeIncidents) {
        document.getElementById("create_incident")!.classList.remove("hidden");
    } else {
        document.getElementById("create_incident")!.classList.add("hidden");
    }
}


//
// Populate field report summary
//

function drawSummary(): void {
    const summaryInput = document.getElementById("field_report_summary") as HTMLInputElement;
    if (fieldReport!.summary) {
        summaryInput.value = fieldReport!.summary;
        summaryInput.removeAttribute("placeholder");
        return;
    }

    summaryInput.value = "";
    const summarized = ims.summarizeIncidentOrFR(fieldReport!);
    if (summarized) {
        // only replace the placeholder if it would be nonempty
        summaryInput.setAttribute("placeholder", summarized);
    }
}


//
// Editing
//

async function frSendEdits(edits: ims.FieldReport): Promise<{err:string|null}> {
    if (fieldReport == null) {
        return {err: "fieldReport is null!"};
    }
    const number = fieldReport.number;
    let url = ims.urlReplace(url_fieldReports);

    if (number == null) {
        // No fields are required for a new FR, nothing to do here
    } else {
        // We're editing an existing field report.
        edits.number = number;
        url += number;
    }

    const {resp, err} = await ims.fetchJsonNoThrow(url, {
        body: JSON.stringify(edits),
    });
    if (err != null) {
        const message = `Failed to apply edit: ${err}`;
        console.log(message);
        await loadAndDisplayFieldReport();
        ims.setErrorMessage(message);
        return {err: message};
    }
    if (number == null) {
        // We created a new field report.
        // We need to find out the created field report number so that
        // future edits don't keep creating new resources.

        const newNumber: string|null = resp?.headers.get("X-IMS-Field-Report-Number")??null;
        // Check that we got a value back
        if (newNumber == null) {
            return {err: "No X-IMS-Field-Report-Number header provided."};
        }

        const newAsNumber = ims.parseInt10(newNumber);
        // Check that the value we got back is valid
        if (newAsNumber == null) {
            return {err: "Non-integer X-IMS-Field-Report-Number header provided: " + newAsNumber};
        }

        // Store the new number in our field report object
        ims.pathIds.fieldReportNumber = fieldReport.number = newAsNumber;

        // Update browser history to update URL
        drawTitle();
        window.history.pushState(
            null, document.title,
            ims.urlReplace(url_viewFieldReports) + newNumber
        );
    }

    await loadAndDisplayFieldReport();
    return {err: null};
}
ims.setSendEdits(frSendEdits);

async function editSummary(): Promise<void> {
    const summaryInput = document.getElementById("field_report_summary") as HTMLInputElement;
    await ims.editFromElement(summaryInput, "summary");
}

//
// Make a new incident and attach this Field Report to it
//

async function makeIncident(): Promise<void> {
    // Create the new incident
    const incidentsURL = ims.urlReplace(url_incidents);

    if (fieldReport == null) {
        ims.setErrorMessage("fieldReport is null!");
        return;
    }

    const authors: string[] = [];
    if (fieldReport.report_entries) {
        authors.push(fieldReport.report_entries[0]!.author??"null");
    }
    const {resp, err} = await ims.fetchJsonNoThrow(incidentsURL, {
        body:JSON.stringify({
            "summary": fieldReport.summary,
            "ranger_handles": authors,
        }),
    });
    if (err != null || resp == null) {
        ims.disableEditing();
        ims.setErrorMessage(`Failed to create incident: ${err}`);
        return;
    }
    const newNum: string|null = resp.headers.get("X-IMS-Incident-Number");
    if (newNum == null) {
        ims.disableEditing();
        ims.setErrorMessage("Failed to create incident: no IMS Incident Number provided");
        return;
    }
    fieldReport.incident = ims.parseInt10(newNum);

    // Attach this FR to that new incident
    const attachToIncidentUrl =
        `${ims.urlReplace(url_fieldReports)}${fieldReport.number}` +
        `?action=attach;incident=${fieldReport.incident}`;
    const {err: attachErr} = await ims.fetchJsonNoThrow(attachToIncidentUrl, {
        body: JSON.stringify({}),
    });
    if (attachErr != null) {
        ims.disableEditing();
        ims.setErrorMessage(`Failed to attach field report: ${attachErr}`);
        return;
    }
    console.log("Created and attached to new incident " + fieldReport.incident);
    await loadAndDisplayFieldReport();
}


// The success callback for a report entry strike call.
async function frOnStrikeSuccess(): Promise<void> {
    await loadAndDisplayFieldReport();
    ims.clearErrorMessage();
}
ims.setOnStrikeSuccess(frOnStrikeSuccess);
