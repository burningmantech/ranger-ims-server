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

function initDispatchQueuePage() {
    function loadedBody() {
        disableEditing();
        initDispatchQueueTable();

        var command = false;

        function addFieldKeyDown() {
            var keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode == 17 || keyCode == 18) {
                command = true;
            }

            console.warn(keyCode);
        }

        function addFieldKeyUp() {
            var keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode == 17 || keyCode == 18) {
                command = false;
                return;
            }

            if (command && keyCode == 78) {
                $("#new_incident").click();
            }

            if (command) { console.warn(keyCode); }
        }

        document.onkeydown = addFieldKeyDown;
        document.onkeyup   = addFieldKeyUp;
    }

    loadBody(loadedBody);
}


//
// Dispatch queue table
//

var dispatchQueueTable = null;

function initDispatchQueueTable() {
    initDataTables();
    initTableButtons();
    initSearchField();
    initSearch();

    if (editingAllowed) {
        enableEditing();
    }
}


//
// Initialize DataTables
//

function initDataTables() {
    function dataHandler(incidents) {
        return incidents;
    }

    dispatchQueueTable = $("#queue_table").DataTable({
        "deferRender": true,
        "paging": true,
        "lengthChange": false,
        "searching": true,
        "processing": true,
        "scrollX": false, "scrollY": false,
        "ajax": {
            "url": dataURL,
            "dataSrc": dataHandler,
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
                "data": "timestamp",
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
                "render": "[, ]",  // Join array with ", "
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
                "render": "[, ]",  // Join array with ", "
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
                var url = viewIncidentsURL + incident.number;

                // Open new context with link
                window.open(url, eventID + "#" + incident.number);
            });
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

    // Set button defaults

    showState("open");
    showDays(null);
    showRows(25);

    $(".new_incident_link").attr("href", viewIncidentsURL + "new");
}


//
// Initialize search field
//

function initSearchField() {
    // Relocate search container

    $("#queue_table_wrapper")
        .children(".row")
        .children(".col-sm-6:last")
        .replaceWith($("#search_container"));

    // Search field handling

    $("#search_input").on("keyup", function () {
        dispatchQueueTable.search(this.value);
        dispatchQueueTable.draw();
    });
}


//
// Initialize search plug-in
//

function initSearch() {
    function modifiedAfter(incident, timestamp) {
        if (timestamp.isBefore(incident.timestamp)) {
            return true;
        }

      for (var i in incident.report_entries) {
          if (timestamp.isBefore(incident.report_entries[i].created)) {
              return true;
          }
      }

      return false;
    }

    $.fn.dataTable.ext.search.push(
        function(settings, rowData, rowIndex) {
            var incident = dispatchQueueTable.data()[rowIndex];

            switch (_showState) {
                case "all":
                    break;
                case "active":
                    state = stateForIncident(incident);
                    if (state == "on_hold" || state == "closed") {
                        return false;
                    }
                    break;
                case "open":
                    state = stateForIncident(incident);
                    if (state == "closed") {
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

            return true;
        }
    );
}


//
// Show state button handling
//

var _showState = null;

function showState(stateToShow) {
    var menu = $("#show_state");
    var item = $("#show_state_" + stateToShow);

    // Get title from selected item
    var selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    _showState = stateToShow;

    dispatchQueueTable.draw();
}


//
// Show days button handling
//

var _showModifiedAfter = null;

function showDays(daysBackToShow) {
    var id = (daysBackToShow == null) ? "all": daysBackToShow.toString();

    var menu = $("#show_days");
    var item = $("#show_days_" + id);

    // Get title from selected item
    var selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (daysBackToShow == null) {
        _showModifiedAfter = null;
    } else {
        _showModifiedAfter = moment()
            .startOf("day")
            .subtract(daysBackToShow, "days")
            ;
    }

    dispatchQueueTable.draw();
}


//
// Show rows button handling
//

function showRows(rowsToShow) {
    var id = (rowsToShow == null) ? "all": rowsToShow.toString();

    var menu = $("#show_rows");
    var item = $("#show_rows_" + id);

    // Get title from selected item
    var selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (rowsToShow == null) {
        rowsToShow = -1;
    }

    dispatchQueueTable.page.len(rowsToShow);
    dispatchQueueTable.draw()
}
