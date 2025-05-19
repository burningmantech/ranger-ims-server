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
import * as ims from "./ims.js";
let fieldReportsTable = null;
let _frShowModifiedAfter = null;
let _frShowDaysBack = null;
const frDefaultDaysBack = "all";
const _frSearchDelayMs = 250;
let _frSearchDelayTimer = undefined;
let _frShowRows = null;
const frDefaultRows = 25;
//
// Initialize UI
//
initFieldReportsPage();
async function initFieldReportsPage() {
    const initResult = await ims.commonPageInit();
    if (!initResult.authInfo.authenticated) {
        ims.redirectToLogin();
        return;
    }
    window.frShowDays = frShowDays;
    window.frShowRows = frShowRows;
    ims.disableEditing();
    initFieldReportsTable();
    const helpModal = ims.bsModal(document.getElementById("helpModal"));
    // Keyboard shortcuts
    document.addEventListener("keydown", function (e) {
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
            helpModal.toggle();
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
    document.getElementById("helpModal").addEventListener("keydown", function (e) {
        if (e.key === "?") {
            helpModal.toggle();
        }
    });
}
//
// Dispatch queue table
//
function initFieldReportsTable() {
    frInitDataTables();
    frInitTableButtons();
    frInitSearchField();
    frInitSearch();
    ims.clearErrorMessage();
    if (ims.eventAccess?.writeFieldReports) {
        ims.enableEditing();
    }
    ims.requestEventSourceLock();
    ims.newFieldReportChannel().onmessage = function (e) {
        if (e.data.update_all) {
            console.log("Reloading the whole table to be cautious, as an SSE was missed");
            fieldReportsTable.ajax.reload();
            ims.clearErrorMessage();
            return;
        }
        const number = e.data.field_report_number;
        const event = e.data.event_id;
        if (event !== ims.pathIds.eventID) {
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
        ims.clearErrorMessage();
    };
}
//
// Initialize DataTables
//
function frInitDataTables() {
    DataTable.ext.errMode = "none";
    fieldReportsTable = new DataTable("#field_reports_table", {
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
        // DataTables gets mad if you return a Promise from this function, so we use an inner
        // async function instead.
        // https://datatables.net/forums/discussion/47411/i-always-get-error-when-i-use-table-ajax-reload
        "ajax": function (_data, callback, _settings) {
            async function doAjax() {
                const { json, err } = await ims.fetchJsonNoThrow(
                // don't use exclude_system_entries here, since the field reports
                // per-user authorization can exclude field reports entirely from
                // someone who created a field report but then didn't add an
                // entry to it.
                ims.urlReplace(url_fieldReports), null);
                if (err != null || json == null) {
                    ims.setErrorMessage(`Failed to load table: ${err}`);
                    return;
                }
                callback({ data: json });
            }
            doAjax();
        },
        "columns": [
            {
                "name": "field_report_number",
                "className": "field_report_number text-right all",
                "data": "number",
                "defaultContent": null,
                "cellType": "th",
            },
            {
                "name": "field_report_created",
                "className": "field_report_created text-center",
                "data": "created",
                "defaultContent": null,
                "render": ims.renderDate,
                "responsivePriority": 4,
            },
            {
                "name": "field_report_summary",
                "className": "field_report_summary all",
                "data": "summary",
                "defaultContent": "",
                "render": renderSummary,
            },
            {
                "name": "field_report_incident",
                "className": "field_report_incident text-center",
                "data": "incident",
                "defaultContent": "-",
                "render": ims.renderIncidentNumber,
                "responsivePriority": 3,
            },
        ],
        "order": [
            // creation time descending
            [1, "dsc"],
        ],
        "createdRow": function (row, fieldReport, _index) {
            row.addEventListener("click", function (_e) {
                // Open new context with link
                window.open(ims.urlReplace(url_viewFieldReports) + fieldReport.number, "Field_Report:" + fieldReport.number);
            });
            row.getElementsByClassName("field_report_created")[0]
                .setAttribute("title", ims.fullDateTime.format(Date.parse(fieldReport.created)));
        },
    });
}
function renderSummary(_data, type, fieldReport) {
    switch (type) {
        case "display":
            return ims.textAsHTML(ims.summarizeIncidentOrFR(fieldReport));
        case "sort":
            return ims.summarizeIncidentOrFR(fieldReport);
        case "filter":
            return ims.reportTextFromIncident(fieldReport);
        case "type":
            return "";
    }
    return undefined;
}
//
// Initialize table buttons
//
function frInitTableButtons() {
    const fragmentParams = ims.windowFragmentParams();
    // Set button defaults
    frShowDays(fragmentParams.get("days") ?? frDefaultDaysBack, false);
    frShowRows(fragmentParams.get("rows") ?? frDefaultRows, false);
}
//
// Initialize search field
//
function frInitSearchField() {
    // Search field handling
    const searchInput = document.getElementById("search_input");
    function searchAndDraw() {
        frReplaceWindowState();
        let q = searchInput.value;
        let isRegex = false;
        if (q.startsWith("/") && q.endsWith("/")) {
            isRegex = true;
            q = q.slice(1, q.length - 1);
        }
        fieldReportsTable.search(q, isRegex);
        fieldReportsTable.draw();
    }
    const fragmentParams = ims.windowFragmentParams();
    const queryString = fragmentParams.get("q");
    if (queryString) {
        searchInput.value = queryString;
        searchAndDraw();
    }
    searchInput.addEventListener("keyup", function (e) {
        // No action on Enter key
        if (e.key === "Enter") {
            return;
        }
        // Delay the search in case the user is still typing.
        // This reduces perceived lag, since searching can be
        // very slow, and it's super annoying for a user when
        // the page fully locks up before they're done typing.
        clearTimeout(_frSearchDelayTimer);
        _frSearchDelayTimer = setTimeout(searchAndDraw, _frSearchDelayMs);
    });
    searchInput.addEventListener("keydown", function (e) {
        // No shortcuts when ctrl, alt, or meta is being held down
        if (e.altKey || e.ctrlKey || e.metaKey) {
            return;
        }
        // "Jump to Field Report" functionality, triggered on hitting Enter
        if (e.key === "Enter") {
            // If the value in the search box is an integer, assume it's an FR number and go to it.
            // This will work regardless of whether that FR is visible with the current filters.
            const val = searchInput.value;
            if (ims.integerRegExp.test(val)) {
                // Open new context with link
                window.open(ims.urlReplace(url_viewFieldReports) + val, "Field_Report:" + val);
                searchInput.value = "";
            }
            // Otherwise, search immediately on Enter.
            clearTimeout(_frSearchDelayTimer);
            searchAndDraw();
        }
    });
}
//
// Initialize search plug-in
//
function frInitSearch() {
    function modifiedAfter(fieldReport, timestamp) {
        if (timestamp < new Date(Date.parse(fieldReport.created))) {
            return true;
        }
        // needs to use native comparison
        for (const entry of fieldReport.report_entries ?? []) {
            if (timestamp < new Date(Date.parse(entry.created))) {
                return true;
            }
        }
        return false;
    }
    fieldReportsTable.search.fixed("modification_date", function (_searchStr, _rowData, rowIndex) {
        const fieldReport = fieldReportsTable.data()[rowIndex];
        return !(_frShowModifiedAfter != null &&
            !modifiedAfter(fieldReport, _frShowModifiedAfter));
    });
}
//
// Show days button handling
//
function frShowDays(daysBackToShow, replaceState) {
    const id = daysBackToShow.toString();
    _frShowDaysBack = daysBackToShow;
    const item = document.getElementById("show_days_" + id);
    // Get title from selected item
    const selection = item.getElementsByClassName("name")[0].textContent;
    // Update menu title to reflect selected item
    const menu = document.getElementById("show_days");
    menu.getElementsByClassName("selection")[0].textContent = selection;
    if (daysBackToShow === "all") {
        _frShowModifiedAfter = null;
    }
    else {
        const after = new Date();
        after.setHours(0);
        after.setMinutes(0);
        after.setSeconds(0);
        after.setDate(after.getDate() - Number(daysBackToShow));
        _frShowModifiedAfter = after;
    }
    if (replaceState) {
        frReplaceWindowState();
    }
    fieldReportsTable.draw();
}
//
// Show rows button handling
//
function frShowRows(rowsToShow, replaceState) {
    const id = rowsToShow.toString();
    _frShowRows = rowsToShow;
    const item = document.getElementById("show_rows_" + id);
    // Get title from selected item
    const selection = item.getElementsByClassName("name")[0].textContent;
    // Update menu title to reflect selected item
    const menu = document.getElementById("show_rows");
    menu.getElementsByClassName("selection")[0].textContent = selection;
    if (rowsToShow === "all") {
        rowsToShow = -1;
    }
    if (replaceState) {
        frReplaceWindowState();
    }
    fieldReportsTable.page.len(rowsToShow);
    fieldReportsTable.draw();
}
//
// Update the page URL based on the search input and other filters.
//
function frReplaceWindowState() {
    const newParams = [];
    const searchVal = document.getElementById("search_input").value;
    if (searchVal) {
        newParams.push(["q", searchVal]);
    }
    if (_frShowDaysBack != null && _frShowDaysBack !== frDefaultDaysBack) {
        newParams.push(["days", _frShowDaysBack.toString()]);
    }
    if (_frShowRows != null && _frShowRows !== frDefaultRows) {
        newParams.push(["rows", _frShowRows.toString()]);
    }
    // Next step is to create search params for the other filters too
    const newURL = `${ims.urlReplace(url_viewFieldReports)}#${new URLSearchParams(newParams).toString()}`;
    window.history.replaceState(null, "", newURL);
}
