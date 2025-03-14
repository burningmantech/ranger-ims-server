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


// declare var incidentNumber: number;

//
// Initialize UI
//

async function initIncidentPage(): Promise<void> {
    await loadBody();
    addLocationAddressOptions();
    disableEditing();
    await loadAndDisplayIncident();
    await loadPersonnel();
    drawRangers();
    drawRangersToAdd();
    await loadIncidentTypes();
    drawIncidentTypesToAdd();
    await loadAllFieldReports();
    renderFieldReportData();

    // for a new incident, jump to summary field
    if (incident.number == null) {
        // @ts-ignore JQuery
        $("#incident_summary").focus();
    }

    // Warn the user if they're about to navigate away with unsaved text.
    window.addEventListener("beforeunload", function (e) {
        if ((document.getElementById("report_entry_add") as HTMLTextAreaElement).value !== "") {
            e.preventDefault();
        }
    });

    // Fire-and-forget this promise, since it tries forever to acquire a lock
    let ignoredPromise = requestEventSourceLock();

    const incidentChannel = new BroadcastChannel(incidentChannelName);
    incidentChannel.onmessage = async function (e) {
        const number = e.data.incident_number;
        const event = e.data.event_id;
        const updateAll = e.data.update_all;

        if (updateAll || (event === eventID && number === incidentNumber)) {
            console.log("Got incident update: " + number);
            await loadAndDisplayIncident();
            await loadAllFieldReports();
            renderFieldReportData();
        }
    };

    const fieldReportChannel = new BroadcastChannel(fieldReportChannelName);
    fieldReportChannel.onmessage = async function (e: MessageEvent): Promise<void> {
        const updateAll = e.data.update_all;
        if (updateAll) {
            console.log("Updating all field reports");
            await loadAllFieldReports();
            renderFieldReportData();
            return;
        }

        const number = e.data.field_report_number;
        const event = e.data.event_id;
        if (event === eventID) {
            console.log("Got field report update: " + number);
            await loadOneFieldReport(number);
            renderFieldReportData();
            return;
        }
    };

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
        // a --> jump to add a new report entry
        if (e.key === "a") {
            e.preventDefault();
            // Scroll to report_entry_add field
            // @ts-ignore JQuery
            $("html, body").animate({scrollTop: $("#report_entry_add").offset().top}, 500);
            // @ts-ignore JQuery
            $("#report_entry_add").focus();
        }
        // h --> toggle showing system entries
        if (e.key.toLowerCase() === "h") {
            (document.getElementById("history_checkbox") as HTMLInputElement).click();
        }
        // n --> new incident
        if (e.key.toLowerCase() === "n") {
            (window.open("./new", '_blank') as Window).focus();
        }
    });
    (document.getElementById("helpModal") as HTMLDivElement).addEventListener("keydown", function(e) {
        if (e.key === "?") {
            // @ts-ignore JQuery
            $("#helpModal").modal("toggle");
        }
    });
    // @ts-ignore JQuery
    $("#report_entry_add")[0].addEventListener("keydown", function (e) {
        // @ts-ignore JQuery
        const submitEnabled = !$("#report_entry_submit").hasClass("disabled");
        if (submitEnabled && (e.ctrlKey || e.altKey) && e.key === "Enter") {
            submitReportEntry();
        }
    });
}


//
// Load incident
//

let incident: any|null = null;

async function loadIncident() {
    let number: number|null = null;
    if (incident == null) {
        // First time here.  Use page JavaScript initial value.
        number = incidentNumber??null;
    } else {
        // We have an incident already.  Use that number.
        number = incident.number;
    }

    if (number == null) {
        incident = {
            "number": null,
            "state": "new",
            "priority": 3,
            "summary": "",
        };
    } else {
        const {json, err} = await fetchJsonNoThrow(urlReplace(url_incidents) + number, null);
        if (err != null) {
            disableEditing();
            const message = `Failed to load Incident ${number}: ${err}`;
            console.error(message);
            setErrorMessage(message);
            return {err: message};
        }
        incident = json;
    }
    return {err: null};
}

async function loadAndDisplayIncident() {
    await loadIncident();
    if (incident == null) {
        const message = "Incident failed to load";
        console.log(message);
        setErrorMessage(message);
        return;
    }

    drawIncidentFields();
    clearErrorMessage();

    if (editingAllowed) {
        enableEditing();
    }

    if (attachmentsAllowed) {
        (document.getElementById("attach_file") as HTMLInputElement).classList.remove("hidden");
    }
}

// Do all the client-side rendering based on the state of allFieldReports.
function renderFieldReportData() {
    loadAttachedFieldReports();
    drawFieldReportsToAttach();
    drawMergedReportEntries();
    drawAttachedFieldReports();
}


//
// Load personnel
//

let personnel: PersonnelMap|null = null;

interface Personnel {
    handle: string;
    directory_id: number;
}

interface PersonnelMap {
    [index: string]: Personnel,
}

async function loadPersonnel(): Promise<{err: string|null}> {
    const {json, err} = await fetchJsonNoThrow(urlReplace(url_personnel + "?event_id=<event_id>"), null);
    if (err != null) {
        const message = `Failed to load personnel: ${err}`;
        console.error(message);
        setErrorMessage(message);
        return {err: message};
    }
    const _personnel: PersonnelMap = {};
    for (const record of json) {
        // Filter inactive Rangers out
        // FIXME: better yet: filter based on on-playa state
        switch (record.status) {
            case "active":
                break;
            default:
                continue;
        }

        _personnel[record.handle] = record;
    }
    personnel = _personnel;
    return {err: null};
}


//
// Load incident types
//

let incidentTypes: string[] = [];


async function loadIncidentTypes(): Promise<{err: string|null}> {
    const {json, err} = await fetchJsonNoThrow(url_incidentTypes, null);
    if (err != null) {
        const message = `Failed to load incident types: ${err}`;
        console.error(message);
        setErrorMessage(message);
        return {err: message};
    }
    const _incidentTypes: string[] = [];
    for (const record of json) {
        _incidentTypes.push(record);
    }
    _incidentTypes.sort();
    incidentTypes = _incidentTypes;
    return {err: null};
}

//
// Load all field reports
//

let allFieldReports: FieldReport[]|null|undefined = null;

async function loadAllFieldReports(): Promise<{err: string|null}> {
    if (allFieldReports === undefined) {
        return {err: null};
    }

    const {resp, json, err} = await fetchJsonNoThrow(urlReplace(url_fieldReports), null);
    if (err != null) {
        if (resp != null && resp.status === 403) {
            // We're not allowed to look these up.
            allFieldReports = undefined;
            console.error("Got a 403 looking up field reports");
            return {err: null};
        } else {
            const message = `Failed to load field reports: ${err}`;
            console.error(message);
            setErrorMessage(message);
            return {err: message};
        }
    }
    const _allFieldReports: FieldReport[] = [];
    for (const d of json) {
        _allFieldReports.push(d);
    }
    // apply a descending sort based on the field report number,
    // being cautious about field report number being null
    _allFieldReports.sort(function (a, b) {
        return (b.number ?? -1) - (a.number ?? -1);
    });
    allFieldReports = _allFieldReports;
    return {err: null};
}

async function loadOneFieldReport(fieldReportNumber: number): Promise<{err: string|null}> {
    if (allFieldReports === undefined) {
        return {err: null};
    }

    const {resp, json, err} = await fetchJsonNoThrow(
        urlReplace(url_fieldReport).replace("<field_report_number>", fieldReportNumber.toString()), null);
    if (err != null) {
        if (resp == null || resp.status !== 403) {
            const message = `Failed to load field report ${fieldReportNumber} ${err}`;
            console.error(message);
            setErrorMessage(message);
            return {err: message};
        }
    }

    let found = false;
    for (const i in allFieldReports) {
        if (allFieldReports[i].number === json.number) {
            allFieldReports[i] = json;
            found = true;
        }
    }
    if (!found) {
        if (allFieldReports == null) {
            allFieldReports = [];
        }
        allFieldReports.push(json);
        // apply a descending sort based on the field report number,
        // being cautious about field report number being null
        allFieldReports.sort(function (a, b) {
            return (b.number ?? -1) - (a.number ?? -1);
        });
    }

    return {err: null};
}


//
// Load attached field reports
//

let attachedFieldReports: FieldReport[]|null = null;

function loadAttachedFieldReports() {
    if (incidentNumber == null) {
        return;
    }
    const _attachedFieldReports: FieldReport[] = [];
    for (const fr of allFieldReports??[]) {
        if (fr.incident === incidentNumber) {
            _attachedFieldReports.push(fr);
        }
    }
    attachedFieldReports = _attachedFieldReports;
}


//
// Draw all fields
//

function drawIncidentFields() {
    drawIncidentTitle();
    drawIncidentNumber();
    drawState();
    drawCreated();
    drawPriority();
    drawIncidentSummary();
    drawRangers();
    drawIncidentTypes();
    drawLocationName();
    drawLocationAddressRadialHour();
    drawLocationAddressRadialMinute();
    drawLocationAddressConcentric();
    drawLocationDescription();
    toggleShowHistory();
    drawMergedReportEntries();

    // @ts-ignore JQuery
    $("#report_entry_add").on("input", reportEntryEdited);
}


//
// Add option elements to location address select elements
//

function addLocationAddressOptions(): void {
    const hours: number[] = range(1, 13);
    for (const hour of hours) {
        const hourStr = padTwo(hour);
        // @ts-ignore JQuery
        $("#incident_location_address_radial_hour")
            // @ts-ignore JQuery
            .append($("<option />", { "value": hourStr, "text": hourStr }))
            ;
    }

    const minutes: number[] = range(0, 12, 5);
    for (const minute of minutes) {
        const minuteStr = padTwo(minute);
        // @ts-ignore JQuery
        $("#incident_location_address_radial_minute")
            // @ts-ignore JQuery
            .append($("<option />", { "value": minuteStr, "text": minuteStr }))
            ;
    }

    for (const id in concentricStreetNameByID) {
        const name = concentricStreetNameByID[id];
        // @ts-ignore JQuery
        $("#incident_location_address_concentric")
            // @ts-ignore JQuery
            .append($("<option />", { "value": id, "text": name }))
            ;
    }
}


//
// Populate page title
//

function drawIncidentTitle(): void {
    document.title = incidentAsString(incident);
}


//
// Populate incident number
//

function drawIncidentNumber(): void {
    let number = incident.number;
    if (number == null) {
        number = "(new)";
    }
    // @ts-ignore JQuery
    $("#incident_number").text(number);
}


//
// Populate incident state
//

function drawState(): void {
    selectOptionWithValue(
        // @ts-ignore JQuery
        $("#incident_state"), stateForIncident(incident)
    );
}


//
// Populate created datetime
//

function drawCreated(): void {
    const date = incident.created;
    if (date == null) {
        return;
    }
    const d = Date.parse(date);
    // @ts-ignore JQuery
    $("#created_datetime").text(`${shortDate.format(d)} ${shortTimeSec.format(d)}`);
    // @ts-ignore JQuery
    $("#created_datetime").attr("title", fullDateTime.format(d));
}

//
// Populate incident priority
//

function drawPriority(): void {
    selectOptionWithValue(
        // @ts-ignore JQuery
        $("#incident_priority"), incident.priority
    );
}


//
// Populate incident summary
//

function drawIncidentSummary(): void {
    if (incident.summary) {
        // @ts-ignore JQuery
        $("#incident_summary").val(incident.summary);
        // @ts-ignore JQuery
        $("#incident_summary").attr("placeholder", "");
        return;
    }

    // @ts-ignore JQuery
    $("#incident_summary")[0].removeAttribute("value");
    const summarized = summarizeIncident(incident);
    if (summarized) {
        // only replace the placeholder if it would be nonempty
        // @ts-ignore JQuery
        $("#incident_summary").attr("placeholder", summarized);
    }
}


//
// Populate Rangers list
//

let _rangerItem = null;

function drawRangers() {
    if (_rangerItem == null) {
        // @ts-ignore JQuery
        _rangerItem = $("#incident_rangers_list")
            .children(".list-group-item:first")
            ;
    }

    const items: any[] = [];

    const handles = incident.ranger_handles??[];
    handles.sort((a, b) => a.localeCompare(b));

    for (const handle of handles) {
        let ranger: any = null;
        if (personnel?.[handle] == null) {
            ranger = textAsHTML(handle);
        } else {
            const person = personnel[handle];
            // @ts-ignore JQuery
            ranger = $("<a>", {
                text: textAsHTML(rangerAsString(person)),
                href: `${clubhousePersonURL}/${person.directory_id}`,
            });
        }
        // @ts-ignore JQuery
        const item = _rangerItem.clone();
        item.append(ranger);
        item.attr("value", textAsHTML(handle));
        items.push(item);
    }

    // @ts-ignore JQuery
    const container = $("#incident_rangers_list");
    container.empty();
    container.append(items);
}


function drawRangersToAdd(): void {
    // @ts-ignore JQuery
    const datalist = $("#ranger_handles");

    const handles: any[] = [];
    for (const handle in personnel) {
        handles.push(handle);
    }
    handles.sort((a, b) => a.localeCompare(b));

    datalist.empty();
    // @ts-ignore JQuery
    datalist.append($("<option />"));

    if (personnel != null) {
        for (const handle of handles) {
            const ranger = personnel[handle];

            // @ts-ignore JQuery
            const option = $("<option />");
            option.val(handle);
            option.text(rangerAsString(ranger));

            datalist.append(option);
        }
    }
}


function rangerAsString(ranger: Personnel): string {
    return ranger.handle;
}


//
// Populate incident types list
//

let _typesItem: any = null;

function drawIncidentTypes() {
    if (_typesItem == null) {
        // @ts-ignore JQuery
        _typesItem = $("#incident_types_list")
            .children(".list-group-item:first")
            ;
    }

    const items: any[] = [];

    const incidentTypes = incident.incident_types??[];
    incidentTypes.sort();

    for (const incidentType of incidentTypes) {
        const item = _typesItem.clone();
        item.attr("value", textAsHTML(incidentType));
        item.append(textAsHTML(incidentType));
        items.push(item);
    }

    // @ts-ignore JQuery
    const container = $("#incident_types_list");
    container.empty();
    container.append(items);
}


function drawIncidentTypesToAdd() {
    // @ts-ignore JQuery
    const datalist = $("#incident_types");

    datalist.empty();
    // @ts-ignore JQuery
    datalist.append($("<option />"));

    for (const incidentType of incidentTypes) {
        // @ts-ignore JQuery
        const option = $("<option />");
        option.val(incidentType);

        datalist.append(option);
    }
}


//
// Populate location
//

function drawLocationName() {
    if (incident.location?.name) {
        // @ts-ignore JQuery
        $("#incident_location_name").val(incident.location.name);
    }
}


function drawLocationAddressRadialHour() {
    let hour: string|null = null;
    if (incident.location?.radial_hour != null) {
        hour = padTwo(incident.location.radial_hour);
    }
    selectOptionWithValue(
        // @ts-ignore JQuery
        $("#incident_location_address_radial_hour"), hour
    );
}


function drawLocationAddressRadialMinute() {
    let minute: string|null = null;
    if (incident.location?.radial_minute != null) {
        minute = normalizeMinute(incident.location.radial_minute);
    }
    selectOptionWithValue(
        // @ts-ignore JQuery
        $("#incident_location_address_radial_minute"), minute
    );
}


function drawLocationAddressConcentric() {
    let concentric = null;
    if (incident.location?.concentric) {
        concentric = incident.location.concentric;
    }
    selectOptionWithValue(
        // @ts-ignore JQuery
        $("#incident_location_address_concentric"), concentric
    );
}


function drawLocationDescription() {
    if (incident.location?.description) {
        // @ts-ignore JQuery
        $("#incident_location_description")
            .val(incident.location.description)
            ;
    }
}


//
// Draw report entries
//

function drawMergedReportEntries() {
    const entries: ReportEntry[] = [];

    if (incident.report_entries) {
        // @ts-ignore JQuery
        $.merge(entries, incident.report_entries);
    }

    if (attachedFieldReports) {
        // @ts-ignore JQuery
        if ($("#merge_reports_checkbox").is(":checked")) {
            for (const report of attachedFieldReports) {
                for (const entry of report.report_entries??[]) {
                    entry.merged = report.number;
                    entries.push(entry);
                }
            }
        }
    }

    entries.sort(compareReportEntries);

    drawReportEntries(entries);
}


let _reportsItem = null;

function drawAttachedFieldReports() {
    if (_reportsItem == null) {
        // @ts-ignore JQuery
        _reportsItem = $("#attached_field_reports")
            .children(".list-group-item:first")
            ;
        if (_reportsItem == null) {
            console.error("found no reportsItem");
            return;
        }
    }

    const items: object[] = [];

    const reports = attachedFieldReports??[];
    reports.sort();

    for (const report of reports) {
        // @ts-ignore JQuery
        const item = _reportsItem.clone();
        // @ts-ignore JQuery
        const link = $("<a />");
        link.attr("href", urlReplace(url_viewFieldReports) + report.number);
        link.text(fieldReportAsString(report));
        item.append(link);
        item.data(report);
        items.push(item);
    }

    // @ts-ignore JQuery
    const container = $("#attached_field_reports");
    container.empty();
    container.append(items);
}


function drawFieldReportsToAttach() {
    // @ts-ignore JQuery
    const container = $("#attached_field_report_add_container");
    // @ts-ignore JQuery
    const select = $("#attached_field_report_add");

    select.empty();
    // @ts-ignore JQuery
    select.append($("<option />"));

    if (!allFieldReports) {
        container.addClass("hidden");
    } else {
        // @ts-ignore JQuery
        select.append($("<optgroup label=\"Unattached to any incident\">"));
        for (const report of allFieldReports) {
            // Skip field reports that *are* attached to an incident
            if (report.incident != null) {
                continue;
            }
            // @ts-ignore JQuery
            const option = $("<option />");
            option.val(report.number);
            option.text(fieldReportAsString(report));

            select.append(option);
        }
        // @ts-ignore JQuery
        select.append($("</optgroup>"));
        // @ts-ignore JQuery
        select.append($("<optgroup label=\"Attached to another incident\">"));
        for (const report of allFieldReports) {
            // Skip field reports that *are not* attached to an incident
            if (report.incident == null) {
                continue;
            }
            // Skip field reports that are already attached this incident
            if (report.incident === incidentNumber) {
                continue;
            }
            // @ts-ignore JQuery
            const option = $("<option />");
            option.val(report.number);
            option.text(fieldReportAsString(report));

            select.append(option);
        }
        // @ts-ignore JQuery
        select.append($("</optgroup>"));

        container.removeClass("hidden");
    }
}


//
// Editing
//

async function sendEdits(edits: any): Promise<{err:string|null}> {
    const number = incident.number;
    let url = urlReplace(url_incidents);

    if (number == null) {
        // We're creating a new incident.
        const required = ["state", "priority"];
        for (const key of required) {
            if (edits[key] == null) {
                edits[key] = incident[key];
            }
        }
    } else {
        // We're editing an existing incident.
        edits.number = number;
        url += number;
    }

    const {resp, err} = await fetchJsonNoThrow(url, {
        body: edits,
    });

    if (err != null) {
        const message = `Failed to apply edit: ${err}`;
        await loadAndDisplayIncident();
        setErrorMessage(message);
        return {err: message};
    }

    if (number == null && resp != null) {
        // We created a new incident.
        // We need to find out the created incident number so that future
        // edits don't keep creating new resources.

        let newNumber: string|number|null = resp.headers.get("X-IMS-Incident-Number");
        // Check that we got a value back
        if (newNumber == null) {
            const msg = "No X-IMS-Incident-Number header provided.";
            setErrorMessage(msg);
            return {err: msg};
        }

        newNumber = parseInt(newNumber);
        // Check that the value we got back is valid
        if (isNaN(newNumber)) {
            const msg = "Non-integer X-IMS-Incident-Number header provided:" + newNumber;
            setErrorMessage(msg);
            return {err: msg};
        }

        // Store the new number in our incident object
        incidentNumber = incident.number = newNumber;

        // Update browser history to update URL
        drawIncidentTitle();
        window.history.pushState(
            null, document.title, urlReplace(url_viewIncidents) + newNumber
        );
    }

    await loadAndDisplayIncident();
    return {err: null};
}
registerSendEdits = sendEdits;

async function editState() {
    // @ts-ignore JQuery
    const $state = $("#incident_state");

    if ($state.val() === "closed" && (incident.incident_types??[]).length === 0) {
        window.alert(
            "Closing out this incident?\n"+
            "Please add an incident type!\n\n" +
            "Special cases:\n" +
            "    Junk: for erroneously-created Incidents\n" +
            "    Admin: for administrative information, i.e. not Incidents at all\n\n" +
            "See the Incident Types help link for more details.\n"
        );
    }

    await editFromElement($state, "state");
}


async function editIncidentSummary() {
    // @ts-ignore JQuery
    await editFromElement($("#incident_summary"), "summary");
}


async function editLocationName() {
    // @ts-ignore JQuery
    await editFromElement($("#incident_location_name"), "location.name");
}


function transformAddressInteger(value): number|null {
    if (!value) {
        return null;
    }
    return parseInt(value);
}


async function editLocationAddressRadialHour(): Promise<void> {
    await editFromElement(
        // @ts-ignore JQuery
        $("#incident_location_address_radial_hour"),
        "location.radial_hour",
        transformAddressInteger
    );
}


async function editLocationAddressRadialMinute(): Promise<void> {
    await editFromElement(
        // @ts-ignore JQuery
        $("#incident_location_address_radial_minute"),
        "location.radial_minute",
        transformAddressInteger
    );
}


async function editLocationAddressConcentric(): Promise<void> {
    await editFromElement(
        // @ts-ignore JQuery
        $("#incident_location_address_concentric"),
        "location.concentric",
        transformAddressInteger
    );
}


async function editLocationDescription(): Promise<void> {
    // @ts-ignore JQuery
    await editFromElement($("#incident_location_description"), "location.description");
}


async function removeRanger(sender): Promise<void> {
    // @ts-ignore JQuery
    sender = $(sender);

    const rangerHandle = sender.parent().attr("value");

    await sendEdits(
        {
            "ranger_handles": incident.ranger_handles.filter(
                function(h) { return h !== rangerHandle; }
            ),
        },
    );
}


async function removeIncidentType(sender): Promise<void> {
    // @ts-ignore JQuery
    sender = $(sender);

    const incidentType = sender.parent().attr("value");
    await sendEdits({
        "incident_types": incident.incident_types.filter(
            function(t) { return t !== incidentType; }
        ),
    });
}

function normalize(str: string): string {
    return str.toLowerCase().trim();
}

async function addRanger(): Promise<void> {
    // @ts-ignore JQuery
    const select = $("#ranger_add");
    // @ts-ignore JQuery
    let handle = $(select).val();

    // make a copy of the handles
    const handles = (incident.ranger_handles??[]).slice();

    // fuzzy-match on handle, to allow case insensitivity and
    // leading/trailing whitespace.
    if (!(handle in (personnel??[]))) {
        const normalized = normalize(handle);
        for (const validHandle in personnel) {
            if (normalized === normalize(validHandle)) {
                handle = validHandle;
                break;
            }
        }
    }
    if (!(handle in (personnel??[]))) {
        // Not a valid handle
        select.val("");
        return;
    }

    if (handles.indexOf(handle) !== -1) {
        // Already in the list, so… move along.
        select.val("");
        return;
    }

    handles.push(handle);

    const {err} = await sendEdits({"ranger_handles": handles});
    if (err !== null) {
        controlHasError(select);
        select.val("");
        return;
    }
    select.val("");
    controlHasSuccess(select, 1000);
}


async function addIncidentType(): Promise<void> {
    // @ts-ignore JQuery
    const select = $("#incident_type_add");
    // @ts-ignore JQuery
    let incidentType = $(select).val();

    // make a copy of the incident types
    const currentIncidentTypes = (incident.incident_types??[]).slice();

    // fuzzy-match on incidentType, to allow case insensitivity and
    // leading/trailing whitespace.
    if (incidentTypes.indexOf(incidentType) === -1) {
        const normalized = normalize(incidentType);
        for (const validType of incidentTypes) {
            if (normalized === normalize(validType)) {
                incidentType = validType;
                break;
            }
        }
    }
    if (incidentTypes.indexOf(incidentType) === -1) {
        // Not a valid incident type
        select.val("");
        return;
    }

    if (currentIncidentTypes.indexOf(incidentType) !== -1) {
        // Already in the list, so… move along.
        select.val("");
        return;
    }

    currentIncidentTypes.push(incidentType);

    const {err} = await sendEdits({"incident_types": currentIncidentTypes});
    if (err != null) {
        controlHasError(select);
        select.val("");
        return;
    }
    select.val("");
    controlHasSuccess(select, 1000);
}


async function detachFieldReport(sender): Promise<void> {
    // @ts-ignore JQuery
    sender = $(sender);

    const fieldReport = sender.parent().data();

    const url = (
        urlReplace(url_fieldReports) + fieldReport.number +
        "?action=detach;incident=" + incidentNumber
    );
    let {err} = await fetchJsonNoThrow(url, {
        body: JSON.stringify({}),
    });
    if (err != null) {
        const message = `Failed to detach field report ${err}`;
        console.log(message);
        await loadAllFieldReports();
        renderFieldReportData();
        setErrorMessage(message);
        return;
    }
    await loadAllFieldReports();
    renderFieldReportData();
}


async function attachFieldReport(): Promise<void> {
    if (incidentNumber == null) {
        // Incident doesn't exist yet. Create it first.
        const {err} = await sendEdits({});
        if (err != null) {
            return;
        }
    }

    // @ts-ignore JQuery
    const select = $("#attached_field_report_add");
    // @ts-ignore JQuery
    const fieldReportNumber = $(select).val();

    const url = (
        urlReplace(url_fieldReports) + fieldReportNumber +
        "?action=attach;incident=" + incidentNumber
    );
    let {err} = await fetchJsonNoThrow(url, {
        body: JSON.stringify({}),
    });
    if (err != null) {
        const message = `Failed to attach field report: ${err}`;
        console.log(message);
        await loadAllFieldReports();
        renderFieldReportData();
        setErrorMessage(message);
        controlHasError(select);
        return;
    }
    await loadAllFieldReports();
    renderFieldReportData();
    controlHasSuccess(select, 1000);
}


// The success callback for a report entry strike call.
async function onStrikeSuccess(): Promise<void> {
    await loadAndDisplayIncident();
    await loadAllFieldReports();
    renderFieldReportData();
    clearErrorMessage();
}
registerOnStrikeSuccess = onStrikeSuccess;

async function attachFile(): Promise<void> {
    if (incidentNumber == null) {
        // Incident doesn't exist yet.  Create it first.
        const {err} = await sendEdits({});
        if (err != null) {
            return;
        }
    }
    const attachFile = document.getElementById("attach_file_input") as HTMLInputElement;
    const formData = new FormData();

    for (const f of attachFile.files??[]) {
        formData.append("files", f);
    }

    const attachURL = urlReplace(url_incidentAttachments).replace("<incident_number>", (incidentNumber??"").toString());
    const {err} = await fetchJsonNoThrow(attachURL, {
        body: formData
    });
    if (err != null) {
        const message = `Failed to attach file: ${err}`;
        setErrorMessage(message);
        return;
    }
    clearErrorMessage();
    attachFile.value = "";
    await loadAndDisplayIncident();
}
