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
    function loadedBody() {
        addLocationAddressOptions();
        disableEditing();
        loadAndDisplayIncident(function() {
            loadPersonnel(function() {drawRangersToAdd()});
        });
    }

    loadBody(loadedBody);
}


//
// Load incident
//

var incident = null;

function loadIncident(success) {
    var url = incidentsURL + "/" + incidentNumber;

    function ok(data, status, xhr) {
        incident = data;

        if (success != undefined) {
            success();
        }
    }

    function fail(xhr, status, error) {
        disableEditing();
        var message = "Failed to load incident:\n" + error
        console.error(message);
        window.alert(message);
    }

    $.ajax({
        "url": url,
        "method": "GET",
        "dataType": "json",
        "success": ok,
        "error": fail,
    });
}


function loadAndDisplayIncident(success) {
    function loaded() {
        if (incident == null) {
            var message = "Incident failed to load"
            console.log(message);
            alert(message);
            return;
        }

        drawIncidentFields();
        enableEditing();

        if (success != undefined) {
            success();
        }
    }

    loadIncident(loaded);
}


//
// Load personnel
//

var personnel = null;

function loadPersonnel(success) {
    var url = personnelURL;

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

    function fail(xhr, status, error) {
        var message = "Failed to load personnel:\n" + error
        console.error(message);
        window.alert(message);
    }

    $.ajax({
        "url": url,
        "method": "GET",
        "dataType": "json",
        "success": ok,
        "error": fail,
    });
}


//
// Draw all fields
//

function drawIncidentFields() {
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
    drawReportEntries();

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
// Populate incident number
//

function drawNumber() {
    $("#incident_number").text(incident.number);
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
    $("#incident_summary").attr("value", summarizeIncident(incident));
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

    for (var i in incident.ranger_handles) {
        var item = _rangerItem.clone();
        item.append(incident.ranger_handles[i]);
        items.push(item);
    }

    var container = $("#incident_rangers_list");
    container.empty();
    container.append(items);
}


function drawRangersToAdd() {
    console.log("Draw Rangers to add...");

    var select = $("#ranger_add");

    var handles = [];
    for (var handle in personnel) {
        handles.push(handle);
    }
    handles = handles.sort();

    for (var i in handles) {
        var handle = handles[i];
        var ranger = personnel[handle];

        var option = $("<option />");
        option.attr("value", handle);
        option.text(rangerAsString(ranger));

        select.append(option);
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

    for (var i in incident.incident_types) {
        var item = _typesItem.clone();
        item.append(incident.incident_types[i]);
        items.push(item);
    }

    var container = $("#incident_types_list");
    container.empty();
    container.append(items);
}


//
// Populate location
//

function drawLocationName() {
    if (incident.location != undefined) {
        if (incident.location.name != undefined) {
            $("#incident_location_name").attr("value", incident.location.name);
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
                .attr("value", incident.location.description)
                ;
        }
    }
}


//
// Populate report entry text
//

function reportEntryElement(entry) {
    // Build a container for the entry

    var entryContainer = $("<div />", {"class": "report_entry"});

    if (entry.system_entry) {
        entryContainer.addClass("report_entry_system");
    } else {
        entryContainer.addClass("report_entry_user");
    }

    // Add the timestamp and author

    metaDataContainer = $("<p />", {"class": "report_entry_metadata"})

    var timeStampContainer = timeElement(new Date(entry.created));
    timeStampContainer.addClass("report_entry_timestamp");

    metaDataContainer.append([timeStampContainer, ", "]);

    var author = entry.author;
    if (author == undefined) {
        author = "(unknown)";
    }
    var authorContainer = $("<span />");
    authorContainer.text(entry.author);
    authorContainer.addClass("report_entry_author");

    metaDataContainer.append(author);
    metaDataContainer.append(":");

    entryContainer.append(metaDataContainer);

    // Add report text

    var lines = entry.text.split("\n");
    for (var i in lines) {
        var textContainer = $("<p />", {"class": "report_entry_text"});
        textContainer.text(lines[i]);

        entryContainer.append(textContainer);
    }

    // Return container

    return entryContainer;
}

function drawReportEntries() {
    var container = $("#incident_report");
    container.empty();

    var entries = incident.report_entries;

    if (entries != undefined) {
        for (var i in entries) {
            container.append(reportEntryElement(entries[i]));
        }
    }
}


//
// Editing
//

function sendEdits(edits, success, error) {
    edits.number = incident.number;

    var jsonText = JSON.stringify(edits);

    console.log("Sending edit: " + jsonText);

    var url = incidentsURL + "/" + incident.number;

    function ok(data, status, xhr) {
        success();
        loadAndDisplayIncident();
    }

    function fail(xhr, status, e) {
        var message = "Failed to apply edit:\n" + e
        console.log(message);
        error();
        loadAndDisplayIncident();
        window.alert(message);
    }

    $.ajax({
        "url": url,
        "method": "POST",
        "contentType": "application/json",
        "data": jsonText,
        "success": ok,
        "error": fail,
    })
}


function editFromElement(element, jsonKey, transform) {
    var value = element.val();

    if (transform != undefined) {
        value = transform(value);
    }

    // Build a JSON object representing the requested edits

    var edits = {};

    var keyPath = jsonKey.split(".");
    var lastKey = keyPath.pop();

    var current = edits;
    for (var i in keyPath) {
        var next = {};
        current[keyPath[i]] = next;
        current = next;
    }
    current[lastKey] = value;

    // Location must include type

    if (edits.location != undefined) {
        edits.location.type = "garett";  // UI only supports one type
    }

    // Send request to server

    function ok() {
        controlHasSuccess(element);
        // Clear success state after a 1s delay
        element.delay("1000").queue(function() {controlClear(element)});
    }

    function fail() {
        controlHasError(element);
    }

    sendEdits(edits, ok, fail);
}


function editState() {
    editFromElement($("#incident_state"), "state");
}


function editPriority() {
    editFromElement($("#incident_priority"), "priority", Number);
}


function editSummary() {
    editFromElement($("#incident_summary"), "summary");
}


function editLocationName() {
    editFromElement($("#incident_location_name"), "location.name");
}


function editLocationAddressRadialHour() {
    editFromElement(
        $("#incident_location_address_radial_hour"),
        "location.radial_hour",
        Number
    );
}


function editLocationAddressRadialMinute() {
    editFromElement(
        $("#incident_location_address_radial_minute"),
        "location.radial_minute",
        Number
    );
}


function editLocationAddressConcentric() {
    editFromElement(
        $("#incident_location_address_concentric"),
        "location.concentric",
        Number
    );
}


function editLocationDescription() {
    editFromElement($("#incident_location_description"), "location.description");
}


function removeRanger(sender) {
    sender = $(sender);

    var rangerHandle = sender.parent().text().trim();

    function ok() {
        controlHasSuccess(sender);
    }

    function fail() {
        controlHasError(sender);
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
        controlHasSuccess(sender);
    }

    function fail() {
        controlHasError(sender);
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


function addRanger(sender) {
    rangerHandle = $(sender).val().trim();

    console.log("Add Ranger: " + rangerHandle);
}


function addIncidentType(sender) {
    incidentType = $(sender).val().trim();

    console.log("Add incident type: " + incidentType);
}


function reportEntryEdited(event) {
    var text = $("#incident_report_add").val().trim();
    var submitButton = $("#report_entry_submit");

    submitButton.removeClass("btn-default");
    submitButton.removeClass("btn-warning");
    submitButton.removeClass("btn-danger");

    if (text == "") {
        submitButton.addClass("disabled");
        submitButton.addClass("btn-default");
    } else {
        submitButton.removeClass("disabled");
        submitButton.addClass("btn-warning");
    }
}


function submitReportEntry() {
    var text = $("#incident_report_add").val().trim();

    if (text == "") {
        return;
    }

    console.log("New report entry:\n" + text);

    function ok() {
        // Clear the report entry
        $("#incident_report_add").val("");
        // Reset the submit button
        reportEntryEdited();
    }

    function fail() {
        var submitButton = $("#report_entry_submit");
        submitButton.removeClass("btn-default");
        submitButton.removeClass("btn-warning");
        submitButton.addClass("btn-danger");
    }

    sendEdits({"report_entries": [{"text": text}]}, ok, fail);
}
