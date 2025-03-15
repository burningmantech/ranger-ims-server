///<reference path="ims.ts"/>
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
            // @ts-ignore JQuery
            $("#helpModal").modal("toggle");
        }
        // / --> jump to search box
        if (e.key === "/") {
            // don't immediately input a "/" into the search box
            e.preventDefault();
            (document.getElementById("search_input") as HTMLInputElement).focus();
        }
        // n --> new incident
        if (e.key.toLowerCase() === "n") {
            (document.getElementById("new_field_report") as HTMLButtonElement).click();
        }
        // TODO: should there also be a shortcut to show the default filters?
    });
    document.getElementById("helpModal")!.addEventListener("keydown", function(e) {
        if (e.key === "?") {
            // @ts-ignore JQuery
            $("#helpModal").modal("toggle");
        }
    });
}


//
// Dispatch queue table
//

let fieldReportsTable = null;

function initFieldReportsTable() {
    frInitDataTables();
    frInitTableButtons();
    frInitSearchField();
    frInitSearch();
    clearErrorMessage();

    if (editingAllowed) {
        enableEditing();
    }

    // Fire-and-forget this promise, since it tries forever to acquire a lock
    let ignoredPromise = requestEventSourceLock();

    const fieldReportChannel = new BroadcastChannel(fieldReportChannelName);
    fieldReportChannel.onmessage = function (e) {
        if (e.data.update_all) {
            console.log("Reloading the whole table to be cautious, as an SSE was missed");
            // @ts-ignore DataTables
            fieldReportsTable!.ajax.reload();
            clearErrorMessage();
            return;
        }

        const number = e.data.field_report_number;
        const event = e.data.event_id;
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
        // @ts-ignore DataTables
        fieldReportsTable!.ajax.reload();
        clearErrorMessage();
    };
}

//
// Initialize DataTables
//

function frInitDataTables() {
    function dataHandler(fieldReports) {
        return fieldReports;
    }

    // @ts-ignore JQuery
    $.fn.dataTable.ext.errMode = "none";
    // @ts-ignore JQuery
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
            "url": urlReplace(url_fieldReports),
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
            });
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

function frInitTableButtons() {
    // Relocate button container

    // @ts-ignore JQuery
    $("#field_reports_table_wrapper")
        .children(".row")
        .children(".col-sm-6:first")
        // @ts-ignore JQuery
        .replaceWith($("#button_container"));

    const fragment = window.location.hash.startsWith("#") ? window.location.hash.substring(1) : window.location.hash;
    const fragmentParams = new URLSearchParams(fragment);

    // Set button defaults

    frShowDays(fragmentParams.get("days")??frDefaultDaysBack, false);
    frShowRows(fragmentParams.get("rows")??frDefaultRows, false);
}


//
// Initialize search field
//

const _frSearchDelayMs = 250;
let _frSearchDelayTimer: number|undefined = undefined;

function frInitSearchField() {
    // Relocate search container

    // @ts-ignore JQuery
    $("#field_reports_table_wrapper")
        .children(".row")
        .children(".col-sm-6:last")
        // @ts-ignore JQuery
        .replaceWith($("#search_container"));

    // Search field handling
    const searchInput = document.getElementById("search_input") as HTMLInputElement;

    const searchAndDraw = function () {
        frReplaceWindowState();
        let q = searchInput.value;
        let isRegex = false;
        if (q.startsWith("/") && q.endsWith("/")) {
            isRegex = true;
            q = q.slice(1, q.length-1);
        }
        // @ts-ignore DataTables
        fieldReportsTable.search(q, isRegex);
        // @ts-ignore DataTables
        fieldReportsTable.draw();
    };

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
            clearTimeout(_frSearchDelayTimer);
            _frSearchDelayTimer = setTimeout(searchAndDraw, _frSearchDelayMs);
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

function frInitSearch() {
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

    // @ts-ignore JQuery
    $.fn.dataTable.ext.search.push(
        function(settings, rowData, rowIndex) {
            // @ts-ignore DataTables
            const fieldReport = fieldReportsTable.data()[rowIndex];

            if (
                _frShowModifiedAfter != null &&
                ! modifiedAfter(fieldReport, _frShowModifiedAfter)
            ) {
                return false;
            }

            return true;
        }
    );
}


//
// Show days button handling
//

let _frShowModifiedAfter: Date|null = null;
let _frShowDaysBack = null;
const frDefaultDaysBack = "all";

function frShowDays(daysBackToShow, replaceState) {
    const id = daysBackToShow.toString();
    _frShowDaysBack = daysBackToShow;

    // @ts-ignore JQuery
    const menu = $("#show_days");
    // @ts-ignore JQuery
    const item = $("#show_days_" + id);

    // Get title from selected item
    const selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (daysBackToShow === "all") {
        _frShowModifiedAfter = null;
    } else {
        const after = new Date();
        after.setHours(0);
        after.setMinutes(0);
        after.setSeconds(0);
        after.setDate(after.getDate()-daysBackToShow);
        _frShowModifiedAfter = after;
    }

    if (replaceState) {
        frReplaceWindowState();
    }

    // @ts-ignore DataTables
    fieldReportsTable.draw();
}


//
// Show rows button handling
//

let _frShowRows = null;
const frDefaultRows = 25;

function frShowRows(rowsToShow, replaceState) {
    const id = rowsToShow.toString();
    _frShowRows = rowsToShow;

    // @ts-ignore JQuery
    const menu = $("#show_rows");
    // @ts-ignore JQuery
    const item = $("#show_rows_" + id);

    // Get title from selected item
    const selection = item.children(".name").html();

    // Update menu title to reflect selected item
    menu.children(".selection").html(selection);

    if (rowsToShow === "all") {
        rowsToShow = -1;
    }

    if (replaceState) {
        frReplaceWindowState();
    }

    // @ts-ignore DataTables
    fieldReportsTable!.page.len(rowsToShow);
    // @ts-ignore DataTables
    fieldReportsTable!.draw();
}


//
// Update the page URL based on the search input and other filters.
//

function frReplaceWindowState() {
    const newParams: [string, string][] = [];

    const searchVal = (document.getElementById("search_input") as HTMLInputElement).value;
    if (searchVal) {
        newParams.push(["q", searchVal]);
    }
    if (_frShowDaysBack != null && _frShowDaysBack !== frDefaultDaysBack) {
        newParams.push(["days", _frShowDaysBack]);
    }
    if (_frShowRows != null && _frShowRows !== frDefaultRows) {
        newParams.push(["rows", _frShowRows]);
    }

    // Next step is to create search params for the other filters too

    const newURL = `${urlReplace(url_viewFieldReports)}#${new URLSearchParams(newParams).toString()}`;
    window.history.replaceState(null, "", newURL);
}
