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
        $("#incident_summary").focus();
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
        const number = e.data["incident_number"];
        const event = e.data["event_id"]
        const updateAll = e.data["update_all"];

        if (updateAll || (event === eventID && number === incidentNumber)) {
            console.log("Got incident update: " + number);
            await loadAndDisplayIncident();
            await loadAllFieldReports();
            renderFieldReportData();
        }
    }

    const fieldReportChannel = new BroadcastChannel(fieldReportChannelName);
    fieldReportChannel.onmessage = async function (e) {
        const updateAll = e.data["update_all"];
        if (updateAll) {
            console.log("Updating all field reports");
            await loadAllFieldReports();
            renderFieldReportData();
            return;
        }

        const number = e.data["field_report_number"];
        const event = e.data["event_id"]
        if (event === eventID) {
            console.log("Got field report update: " + number);
            await loadFieldReport(number);
            renderFieldReportData();
            return;
        }
    }

    // Keyboard shortcuts
    document.addEventListener("keydown", function(e) {
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
            $("#helpModal").modal("toggle");
        }
        // a --> jump to add a new report entry
        if (e.key === "a") {
            e.preventDefault();
            // Scroll to report_entry_add field
            $("html, body").animate({scrollTop: $("#report_entry_add").offset().top}, 500);
            $("#report_entry_add").focus();
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
    document.getElementById("helpModal").addEventListener("keydown", function(e) {
        if (e.key === "?") {
            $("#helpModal").modal("toggle");
        }
    });
    $("#report_entry_add")[0].addEventListener("keydown", function (e) {
        const submitEnabled = !$("#report_entry_submit").hasClass("disabled");
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
        number = incidentNumber;
    } else {
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
    } else {
        const {json, err} = await fetchJsonNoThrow(incidentsURL + number);
        if (err != null) {
            disableEditing();
            const message = `Failed to load Incident ${number}: ${err}`;
            console.error(message);
            setErrorMessage(message);
            return {err: message};
        }
        incident = json;
    }
    return {err: null};
}

// Set the user-visible error information on the page to the provided string.
function setErrorMessage(msg) {
    msg = "Error: (Cause: " + msg + ")"
    document.getElementById("error_info").classList.remove("hidden");
    document.getElementById("error_text").textContent = msg;
    document.getElementById("error_info").scrollIntoView();
}

function clearErrorMessage() {
    document.getElementById("error_info").classList.add("hidden");
    document.getElementById("error_text").textContent = "";
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

    if (incident.number == null) {
        hide($("#attach-file-form :input"));
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
    const {json, err} = await fetchJsonNoThrow(urlReplace(url_personnel + "?event_id=<event_id>"));
    if (err != null) {
        const message = `Failed to load personnel: ${err}`;
        console.error(message);
        setErrorMessage(message);
        return {err: message};
    }
    const _personnel = {};
    for (const record of json) {
        // Filter inactive Rangers out
        // FIXME: better yet: filter based on on-playa state
        switch (record.status) {
            case "active":
                break;
            default:
                continue;
        }

        _personnel[record.handle] = record;
    }
    personnel = _personnel
}


//
// Load incident types
//

let incidentTypes = null;


async function loadIncidentTypes() {
    const {json, err} = await fetchJsonNoThrow(url_incidentTypes);
    if (err != null) {
        const message = `Failed to load incident types: ${err}`;
        console.error(message);
        setErrorMessage(message);
        return {err: message};
    }
    const _incidentTypes = [];
    for (const record of json) {
        _incidentTypes.push(record)
    }
    _incidentTypes.sort()
    incidentTypes = _incidentTypes
}

//
// Load all field reports
//

let allFieldReports = null;

async function loadAllFieldReports() {
    if (allFieldReports === undefined) {
        return;
    }

    const {resp, json, err} = await fetchJsonNoThrow(urlReplace(url_fieldReports));
    if (err != null) {
        if (resp.status === 403) {
            // We're not allowed to look these up.
            allFieldReports = undefined;
            console.error("Got a 403 looking up field reports");
            return {err: null};
        } else {
            const message = `Failed to load field reports: ${err}`;
            console.error(message);
            setErrorMessage(message);
            return {err: message};
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
    })
    allFieldReports = _allFieldReports;
    return {err: null};
}

async function loadFieldReport(fieldReportNumber) {
    if (allFieldReports === undefined) {
        return;
    }

    const {resp, json, err} = await fetchJsonNoThrow(
        urlReplace(url_fieldReport).replace("<field_report_number>", fieldReportNumber));
    if (err != null) {
        if (resp.status !== 403) {
            const message = `Failed to load field report ${fieldReportNumber} ${err}`;
            console.error(message);
            setErrorMessage(message);
            return {err: message};
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
        allFieldReports.push(json);
        // apply a descending sort based on the field report number,
        // being cautious about field report number being null
        allFieldReports.sort(function (a, b) {
            return (b.number ?? -1) - (a.number ?? -1);
        })
    }

    return {err: null};
}


//
// Load attached field reports
//

let attachedFieldReports = null;

function loadAttachedFieldReports() {
    if (incidentNumber == null) {
        return;
    }
    _attachedFieldReports = [];
    for (const fr of allFieldReports) {
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
    drawTitle();
    drawNumber();
    drawState();
    drawCreated();
    drawPriority();
    drawSummary();
    drawRangers();
    drawIncidentTypes();
    drawLocationName();
    drawLocationAddressRadialHour();
    drawLocationAddressRadialMinute();
    drawLocationAddressConcentric();
    drawLocationDescription();
    toggleShowHistory();
    drawMergedReportEntries();

    $("#report_entry_add").on("input", reportEntryEdited);
}


//
// Add option elements to location address select elements
//

function addLocationAddressOptions() {
    const hours = range(1, 13);
    for (let hour of hours) {
        hour = padTwo(hour);
        $("#incident_location_address_radial_hour")
            .append($("<option />", { "value": hour, "text": hour }))
            ;
    }

    const minutes = range(0, 12, 5);
    for (let minute of minutes) {
        minute = padTwo(minute);
        $("#incident_location_address_radial_minute")
            .append($("<option />", { "value": minute, "text": minute }))
            ;
    }

    for (const id in concentricStreetNameByID) {
        const name = concentricStreetNameByID[id];
        $("#incident_location_address_concentric")
            .append($("<option />", { "value": id, "text": name }))
            ;
    }
}


//
// Populate page title
//

function drawTitle() {
    document.title = incidentAsString(incident);
}


//
// Populate incident number
//

function drawNumber() {
    let number = incident.number;
    if (number == null) {
        number = "(new)";
    }
    $("#incident_number").text(number);
}


//
// Populate incident state
//

function drawState() {
    selectOptionWithValue(
        $("#incident_state"), stateForIncident(incident)
    );
}


//
// Populate created datetime
//

function drawCreated() {
    const date = incident.created;
    if (date == null) {
        return;
    }
    const d = Date.parse(date);
    $("#created_datetime").text(`${shortDate.format(d)} ${shortTimeSec.format(d)}`);
    $("#created_datetime").attr("title", fullDateTime.format(d));
}

//
// Populate incident priority
//

function drawPriority() {
    selectOptionWithValue(
        $("#incident_priority"), incident.priority
    );
}


//
// Populate incident summary
//

function drawSummary() {
    if (incident.summary) {
        $("#incident_summary").val(incident.summary);
        $("#incident_summary").attr("placeholder", "");
        return;
    }

    $("#incident_summary")[0].removeAttribute("value");
    const summarized = summarizeIncident(incident);
    if (summarized) {
        // only replace the placeholder if it would be nonempty
        $("#incident_summary").attr("placeholder", summarized);
    }
}


//
// Populate Rangers list
//

let _rangerItem = null;

function drawRangers() {
    if (_rangerItem == null) {
        _rangerItem = $("#incident_rangers_list")
            .children(".list-group-item:first")
            ;
    }

    const items = [];

    const handles = incident.ranger_handles??[];
    handles.sort((a, b) => a.localeCompare(b));

    for (const handle of handles) {
        let ranger = null;
        if (personnel?.[handle] == null) {
            ranger = textAsHTML(handle);
        } else {
            const person = personnel[handle];
            ranger = $("<a>", {
                text: textAsHTML(rangerAsString(person)),
                href: `${clubhousePersonURL}/${person.directory_id}`,
            });
        }
        const item = _rangerItem.clone();
        item.append(ranger);
        item.attr("value", textAsHTML(handle));
        items.push(item);
    }

    const container = $("#incident_rangers_list");
    container.empty();
    container.append(items);
}


function drawRangersToAdd() {
    const datalist = $("#ranger_handles");

    const handles = [];
    for (const handle in personnel) {
        handles.push(handle);
    }
    handles.sort((a, b) => a.localeCompare(b));

    datalist.empty();
    datalist.append($("<option />"));

    for (const handle of handles) {
        const ranger = personnel[handle];

        const option = $("<option />");
        option.val(handle);
        option.text(rangerAsString(ranger));

        datalist.append(option);
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
        _typesItem = $("#incident_types_list")
            .children(".list-group-item:first")
            ;
    }

    const items = [];

    const incidentTypes = incident.incident_types??[];
    incidentTypes.sort();

    for (const incidentType of incidentTypes) {
        const item = _typesItem.clone();
        item.attr("value", textAsHTML(incidentType));
        item.append(textAsHTML(incidentType));
        items.push(item);
    }

    const container = $("#incident_types_list");
    container.empty();
    container.append(items);
}


function drawIncidentTypesToAdd() {
    const datalist = $("#incident_types");

    datalist.empty();
    datalist.append($("<option />"));

    for (const incidentType of incidentTypes) {
        const option = $("<option />");
        option.val(incidentType);

        datalist.append(option);
    }
}


//
// Populate location
//

function drawLocationName() {
    if (incident.location?.name) {
        $("#incident_location_name").val(incident.location.name);
    }
}


function drawLocationAddressRadialHour() {
    let hour = null;
    if (incident.location?.radial_hour != null) {
        hour = padTwo(incident.location.radial_hour);
    }
    selectOptionWithValue(
        $("#incident_location_address_radial_hour"), hour
    );
}


function drawLocationAddressRadialMinute() {
    let minute = null;
    if (incident.location?.radial_minute != null) {
        minute = normalizeMinute(incident.location.radial_minute);
    }
    selectOptionWithValue(
        $("#incident_location_address_radial_minute"), minute
    );
}


function drawLocationAddressConcentric() {
    let concentric = null;
    if (incident.location?.concentric) {
        concentric = incident.location.concentric;
    }
    selectOptionWithValue(
        $("#incident_location_address_concentric"), concentric
    );
}


function drawLocationDescription() {
    if (incident.location?.description) {
        $("#incident_location_description")
            .val(incident.location.description)
            ;
    }
}


//
// Draw report entries
//

function drawMergedReportEntries() {
    const entries = [];

    if (incident.report_entries) {
        $.merge(entries, incident.report_entries);
    }

    if (attachedFieldReports) {
        if ($("#merge_reports_checkbox").is(":checked")) {
            for (const report of attachedFieldReports) {
                for (const entry of report.report_entries??[]) {
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
        _reportsItem = $("#attached_field_reports")
            .children(".list-group-item:first")
            ;
    }

    const items = [];

    const reports = attachedFieldReports??[];
    reports.sort();

    for (const report of reports) {
        const item = _reportsItem.clone();
        const link = $("<a />");
        link.attr("href", urlReplace(url_viewFieldReports) + report.number);
        link.text(fieldReportAsString(report));
        item.append(link);
        item.data(report);
        items.push(item);
    }

    const container = $("#attached_field_reports");
    container.empty();
    container.append(items);
}


function drawFieldReportsToAttach() {
    const container = $("#attached_field_report_add_container");
    const select = $("#attached_field_report_add");

    select.empty();
    select.append($("<option />"));

    if (!allFieldReports) {
        container.addClass("hidden");
    } else {

        select.append($("<optgroup label=\"Unattached to any incident\">"));
        for (const report of allFieldReports) {
            // Skip field reports that *are* attached to an incident
            if (report.incident != null) {
                continue;
            }
            const option = $("<option />");
            option.val(report.number);
            option.text(fieldReportAsString(report));

            select.append(option);
        }
        select.append($("</optgroup>"));

        select.append($("<optgroup label=\"Attached to another incident\">"));
        for (const report of allFieldReports) {
            // Skip field reports that *are not* attached to an incident
            if (report.incident == null) {
                continue;
            }
            // Skip field reports that are already attached this incident
            if (report.incident === incidentNumber) {
                continue;
            }
            const option = $("<option />");
            option.val(report.number);
            option.text(fieldReportAsString(report));

            select.append(option);
        }
        select.append($("</optgroup>"));

        container.removeClass("hidden");
    }
}


//
// Editing
//

async function sendEdits(edits) {
    const number = incident.number;
    let url = incidentsURL;

    if (number == null) {
        // We're creating a new incident.
        const required = ["state", "priority"];
        for (const key of required) {
            if (edits[key] == null) {
                edits[key] = incident[key];
            }
        }
    } else {
        // We're editing an existing incident.
        edits.number = number;
        url += number;
    }

    const {resp, err} = await fetchJsonNoThrow(url, {
        body: edits,
    });

    if (err != null) {
        const message = `Failed to apply edit: ${err}`;
        await loadAndDisplayIncident();
        setErrorMessage(message);
        return {err: message}
    }

    if (number == null) {
        // We created a new incident.
        // We need to find out the create incident number so that future
        // edits don't keep creating new resources.

        let newNumber = resp.headers.get("X-IMS-Incident-Number")
        // Check that we got a value back
        if (newNumber == null) {
            const msg = "No X-IMS-Incident-Number header provided.";
            setErrorMessage(msg);
            return {err: msg};
        }

        newNumber = parseInt(newNumber);
        // Check that the value we got back is valid
        if (isNaN(newNumber)) {
            const msg = "Non-integer X-IMS-Incident-Number header provided:" + newNumber;
            setErrorMessage(msg);
            return {err: msg};
        }

        // Store the new number in our incident object
        incidentNumber = incident.number = newNumber;

        // Update browser history to update URL
        drawTitle();
        window.history.pushState(
            null, document.title, viewIncidentsURL + newNumber
        );
    }

    await loadAndDisplayIncident();
    return {err: null};
}


async function editState() {
    const $state = $("#incident_state");

    if ($state.val() === "closed" && (incident.incident_types??[]).length === 0) {
        window.alert(
            "Closing out this incident?\n"+
            "Please add an incident type!\n\n" +
            "Special cases:\n" +
            "    Junk: for erroneously-created Incidents\n" +
            "    Admin: for administrative information, i.e. not Incidents at all\n\n" +
            "See the Incident Types help link for more details.\n"
        );
    }

    await editFromElement($state, "state");
}


async function editSummary() {
    await editFromElement($("#incident_summary"), "summary");
}


async function editLocationName() {
    await editFromElement($("#incident_location_name"), "location.name");
}


function transformAddressInteger(value) {
    if (!value) {
        return null;
    }
    return parseInt(value);
}


async function editLocationAddressRadialHour() {
    await editFromElement(
        $("#incident_location_address_radial_hour"),
        "location.radial_hour",
        transformAddressInteger
    );
}


async function editLocationAddressRadialMinute() {
    await editFromElement(
        $("#incident_location_address_radial_minute"),
        "location.radial_minute",
        transformAddressInteger
    );
}


async function editLocationAddressConcentric() {
    await editFromElement(
        $("#incident_location_address_concentric"),
        "location.concentric",
        transformAddressInteger
    );
}


async function editLocationDescription() {
    await editFromElement($("#incident_location_description"), "location.description");
}


async function removeRanger(sender) {
    sender = $(sender);

    const rangerHandle = sender.parent().attr("value");

    await sendEdits(
        {
            "ranger_handles": incident.ranger_handles.filter(
                function(h) { return h !== rangerHandle }
            ),
        },
    );
}


async function removeIncidentType(sender) {
    sender = $(sender);

    const incidentType = sender.parent().attr("value");
    await sendEdits({
        "incident_types": incident.incident_types.filter(
            function(t) { return t !== incidentType }
        ),
    });
}

function normalize(str) {
    return str.toLowerCase().trim();
}

async function addRanger() {
    const select = $("#ranger_add");
    let handle = $(select).val();

    // make a copy of the handles
    const handles = (incident.ranger_handles??[]).slice();

    // fuzzy-match on handle, to allow case insensitivity and
    // leading/trailing whitespace.
    if (!(handle in personnel)) {
        const normalized = normalize(handle);
        for (const validHandle in personnel) {
            if (normalized === normalize(validHandle)) {
                handle = validHandle;
                break;
            }
        }
    }
    if (!(handle in personnel)) {
        // Not a valid handle
        select.val("");
        return;
    }

    if (handles.indexOf(handle) !== -1) {
        // Already in the list, so… move along.
        select.val("");
        return;
    }

    handles.push(handle);

    const {err} = await sendEdits({"ranger_handles": handles});
    if (err !== null) {
        controlHasError(select);
        select.val("");
        return;
    }
    select.val("");
    controlHasSuccess(select, 1000);
}


async function addIncidentType() {
    const select = $("#incident_type_add");
    let incidentType = $(select).val();

    // make a copy of the incident types
    const currentIncidentTypes = (incident.incident_types??[]).slice();

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
        select.val("");
        return;
    }

    if (currentIncidentTypes.indexOf(incidentType) !== -1) {
        // Already in the list, so… move along.
        select.val("");
        return;
    }

    currentIncidentTypes.push(incidentType);

    const {err} = await sendEdits({"incident_types": currentIncidentTypes});
    if (err != null) {
        controlHasError(select);
        select.val("");
        return;
    }
    select.val("");
    controlHasSuccess(select, 1000);
}


async function detachFieldReport(sender) {
    sender = $(sender);

    const fieldReport = sender.parent().data();

    const url = (
        urlReplace(url_fieldReports) + fieldReport.number +
        "?action=detach;incident=" + incidentNumber
    );
    let {err} = await fetchJsonNoThrow(url, {
        body: {},
    })
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
        const {err} = await sendEdits({});
        if (err != null) {
            return;
        }
    }

    const select = $("#attached_field_report_add");
    const fieldReportNumber = $(select).val();

    const url = (
        urlReplace(url_fieldReports) + fieldReportNumber +
        "?action=attach;incident=" + incidentNumber
    );
    let {err} = await fetchJsonNoThrow(url, {
        body: {},
    })
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

async function attachFile() {
    if (incidentNumber == null) {
        // Incident doesn't exist yet.  Create it first.
        const {err} = await sendEdits({});
        if (err != null) {
            return;
        }
    }
    const attachFile = document.getElementById("attach_file_input");
    const formData = new FormData();

    for (const f of attachFile.files) {
        formData.append("files", f);
    }

    const attachURL = urlReplace(url_incidentAttachments).replace("<incident_number>", incidentNumber);
    const {err} = await fetchJsonNoThrow(attachURL, {
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
