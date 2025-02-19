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

async function initFieldReportsPage() {

    await loadBody();

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
        // ? --> show help modal
        if (e.key === "?") {
            $("#helpModal").modal("toggle");
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
        // TODO: should there also be a shortcut to show the default filters?
    });
    document.getElementById("helpModal").addEventListener("keydown", function(e) {
        if (e.key === "?") {
            $("#helpModal").modal("toggle");
        }
    });
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

    // Fire-and-forget this promise, since it tries forever to acquire a lock
    let ignoredPromise = requestEventSourceLock();

    const fieldReportChannel = new BroadcastChannel(fieldReportChannelName);
    fieldReportChannel.onmessage = function (e) {
        if (e.data["update_all"]) {
            console.log("Reloading the whole table to be cautious, as an SSE was missed")
            fieldReportsTable.ajax.reload();
            clearErrorMessage();
            return;
        }

        const number = e.data["field_report_number"];
        const event = e.data["event_id"]
        if (event !== eventID) {
            return;
        }
        console.log("Got field report update: " + number);
        // TODO(issue/1498): this reloads the entire Field Report table on any
        //  update to any Field Report. That's not ideal. The thing of which
        //  to be mindful when GETting a particular single Field Report is that
        //  limited access users will receive errors when they try to access
        //  Field Reports for which they're not authorized, and those errors
        //  show up in the browser console. I'd like to find a way to avoid
        //  bringing those errors into the console constantly.
        fieldReportsTable.ajax.reload();
        clearErrorMessage();
    }
}

// Set the user-visible error information on the page to the provided string.
function setErrorMessage(msg) {
    msg = "Error: (Cause: " + msg + ")"
    document.getElementById("error_info").classList.remove("hidden");
    document.getElementById("error_text").textContent = msg;
}

function clearErrorMessage() {
    document.getElementById("error_info").classList.add("hidden");
    document.getElementById("error_text").textContent = "";
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
        // Responsive is too slow to resize when all FRs are shown.
        // Decide on this another day.
        // "responsive": {
        //     "details": false,
        // },
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
                "className": "field_report_number text-right all",
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
                "responsivePriority": 4,
            },
            {   // 2
                "name": "field_report_incident",
                "className": "field_report_incident text-center",
                "data": "incident",
                "defaultContent": "-",
                "render": renderIncidentNumber,
                "responsivePriority": 3,
            },
            {   // 3
                "name": "field_report_summary",
                "className": "field_report_summary all",
                "data": "summary",
                "defaultContent": "",
                "render": renderSummary,
            },
        ],
        "order": [
            // creation time descending
            [1, "dsc"],
        ],
        "createdRow": function (row, fieldReport, index) {
            row.addEventListener("click", function (e) {
                // Open new context with link
                window.open(
                    urlReplace(url_viewFieldReports) + fieldReport.number,
                    "Field_Report:" + fieldReport.number,
                );
            })
            row.getElementsByClassName("field_report_created")[0]
                .setAttribute(
                    "title",
                    fullDateTime.format(Date.parse(fieldReport.created)),
                );
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

    const fragment = window.location.hash.startsWith("#") ? window.location.hash.substring(1) : window.location.hash;
    const fragmentParams = new URLSearchParams(fragment);

    // Set button defaults

    showDays(fragmentParams.get("days")??defaultDaysBack, false);
    showRows(fragmentParams.get("rows")??defaultRows, false);
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
    const searchInput = document.getElementById("search_input");

    const searchAndDraw = function () {
        replaceWindowState();
        let q = searchInput.value;
        let isRegex = false;
        if (q.startsWith("/") && q.endsWith("/")) {
            isRegex = true;
            q = q.slice(1, q.length-1);
        }
        fieldReportsTable.search(q, isRegex);
        fieldReportsTable.draw();
    }

    const fragment = window.location.hash.startsWith("#") ? window.location.hash.substring(1) : window.location.hash;
    const fragmentParams = new URLSearchParams(fragment);
    const queryString = fragmentParams.get("q");
    if (queryString) {
        searchInput.value = queryString;
        searchAndDraw();
    }

    searchInput.addEventListener("keyup",
        function () {
            // Delay the search in case the user is still typing.
            // This reduces perceived lag, since searching can be
            // very slow, and it's super annoying for a user when
            // the page fully locks up before they're done typing.
            clearTimeout(_searchDelayTimer);
            _searchDelayTimer = setTimeout(searchAndDraw, _searchDelayMs);
        }
    );
    searchInput.addEventListener("keydown",
        function (e) {
            // No shortcuts when ctrl, alt, or meta is being held down
            if (e.altKey || e.ctrlKey || e.metaKey) {
                return;
            }
            // "Jump to Field Report" functionality, triggered on hitting Enter
            if (e.key === "Enter") {
                // If the value in the search box is an integer, assume it's an FR number and go to it.
                // This will work regardless of whether that FR is visible with the current filters.
                const val = searchInput.value;
                if (integerRegExp.test(val)) {
                    // Open new context with link
                    window.open(
                        urlReplace(url_viewFieldReports) + val,
                        "Field_Report:" + val,
                    );
                    searchInput.value = "";
                }
            }
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
let _showDaysBack = null;
const defaultDaysBack = "all";

function showDays(daysBackToShow, replaceState) {
    const id = daysBackToShow.toString();
    _showDaysBack = daysBackToShow;

    const menu = $("#show_days");
    const item = $("#show_days_" + id);

    // Get title from selected item
    const selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (daysBackToShow === "all") {
        _showModifiedAfter = null;
    } else {
        const after = new Date();
        after.setHours(0);
        after.setMinutes(0);
        after.setSeconds(0);
        after.setDate(after.getDate()-daysBackToShow);
        _showModifiedAfter = after;
    }

    if (replaceState) {
        replaceWindowState();
    }

    fieldReportsTable.draw();
}


//
// Show rows button handling
//

let _showRows = null;
const defaultRows = 25;

function showRows(rowsToShow, replaceState) {
    const id = rowsToShow.toString();
    _showRows = rowsToShow;

    const menu = $("#show_rows");
    const item = $("#show_rows_" + id);

    // Get title from selected item
    const selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (rowsToShow === "all") {
        rowsToShow = -1;
    }

    if (replaceState) {
        replaceWindowState();
    }

    fieldReportsTable.page.len(rowsToShow);
    fieldReportsTable.draw()
}


//
// Update the page URL based on the search input and other filters.
//

function replaceWindowState() {
    const newParams = [];

    const searchVal = document.getElementById("search_input").value;
    if (searchVal) {
        newParams.push(["q", searchVal]);
    }
    if (_showDaysBack != null && _showDaysBack !== defaultDaysBack) {
        newParams.push(["days", _showDaysBack]);
    }
    if (_showRows != null && _showRows !== defaultRows) {
        newParams.push(["rows", _showRows]);
    }

    // Next step is to create search params for the other filters too

    const newURL = `${urlReplace(url_viewFieldReports)}#${new URLSearchParams(newParams).toString()}`;
    window.history.replaceState(null, null, newURL);
}
