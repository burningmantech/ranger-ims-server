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

function initFieldReportsPage() {
    function loadedBody() {
        disableEditing();
        initFieldReportsTable();

        let command = false;

        function addFieldKeyDown() {
            const keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode === 17 || keyCode === 18) {
                command = true;
            }

            // console.warn(keyCode);
        }

        function addFieldKeyUp() {
            const keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode === 17 || keyCode === 18) {
                command = false;
                return;
            }

            // 78 = n
            if (command && keyCode === 78) {
                $("#new_field_report").click();
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

let fieldReportsTable = null;

function initFieldReportsTable() {
    initDataTables();
    initTableButtons();
    initSearchField();
    initSearch();
    clearErrorMessage();

    if (editingAllowed) {
        enableEditing();
    }

    // it's ok to ignore the returned promise
    requestEventSourceLock();
    const fieldReportChannel = new BroadcastChannel(fieldReportChannelName);
    fieldReportChannel.onmessage = function (e) {
        const number = e.data;
        console.log("Got field report update: " + number);
        fieldReportsTable.ajax.reload(clearErrorMessage);
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
// Initialize DataTables
//

function initDataTables() {
    function dataHandler(fieldReports) {
        return fieldReports;
    }

    $.fn.dataTable.ext.errMode = "none";
    fieldReportsTable = $("#field_reports_table").DataTable({
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
            // don't use exclude_system_entries here, since the field reports
            // per-user authorization can exclude field reports entirely from
            // someone who created an field report but then didn't add an
            // entry to it.
            "url": urlReplace(url_fieldReports, eventID),
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
                "name": "field_report_number",
                "className": "field_report_number text-right",
                "data": "number",
                "defaultContent": null,
                "cellType": "th",
            },
            {   // 1
                "name": "field_report_created",
                "className": "field_report_created text-center",
                "data": "created",
                "defaultContent": null,
                "render": renderDate,
            },
            {   // 2
                "name": "field_report_incident",
                "className": "field_report_incident text-center",
                "data": "incident",
                "defaultContent": "-",
                "render": renderIncidentNumber,
            },
            {   // 3
                "name": "field_report_summary",
                "className": "field_report_summary",
                "data": "summary",
                "defaultContent": "",
                "render": renderSummary,
            },
        ],
        "order": [
            [1, "asc"],
        ],
        "createdRow": function (row, fieldReport, index) {
            $(row).click(function () {
                const url = (
                    urlReplace(url_viewFieldReports) + fieldReport.number
                );

                // Open new context with link
                window.open(url, "Field_Report:" + fieldReport.number);
            });
            $(row).find(".field_report_created")
                .attr("title", fullDateTime.format(Date.parse(fieldReport.created)));
        },
    });
}


//
// Initialize table buttons
//

function initTableButtons() {
    // Relocate button container

    $("#field_reports_table_wrapper")
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

    $("#field_reports_table_wrapper")
        .children(".row")
        .children(".col-sm-6:last")
        .replaceWith($("#search_container"));

    // Search field handling

    $("#search_input").on("keyup", function () {
        fieldReportsTable.search(this.value);
        fieldReportsTable.draw();
    });
}


//
// Initialize search plug-in
//

function initSearch() {
    function modifiedAfter(fieldReport, timestamp) {
        if (timestamp < Date.parse(fieldReport.created)) {
            return true;
        }

        // needs to use native comparison
      for (const entry of fieldReport.report_entries??[]) {
          if (timestamp < Date.parse(entry.created)) {
              return true;
          }
      }

      return false;
    }

    $.fn.dataTable.ext.search.push(
        function(settings, rowData, rowIndex) {
            const fieldReport = fieldReportsTable.data()[rowIndex];

            if (
                _showModifiedAfter != null &&
                ! modifiedAfter(fieldReport, _showModifiedAfter)
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

    fieldReportsTable.draw();
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

    fieldReportsTable.page.len(rowsToShow);
    fieldReportsTable.draw()
}
