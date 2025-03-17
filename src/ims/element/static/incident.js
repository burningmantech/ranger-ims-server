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
// declare var incidentNumber: number;
//
// Initialize UI
//
async function initIncidentPage() {
    await loadBody();
    addLocationAddressOptions();
    disableEditing();
    await loadAndDisplayIncident();
    await loadPersonnel();
    drawRangers();
    drawRangersToAdd();
    await loadIncidentTypes();
    drawIncidentTypesToAdd();
    await loadAllFieldReports();
    renderFieldReportData();
    // for a new incident, jump to summary field
    if (incident.number == null) {
        document.getElementById("incident_summary").focus();
    }
    // Warn the user if they're about to navigate away with unsaved text.
    window.addEventListener("beforeunload", function (e) {
        if (document.getElementById("report_entry_add").value !== "") {
            e.preventDefault();
        }
    });
    // Fire-and-forget this promise, since it tries forever to acquire a lock
    let ignoredPromise = requestEventSourceLock();
    const incidentChannel = new BroadcastChannel(incidentChannelName);
    incidentChannel.onmessage = async function (e) {
        const number = e.data.incident_number;
        const event = e.data.event_id;
        const updateAll = e.data.update_all;
        if (updateAll || (event === eventID && number === incidentNumber)) {
            console.log("Got incident update: " + number);
            await loadAndDisplayIncident();
            await loadAllFieldReports();
            renderFieldReportData();
        }
    };
    const fieldReportChannel = new BroadcastChannel(fieldReportChannelName);
    fieldReportChannel.onmessage = async function (e) {
        const updateAll = e.data.update_all;
        if (updateAll) {
            console.log("Updating all field reports");
            await loadAllFieldReports();
            renderFieldReportData();
            return;
        }
        const number = e.data.field_report_number;
        const event = e.data.event_id;
        if (event === eventID) {
            console.log("Got field report update: " + number);
            await loadOneFieldReport(number);
            renderFieldReportData();
            return;
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
        // n --> new incident
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
// Load incident
//
let incident = null;
async function loadIncident() {
    let number = null;
    if (incident == null) {
        // First time here.  Use page JavaScript initial value.
        number = incidentNumber ?? null;
    }
    else {
        // We have an incident already.  Use that number.
        number = incident.number;
    }
    if (number == null) {
        incident = {
            "number": null,
            "state": "new",
            "priority": 3,
            "summary": "",
        };
    }
    else {
        const { json, err } = await fetchJsonNoThrow(urlReplace(url_incidents) + number, null);
        if (err != null) {
            disableEditing();
            const message = `Failed to load Incident ${number}: ${err}`;
            console.error(message);
            setErrorMessage(message);
            return { err: message };
        }
        incident = json;
    }
    return { err: null };
}
async function loadAndDisplayIncident() {
    await loadIncident();
    if (incident == null) {
        const message = "Incident failed to load";
        console.log(message);
        setErrorMessage(message);
        return;
    }
    drawIncidentFields();
    clearErrorMessage();
    if (editingAllowed) {
        enableEditing();
    }
    if (attachmentsAllowed) {
        document.getElementById("attach_file").classList.remove("hidden");
    }
}
// Do all the client-side rendering based on the state of allFieldReports.
function renderFieldReportData() {
    loadAttachedFieldReports();
    drawFieldReportsToAttach();
    drawMergedReportEntries();
    drawAttachedFieldReports();
}
//
// Load personnel
//
let personnel = null;
async function loadPersonnel() {
    const { json, err } = await fetchJsonNoThrow(urlReplace(url_personnel + "?event_id=<event_id>"), null);
    if (err != null) {
        const message = `Failed to load personnel: ${err}`;
        console.error(message);
        setErrorMessage(message);
        return { err: message };
    }
    const _personnel = {};
    for (const record of json) {
        // Filter inactive Rangers out
        if (record.status === "active") {
            _personnel[record.handle] = record;
        }
    }
    personnel = _personnel;
    return { err: null };
}
//
// Load incident types
//
let incidentTypes = [];
async function loadIncidentTypes() {
    const { json, err } = await fetchJsonNoThrow(url_incidentTypes, null);
    if (err != null) {
        const message = `Failed to load incident types: ${err}`;
        console.error(message);
        setErrorMessage(message);
        return { err: message };
    }
    const _incidentTypes = [];
    for (const record of json) {
        _incidentTypes.push(record);
    }
    _incidentTypes.sort();
    incidentTypes = _incidentTypes;
    return { err: null };
}
//
// Load all field reports
//
let allFieldReports = null;
async function loadAllFieldReports() {
    if (allFieldReports === undefined) {
        return { err: null };
    }
    const { resp, json, err } = await fetchJsonNoThrow(urlReplace(url_fieldReports), null);
    if (err != null) {
        if (resp != null && resp.status === 403) {
            // We're not allowed to look these up.
            allFieldReports = undefined;
            console.error("Got a 403 looking up field reports");
            return { err: null };
        }
        else {
            const message = `Failed to load field reports: ${err}`;
            console.error(message);
            setErrorMessage(message);
            return { err: message };
        }
    }
    const _allFieldReports = [];
    for (const d of json) {
        _allFieldReports.push(d);
    }
    // apply a descending sort based on the field report number,
    // being cautious about field report number being null
    _allFieldReports.sort(function (a, b) {
        return (b.number ?? -1) - (a.number ?? -1);
    });
    allFieldReports = _allFieldReports;
    return { err: null };
}
async function loadOneFieldReport(fieldReportNumber) {
    if (allFieldReports === undefined) {
        return { err: null };
    }
    const { resp, json, err } = await fetchJsonNoThrow(urlReplace(url_fieldReport).replace("<field_report_number>", fieldReportNumber.toString()), null);
    if (err != null) {
        if (resp == null || resp.status !== 403) {
            const message = `Failed to load field report ${fieldReportNumber} ${err}`;
            console.error(message);
            setErrorMessage(message);
            return { err: message };
        }
    }
    let found = false;
    for (const i in allFieldReports) {
        if (allFieldReports[i].number === json.number) {
            allFieldReports[i] = json;
            found = true;
        }
    }
    if (!found) {
        if (allFieldReports == null) {
            allFieldReports = [];
        }
        allFieldReports.push(json);
        // apply a descending sort based on the field report number,
        // being cautious about field report number being null
        allFieldReports.sort(function (a, b) {
            return (b.number ?? -1) - (a.number ?? -1);
        });
    }
    return { err: null };
}
//
// Load attached field reports
//
let attachedFieldReports = null;
function loadAttachedFieldReports() {
    if (incidentNumber == null) {
        return;
    }
    const _attachedFieldReports = [];
    for (const fr of allFieldReports ?? []) {
        if (fr.incident === incidentNumber) {
            _attachedFieldReports.push(fr);
        }
    }
    attachedFieldReports = _attachedFieldReports;
}
//
// Draw all fields
//
function drawIncidentFields() {
    drawIncidentTitle();
    drawIncidentNumber();
    drawState();
    drawCreated();
    drawPriority();
    drawIncidentSummary();
    drawRangers();
    drawIncidentTypes();
    drawLocationName();
    drawLocationAddressRadialHour();
    drawLocationAddressRadialMinute();
    drawLocationAddressConcentric();
    drawLocationDescription();
    toggleShowHistory();
    drawMergedReportEntries();
    document.getElementById("report_entry_add").addEventListener("input", reportEntryEdited);
}
//
// Add option elements to location address select elements
//
function addLocationAddressOptions() {
    const hours = range(1, 13);
    const hourElement = document.getElementById("incident_location_address_radial_hour");
    for (const hour of hours) {
        const hourStr = padTwo(hour);
        const newOption = document.createElement("option");
        newOption.value = hourStr;
        newOption.textContent = hourStr;
        hourElement.append(newOption);
    }
    const minutes = range(0, 12, 5);
    const minuteElement = document.getElementById("incident_location_address_radial_minute");
    for (const minute of minutes) {
        const minuteStr = padTwo(minute);
        const newOption = document.createElement("option");
        newOption.value = minuteStr;
        newOption.textContent = minuteStr;
        minuteElement.append(newOption);
    }
    const concentricElement = document.getElementById("incident_location_address_concentric");
    for (const id in concentricStreetNameByID) {
        const newOption = document.createElement("option");
        newOption.value = id;
        newOption.textContent = concentricStreetNameByID[id];
        concentricElement.append(newOption);
    }
}
//
// Populate page title
//
function drawIncidentTitle() {
    document.title = incidentAsString(incident);
}
//
// Populate incident number
//
function drawIncidentNumber() {
    let number = incident.number ?? null;
    if (number == null) {
        number = "(new)";
    }
    document.getElementById("incident_number").textContent = number.toString();
}
//
// Populate incident state
//
function drawState() {
    selectOptionWithValue(document.getElementById("incident_state"), stateForIncident(incident));
}
//
// Populate created datetime
//
function drawCreated() {
    const date = incident.created ?? null;
    if (date == null) {
        return;
    }
    const d = Date.parse(date);
    const createdElement = document.getElementById("created_datetime");
    createdElement.textContent = `${shortDate.format(d)} ${shortTimeSec.format(d)}`;
    createdElement.setAttribute("title", fullDateTime.format(d));
}
//
// Populate incident priority
//
function drawPriority() {
    const priorityElement = document.getElementById("incident_priority");
    // priority is currently hidden from the incident page, so we should expect this early return
    if (priorityElement == null) {
        return;
    }
    selectOptionWithValue(priorityElement, (incident.priority ?? "").toString());
}
//
// Populate incident summary
//
function drawIncidentSummary() {
    const summaryElement = document.getElementById("incident_summary");
    if (incident.summary) {
        summaryElement.value = incident.summary;
        summaryElement.placeholder = "";
        summaryElement.setAttribute("placeholder", "");
        return;
    }
    summaryElement.value = "";
    const summarized = summarizeIncident(incident);
    // only replace the placeholder if it would be nonempty
    if (summarized) {
        summaryElement.placeholder = summarized;
    }
}
//
// Populate Rangers list
//
let _rangerItem = null;
function drawRangers() {
    if (_rangerItem == null) {
        _rangerItem = document.getElementById("incident_rangers_list")
            .getElementsByClassName("list-group-item")[0];
    }
    const handles = incident.ranger_handles ?? [];
    handles.sort((a, b) => a.localeCompare(b));
    const rangersElement = document.getElementById("incident_rangers_list");
    rangersElement.replaceChildren();
    for (const handle of handles) {
        let ranger = null;
        if (personnel?.[handle] == null) {
            ranger = textAsHTML(handle);
        }
        else {
            const person = personnel[handle];
            ranger = document.createElement("a");
            ranger.innerText = textAsHTML(rangerAsString(person));
            ranger.href = `${clubhousePersonURL}/${person.directory_id}`;
        }
        const item = _rangerItem.cloneNode(true);
        item.append(ranger);
        item.setAttribute("value", textAsHTML(handle));
        rangersElement.append(item);
    }
}
function drawRangersToAdd() {
    const datalist = document.getElementById("ranger_handles");
    const handles = [];
    for (const handle in personnel) {
        handles.push(handle);
    }
    handles.sort((a, b) => a.localeCompare(b));
    datalist.replaceChildren();
    datalist.append(document.createElement("option"));
    if (personnel != null) {
        for (const handle of handles) {
            const ranger = personnel[handle];
            const option = document.createElement("option");
            option.value = handle;
            option.text = rangerAsString(ranger);
            datalist.append(option);
        }
    }
}
function rangerAsString(ranger) {
    return ranger.handle;
}
//
// Populate incident types list
//
let _typesItem = null;
function drawIncidentTypes() {
    if (_typesItem == null) {
        _typesItem = document.getElementById("incident_types_list")
            .getElementsByClassName("list-group-item")[0];
    }
    const incidentTypes = incident.incident_types ?? [];
    incidentTypes.sort();
    const typesElement = document.getElementById("incident_types_list");
    typesElement.replaceChildren();
    for (const incidentType of incidentTypes) {
        const item = _typesItem.cloneNode(true);
        item.append(textAsHTML(incidentType));
        item.setAttribute("value", textAsHTML(incidentType));
        typesElement.append(item);
    }
}
function drawIncidentTypesToAdd() {
    const datalist = document.getElementById("incident_types");
    datalist.replaceChildren();
    datalist.append(document.createElement("option"));
    for (const incidentType of incidentTypes) {
        const option = document.createElement("option");
        option.value = incidentType;
        datalist.append(option);
    }
}
//
// Populate location
//
function drawLocationName() {
    if (incident.location?.name) {
        const locName = document.getElementById("incident_location_name");
        locName.value = incident.location.name;
    }
}
function drawLocationAddressRadialHour() {
    let hour = null;
    if (incident.location?.radial_hour != null) {
        hour = padTwo(incident.location.radial_hour);
    }
    selectOptionWithValue(document.getElementById("incident_location_address_radial_hour"), hour);
}
function drawLocationAddressRadialMinute() {
    let minute = null;
    if (incident.location?.radial_minute != null) {
        minute = normalizeMinute(incident.location.radial_minute);
    }
    selectOptionWithValue(document.getElementById("incident_location_address_radial_minute"), minute);
}
function drawLocationAddressConcentric() {
    let concentric = null;
    if (incident.location?.concentric) {
        concentric = incident.location.concentric;
    }
    selectOptionWithValue(document.getElementById("incident_location_address_concentric"), concentric);
}
function drawLocationDescription() {
    if (incident.location?.description) {
        const description = document.getElementById("incident_location_description");
        description.value = incident.location.description;
    }
}
//
// Draw report entries
//
function drawMergedReportEntries() {
    const entries = (incident.report_entries ?? []).slice();
    if (attachedFieldReports) {
        const mergedCheckbox = document.getElementById("merge_reports_checkbox");
        if (mergedCheckbox.checked) {
            for (const report of attachedFieldReports) {
                for (const entry of report.report_entries ?? []) {
                    entry.merged = report.number;
                    entries.push(entry);
                }
            }
        }
    }
    entries.sort(compareReportEntries);
    drawReportEntries(entries);
}
let _reportsItem = null;
function drawAttachedFieldReports() {
    if (_reportsItem == null) {
        const elements = document.getElementById("attached_field_reports")
            .getElementsByClassName("list-group-item");
        if (elements.length === 0) {
            console.error("found no reportsItem");
            return;
        }
        _reportsItem = elements[0];
    }
    const reports = attachedFieldReports ?? [];
    reports.sort();
    const container = document.getElementById("attached_field_reports");
    container.replaceChildren();
    for (const report of reports) {
        const link = document.createElement("a");
        link.href = urlReplace(url_viewFieldReports) + report.number;
        link.innerText = fieldReportAsString(report);
        const item = _reportsItem.cloneNode(true);
        item.append(link);
        item.setAttribute("fr-number", report.number.toString());
        container.append(item);
    }
}
function drawFieldReportsToAttach() {
    const container = document.getElementById("attached_field_report_add_container");
    const select = document.getElementById("attached_field_report_add");
    select.replaceChildren();
    select.append(document.createElement("option"));
    if (!allFieldReports) {
        container.classList.add("hidden");
    }
    else {
        const unattachedGroup = document.createElement("optgroup");
        unattachedGroup.label = "Unattached to any incident";
        select.append(unattachedGroup);
        for (const report of allFieldReports) {
            // Skip field reports that *are* attached to an incident
            if (report.incident != null) {
                continue;
            }
            const option = document.createElement("option");
            option.value = report.number.toString();
            option.text = fieldReportAsString(report);
            select.append(option);
        }
        const attachedGroup = document.createElement("optgroup");
        attachedGroup.label = "Attached to another incident";
        select.append(attachedGroup);
        for (const report of allFieldReports) {
            // Skip field reports that *are not* attached to an incident
            if (report.incident == null) {
                continue;
            }
            // Skip field reports that are already attached this incident
            if (report.incident === incidentNumber) {
                continue;
            }
            const option = document.createElement("option");
            option.value = report.number.toString();
            option.text = fieldReportAsString(report);
            select.append(option);
        }
        select.append(document.createElement("optgroup"));
        container.classList.remove("hidden");
    }
}
//
// Editing
//
async function sendEdits(edits) {
    const number = incident.number;
    let url = urlReplace(url_incidents);
    if (number == null) {
        // We're creating a new incident.
        // required fields are ["state", "priority"];
        if (edits.state == null) {
            edits.state = incident.state;
        }
        if (edits.priority == null) {
            edits.priority = incident.priority;
        }
    }
    else {
        // We're editing an existing incident.
        edits.number = number;
        url += number;
    }
    const { resp, err } = await fetchJsonNoThrow(url, {
        body: JSON.stringify(edits),
    });
    if (err != null) {
        const message = `Failed to apply edit: ${err}`;
        await loadAndDisplayIncident();
        setErrorMessage(message);
        return { err: message };
    }
    if (number == null && resp != null) {
        // We created a new incident.
        // We need to find out the created incident number so that future
        // edits don't keep creating new resources.
        let newNumber = resp.headers.get("X-IMS-Incident-Number");
        // Check that we got a value back
        if (newNumber == null) {
            const msg = "No X-IMS-Incident-Number header provided.";
            setErrorMessage(msg);
            return { err: msg };
        }
        newNumber = parseInt(newNumber);
        // Check that the value we got back is valid
        if (isNaN(newNumber)) {
            const msg = "Non-integer X-IMS-Incident-Number header provided:" + newNumber;
            setErrorMessage(msg);
            return { err: msg };
        }
        // Store the new number in our incident object
        incidentNumber = incident.number = newNumber;
        // Update browser history to update URL
        drawIncidentTitle();
        window.history.pushState(null, document.title, urlReplace(url_viewIncidents) + newNumber);
    }
    await loadAndDisplayIncident();
    return { err: null };
}
registerSendEdits = sendEdits;
async function editState() {
    // @ts-ignore JQuery
    // const $state = $("#incident_state");
    const state = document.getElementById("incident_state");
    if (state.value === "closed" && (incident.incident_types ?? []).length === 0) {
        window.alert("Closing out this incident?\n" +
            "Please add an incident type!\n\n" +
            "Special cases:\n" +
            "    Junk: for erroneously-created Incidents\n" +
            "    Admin: for administrative information, i.e. not Incidents at all\n\n" +
            "See the Incident Types help link for more details.\n");
    }
    await editFromElement(state, "state");
}
async function editIncidentSummary() {
    const summaryInput = document.getElementById("incident_summary");
    await editFromElement(summaryInput, "summary");
}
async function editLocationName() {
    const locationInput = document.getElementById("incident_location_name");
    await editFromElement(locationInput, "location.name");
}
function transformAddressInteger(value) {
    if (!value) {
        return null;
    }
    return parseInt(value);
}
async function editLocationAddressRadialHour() {
    const hourInput = document.getElementById("incident_location_address_radial_hour");
    await editFromElement(hourInput, "location.radial_hour", transformAddressInteger);
}
async function editLocationAddressRadialMinute() {
    const minuteInput = document.getElementById("incident_location_address_radial_minute");
    await editFromElement(minuteInput, "location.radial_minute", transformAddressInteger);
}
async function editLocationAddressConcentric() {
    const concentricInput = document.getElementById("incident_location_address_concentric");
    await editFromElement(concentricInput, "location.concentric", transformAddressInteger);
}
async function editLocationDescription() {
    const descriptionInput = document.getElementById("incident_location_description");
    await editFromElement(descriptionInput, "location.description");
}
async function removeRanger(sender) {
    const parent = sender.parentElement;
    const rangerHandle = parent.getAttribute("value");
    await sendEdits({
        "ranger_handles": (incident.ranger_handles ?? []).filter(function (h) { return h !== rangerHandle; }),
    });
}
async function removeIncidentType(sender) {
    const parent = sender.parentElement;
    const incidentType = parent.getAttribute("value");
    await sendEdits({
        "incident_types": (incident.incident_types ?? []).filter(function (t) { return t !== incidentType; }),
    });
}
function normalize(str) {
    return str.toLowerCase().trim();
}
async function addRanger() {
    const select = document.getElementById("ranger_add");
    let handle = select.value;
    // make a copy of the handles
    const handles = (incident.ranger_handles ?? []).slice();
    // fuzzy-match on handle, to allow case insensitivity and
    // leading/trailing whitespace.
    if (!(handle in (personnel ?? []))) {
        const normalized = normalize(handle);
        for (const validHandle in personnel) {
            if (normalized === normalize(validHandle)) {
                handle = validHandle;
                break;
            }
        }
    }
    if (!(handle in (personnel ?? []))) {
        // Not a valid handle
        select.value = "";
        return;
    }
    if (handles.indexOf(handle) !== -1) {
        // Already in the list, so… move along.
        select.value = "";
        return;
    }
    handles.push(handle);
    const { err } = await sendEdits({ "ranger_handles": handles });
    if (err !== null) {
        controlHasError(select);
        select.value = "";
        return;
    }
    select.value = "";
    controlHasSuccess(select, 1000);
}
async function addIncidentType() {
    const select = document.getElementById("incident_type_add");
    let incidentType = select.value;
    // make a copy of the incident types
    const currentIncidentTypes = (incident.incident_types ?? []).slice();
    // fuzzy-match on incidentType, to allow case insensitivity and
    // leading/trailing whitespace.
    if (incidentTypes.indexOf(incidentType) === -1) {
        const normalized = normalize(incidentType);
        for (const validType of incidentTypes) {
            if (normalized === normalize(validType)) {
                incidentType = validType;
                break;
            }
        }
    }
    if (incidentTypes.indexOf(incidentType) === -1) {
        // Not a valid incident type
        select.value = "";
        return;
    }
    if (currentIncidentTypes.indexOf(incidentType) !== -1) {
        // Already in the list, so… move along.
        select.value = "";
        return;
    }
    currentIncidentTypes.push(incidentType);
    const { err } = await sendEdits({ "incident_types": currentIncidentTypes });
    if (err != null) {
        controlHasError(select);
        select.value = "";
        return;
    }
    select.value = "";
    controlHasSuccess(select, 1000);
}
async function detachFieldReport(sender) {
    const parent = sender.parentElement;
    const frNumber = parent.getAttribute("fr-number");
    const url = (urlReplace(url_fieldReports) + frNumber +
        "?action=detach;incident=" + incidentNumber);
    let { err } = await fetchJsonNoThrow(url, {
        body: JSON.stringify({}),
    });
    if (err != null) {
        const message = `Failed to detach field report ${err}`;
        console.log(message);
        await loadAllFieldReports();
        renderFieldReportData();
        setErrorMessage(message);
        return;
    }
    await loadAllFieldReports();
    renderFieldReportData();
}
async function attachFieldReport() {
    if (incidentNumber == null) {
        // Incident doesn't exist yet. Create it first.
        const { err } = await sendEdits({});
        if (err != null) {
            return;
        }
    }
    const select = document.getElementById("attached_field_report_add");
    const fieldReportNumber = select.value;
    const url = (urlReplace(url_fieldReports) + fieldReportNumber +
        "?action=attach;incident=" + incidentNumber);
    let { err } = await fetchJsonNoThrow(url, {
        body: JSON.stringify({}),
    });
    if (err != null) {
        const message = `Failed to attach field report: ${err}`;
        console.log(message);
        await loadAllFieldReports();
        renderFieldReportData();
        setErrorMessage(message);
        controlHasError(select);
        return;
    }
    await loadAllFieldReports();
    renderFieldReportData();
    controlHasSuccess(select, 1000);
}
// The success callback for a report entry strike call.
async function onStrikeSuccess() {
    await loadAndDisplayIncident();
    await loadAllFieldReports();
    renderFieldReportData();
    clearErrorMessage();
}
registerOnStrikeSuccess = onStrikeSuccess;
async function attachFile() {
    if (incidentNumber == null) {
        // Incident doesn't exist yet.  Create it first.
        const { err } = await sendEdits({});
        if (err != null) {
            return;
        }
    }
    const attachFile = document.getElementById("attach_file_input");
    const formData = new FormData();
    for (const f of attachFile.files ?? []) {
        formData.append("files", f);
    }
    const attachURL = urlReplace(url_incidentAttachments)
        .replace("<incident_number>", (incidentNumber ?? "").toString());
    const { err } = await fetchJsonNoThrow(attachURL, {
        body: formData
    });
    if (err != null) {
        const message = `Failed to attach file: ${err}`;
        setErrorMessage(message);
        return;
    }
    clearErrorMessage();
    attachFile.value = "";
    await loadAndDisplayIncident();
}
