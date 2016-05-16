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
        drawIncidentFields();
        enableEditing();
    }

    function loadedBody() {
        addLocationAddressOptions();
        disableEditing();
        loadIncident(loadedIncident);
    }

    loadBody(loadedBody);
}


//
// Load HTML template.
//

function loadBody(success) {
    function complete() {
        if (success != undefined) {
            success();
        }
    }

    $("body").load(incidentTemplateURL, complete);
}


//
// Enable.disable editing
//

function disableEditing() {
    $(".row").addClass("disabled");
    $(".form-control").attr("disabled", "");
}


function enableEditing() {
    $(".row").removeClass("disabled");
    $(".form-control").removeAttr("disabled");
}


//
// Load incident
//

var incident = null;

function loadIncident(success) {
    function complete(data, status, request) {
        incident = data;

        if (success != undefined) {
            success();
        }
    }

    $.get(incidentsURL + "/" + incidentNumber, complete, "json");
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
        $("#incident_priority"), priorityNameFromNumber(incident.priority)
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

var rangerItem = null;

function drawRangers() {
    if (rangerItem == null) {
        rangerItem = $("#incident_rangers_list")
            .children(".list-group-item:first")
            ;
    }

    var items = [];

    for (var i in incident.ranger_handles) {
        var item = rangerItem.clone();
        item.append(incident.ranger_handles[i]);
        items.push(item);
    }

    var container = $("#incident_rangers_list");
    container.empty();
    container.append(items);
}


//
// Populate incident types list
//

var typesItem = null;

function drawIncidentTypes() {
    if (typesItem == null) {
        typesItem = $("#incident_types_list")
            .children(".list-group-item:first")
            ;
    }

    var items = [];

    for (var i in incident.incident_types) {
        var item = typesItem.clone();
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
