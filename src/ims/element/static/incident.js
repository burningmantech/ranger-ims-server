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

function initIncidentPage() {
    function loadedIncident() {
        loadPersonnelAndCache(function() {
            drawRangers();
            drawRangersToAdd();
        });
        loadIncidentTypesAndCache(drawIncidentTypesToAdd);
        loadAndDisplayFieldReports();

        // for a new incident
        if (incident.number == null) {
            $("#incident_summary").focus();
        } else {
            // Scroll to report_entry_add field
            $("html, body").animate({scrollTop: $("#report_entry_add").offset().top}, 500);
            $("#report_entry_add").focus();
        }

        // Warn the user if they're about to navigate away with unsaved text.
        window.addEventListener("beforeunload", function (e) {
            if (document.getElementById("report_entry_add").value !== "") {
                e.preventDefault();
            }
        });
    }

    function loadedBody() {
        addLocationAddressOptions();
        disableEditing();
        loadAndDisplayIncident(loadedIncident);

        // Updates...it's fine to ignore the returned promise here
        requestEventSourceLock();

        const incidentChannel = new BroadcastChannel(incidentChannelName);
        incidentChannel.onmessage = function (e) {
            const number = e.data["incident_number"];
            const event = e.data["event_id"]
            const updateAll = e.data["update_all"];

            if (updateAll || (event === eventID && number === incidentNumber)) {
                console.log("Got incident update: " + number);
                loadAndDisplayIncident();
                loadAndDisplayFieldReports();
            }
        }
        // TODO(issue/1498): this page doesn't currently listen for Field Report
        //  updates, but it probably should. Those updates could be used to add
        //  to the merged report entries or to the list of Field Reports available
        //  to be attached. We just want to be careful not to reload all the Field
        //  Reports on any update, lest we introduce heightened latency.

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
            if ((e.ctrlKey || e.altKey) && e.key === "Enter") {
                submitReportEntry();
            }
        });
    }

    loadBody(loadedBody);
}


//
// Load incident
//

let incident = null;

function loadIncident(success) {
    let number = null;
    if (incident == null) {
        // First time here.  Use page JavaScript initial value.
        number = incidentNumber;
    } else {
        // We have an incident already.  Use that number.
        number = incident.number;
    }

    function ok(data, status, xhr) {
        incident = data;

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        disableEditing();
        const message = "Failed to load Incident " + number + ": " + error;
        console.error(message);
        setErrorMessage(message);
    }

    if (number == null) {
        ok({
            "number": null,
            "state": "new",
            "priority": 3,
            "summary": "",
        });
    } else {
        const url = incidentsURL + number;
        jsonRequest(url, null, ok, fail);
    }
}

// Set the user-visible error information on the page to the provided string.
function setErrorMessage(msg) {
    msg = "Error: (Cause: " + msg + ")"
    $("#error_info").removeClass("hidden");
    $("#error_text").text(msg);
}

function clearErrorMessage() {
    $("#error_info").addClass("hidden");
    $("#error_text").text("");
}

function loadAndDisplayIncident(success) {
    function loaded() {
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

        if (success) {
            success();
        }
    }

    loadIncident(loaded);
}


function loadAndDisplayFieldReports() {
    loadAllFieldReports(function () {
        drawFieldReportsToAttach();
    });
    loadAttachedFieldReports(function () {
        drawMergedReportEntries();
        drawAttachedFieldReports();
    });
}


//
// Load personnel
//

let personnel = null;

function loadPersonnelAndCache(success) {
    const cached = localLoadPersonnel();

    function loadedPersonnel() {
        localCachePersonnel(personnel);
        success();
    }

    if (cached == null) {
        loadPersonnel(loadedPersonnel);
    } else {
        personnel = cached;
        success();
    }
}


function loadPersonnel(success) {
    function ok(data, status, xhr) {
        const _personnel = {};
        for (const record of data) {
            // Filter inactive Rangers out
            // FIXME: better yet: filter based on on-playa state
            switch (record.status) {
                case "active":
                case "vintage":
                    break;
                default:
                    continue;
            }

            _personnel[record.handle] = record;
        }
        personnel = _personnel

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        const message = "Failed to load personnel";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    jsonRequest(urlReplace(url_personnel + "?event_id=<event_id>"), null, ok, fail);
}


function localCachePersonnel(personnel) {
    if (personnel == null) {
        alert("Attempt to cache undefined personnel")
        return;
    }
    lscache.set("ims.personnel", personnel, 10);
}


function localLoadPersonnel() {
    return lscache.get("ims.personnel");
}


//
// Load incident types
//

let incidentTypes = null;


function loadIncidentTypesAndCache(success) {
    const cached = localLoadIncidentTypes();

    function loadedIncidentTypes() {
        localCacheIncidentTypes(incidentTypes);
        success();
    }

    if (cached == null) {
        loadIncidentTypes(loadedIncidentTypes);
    } else {
        incidentTypes = cached;
        success();
    }
}


function loadIncidentTypes(success) {
    function ok(data, status, xhr) {
        const _incidentTypes = [];
        for (const record of data) {
            _incidentTypes.push(record)
        }
        _incidentTypes.sort()
        incidentTypes = _incidentTypes

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        const message = "Failed to load incident types";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    jsonRequest(url_incidentTypes, null, ok, fail);
}


function localCacheIncidentTypes(incidentTypes) {
    if (incidentTypes == null) {
        alert("Attempt to cache undefined incident types")
        return;
    }
    lscache.set("ims.incident_types", incidentTypes, 10);
}


function localLoadIncidentTypes() {
    return lscache.get("ims.incident_types");
}


//
// Load all field reports
//

let allFieldReports = null;

function loadAllFieldReports(success) {
    if (allFieldReports === undefined) {
        return;
    }

    function ok(data, status, xhr) {
        const _allFieldReports = [];
        for (const d of data) {
            _allFieldReports.push(d);
        }
        // apply a descending sort based on the field report number,
        // being cautious about field report number being null
        _allFieldReports.sort(function (a, b) {
            return (b.number ?? -1) - (a.number ?? -1);
        })
        allFieldReports = _allFieldReports;

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        if (xhr.status === 403) {
            // We're not allowed to look these up.
            allFieldReports = undefined;
        } else {
            const message = "Failed to load field reports";
            console.error(message + ": " + error);
            setErrorMessage(message);
        }
    }

    jsonRequest(
        urlReplace(url_fieldReports),
        null, ok, fail,
    );
}


//
// Load attached field reports
//

let attachedFieldReports = null;

function loadAttachedFieldReports(success) {
    if (incidentNumber == null) {
        return;
    }

    function ok(data, status, xhr) {
        attachedFieldReports = data;

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        const message = "Failed to load attached field reports";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    const url = (
        urlReplace(url_fieldReports) + "?incident=" + incidentNumber
    );

    jsonRequest(url, null, ok, fail);
}


//
// Draw all fields
//

function drawIncidentFields() {
    drawTitle();
    drawNumber();
    drawState();
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
            ranger = handle;
        } else {
            ranger = rangerAsString(personnel[handle]);
        }
        const item = _rangerItem.clone();
        item.append(textAsHTML(ranger));
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
    let result = ranger.handle;

    if (ranger.name) {
        result += " (" + ranger.name + ")";
    }

    if (ranger.status === "vintage") {
        result += "*";
    }

    return result;
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

function sendEdits(edits, success, error) {
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

    function ok(data, status, xhr) {
        if (number == null) {
            // We created a new incident.
            // We need to find out the create incident number so that future
            // edits don't keep creating new resources.

            let newNumber = xhr.getResponseHeader("X-IMS-Incident-Number")
            // Check that we got a value back
            if (newNumber == null) {
                fail("No X-IMS-Incident-Number header provided.", status, xhr);
                return;
            }

            newNumber = parseInt(newNumber);
            // Check that the value we got back is valid
            if (isNaN(newNumber)) {
                fail(
                    "Non-integer X-IMS-Incident-Number header provided:" + newNumber,
                    status, xhr
                );
                return;
            }

            // Store the new number in our incident object
            incidentNumber = incident.number = newNumber;

            // Update browser history to update URL
            drawTitle();
            window.history.pushState(
                null, document.title, viewIncidentsURL + newNumber
            );
        }

        success();
        loadAndDisplayIncident();
    }

    function fail(requestError, status, xhr) {
        const message = "Failed to apply edit";
        console.log(message + ": " + requestError);
        error();
        loadAndDisplayIncident();
        setErrorMessage(message);
    }

    jsonRequest(url, edits, ok, fail);
}


function editState() {
    editFromElement($("#incident_state"), "state");
}


function editPriority() {
    editFromElement($("#incident_priority"), "priority", parseInt);
}


function editSummary() {
    editFromElement($("#incident_summary"), "summary");
}


function editLocationName() {
    editFromElement($("#incident_location_name"), "location.name");
}


function transformAddressInteger(value) {
    if (!value) {
        return null;
    }
    return parseInt(value);
}


function editLocationAddressRadialHour() {
    editFromElement(
        $("#incident_location_address_radial_hour"),
        "location.radial_hour",
        transformAddressInteger
    );
}


function editLocationAddressRadialMinute() {
    editFromElement(
        $("#incident_location_address_radial_minute"),
        "location.radial_minute",
        transformAddressInteger
    );
}


function editLocationAddressConcentric() {
    editFromElement(
        $("#incident_location_address_concentric"),
        "location.concentric",
        transformAddressInteger
    );
}


function editLocationDescription() {
    editFromElement($("#incident_location_description"), "location.description");
}


function removeRanger(sender) {
    sender = $(sender);

    const rangerHandle = sender.parent().attr("value");

    function ok() {
        // FIXME
        // controlHasSuccess(sender);
    }

    function fail() {
        // FIXME
        // controlHasError(sender);
    }

    sendEdits(
        {
            "ranger_handles": incident.ranger_handles.filter(
                function(h) { return h !== rangerHandle }
            ),
        },
        ok, fail
    );
}


function removeIncidentType(sender) {
    sender = $(sender);

    const incidentType = sender.parent().attr("value");

    function ok() {
        // FIXME
        // controlHasSuccess(sender);
    }

    function fail() {
        // FIXME
        // controlHasError(sender);
    }

    sendEdits(
        {
            "incident_types": incident.incident_types.filter(
                function(t) { return t !== incidentType }
            ),
        },
        ok, fail
    );
}

function normalize(str) {
    return str.toLowerCase().trim();
}

function addRanger() {
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

    function ok() {
        select.val("");
        controlHasSuccess(select, 1000);
    }

    function fail() {
        controlHasError(select);
        select.val("");
    }

    sendEdits({"ranger_handles": handles}, ok, fail);
}


function addIncidentType() {
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

    function ok() {
        select.val("");
        controlHasSuccess(select, 1000);
    }

    function fail() {
        controlHasError(select);
        select.val("");
    }

    sendEdits({"incident_types": currentIncidentTypes}, ok, fail);
}


function detachFieldReport(sender) {
    sender = $(sender);

    const fieldReport = sender.parent().data();

    function ok(data, status, xhr) {
        // FIXME
        // controlHasSuccess(sender);
        loadAndDisplayFieldReports();
    }

    function fail(requestError, status, xhr) {
        // FIXME
        // controlHasError(sender);

        const message = "Failed to detach field report";
        console.log(message + ": " + requestError);
        loadAndDisplayFieldReports();
        setErrorMessage(message);
    }

    const url = (
        urlReplace(url_fieldReports) + fieldReport.number +
        "?action=detach;incident=" + incidentNumber
    );

    jsonRequest(url, {}, ok, fail);
}


function attachFieldReport() {
    if (incidentNumber == null) {
        // Incident doesn't exist yet.  Create it and then retry.
        sendEdits({}, attachFieldReport);
        return;
    }

    const select = $("#attached_field_report_add");
    const fieldReportNumber = $(select).val();

    function ok(data, status, xhr) {
        loadAndDisplayFieldReports();
        controlHasSuccess(select, 1000);
    }

    function fail(requestError, status, xhr) {
        const message = "Failed to attach field report";
        console.log(message + ": " + requestError);
        loadAndDisplayFieldReports();
        setErrorMessage(message);
        controlHasError(select);
    }

    const url = (
        urlReplace(url_fieldReports) + fieldReportNumber +
        "?action=attach;incident=" + incidentNumber
    );

    jsonRequest(url, {}, ok, fail);
}


// The success callback for a report entry strike call.
function onStrikeSuccess() {
    loadAndDisplayIncident();
    loadAndDisplayFieldReports();
    clearErrorMessage();
}
