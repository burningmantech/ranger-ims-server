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

function initIncidentsPage() {
    function loadedBody() {
        disableEditing();
        loadEventFieldReports(initIncidentsTable);

        // Keyboard shortcuts
        document.addEventListener("keydown", function(e) {
            if (document.activeElement !== document.body) {
                return;
            }
            if (e.altKey || e.ctrlKey || e.metaKey) {
                return;
            }
            // n --> new incident
            if (e.key.toLowerCase() === "n") {
                $("#new_incident").click();
            }
            // a --> show all for this event
            if (e.key.toLowerCase() === "a") {
                showState("all");
                showDays(null);
                showRows(null);
                showType("all");
            }
            // TODO: should there also be a shortcut to show the default filters?
        });

    }

    loadBody(loadedBody);
}


//
// Load event field reports
//
// Note that nothing from these data is displayed in the incidents table.
// We do this fetch in order to make incidents searchable by text in their
// attached field reports.

let eventFieldReports = null;

function loadEventFieldReports(success) {
    function ok(data, status, xhr) {
        const reports = {};

        for (const report of data) {
            reports[report.number] = report;
        }

        eventFieldReports = reports;

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        const message = "Failed to load event field reports";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    jsonRequest(urlReplace(url_fieldReports + "?exclude_system_entries=true"), null, ok, fail);

    console.log("Loaded event field reports");
    if (incidentsTable != null) {
        incidentsTable.ajax.reload(clearErrorMessage);
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

//
// Dispatch queue table
//

let incidentsTable = null;

function initIncidentsTable() {
    initDataTables();
    initTableButtons();
    initSearchField();
    initSearch();
    clearErrorMessage();

    if (editingAllowed) {
        enableEditing();
    }

    // ok to ignore returned Promise...have the tab wait for the lock
    requestEventSourceLock();
    const incidentChannel = new BroadcastChannel(incidentChannelName);
    incidentChannel.onmessage = function (e) {
        const number = e.data;
        console.log("Got incident update: " + number);
        incidentsTable.ajax.reload(clearErrorMessage);
    }
}


//
// Initialize DataTables
//

function initDataTables() {
    function dataHandler(incidents) {
        return incidents;
    }

    $.fn.dataTable.ext.errMode = "none";
    incidentsTable = $("#queue_table").DataTable({
        "deferRender": true,
        "paging": true,
        "lengthChange": false,
        "searching": true,
        "processing": true,
        "scrollX": false, "scrollY": false,
        "layout": {
            "topStart": null,
            "topEnd": null,
            "bottomStart": "info",
            "bottomEnd": "paging",
        },
        "ajax": {
            "url": dataURL,
            "dataSrc": dataHandler,
            "error": function (request, status, error) {
                // The "abort" case is a special snowflake.
                // There are times we do two table refreshes in quick succession, and in
                // those cases, the first call gets aborted. We don't want to set an error
                // messages in those cases.
                if (error === "abort") {
                    return;
                }
                let errMsg = "";
                if (error) {
                    errMsg = error;
                } else if (request.responseText) {
                    errMsg = request.responseText;
                } else {
                    errMsg = "DataTables error";
                }
                setErrorMessage(errMsg);
            },
        },
        "columns": [
            {   // 0
                "name": "incident_number",
                "className": "incident_number text-right",
                "data": "number",
                "defaultContent": null,
                "cellType": "th",
            },
            {   // 1
                "name": "incident_priority",
                "className": "incident_priority text-center",
                "data": "priority",
                "defaultContent": null,
                "searchable": false,
                "render": renderPriority,
            },
            {   // 2
                "name": "incident_created",
                "className": "incident_created text-center",
                "data": "created",
                "defaultContent": null,
                "render": renderDate,
            },
            {   // 3
                "name": "incident_state",
                "className": "incident_state text-center",
                "data": "state",
                "defaultContent": null,
                "render": renderState,
            },
            {   // 4
                "name": "incident_ranger_handles",
                "className": "incident_ranger_handles",
                "data": "ranger_handles",
                "defaultContent": "",
                "render": renderSafeSorted,
                "width": "6em",
            },
            {   // 5
                "name": "incident_location",
                "className": "incident_location",
                "data": "location",
                "defaultContent": "",
                "render": renderLocation,
            },
            {   // 6
                "name": "incident_types",
                "className": "incident_types",
                "data": "incident_types",
                "defaultContent": "",
                "render": renderSafeSorted,
                "width": "5em",
            },
            {   // 7
                "name": "incident_summary",
                "className": "incident_summary",
                "data": "summary",
                "defaultContent": "",
                "render": renderSummary,
            },
        ],
        "order": [
            [1, "asc"],
            [2, "dsc"],
        ],
        "createdRow": function (row, incident, index) {
            $(row).click(function () {
                const url = viewIncidentsURL + incident.number;

                // Open new context with link
                window.open(
                    url, "Incident:" + eventID + "#" + incident.number
                );
            });
            $(row).find(".incident_created")
                .attr("title", fullDateTime.format(Date.parse(incident.created)));
        },
    });
}


//
// Initialize table buttons
//

function initTableButtons() {
    // Relocate button container

    $("#queue_table_wrapper")
        .children(".row")
        .children(".col-sm-6:first")
        .replaceWith($("#button_container"));

    const $typeFilter = $("#ul_show_type");
    for (const i in allIncidentTypes) {
        const type = allIncidentTypes[i];
        const $a = $("<a>", {class: "name dropdown-item", href:"#"});
        $a.text(type.toString());
        const $li = $("<li>", {id: "show_type_" + i, onclick: "showType(" + i + ")"});
        $li.append($a);
        $typeFilter.append($li);
    }


    // Set button defaults

    showState("open");
    showDays(null);
    showRows(25);
    showType("all");
}


//
// Initialize search field
//

const _searchDelayMs = 250;
let _searchDelayTimer = null;

function initSearchField() {
    // Relocate search container

    $("#queue_table_wrapper")
        .children(".row")
        .children(".col-sm-6:last")
        .replaceWith($("#search_container"));

    // Search field handling
    document.getElementById("search_input")
        .addEventListener("keyup",
            function () {
                // Delay the search in case the user is still typing.
                // This reduces perceived lag, since searching can be
                // very slow, and it's super annoying for a user when
                // the page fully locks up before they're done typing.
                clearTimeout(_searchDelayTimer);
                const val = this.value;
                _searchDelayTimer = setTimeout(function () {
                    incidentsTable.search(val);
                    incidentsTable.draw();
                }, _searchDelayMs);
            }
        );
}


//
// Initialize search plug-in
//

function initSearch() {
    function modifiedAfter(incident, timestamp) {
        if (timestamp < Date.parse(incident.created)) {
            return true;
        }

        for (const entry of incident.report_entries??[]) {
            if (timestamp < Date.parse(entry.created)) {
                return true;
            }
        }

      return false;
    }

    $.fn.dataTable.ext.search.push(
        function(settings, rowData, rowIndex) {
            const incident = incidentsTable.data()[rowIndex];
            let state;
            switch (_showState) {
                case "all":
                    break;
                case "active":
                    state = stateForIncident(incident);
                    if (state === "on_hold" || state === "closed") {
                        return false;
                    }
                    break;
                case "open":
                    state = stateForIncident(incident);
                    if (state === "closed") {
                        return false;
                    }
                    break;
            }

            if (
                _showModifiedAfter != null &&
                ! modifiedAfter(incident, _showModifiedAfter)
            ) {
                return false
            }

            switch (_showType) {
                case null:
                    // fallthrough
                case "all":
                    break;
                default:
                    if (_showType >= 0 && _showType < allIncidentTypes.length) {
                        const st = allIncidentTypes[_showType];
                        if (!(incident.incident_types??[]).includes(st)) {
                            return false;
                        }
                    }
                    break;
            }

            return true;
        }
    );
}


//
// Show state button handling
//

let _showState = null;

function showState(stateToShow) {
    const menu = $("#show_state");
    const item = $("#show_state_" + stateToShow);

    // Get title from selected item
    const selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    _showState = stateToShow;

    incidentsTable.draw();
}


//
// Show days button handling
//

let _showModifiedAfter = null;

function showDays(daysBackToShow) {
    const id = (daysBackToShow == null) ? "all" : daysBackToShow.toString();

    const menu = $("#show_days");
    const item = $("#show_days_" + id);

    // Get title from selected item
    const selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (daysBackToShow == null) {
        _showModifiedAfter = null;
    } else {
        const after = new Date();
        after.setHours(0);
        after.setMinutes(0);
        after.setSeconds(0);
        after.setDate(after.getDate()-daysBackToShow);
        _showModifiedAfter = after;
    }

    incidentsTable.draw();
}

//
// Show type button handling
//

// _showType will be one of:
//  "all" or null (meaning show everything)
//  a numeric index into allIncidentTypes
let _showType = null;

function showType(typeToShow) {
    // see _showType above for values of "typeToShow"
    const id = typeToShow??"all";

    const $menu = $("#show_type");
    const $item = $("#show_type_" + id);

    // Get title from selected item
    const selection = $item.children(".name").html();

    // Update menu title to reflect selected item
    $menu.children(".selection").html(selection);

    _showType = typeToShow;

    incidentsTable.draw();
}

//
// Show rows button handling
//

function showRows(rowsToShow) {
    const id = (rowsToShow == null) ? "all" : rowsToShow.toString();

    const menu = $("#show_rows");
    const item = $("#show_rows_" + id);

    // Get title from selected item
    const selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (rowsToShow == null) {
        rowsToShow = -1;
    }

    incidentsTable.page.len(rowsToShow);
    incidentsTable.draw()
}
