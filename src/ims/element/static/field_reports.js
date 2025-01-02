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
            // / --> jump to search box
            if (e.key === "/") {
                // don't immediately input a "/" into the search box
                e.preventDefault();
                document.getElementById("search_input").focus();
            }
            // n --> new incident
            if (e.key.toLowerCase() === "n") {
                document.getElementById("new_field_report").click();
            }
            // a --> show all for this event
            if (e.key.toLowerCase() === "a") {
                showDays(null);
                showRows(null);
            }
            // TODO: should there also be a shortcut to show the default filters?
        });
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

const _searchDelayMs = 250;
let _searchDelayTimer = null;

function initSearchField() {
    // Relocate search container

    $("#field_reports_table_wrapper")
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
                    fieldReportsTable.search(val);
                    fieldReportsTable.draw();
                }, _searchDelayMs);
            }
        );
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
