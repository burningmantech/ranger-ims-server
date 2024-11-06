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
        loadAndDisplayIncidentReports();

        // Scroll to incident_report_add field
        $("html, body").animate({ scrollTop: $("#incident_report_add").offset().top }, 500);
        $("#incident_report_add").focus();

        // Warn the user if they're about to navigate away with unsaved text.
        window.addEventListener('beforeunload', function (e) {
            if (document.getElementById("incident_report_add").value !== '') {
                e.preventDefault();
            }
        });
    }

    function loadedBody() {
        addLocationAddressOptions();
        disableEditing();
        loadAndDisplayIncident(loadedIncident);

        // Updates
        requestEventSourceLock();

        const incidentChannel = new BroadcastChannel(incidentChannelName);
        incidentChannel.onmessage = function (e) {
            const number = e.data;
            if (number == incidentNumber) {
                console.log("Got incident update: " + number);
                loadAndDisplayIncident();
                loadAndDisplayIncidentReports();
            }
        }

        // Keyboard shortcuts

        var command = false;

        function addFieldKeyDown() {
            var keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode == 17 || keyCode == 18) {
                command = true;
            }

            // console.warn(keyCode);
        }

        function addFieldKeyUp() {
            var keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode == 17 || keyCode == 18) {
                command = false;
                return;
            }

            // 13 = return
            if (command && keyCode == 13) {
                submitReportEntry();
            }
        }

        $("#incident_report_add")[0].onkeydown = addFieldKeyDown;
        $("#incident_report_add")[0].onkeyup   = addFieldKeyUp;
    }

    loadBody(loadedBody);
}


//
// Load incident
//

var incident = null;

function loadIncident(success) {
    var number = null;
    if (incident == null) {
        // First time here.  Use page JavaScript initial value.
        number = incidentNumber;
    } else {
        // We have an incident already.  Use that number.
        number = incident.number;
    }

    function ok(data, status, xhr) {
        incident = data;

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        disableEditing();
        var message = "Failed to load incident";
        console.error(message + ": " + error);
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
        var url = incidentsURL + number;
        jsonRequest(url, null, ok, fail);
    }
}

// Set the user-visible error information on the page to the provided string.
function setErrorMessage(msg) {
    msg = "Error: Please reload this page. (Cause: " + msg + ")"
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
            var message = "Incident failed to load";
            console.log(message);
            setErrorMessage(message);
            return;
        }

        drawIncidentFields();
        clearErrorMessage();

        if (editingAllowed) {
            enableEditing();
        }

        if (success != undefined) {
            success();
        }
    }

    loadIncident(loaded);
}


function loadAndDisplayIncidentReports() {
    loadUnattachedIncidentReports(function () {
        drawMergedReportEntries();
        drawIncidentReportsToAttach();
    });
    loadAttachedIncidentReports(function () {
        drawMergedReportEntries();
        drawAttachedIncidentReports();
    });
}


//
// Load personnel
//

var personnel = null;


function loadPersonnelAndCache(success) {
    var cached = localLoadPersonnel();

    function loadedPersonnel() {
        localCachePersonnel(personnel);
        success();
    }

    if (cached == undefined) {
        loadPersonnel(loadedPersonnel);
    } else {
        personnel = cached;
        success();
    }
}


function loadPersonnel(success) {
    function ok(data, status, xhr) {
        var _personnel = {};
        for (var i in data) {
            var record = data[i];

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

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        var message = "Failed to load personnel";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    jsonRequest(urlReplace(url_personnel + "?event_id=<event_id>"), null, ok, fail);
}


function localCachePersonnel(personnel) {
    if (personnel == undefined) {
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

var incidentTypes = null;


function loadIncidentTypesAndCache(success) {
    var cached = localLoadIncidentTypes();

    function loadedIncidentTypes() {
        localCacheIncidentTypes(incidentTypes);
        success();
    }

    if (cached == undefined) {
        loadIncidentTypes(loadedIncidentTypes);
    } else {
        incidentTypes = cached;
        success();
    }
}


function loadIncidentTypes(success) {
    function ok(data, status, xhr) {
        var _incidentTypes = [];
        for (var i in data) {
            _incidentTypes.push(data[i])
        }
        _incidentTypes.sort()
        incidentTypes = _incidentTypes

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        var message = "Failed to load incident types";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    jsonRequest(url_incidentTypes, null, ok, fail);
}


function localCacheIncidentTypes(incidentTypes) {
    if (incidentTypes == undefined) {
        alert("Attempt to cache undefined incident types")
        return;
    }
    lscache.set("ims.incident_types", incidentTypes, 10);
}


function localLoadIncidentTypes() {
    return lscache.get("ims.incident_types");
}


//
// Load unattached field reports
//

var unattachedIncidentReports = null;

function loadUnattachedIncidentReports(success) {
    if (unattachedIncidentReports === undefined) {
        return;
    }

    function ok(data, status, xhr) {
        const _unattachedIncidentReports = [];
        for (const d of data) {
            _unattachedIncidentReports.push(d);
        }
        // apply an ascending sort based on the field report number,
        // being cautious about field report number being null
        _unattachedIncidentReports.sort(function (a, b) {
            return (a.number ?? -1) - (b.number ?? -1);
        })
        unattachedIncidentReports = _unattachedIncidentReports;

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        if (xhr.status == 403) {
            // We're not allowed to look these up.
            unattachedIncidentReports = undefined;
        } else {
            var message = "Failed to load unattached field reports";
            console.error(message + ": " + error);
            setErrorMessage(message);
        }
    }

    jsonRequest(
        urlReplace(url_incidentReports),
        null, ok, fail,
    );
}


//
// Load attached field reports
//

var attachedIncidentReports = null;

function loadAttachedIncidentReports(success) {
    if (incidentNumber == null) {
        return;
    }

    function ok(data, status, xhr) {
        attachedIncidentReports = data;

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        var message = "Failed to load attached field reports";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    var url = (
        urlReplace(url_incidentReports) + "?incident=" + incidentNumber
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

    $("#incident_report_add").on("input", reportEntryEdited);
}


//
// Add option elements to location address select elements
//

function addLocationAddressOptions() {
    var hours = range(1, 13);
    for (var i in hours) {
        var hour = padTwo(hours[i]);
        $("#incident_location_address_radial_hour")
            .append($("<option />", { "value": hour, "text": hour }))
            ;
    }

    var minutes = range(0, 12, 5);
    for (var i in minutes) {
        var minute = padTwo(minutes[i]);
        $("#incident_location_address_radial_minute")
            .append($("<option />", { "value": minute, "text": minute }))
            ;
    }

    for (var id in concentricStreetNameByID) {
        var name = concentricStreetNameByID[id];
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
    var number = incident.number;
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
    var summary = incident.summary;

    if (summary == undefined || summary == "") {
        $("#incident_summary")[0].removeAttribute("value");
        $("#incident_summary").attr(
            "placeholder", summarizeIncident(incident)
        );
    } else {
        $("#incident_summary").val(summary);
        $("#incident_summary").attr("placeholder", "");
    }
}


//
// Populate Rangers list
//

var _rangerItem = null;

function drawRangers() {
    if (_rangerItem == null) {
        _rangerItem = $("#incident_rangers_list")
            .children(".list-group-item:first")
            ;
    }

    var items = [];

    var handles = incident.ranger_handles;
    if (handles == undefined) {
        handles = [];
    } else {
        handles.sort((a, b) => a.localeCompare(b));
    }

    for (var i in handles) {
        var handle = handles[i]
        var ranger = null;
        if (personnel == null || personnel[handle] == undefined) {
            ranger = handle;
        } else {
            ranger = rangerAsString(personnel[handle]);
        }
        var item = _rangerItem.clone();
        item.append(textAsHTML(ranger));
        item.attr("value", textAsHTML(handle));
        items.push(item);
    }

    var container = $("#incident_rangers_list");
    container.empty();
    container.append(items);
}


function drawRangersToAdd() {
    var datalist = $("#ranger_handles");

    var handles = [];
    for (var handle in personnel) {
        handles.push(handle);
    }
    handles.sort((a, b) => a.localeCompare(b));

    datalist.empty();
    datalist.append($("<option />"));

    for (var i in handles) {
        var handle = handles[i];
        var ranger = personnel[handle];

        var option = $("<option />");
        option.val(handle);
        option.text(rangerAsString(ranger));

        datalist.append(option);
    }
}


function rangerAsString(ranger) {
    var result = ranger.handle;

    if (ranger.name != undefined && ranger.name != null && ranger.name != "") {
        result += " (" + ranger.name + ")";
    }

    if (ranger.status == "vintage") {
        result += "*";
    }

    return result;
}


//
// Populate incident types list
//

var _typesItem = null;

function drawIncidentTypes() {
    if (_typesItem == null) {
        _typesItem = $("#incident_types_list")
            .children(".list-group-item:first")
            ;
    }

    var items = [];

    var incidentTypes = incident.incident_types;
    if (incidentTypes == undefined) {
        incidentTypes = [];
    } else {
        incidentTypes.sort();
    }

    for (var i in incidentTypes) {
        var item = _typesItem.clone();
        item.append(textAsHTML(incidentTypes[i]));
        items.push(item);
    }

    var container = $("#incident_types_list");
    container.empty();
    container.append(items);
}


function drawIncidentTypesToAdd() {
    var datalist = $("#incident_types");

    datalist.empty();
    datalist.append($("<option />"));

    for (var i in incidentTypes) {
        var incidentType = incidentTypes[i];

        var option = $("<option />");
        option.val(incidentType);

        datalist.append(option);
    }
}


//
// Populate location
//

function drawLocationName() {
    if (incident.location != undefined) {
        if (incident.location.name != undefined) {
            $("#incident_location_name").val(incident.location.name);
        }
    }
}


function drawLocationAddressRadialHour() {
    var hour = null;
    if (incident.location != undefined) {
        if (incident.location.radial_hour != undefined) {
            hour = padTwo(incident.location.radial_hour);
        }
    }
    selectOptionWithValue(
        $("#incident_location_address_radial_hour"), hour
    );
}


function drawLocationAddressRadialMinute() {
    var minute = null;
    if (incident.location != undefined) {
        if (incident.location.radial_minute != undefined) {
            minute = normalizeMinute(incident.location.radial_minute);
        }
    }
    selectOptionWithValue(
        $("#incident_location_address_radial_minute"), minute
    );
}


function drawLocationAddressConcentric() {
    var concentric = null;
    if (incident.location != undefined) {
        if (incident.location.concentric != undefined) {
            concentric = incident.location.concentric;
        }
    }
    selectOptionWithValue(
        $("#incident_location_address_concentric"), concentric
    );
}


function drawLocationDescription() {
    if (incident.location != undefined) {
        if (incident.location.description != undefined) {
            $("#incident_location_description")
                .val(incident.location.description)
                ;
        }
    }
}


//
// Incident report display
//

function toggleShowHistory() {
    if ($("#history_checkbox").is(":checked")) {
        $("#incident_report").removeClass("hide-history");
    } else {
        $("#incident_report").addClass("hide-history");
    }
}


//
// Draw report entries
//

function drawMergedReportEntries() {
    var entries = [];

    if (incident.report_entries) {
        $.merge(entries, incident.report_entries);
    }

    if (attachedIncidentReports != null) {
        if ($("#merge_reports_checkbox").is(":checked")) {
            for (var i in attachedIncidentReports) {
                var report = attachedIncidentReports[i];
                for (var j in report.report_entries) {
                    var entry = report.report_entries[j];
                    entry.merged = report.number;
                    entries.push(entry);
                }
            }
        }
    }

    entries.sort(compareReportEntries)

    drawReportEntries(entries);
}


var _reportsItem = null;

function drawAttachedIncidentReports() {
    if (_reportsItem == null) {
        _reportsItem = $("#attached_incident_reports")
            .children(".list-group-item:first")
            ;
    }

    var items = [];

    var reports = attachedIncidentReports;
    if (reports == undefined) {
        reports = [];
    } else {
        reports.sort();
    }

    for (var i in reports) {
        var report = reports[i];
        var item = _reportsItem.clone();
        var link = $("<a />");
        link.attr("href", urlReplace(url_viewIncidentReports) + report.number);
        link.text(incidentReportAsString(report));
        item.append(link);
        item.data(report);
        items.push(item);
    }

    var container = $("#attached_incident_reports");
    container.empty();
    container.append(items);
}


function drawIncidentReportsToAttach() {
    var container = $("#attached_incident_report_add_container");
    var select = $("#attached_incident_report_add");

    select.empty();
    select.append($("<option />"));

    if (unattachedIncidentReports.length == 0) {
        container.addClass("hidden");
    } else {

        select.append($("<optgroup label=\"Unattached to any incident\">"));
        for (const report of unattachedIncidentReports) {
            // Skip field reports that *are* attached to an incident
            if (report.incident != null) {
                continue;
            }
            const option = $("<option />");
            option.val(report.number);
            option.text(incidentReportAsString(report));

            select.append(option);
        }
        select.append($("</optgroup>"));

        select.append($("<optgroup label=\"Attached to another incident\">"));
        for (const report of unattachedIncidentReports) {
            // Skip field reports that *are not* attached to an incident
            if (report.incident == null) {
                continue;
            }
            const option = $("<option />");
            option.val(report.number);
            option.text(incidentReportAsString(report));

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
    var number = incident.number
    var url = incidentsURL;

    if (number == null) {
        // We're creating a new incident.
        var required = ["state", "priority"];
        for (var i in required) {
            var key = required[i];
            if (edits[key] == undefined) {
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

            newNumber = xhr.getResponseHeader("X-IMS-Incident-Number")
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
        var message = "Failed to apply edit";
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
    if (value == "") {
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

    var rangerHandle = sender.parent().attr("value");

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
                function(h) { return h != rangerHandle }
            ),
        },
        ok, fail
    );
}


function removeIncidentType(sender) {
    sender = $(sender);

    var incidentType = sender.parent().text().trim();

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
                function(t) { return t != incidentType }
            ),
        },
        ok, fail
    );
}

function normalize(str) {
    return str.toLowerCase().trim();
}

function addRanger() {
    var select = $("#ranger_add");
    var handle = $(select).val();
    var handles = incident.ranger_handles;

    if (handles == undefined) {
        handles = [];
    } else {
        handles = handles.slice();  // copy
    }

    // fuzzy-match on handle, to allow case insensitivity and
    // leading/trailing whitespace.
    if (!(handle in personnel)) {
        const normalized = normalize(handle);
        for (const validHandle in personnel) {
            if (normalized == normalize(validHandle)) {
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

    if (handles.indexOf(handle) != -1) {
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
    var select = $("#incident_type_add");
    var incidentType = $(select).val();
    var currentIncidentTypes = incident.incident_types

    if (currentIncidentTypes == undefined) {
        currentIncidentTypes = [];
    } else {
        currentIncidentTypes = currentIncidentTypes.slice();  // copy
    }

    // fuzzy-match on incidentType, to allow case insensitivity and
    // leading/trailing whitespace.
    if (incidentTypes.indexOf(incidentType) == -1) {
        const normalized = normalize(incidentType);
        for (const validType of incidentTypes) {
            if (normalized == normalize(validType)) {
                incidentType = validType;
                break;
            }
        }
    }
    if (incidentTypes.indexOf(incidentType) == -1) {
        // Not a valid incident type
        select.val("");
        return;
    }

    if (currentIncidentTypes.indexOf(incidentType) != -1) {
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


function detachIncidentReport(sender) {
    sender = $(sender);

    var incidentReport = sender.parent().data();

    function ok(data, status, xhr) {
        // FIXME
        // controlHasSuccess(sender);
        loadAndDisplayIncidentReports();
    }

    function fail(requestError, status, xhr) {
        // FIXME
        // controlHasError(sender);

        var message = "Failed to detach field report";
        console.log(message + ": " + requestError);
        loadAndDisplayIncidentReports();
        setErrorMessage(message);
    }

    var url = (
        urlReplace(url_incidentReports) + incidentReport.number +
        "?action=detach;incident=" + incidentNumber
    );

    jsonRequest(url, {}, ok, fail);
}


function attachIncidentReport() {
    if (incidentNumber == null) {
        // Incident doesn't exist yet.  Create it and then retry.
        sendEdits({}, attachIncidentReport);
        return;
    }

    var select = $("#attached_incident_report_add");
    var incidentReportNumber = $(select).val();

    function ok(data, status, xhr) {
        loadAndDisplayIncidentReports();
    }

    function fail(requestError, status, xhr) {
        var message = "Failed to attach field report";
        console.log(message + ": " + requestError);
        loadAndDisplayIncidentReports();
        setErrorMessage(message);
    }

    var url = (
        urlReplace(url_incidentReports) + incidentReportNumber +
        "?action=attach;incident=" + incidentNumber
    );

    jsonRequest(url, {}, ok, fail);
}
