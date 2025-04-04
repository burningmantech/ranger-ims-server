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
const eventID = ims.eventID();
//
// Initialize UI
//
initIncidentsPage();
async function initIncidentsPage() {
    ims.commonPageInit();
    window.showState = showState;
    window.showDays = showDays;
    window.showRows = showRows;
    window.toggleCheckAllTypes = toggleCheckAllTypes;
    ims.disableEditing();
    await loadEventFieldReports();
    initIncidentsTable();
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
            document.getElementById("new_incident").click();
        }
    });
    document.getElementById("helpModal").addEventListener("keydown", function (e) {
        if (e.key === "?") {
            helpModal.toggle();
        }
    });
}
//
// Load event field reports
//
// Note that nothing from these data is displayed in the incidents table.
// We do this fetch in order to make incidents searchable by text in their
// attached field reports.
async function loadEventFieldReports() {
    const { json, err } = await ims.fetchJsonNoThrow(ims.urlReplace(url_fieldReports + "?exclude_system_entries=true"), null);
    if (err != null) {
        const message = `Failed to load event field reports: ${err}`;
        console.error(message);
        ims.setErrorMessage(message);
        return { err: message };
    }
    const reports = {};
    for (const report of json) {
        reports[report.number] = report;
    }
    ims.setEventFieldReports(reports);
    console.log("Loaded event field reports");
    if (incidentsTable != null) {
        incidentsTable.ajax.reload();
        ims.clearErrorMessage();
    }
    return { err: null };
}
//
// Dispatch queue table
//
// The DataTables object
let incidentsTable = null;
function initIncidentsTable() {
    initDataTables();
    initTableButtons();
    initSearchField();
    initSearch();
    ims.clearErrorMessage();
    if (editingAllowed) {
        ims.enableEditing();
    }
    ims.requestEventSourceLock();
    ims.newIncidentChannel().onmessage = async function (e) {
        if (e.data.update_all) {
            console.log("Reloading the whole table to be cautious, as an SSE was missed");
            incidentsTable.ajax.reload();
            ims.clearErrorMessage();
            return;
        }
        const number = e.data.incident_number;
        const event = e.data.event_id;
        if (event !== eventID) {
            return;
        }
        const { json, err } = await ims.fetchJsonNoThrow(ims.urlReplace(url_incidentNumber).replace("<incident_number>", number.toString()), null);
        if (err != null) {
            const message = `Failed to update Incident ${number}: ${err}`;
            console.error(message);
            ims.setErrorMessage(message);
            return;
        }
        // Now update/create the relevant row. This is a change from pre-2025, in that
        // we no longer reload all incidents here on any single incident update.
        let done = false;
        incidentsTable.rows().every(function () {
            // @ts-expect-error use of "this" for DataTables
            const existingIncident = this.data();
            if (existingIncident.number === number) {
                console.log("Updating Incident " + number);
                // @ts-expect-error use of "this" for DataTables
                this.data(json);
                done = true;
            }
        });
        if (!done) {
            console.log("Loading new Incident " + number);
            incidentsTable.row.add(json);
        }
        ims.clearErrorMessage();
        incidentsTable.processing(false);
        incidentsTable.draw();
    };
}
//
// Initialize DataTables
//
function initDataTables() {
    function dataHandler(incidents) {
        return incidents;
    }
    // @ts-expect-error JQuery
    $.fn.dataTable.ext.errMode = "none";
    // @ts-expect-error JQuery
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
        // Responsive is too slow to resize when all Incidents are shown.
        // Decide on this another day.
        // "responsive": {
        //     "details": false,
        // },
        "ajax": {
            "url": ims.urlReplace(url_incidents + "?exclude_system_entries=true"),
            "dataSrc": dataHandler,
            "error": function (request, _status, error) {
                // The "abort" case is a special snowflake.
                // There are times we do two table refreshes in quick succession, and in
                // those cases, the first call gets aborted. We don't want to set an error
                // message in those cases.
                if (error === "abort") {
                    return;
                }
                let errMsg = "";
                if (error) {
                    errMsg = error;
                }
                else if (request.responseText) {
                    errMsg = request.responseText;
                }
                else {
                    errMsg = "DataTables error";
                }
                ims.setErrorMessage(errMsg);
            },
        },
        "columns": [
            {
                "name": "incident_number",
                "className": "incident_number text-right all",
                "data": "number",
                "defaultContent": null,
                "cellType": "th",
                // "all" class --> very high responsivePriority
            },
            {
                "name": "incident_created",
                "className": "incident_created text-center",
                "data": "created",
                "defaultContent": null,
                "render": ims.renderDate,
                "responsivePriority": 7,
            },
            {
                "name": "incident_state",
                "className": "incident_state text-center",
                "data": "state",
                "defaultContent": null,
                "render": ims.renderState,
                "responsivePriority": 3,
            },
            {
                "name": "incident_summary",
                "className": "incident_summary all",
                "data": "summary",
                "defaultContent": "",
                "render": ims.renderSummary,
                // "all" class --> very high responsivePriority
            },
            {
                "name": "incident_types",
                "className": "incident_types",
                "data": "incident_types",
                "defaultContent": "",
                "render": ims.renderSafeSorted,
                "width": "5em",
                "responsivePriority": 4,
            },
            {
                "name": "incident_location",
                "className": "incident_location",
                "data": "location",
                "defaultContent": "",
                "render": ims.renderLocation,
                "responsivePriority": 5,
            },
            {
                "name": "incident_ranger_handles",
                "className": "incident_ranger_handles",
                "data": "ranger_handles",
                "defaultContent": "",
                "render": ims.renderSafeSorted,
                "width": "6em",
                "responsivePriority": 6,
            },
            {
                "name": "incident_last_modified",
                "className": "incident_last_modified text-center",
                "data": "last_modified",
                "defaultContent": null,
                "render": ims.renderDate,
                "responsivePriority": 8,
            },
        ],
        "order": [
            [0, "dsc"],
        ],
        "createdRow": function (row, incident, _index) {
            row.addEventListener("click", function (_e) {
                // Open new context with link
                window.open(ims.urlReplace(url_viewIncidents) + incident.number, "Incident:" + eventID + "#" + incident.number);
            });
            row.getElementsByClassName("incident_created")[0]
                .setAttribute("title", ims.fullDateTime.format(Date.parse(incident.created)));
            row.getElementsByClassName("incident_last_modified")[0]
                .setAttribute("title", ims.fullDateTime.format(Date.parse(incident.last_modified)));
        },
    });
}
//
// Initialize table buttons
//
function initTableButtons() {
    const typeFilter = document.getElementById("ul_show_type");
    for (const type of allIncidentTypes) {
        const a = document.createElement("a");
        a.href = "#";
        a.classList.add("dropdown-item", "dropdown-item-checkable", "dropdown-item-checked");
        a.textContent = type.toString();
        typeFilter.append(a);
    }
    for (const el of document.getElementsByClassName("dropdown-item-checkable")) {
        const htmlEl = el;
        htmlEl.addEventListener("click", function (e) {
            e.preventDefault();
            htmlEl.classList.toggle("dropdown-item-checked");
            showCheckedTypes(true);
        });
    }
    const fragmentParams = ims.windowFragmentParams();
    // Set button defaults
    const types = fragmentParams.getAll("type");
    if (types.length > 0) {
        const validTypes = [];
        let includeBlanks = false;
        let includeOthers = false;
        for (const t of types) {
            if (t && allIncidentTypes.indexOf(t) !== -1) {
                validTypes.push(t);
            }
            else if (t === _blankPlaceholder) {
                includeBlanks = true;
            }
            else if (t === _otherPlaceholder) {
                includeOthers = true;
            }
        }
        setCheckedTypes(validTypes, includeBlanks, includeOthers);
    }
    showCheckedTypes(false);
    showState(fragmentParams.get("state") ?? defaultState, false);
    showDays(fragmentParams.get("days") ?? defaultDaysBack, false);
    showRows(fragmentParams.get("rows") ?? defaultRows, false);
}
//
// Initialize search field
//
const _searchDelayMs = 250;
let _searchDelayTimer = undefined;
function initSearchField() {
    // Search field handling
    const searchInput = document.getElementById("search_input");
    function searchAndDraw() {
        replaceWindowState();
        let q = searchInput.value;
        let isRegex = false;
        if (q.startsWith("/") && q.endsWith("/")) {
            isRegex = true;
            q = q.slice(1, q.length - 1);
        }
        incidentsTable.search(q, isRegex);
        incidentsTable.draw();
    }
    const fragmentParams = ims.windowFragmentParams();
    const queryString = fragmentParams.get("q");
    if (queryString) {
        searchInput.value = queryString;
        searchAndDraw();
    }
    searchInput.addEventListener("keyup", function () {
        // Delay the search in case the user is still typing.
        // This reduces perceived lag, since searching can be
        // very slow, and it's super annoying for a user when
        // the page fully locks up before they're done typing.
        clearTimeout(_searchDelayTimer);
        _searchDelayTimer = setTimeout(searchAndDraw, _searchDelayMs);
    });
    searchInput.addEventListener("keydown", function (e) {
        // No shortcuts when ctrl, alt, or meta is being held down
        if (e.altKey || e.ctrlKey || e.metaKey) {
            return;
        }
        // "Jump to Incident" functionality, triggered on hitting Enter
        if (e.key === "Enter") {
            // If the value in the search box is an integer, assume it's an IMS number and go to it.
            // This will work regardless of whether that incident is visible with the current filters.
            const val = searchInput.value;
            if (ims.integerRegExp.test(val)) {
                // Open new context with link
                window.open(ims.urlReplace(url_viewIncidents) + val, "Incident:" + eventID + "#" + val);
                searchInput.value = "";
            }
        }
    });
}
//
// Initialize search plug-in
//
function initSearch() {
    incidentsTable.search.fixed("modification_date", function (_searchStr, _rowData, rowIndex) {
        const incident = incidentsTable.data()[rowIndex];
        return !(_showModifiedAfter != null &&
            new Date(Date.parse(incident.last_modified)) < _showModifiedAfter);
    });
    incidentsTable.search.fixed("state", function (_searchStr, _rowData, rowIndex) {
        const incident = incidentsTable.data()[rowIndex];
        let state;
        if (_showState != null) {
            switch (_showState) {
                case "all":
                    break;
                case "active":
                    state = ims.stateForIncident(incident);
                    if (state === "on_hold" || state === "closed") {
                        return false;
                    }
                    break;
                case "open":
                    state = ims.stateForIncident(incident);
                    if (state === "closed") {
                        return false;
                    }
                    break;
            }
        }
        return true;
    });
    incidentsTable.search.fixed("type", function (_searchStr, _rowData, rowIndex) {
        const incident = incidentsTable.data()[rowIndex];
        // don't bother with filtering, which may be computationally expensive,
        // if all types seem to be selected
        if (!allTypesChecked()) {
            const rowTypes = Object.values(incident.incident_types ?? []);
            const intersect = rowTypes.filter(t => _showTypes.includes(t)).length > 0;
            const blankShow = _showBlankType && rowTypes.length === 0;
            const otherShow = _showOtherType && rowTypes.filter(t => !(allIncidentTypes.includes(t))).length > 0;
            if (!intersect && !blankShow && !otherShow) {
                return false;
            }
        }
        return true;
    });
}
//
// Show state button handling
//
let _showState = null;
const defaultState = "open";
function showState(stateToShow, replaceState) {
    const item = document.getElementById("show_state_" + stateToShow);
    // Get title from selected item
    const selection = item.getElementsByClassName("name")[0].textContent;
    // Update menu title to reflect selected item
    const menu = document.getElementById("show_state");
    menu.getElementsByClassName("selection")[0].textContent = selection;
    _showState = stateToShow;
    if (replaceState) {
        replaceWindowState();
    }
    incidentsTable.draw();
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
    const item = document.getElementById("show_days_" + id);
    // Get title from selected item
    const selection = item.getElementsByClassName("name")[0].textContent;
    // Update menu title to reflect selected item
    const menu = document.getElementById("show_days");
    menu.getElementsByClassName("selection")[0].textContent = selection;
    if (daysBackToShow === "all") {
        _showModifiedAfter = null;
    }
    else {
        const after = new Date();
        after.setHours(0);
        after.setMinutes(0);
        after.setSeconds(0);
        after.setDate(after.getDate() - Number(daysBackToShow));
        _showModifiedAfter = after;
    }
    if (replaceState) {
        replaceWindowState();
    }
    incidentsTable.draw();
}
//
// Show type button handling
//
// list of Incident Types to show, in text form
let _showTypes = [];
let _showBlankType = true;
let _showOtherType = true;
// these must match values in incidents_template/template.xhtml
const _blankPlaceholder = "(blank)";
const _otherPlaceholder = "(other)";
function setCheckedTypes(types, includeBlanks, includeOthers) {
    for (const type of document.querySelectorAll('#ul_show_type > a')) {
        if (types.includes(type.textContent) ||
            (includeBlanks && type.id === "show_blank_type") ||
            (includeOthers && type.id === "show_other_type")) {
            type.classList.add("dropdown-item-checked");
        }
        else {
            type.classList.remove("dropdown-item-checked");
        }
    }
}
function toggleCheckAllTypes() {
    if (_showTypes.length === 0 || _showTypes.length < allIncidentTypes.length) {
        setCheckedTypes(allIncidentTypes, true, true);
    }
    else {
        setCheckedTypes([], false, false);
    }
    showCheckedTypes(true);
}
function readCheckedTypes() {
    _showTypes = [];
    for (const type of document.querySelectorAll('#ul_show_type > a')) {
        if (type.id === "show_blank_type") {
            _showBlankType = type.classList.contains("dropdown-item-checked");
        }
        else if (type.id === "show_other_type") {
            _showOtherType = type.classList.contains("dropdown-item-checked");
        }
        else if (type.classList.contains("dropdown-item-checked")) {
            _showTypes.push(type.textContent);
        }
    }
}
function allTypesChecked() {
    return _showTypes.length === allIncidentTypes.length && _showBlankType && _showOtherType;
}
function showCheckedTypes(replaceState) {
    readCheckedTypes();
    const numTypesShown = _showTypes.length + (_showBlankType ? 1 : 0) + (_showOtherType ? 1 : 0);
    const showTypeText = allTypesChecked() ? "All Types" : `Types (${numTypesShown})`;
    document.getElementById("show_type").textContent = showTypeText;
    if (replaceState) {
        replaceWindowState();
    }
    incidentsTable.draw();
}
//
// Show rows button handling
//
let _showRows = null;
const defaultRows = 25;
function showRows(rowsToShow, replaceState) {
    const id = rowsToShow.toString();
    _showRows = rowsToShow;
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
        replaceWindowState();
    }
    incidentsTable.page.len(rowsToShow);
    incidentsTable.draw();
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
    if (!allTypesChecked()) {
        for (const t of _showTypes) {
            newParams.push(["type", t]);
        }
        if (_showBlankType) {
            newParams.push(["type", _blankPlaceholder]);
        }
        if (_showOtherType) {
            newParams.push(["type", _otherPlaceholder]);
        }
    }
    if (_showState != null && _showState !== defaultState) {
        newParams.push(["state", _showState]);
    }
    if (_showDaysBack != null && _showDaysBack !== defaultDaysBack) {
        newParams.push(["days", _showDaysBack.toString()]);
    }
    if (_showRows != null && _showRows !== defaultRows) {
        newParams.push(["rows", _showRows.toString()]);
    }
    const newURL = `${ims.urlReplace(url_viewIncidents)}#${new URLSearchParams(newParams).toString()}`;
    window.history.replaceState(null, "", newURL);
}
