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

function initIncidentReportsPage() {
    function loadedBody() {
        disableEditing();
        initIncidentReportsTable();

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

            if (command && keyCode == 78) {
                $("#new_incident_report").click();
            }

            // if (command) { console.warn(keyCode); }
        }

        document.onkeydown = addFieldKeyDown;
        document.onkeyup   = addFieldKeyUp;
    }

    loadBody(loadedBody);
}


//
// Dispatch queue table
//

var incidentReportsTable = null;

function initIncidentReportsTable() {
    initDataTables();
    initTableButtons();
    initSearchField();
    initSearch();

    if (editingAllowed) {
        enableEditing();
    }

    subscribeToUpdates();

    eventSource.addEventListener("IncidentReport", function(e) {
        var jsonText = e.data;
        var json = JSON.parse(jsonText);
        var number = json["incident_report_number"];

        console.log("Got incident report update: " + number);
        incidentReportsTable.ajax.reload();
    }, true);
}


//
// Initialize DataTables
//

function initDataTables() {
    function dataHandler(incidentReports) {
        return incidentReports;
    }

    incidentReportsTable = $("#incident_reports_table").DataTable({
        "deferRender": true,
        "paging": true,
        "lengthChange": false,
        "searching": true,
        "processing": true,
        "scrollX": false, "scrollY": false,
        "ajax": {
            "url": urlReplace(url_incidentReports, eventID),
            "dataSrc": dataHandler,
        },
        "columns": [
            {   // 0
                "name": "incident_report_number",
                "className": "incident_report_number text-right",
                "data": "number",
                "defaultContent": null,
                "cellType": "th",
            },
            {   // 1
                "name": "incident_report_created",
                "className": "incident_report_created text-center",
                "data": "created",
                "defaultContent": null,
                "render": renderDate,
            },
            {   // 2
                "name": "incident_report_incident",
                "className": "incident_report_incident text-center",
                "data": "incident",
                "defaultContent": "-",
                "render": renderIncidentNumber,
            },
            {   // 3
                "name": "incident_report_summary",
                "className": "incident_report_summary",
                "data": "summary",
                "defaultContent": "",
                "render": renderSummary,
            },
        ],
        "order": [
            [1, "asc"],
        ],
        "createdRow": function (row, incidentReport, index) {
            $(row).click(function () {
                var url = (
                    urlReplace(url_viewIncidentReports) + incidentReport.number
                );

                // Open new context with link
                window.open(url, "Incident_Report:" + incidentReport.number);
            });
        },
    });
}


//
// Initialize table buttons
//

function initTableButtons() {
    // Relocate button container

    $("#incident_reports_table_wrapper")
        .children(".row")
        .children(".col-sm-6:first")
        .replaceWith($("#button_container"));

    // Set button defaults

    showDays(null);
    showRows(25);
}


//
// Initialize search field
//

function initSearchField() {
    // Relocate search container

    $("#incident_reports_table_wrapper")
        .children(".row")
        .children(".col-sm-6:last")
        .replaceWith($("#search_container"));

    // Search field handling

    $("#search_input").on("keyup", function () {
        incidentReportsTable.search(this.value);
        incidentReportsTable.draw();
    });
}


//
// Initialize search plug-in
//

function initSearch() {
    function modifiedAfter(incidentReport, timestamp) {
        if (timestamp.isBefore(incidentReport.created)) {
            return true;
        }

      for (var i in incidentReport.report_entries) {
          if (timestamp.isBefore(incidentReport.report_entries[i].created)) {
              return true;
          }
      }

      return false;
    }

    $.fn.dataTable.ext.search.push(
        function(settings, rowData, rowIndex) {
            var incidentReport = incidentReportsTable.data()[rowIndex];

            if (
                _showModifiedAfter != null &&
                ! modifiedAfter(incidentReport, _showModifiedAfter)
            ) {
                return false
            }

            return true;
        }
    );
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

    incidentReportsTable.draw();
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

    incidentReportsTable.page.len(rowsToShow);
    incidentReportsTable.draw()
}
