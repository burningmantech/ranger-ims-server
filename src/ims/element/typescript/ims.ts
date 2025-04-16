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
// Globals
//

export let pathIds: {
    eventID: string|null,
    incidentNumber: number|null,
    fieldReportNumber: number|null,
} = {
    eventID: null,
    incidentNumber: null,
    fieldReportNumber: null,
};

export let eventAccess: AuthInfoEventAccess|null = null;

const accessTokenKey = "access_token";

//
// HTML encoding
//

// It seems ridiculous that this isn't standard in JavaScript
// It is certainly ridiculous to involve the DOM, but on the other hand, the
// browser will implement this correctly, and any solution using .replace()
// will be buggy.  And this will be fast.  But still, this is weak.

const _domTextAreaForHaxxors: HTMLTextAreaElement = document.createElement("textarea");

// Convert text to HTML.
export function textAsHTML(text: string): string {
    _domTextAreaForHaxxors.textContent = text;
    return _domTextAreaForHaxxors.innerHTML;
}

export const integerRegExp: RegExp = /^\d+$/;

function idsFromPath(): {eventID: string|null, incidentNumber: number|null, fieldReportNumber: number|null} {
    const splits = window.location.pathname.split("/");

    // e.g. given splits of [dog, cat, emu] and s = "cat",
    // this will return "emu"
    function tokenAfter(s: string): string|null {
        const index = splits.indexOf(s);
        if (index < 0) {
            return null;
        }
        if (index >= splits.length-1) {
            return null;
        }
        if (splits[index+1] === "") {
            return null;
        }
        return splits[index+1]??null;
    }
    return {
        eventID: tokenAfter("events"),
        incidentNumber: parseInt10(tokenAfter("incidents")),
        fieldReportNumber: parseInt10(tokenAfter("field_reports")),
    };
}

//
// URL substitution
//
export function urlReplace(url: string): string {
    const event = pathIds.eventID;
    if (event) {
        url = url.replace("<event_id>", event);
    }
    return url;
}


//
// Arrays
//

// Build an array from a range.
export function range(start: number, end: number, step?: number|null): number[] {
    if (step == null) {
        step = 1;
    } else if (step === 0) {
        throw new RangeError("step = 0");
    }

    return Array(end - start)
        .join("a")
        .split("a")
        .map(function(_val: string, i: number) { return (i * step) + start;} )
        ;
}


export function compareReportEntries(a: ReportEntry, b: ReportEntry): number {
    if (a.created! < b.created!) { return -1; }
    if (a.created! > b.created!) { return  1; }

    if (a.system_entry && ! b.system_entry) { return -1; }
    if (! a.system_entry && b.system_entry) { return  1; }

    if (a.text! < b.text!) { return -1; }
    if (a.text! > b.text!) { return  1; }

    return 0;
}


//
// Request making
//

export async function fetchJsonNoThrow<T>(url: string, init: RequestInit|null): Promise<FetchRes<T>> {
    if (init == null) {
        init = {};
    }
    init.headers = new Headers(init.headers);
    init.headers.set("Accept", "application/json");
    // Pretend we're using XMLHttpRequest (rather than fetch API) so that the server
    // follows this code path:
    // https://github.com/burningmantech/ranger-ims-server/blob/0ae6fed861c7ba9d960d7e7ef3ba3258352a79c6/src/ims/application/_klein.py#L486
    init.headers.set("X-Requested-With", "XMLHttpRequest");
    const tok = getAccessToken();
    if (tok) {
        init.headers.set("Authorization", "Bearer " + tok);
    }
    if (init.body != null) {
        init.method = "POST";

        if (init.body.constructor.name === "FormData") {
            let size = 0;
            const fd = init.body as FormData;
            for(const [k,v] of fd.entries()) {
                size += k.length;
                if (v instanceof Blob) {
                    size += v.size;
                } else {
                    size += v.length;
                }
            }
            // Large file uploads are a problem, since the server locks up the Reactor thread
            // until the file is done uploading. Also, a large enough upload (multi-gig) can
            // cause the server to consume all the memory on the system and require a manual
            // restart. Yuck.
            if (size > 20 * 1024 * 1024) {
                return {resp: null, json: null, err: "Please keep data uploads small, " +
                        "ideally under 10 MB"};
            }

            // don't JSONify, don't set a Content-Type (fetch does it automatically for FormData)
        } else {
            // otherwise assume body is supposed to be json
            init.headers.set("Content-Type", "application/json");
            if (typeof init.body !== "string") {
                init.body = JSON.stringify(init.body);
            }
        }
    }
    let response: Response|null = null;
    try {
        response = await fetch(url, init);
        if (!response.ok) {
            return {resp: response, json: null, err: `${response.statusText} (${response.status})`};
        }
        let json = null;
        if (response.headers.get("content-type") === "application/json") {
            json = await response.json();
        }
        return {resp: response, json: json, err: null};
    } catch (err: any) {
        return {resp: response, json: null, err: err.message};
    }
}


//
// Generic string formatting
//

// Pad a string representing an integer to two digits.
export function padTwo(value: number|null): string {
    if (value == null) {
        return "?";
    }

    const val = value.toString();

    if (val.length === 1) {
        return "0" + val;
    }

    return val;
}


// Convert a minute (0-60) into a value used by IMS form inputs.
// That is: round to the nearest multiple of 5 and pad to two digits.
export function normalizeMinute(minute: number): string {
    minute = Math.round(minute / 5) * 5;
    while (minute > 60) {
        minute -= 60;
    }
    return padTwo(minute);
}


// Apparently some implementations of Number.parseInt don't reliably use base
// 10 by default (eg. when encountering leading zeroes).
//
// This takes something like a string, and returns an integer if it can be parsed
// as an integer, or null otherwise (unlike parseInt!).
export function parseInt10(stringInt: string|null|undefined): number|null {
    if (stringInt == null) {
        return null;
    }
    const int = Number.parseInt(stringInt, 10);
    if (isNaN(int)) {
        return null;
    }
    return int;
}


//
// Elements
//

// Create a <time> element from a date.
function timeElement(date: Date): HTMLTimeElement {
    const timeStampContainer = document.createElement("time");
    timeStampContainer.setAttribute("datetime", date.toISOString());
    timeStampContainer.textContent = fullDateTime.format(date);
    return timeStampContainer;
}


// Disable an element
function disable(elements: Iterable<Element>) {
    for (const e of elements) {
        e.setAttribute("disabled", "");
    }
}


// Enable an element
function enable(elements: Iterable<Element>) {
    for (const e of elements) {
        e.removeAttribute("disabled");
    }
}


// Disable editing for an element
export function disableEditing() {
    disable(document.querySelectorAll(".form-control"));
    // these forms don't actually exist
    // disable(document.querySelectorAll("#entries-form input,select,textarea,button"));
    // disable(document.querySelectorAll("#attach-file-form input,select,textarea,button"));
    enable(document.querySelectorAll("input[type=search]"));  // Don't disable search fields
    document.documentElement.classList.add("no-edit");
}


// Enable editing for an element
export function enableEditing() {
    enable(document.querySelectorAll(".form-control"));
    // these forms don't actually exist
    // enable(document.querySelectorAll("#entries-form input,select,textarea,button"));
    // enable(document.querySelectorAll("#attach-file-form :input,select,textarea,button"));
    document.documentElement.classList.remove("no-edit");
}

export function hide(selector: string): void {
    document.querySelectorAll(selector).forEach((el) => {
        el.classList.add("hidden");
    })
}

export function unhide(selector: string): void {
    document.querySelectorAll(selector).forEach((el) => {
        el.classList.remove("hidden");
    })
}

// Add an error indication to a control
export function controlHasError(element: HTMLElement) {
    element.classList.add("is-invalid");
}


// Add a success indication to a control
export function controlHasSuccess(element: HTMLElement, clearTimeout: number) {
    element.classList.add("is-valid");
    if (clearTimeout != null) {
        setTimeout(()=>{
            controlClear(element);
        }, clearTimeout);
    }
}


// Clear error/success indication from a control
function controlClear(element: HTMLElement) {
    element.classList.remove("is-invalid");
    element.classList.remove("is-valid");
}


//
// Initialize the page. This should be called by each page after loading the DOM.
//
export async function commonPageInit(): Promise<PageInitResult> {
    detectTouchDevice();
    let authInfo: AuthInfo|null = null;
    pathIds = idsFromPath();
    {
        const url = url_auth + (pathIds.eventID ? `?event_id=${pathIds.eventID}` : "");
        const {json, resp, err} = await fetchJsonNoThrow<AuthInfo>(url, null);
        if (err != null || json == null) {
            console.log(`Failed to fetch auth info: ${err}, ${resp?.status}`);
            setErrorMessage(`Failed to fetch auth info: ${err}, ${resp?.status}`);
            return {
                authInfo: {authenticated: false},
                eventDatas: Promise.resolve(null),
            };
        }
        authInfo = json;
    }
    let eds: Promise<EventData[]|null> = Promise.resolve(null);
    if (authInfo.authenticated) {
        if (authInfo.event_access?.[pathIds.eventID!] != null) {
            eventAccess = authInfo.event_access?.[pathIds.eventID!]!;
        }
        eds = fetchJsonNoThrow<EventData[]>(url_events, null).then(
            result => {
                if (result.err != null || result.json == null) {
                    console.log(`Failed to fetch events: ${result.err}`);
                    return null;
                }
                renderNavEvents(result.json);
                return result.json;
            }
        );
    }
    renderCommonPageItems(authInfo);
    return {authInfo: authInfo, eventDatas: eds};
}

export function redirectToLogin(): void {
    console.log("redirecting to login page")
    window.location.replace(`${url_login}?o=${window.location.pathname}`);
}

function renderCommonPageItems(authInfo: AuthInfo): void {
    if (authInfo.authenticated) {
        unhide(".if-logged-in");
        hide(".if-not-logged-in");
        document.querySelectorAll(".logged-in-user").forEach(e => {
            e.textContent = authInfo.user;
        });
        if (authInfo.admin) {
            unhide(".if-admin");
        }
    }
    if (!authInfo.authenticated) {
        hide(".if-logged-in");
        unhide(".if-not-logged-in");
        hide(".if-admin");
    }

    // Set the active event in the navbar, show "Incidents" and "Field Report" buttons
    const event = pathIds.eventID;
    if (event != null) {
        const eventLabel = document.getElementById("nav-event-id")!;
        eventLabel.textContent = event;
        eventLabel.classList.add("active-event");

        const activeEventIncidents = document.getElementById("active-event-incidents") as HTMLAnchorElement|null;
        if (activeEventIncidents != null) {
            activeEventIncidents.href = urlReplace(url_viewIncidents);
            activeEventIncidents.classList.remove("hidden");

            if (window.location.pathname.startsWith(urlReplace(url_viewIncidents))) {
                activeEventIncidents.classList.add("active");
            }
        }

        const activeEventFRs = document.getElementById("active-event-field-reports") as HTMLAnchorElement|null;
        if (activeEventFRs != null) {
            activeEventFRs.href = urlReplace(url_viewFieldReports);
            activeEventFRs.classList.remove("hidden");

            if (window.location.pathname.startsWith(urlReplace(url_viewFieldReports))) {
                activeEventFRs.classList.add("active");
            }
        }
    }
}

function renderNavEvents(eds: EventData[]): void {
    const eventIds: string[] = eds.map((ed) => ed.id);
    eventIds.sort((a, b) => b.localeCompare(a));
    const navEvents = document.getElementById("nav-events") as HTMLUListElement;
    for (const id of eventIds) {
        const anchor = document.createElement("a");
        anchor.textContent = id;
        anchor.classList.add("dropdown-item");
        anchor.href = url_viewIncidents.replace("<event_id>", id);
        const li = document.createElement("li");
        li.append(anchor);
        navEvents.append(li);
    }
}


//
// Touch device detection
//

// Add .touch or .no-touch class to top-level element if the browser is or is
// not on a touch device, respectively.
export function detectTouchDevice(): void {
    if ("ontouchstart" in document.documentElement) {
        document.documentElement.classList.add("touch");
    } else {
        document.documentElement.classList.add("no-touch");
    }
}


//
// Controls
//

// Select an option element with a given value from a given select element.
export function selectOptionWithValue(select: HTMLSelectElement, value: string|null) {
    for (const opt of select.options) {
        opt.selected = (opt.value === value);
    }
}


//
// Incident data
//


// Look up a state's name given its ID.
function stateNameFromID(stateID: string): string {
    switch (stateID) {
        case "new"       : return "New";
        case "on_hold"   : return "On Hold";
        case "dispatched": return "Dispatched";
        case "on_scene"  : return "On Scene";
        case "closed"    : return "Closed";
        default:
            console.warn("Unknown incident state ID: " + stateID);
            return "Unknown";
    }
}


// Look up a state's sort key given its ID.
function stateSortKeyFromID(stateID: string): number|undefined {
    switch (stateID) {
        case "new"       : return 1;
        case "on_hold"   : return 2;
        case "dispatched": return 3;
        case "on_scene"  : return 4;
        case "closed"    : return 5;
        default:
            console.warn("Unknown incident state ID: " + stateID);
            return undefined;
    }
}

export let concentricStreetNameByID: Streets|undefined = undefined;

export async function loadStreets(eventID: string|null): Promise<{err:string|null}> {
    const {json, err} = await fetchJsonNoThrow<EventsStreets>(url_streets + "?event_id=" + eventID, null);
    if (err != null) {
        const message = `Failed to load streets: ${err}`;
        console.error(message);
        window.alert(message);
        return {err: message};
    }
    concentricStreetNameByID = json![eventID!];
    return {err: null};
}

// Look up a concentric street's name given its ID.
function concentricStreetFromID(streetID: string|null): string {
    if (streetID == null || typeof concentricStreetNameByID === "undefined") {
        return "";
    }

    const name: string|undefined = concentricStreetNameByID[streetID];
    if (name == null) {
        console.warn("Unknown street ID: " + streetID);
        return "";
    }
    return name;
}


// Return the state ID for a given incident.
export function stateForIncident(incident: Incident): string {
    // Data from 2014+ should have incident.state set.
    if (incident.state !== undefined) {
        return incident.state!;
    }

    console.warn("Unknown state for incident: " + incident);
    return "Unknown";
}


// Return a summary for a given incident.
export function summarizeIncidentOrFR(ifr: Incident|FieldReport): string {
    if (ifr.summary) {
        return ifr.summary;
    }

    // Get the first line of the first report entry.
    for (const reportEntry of ifr.report_entries??[]) {
        if (reportEntry.system_entry) {
            // Don't use a system-generated entry in the summary
            continue;
        }

        const lines = reportEntry.text!.split("\n");
        for (const line of lines) {
            if (line) {
                return line;
            }
        }
    }
    return "";
}


// Get author for incident
function incidentAuthor(incident: Incident): string {
    for (const entry of incident.report_entries??[]) {
        if (entry.author) {
            return entry.author;
        }
    }

    return "(none)";
}


// Get author for field report
function fieldReportAuthor(report: FieldReport): string {
    return incidentAuthor(report);
}


// Render incident as a string
export function incidentAsString(incident: Incident): string {
    if (incident.number == null) {
        return "New Incident";
    }
    return `#${incident.number}: ${summarizeIncidentOrFR(incident)} (${incident.event})`;
}


// Render field report as a string
export function fieldReportAsString(report: FieldReport): string {
    if (report.number == null) {
        return "New Field Report";
    }
    return `FR #${report.number} (${fieldReportAuthor(report)}): ` +
        `${summarizeIncidentOrFR(report)} (${report.event})`;
}

// Return all user-entered report text for a given incident as a single string.
export function reportTextFromIncident(incidentOrFR: Incident|FieldReport, eventFieldReports?: FieldReportsByNumber): string {
    const texts: string[] = [];

    if (incidentOrFR.summary != null) {
        texts.push(incidentOrFR.summary);
    }

    for (const reportEntry of incidentOrFR.report_entries??[]) {

        // Skip system entries
        if (reportEntry.system_entry) {
            continue;
        }

        const text = reportEntry.text;

        if (text != null) {
            texts.push(text);
        }
    }

    // Incidents page loads all field reports for the event
    if (eventFieldReports != null && "field_reports" in incidentOrFR) {
        for (const reportNumber of incidentOrFR.field_reports??[]) {
            const report: FieldReport = eventFieldReports[reportNumber]!;
            const reportText = reportTextFromIncident(report);

            texts.push(reportText);
        }
    }

    return texts.join(" ");
}


// Return a short description for a given location.
function shortDescribeLocation(location: EventLocation): string {
    const locationBits: string[] = [];

    if (location.name != null) {
        locationBits.push(location.name);
    }

    switch (location.type) {
        case undefined:
            // Fall through to "text" case
        case "text":
            if (location.description != null) {
                locationBits.push(" ");
                locationBits.push(location.description);
            }
            break;
        case "garett":
            if (location.radial_hour || location.radial_minute || location.concentric) {
                locationBits.push(" (");
                locationBits.push(padTwo(location.radial_hour!));
                locationBits.push(":");
                locationBits.push(padTwo(location.radial_minute!));
                locationBits.push("@");
                locationBits.push(concentricStreetFromID(location.concentric!));
                locationBits.push(")");
            }
            break;
        default:
            locationBits.push(
                "Unknown location type:" + location.type
            );
            break;
    }

    return locationBits.join("");
}


//
// DataTables rendering
//

export function renderSafeSorted(strings: string[]): string {
    const safe = strings.map(s => textAsHTML(s));
    const copy = safe.toSorted((a, b) => a.localeCompare(b));
    return copy.join(", ");
}

export function renderIncidentNumber(incidentNumber: number|null, type: string, _incident: any): number|null|undefined {
    switch (type) {
        case "display":
            return incidentNumber;
        case "filter":
            return incidentNumber;
        case "type":
        case "sort":
            return incidentNumber;
    }
    return undefined;
}

// e.g. "Wed, 8/28"
export const shortDate: Intl.DateTimeFormat = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "numeric",
    day: "2-digit",
    // timeZone not specified; will use user's timezone
});

// e.g. "19:21"
const shortTime: Intl.DateTimeFormat = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    hour12: false,
    minute: "numeric",
    // timeZone not specified; will use user's timezone
});

// e.g. "19:21"
export const shortTimeSec: Intl.DateTimeFormat = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    hour12: false,
    minute: "numeric",
    second: "numeric",
    // timeZone not specified; will use user's timezone
});

// e.g. "Thu, Aug 29, 2024, 19:11:04 EDT"
export const fullDateTime: Intl.DateTimeFormat = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    hour12: false,
    minute: "numeric",
    second: "numeric",
    timeZoneName: "short",
    // timeZone not specified; will use user's timezone
});

export function renderDate(date: string, type: string, _incident: any): string|number|undefined {
    const d = Date.parse(date);
    switch (type) {
        case "display":
            return shortDate.format(d) + "<wbr />@" + shortTime.format(d);
        case "filter":
            return shortDate.format(d) + " " + shortTime.format(d);
        case "type":
        case "sort":
            return d;
    }
    return undefined;
}

export function renderState(state: string, type: string, incident: Incident): string|number|undefined {
    if (state == null) {
        state = stateForIncident(incident);
    }

    switch (type) {
        case "display":
            return textAsHTML(stateNameFromID(state));
        case "filter":
            return stateNameFromID(state);
        case "type":
            return state;
        case "sort":
            return stateSortKeyFromID(state);
    }
    return undefined;
}

export function renderLocation(data: EventLocation|null, type: string, _incident: Incident): string|undefined {
    if (data == null) {
        return undefined;
    }
    switch (type) {
        case "display":
            return textAsHTML(shortDescribeLocation(data)??"");
        case "filter":
        case "sort":
            return shortDescribeLocation(data);
        case "type":
            return "";
    }
    return undefined;
}

//
// Populate report entry text
//

function reportEntryElement(entry: ReportEntry): HTMLDivElement {
    // Build a container for the entry

    const entryContainer: HTMLDivElement = document.createElement("div");
    entryContainer.classList.add("report_entry");

    const strikable: boolean = !entry.system_entry;

    if (entry.system_entry) {
        entryContainer.classList.add("report_entry_system");
    } else if (entry.stricken) {
        entryContainer.classList.add("report_entry_stricken");
    } else {
        entryContainer.classList.add("report_entry_user");
    }

    if (entry.merged) {
        entryContainer.classList.add("report_entry_merged");
    }

    // Add the timestamp and author, with a Strike/Unstrike button

    const metaDataContainer: HTMLParagraphElement = document.createElement("p");
    metaDataContainer.classList.add("report_entry_metadata");

    if (strikable) {
        const strikeContainer: HTMLButtonElement = document.createElement("button");
        const entryId = parseInt10(entry.id)!;
        const entryStricken = entry.stricken!;
        if (pathIds.incidentNumber != null) {
            // we're on the incident page
            if (entry.merged) {
                const entryMerged = entry.merged;
                // this is an entry from a field report, as shown on the incident page
                strikeContainer.onclick = (_e: MouseEvent): any => {
                    setStrikeFieldReportEntry(entryMerged, entryId, !entryStricken);
                }
            } else {
                const incidentNum = pathIds.incidentNumber;
                // this is an incident entry on the incident page
                strikeContainer.onclick = (_e: MouseEvent): any => {
                    setStrikeIncidentEntry(incidentNum, entryId, !entryStricken);
                }
            }
        } else if (pathIds.fieldReportNumber != null) {
            // we're on the field report page
            const fieldReportNum = pathIds.fieldReportNumber;
            strikeContainer.onclick =  (_e: MouseEvent): any => {
                setStrikeFieldReportEntry(fieldReportNum, entryId, !entryStricken);
            }
        }
        strikeContainer.classList.add("badge", "btn", "btn-danger", "remove-badge", "float-end");
        strikeContainer.textContent = entry.stricken ? "Unstrike" : "Strike";

        metaDataContainer.append(strikeContainer);
    }

    const timeStampContainer = timeElement(new Date(entry.created!));
    timeStampContainer.classList.add("report_entry_timestamp");

    metaDataContainer.append(timeStampContainer, ", ");

    const authorContainer: HTMLSpanElement = document.createElement("span");
    authorContainer.textContent = entry.author??"(unknown)";
    authorContainer.classList.add("report_entry_author");

    metaDataContainer.append(authorContainer);

    if (entry.merged) {
        metaDataContainer.append(" ");

        const link: HTMLAnchorElement = document.createElement("a");
        link.textContent = "field report #" + entry.merged;
        link.href = urlReplace(url_viewFieldReports) + entry.merged;

        metaDataContainer.append("(via ", link, ")");
        metaDataContainer.classList.add("report_entry_source");
    }

    metaDataContainer.append(":");

    entryContainer.append(metaDataContainer);

    // Add report text

    const lines: string[] = entry.text!.split("\n");
    for (const line of lines) {
        const textContainer: HTMLParagraphElement = document.createElement("p");
        textContainer.classList.add("report_entry_text");
        textContainer.textContent = line;

        entryContainer.append(textContainer);
    }
    if (entry.has_attachment && pathIds.incidentNumber != null) {
        const url = urlReplace(url_incidentAttachmentNumber)
            .replace("<incident_number>", pathIds.incidentNumber.toString())
            .replace("<attachment_number>", entry.id!.toString());

        const attachmentLink: HTMLAnchorElement = document.createElement("a");
        attachmentLink.href = url;
        attachmentLink.textContent = "Attached file";

        entryContainer.append(attachmentLink);

    }

    // Add a horizontal line after each entry

    const hr: HTMLHRElement = document.createElement("hr");
    hr.classList.add("m-1");
    entryContainer.append(hr);

    return entryContainer;
}

export function drawReportEntries(entries: ReportEntry[]): void {
    const container: HTMLElement = document.getElementById("report_entries")!;
    container.replaceChildren();

    for (const entry of entries) {
        container.append(reportEntryElement(entry));
    }
}

export function reportEntryEdited(): void {
    const text = (document.getElementById("report_entry_add")! as HTMLTextAreaElement).value.trim();
    const submitButton = document.getElementById("report_entry_submit")!;

    submitButton.classList.remove("btn-default");
    submitButton.classList.remove("btn-warning");
    submitButton.classList.remove("btn-danger");

    if (!text) {
        submitButton.classList.add("disabled");
        submitButton.classList.add("btn-default");
    } else {
        submitButton.classList.remove("disabled");
        submitButton.classList.add("btn-warning");
    }
}

// The error callback for a report entry strike call.
// This function is designed to work from either the incident
// or the field report page.
function onStrikeError(err: string): void {
    const message = `Failed to set report entry strike status: ${err}`;
    console.log(message);
    setErrorMessage(message);
}

// This is the function to call when a report entry is successfully stricken.
// We need to be able to call either the incident.ts version or the field_report.ts
// version, depending on the current page in scope. The ims.ts TypeScript file should
// not depend on those files (lest there be a circular dependency), so we let those
// files register their functions here instead.
let strikeSuccessFunc: (() => Promise<void>)|null = null;
export function setOnStrikeSuccess(func: (() => Promise<void>)): void {
    strikeSuccessFunc = func;
}

async function setStrikeIncidentEntry(incidentNumber: number, reportEntryId: number, strike: boolean): Promise<void> {
    const url = urlReplace(url_incident_reportEntry)
        .replace("<incident_number>", incidentNumber.toString())
        .replace("<report_entry_id>", reportEntryId.toString());
    const {err} = await fetchJsonNoThrow(url, {
        body: JSON.stringify({"stricken": strike}),
    });
    if (err != null) {
        onStrikeError(err);
    } else {
        await strikeSuccessFunc!();
    }
}

async function setStrikeFieldReportEntry(fieldReportNumber: number, reportEntryId: number, strike: boolean): Promise<void> {
    const url = urlReplace(url_fieldReport_reportEntry)
        .replace("<field_report_number>", fieldReportNumber.toString())
        .replace("<report_entry_id>", reportEntryId.toString());
    const {err} = await fetchJsonNoThrow(url, {
        body: JSON.stringify({"stricken": strike}),
    });
    if (err != null) {
        onStrikeError(err);
    } else {
        await strikeSuccessFunc!();
    }
}

// This is the function to call when edits are being sent to the server.
// We need to be able to call either the incident.ts version or the field_report.ts
// version, depending on the current page in scope. The ims.ts TypeScript file should
// not depend on those files (lest there be a circular dependency), so we let those
// files register their functions here instead.
let sendEditsFunc: ((edits: any)=>Promise<{err:string|null}>)|null = null;
export function setSendEdits(func: ((edits: any)=>Promise<{err:string|null}>)): void {
    sendEditsFunc = func;
}

export async function submitReportEntry(): Promise<void> {
    const text = (document.getElementById("report_entry_add") as HTMLTextAreaElement).value.trim();

    if (!text) {
        return;
    }

    console.log("New report entry:\n" + text);

    // Disable the submit button to prevent repeat submissions
    document.getElementById("report_entry_submit")!.classList.add("disabled");
    // send a dummy ID to appease the JSON parser in the server
    const {err} = await sendEditsFunc!({"report_entries": [{"text": text, "id": -1}]});
    if (err != null) {
        const submitButton = document.getElementById("report_entry_submit")!;
        submitButton.classList.remove("disabled");
        submitButton.classList.remove("btn-default");
        submitButton.classList.remove("btn-warning");
        submitButton.classList.add("btn-danger");
        controlHasError(document.getElementById("report_entry_add")!);
        return;
    }
    const textArea = document.getElementById("report_entry_add")! as HTMLTextAreaElement;
    // Clear the report entry
    textArea.value = "";
    controlHasSuccess(textArea, 1000);
    // Reset the submit button and its "disabled" status
    reportEntryEdited();
}

//
// Generated history display
//

export function toggleShowHistory(): void {
    if ((document.getElementById("history_checkbox") as HTMLInputElement).checked) {
        document.getElementById("report_entries")!.classList.remove("hide-history");
    } else {
        document.getElementById("report_entries")!.classList.add("hide-history");
    }
}

export async function editFromElement(element: HTMLInputElement|HTMLSelectElement, jsonKey: string, transform?: (v: string)=>string|null): Promise<void> {
    let value: string|null = element.value;

    if (transform != null) {
        value = transform(value);
    }

    // Build a JSON object representing the requested edits

    const edits: EditMap = {};

    const keyPath: string[] = jsonKey.split(".");
    const lastKey: string = keyPath.pop()!;

    let current: EditMap = edits;
    for (const path of keyPath) {
        const next: EditMap = {};
        current[path] = next;
        current = next;
    }
    current[lastKey] = value??"null";

    // Location must include type

    if (edits["location"] != null && typeof edits["location"] !== "string") {
        edits["location"]["type"] = "garett";  // UI only supports one type
    }

    // Send request to server

    const {err} = await sendEditsFunc!(edits);
    if (err != null) {
        controlHasError(element);
    } else {
        controlHasSuccess(element, 1000);
    }
}

//
// BroadcastChannel
//

export function newIncidentChannel(): BroadcastChannelTyped<IncidentBroadcast> {
    const incidentChannelName = "incident_update";
    return new BroadcastChannel(incidentChannelName);
}
export function newFieldReportChannel(): BroadcastChannelTyped<FieldReportBroadcast> {
    const fieldReportChannelName= "field_report_update";
    return new BroadcastChannel(fieldReportChannelName);
}


//
// EventSource
//

const reattemptMinTimeMillis = 10000;
const lastSseIDKey = "last_sse_id";

// Call this from each browsing context, so that it can queue up to become a leader
// to manage the EventSource.
export function requestEventSourceLock(): void  {
    // The "navigator.locks" API is only available over secure browsing contexts.
    // Secure contexts include HTTPS as well as non-HTTPS via localhost, so this is
    // really only when you try to connect directly to another host without TLS.
    // https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts
    if (!window.isSecureContext) {
        setErrorMessage("You're connected through an insecure browsing context. " +
            "Background SSE updates will not work!");
        return;
    }

    function tryAcquireLock(): Promise<void> {
        const {promise, resolve} = Promise.withResolvers<undefined>();
        subscribeToUpdates(resolve);
        return promise;
    }

    // Fire-and-forget this Promise to infinitely attempt to reconnect to the EventSource.
    // This addresses the following issue for when IMS lives on AWS, and ensures the
    // browsing context will always try to reestablish the EventSource connection.
    // https://github.com/burningmantech/ranger-ims-server/issues/1364
    new Promise<unknown>(async function(): Promise<void> {
        while (true) {
            const reattempt = new Promise(res => setTimeout(res, reattemptMinTimeMillis));
            // Acquire the lock, set up the EventSource, and start
            // broadcasting events to other browsing contexts.
            await navigator.locks.request("ims_eventsource_lock", tryAcquireLock);
            await reattempt;
        }
    });
    return;
}

// This starts the EventSource call and configures event listeners to propagate
// updates to BroadcastChannels. The idea is that only one browsing context should
// have an EventSource connection at any given time.
//
// The "closed" param is a callback to notify the caller that the EventSource has
// been closed.
function subscribeToUpdates(closed: (_value?: undefined)=>void): void {
    const eventSource = new EventSource(
        url_eventSource, { withCredentials: true }
    );

    eventSource.addEventListener("open", function(): void {
        console.log("Event listener opened");
    });

    eventSource.addEventListener("error", function(): void {
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log("Event listener closed");
            eventSource.close();
            closed();
        } else {
            // EventSource automatically reconnects in this case.
            console.log("Event listener error");
        }
    });

    eventSource.addEventListener("InitialEvent", function(e: MessageEvent<string>) {
        const previousId = localStorage.getItem(lastSseIDKey);
        if (e.lastEventId === previousId) {
            return;
        }
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        newIncidentChannel().postMessage({update_all: true});
        newFieldReportChannel().postMessage({update_all: true});
    });

    eventSource.addEventListener("Incident", function(e: MessageEvent<string>) {
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        newIncidentChannel().postMessage(JSON.parse(e.data) as IncidentBroadcast);
    });

    eventSource.addEventListener("FieldReport", function(e: MessageEvent<string>) {
        localStorage.setItem(lastSseIDKey, e.lastEventId);
        newFieldReportChannel().postMessage(JSON.parse(e.data) as FieldReportBroadcast);
    });
}

// Set the user-visible error information on the page to the provided string.
export function setErrorMessage(msg: string): void {
    msg = `Error: ${msg}`;
    const errText: HTMLElement|null = document.getElementById("error_text");
    if (errText) {
        errText.textContent = msg;
    }
    const errInfo: HTMLElement|null = document.getElementById("error_info");
    if (errInfo) {
        errInfo.classList.remove("hidden");
        errInfo.scrollIntoView();
    }
}

export function clearErrorMessage(): void {
    const errText: HTMLElement|null = document.getElementById("error_text");
    if (errText) {
        errText.textContent = "";
    }
    const errInfo: HTMLElement|null = document.getElementById("error_info");
    if (errInfo) {
        errInfo.classList.add("hidden");
    }
}

export function bsModal(el: HTMLElement) {
    return new bootstrap.Modal(el);
}

export function windowFragmentParams() {
    const fragment = window.location.hash.startsWith("#")
        ? window.location.hash.substring(1)
        : window.location.hash;
    return new URLSearchParams(fragment);
}

function getAccessToken(): string|null {
    return localStorage.getItem(accessTokenKey);
}

export function setAccessToken(token: string): void {
    localStorage.setItem(accessTokenKey, token);
}

export function clearAccessToken(): void {
    localStorage.removeItem(accessTokenKey);
}


//
// Load incident types
//

export async function loadIncidentTypes(): Promise<{types: string[], err: string|null}> {
    const {json, err} = await fetchJsonNoThrow<string[]>(url_incidentTypes, null);
    if (err != null) {
        const message = `Failed to load incident types: ${err}`;
        console.error(message);
        setErrorMessage(message);
        return {
            types: [],
            err: message,
        };
    }
    const _incidentTypes: string[] = [];
    for (const record of json!) {
        _incidentTypes.push(record);
    }
    _incidentTypes.sort();
    return {
        types: _incidentTypes,
        err: null,
    };
}

// Remove the old LocalStorage caches that IMS no longer uses, so that
// they can't act against the ~5 MB per-domain limit of HTML5 LocalStorage.
// This can probably be removed after the 2025 event, when all the relevant
// computers have their caches purged.
function cleanupOldCaches(): void {
    localStorage.removeItem("lscache-ims.incident_types");
    localStorage.removeItem("lscache-ims.incident_types-cacheexpiration");
    localStorage.removeItem("lscache-ims.personnel");
    localStorage.removeItem("lscache-ims.personnel-cacheexpiration");
    localStorage.removeItem("ims.incident_types");
    localStorage.removeItem("ims.incident_types.deadline");
    localStorage.removeItem("ims.personnel");
    localStorage.removeItem("ims.personnel.deadline");
}
cleanupOldCaches();


//
// TypeScript declarations. These won't appear in the final JavaScript.
//

declare let url_auth: string;
declare let url_events: string;
declare let url_eventSource: string;
declare let url_fieldReport_reportEntry: string;
declare let url_incidentAttachmentNumber: string;
declare let url_incidentTypes: string;
declare let url_incident_reportEntry: string;
declare let url_login: string;
declare let url_streets: string;
declare let url_viewEvent: string;
declare let url_viewFieldReports: string;
declare let url_viewIncidents: string;

export type PageInitResult = {
    authInfo: AuthInfo;
    eventDatas: Promise<EventData[]|null>;
}

export type Streets = Record<string, string>;
export interface EventsStreets {
    // key is event name
    [index: string]: Streets,
}

interface EventLocation {
    name?: string|null;
    radial_hour?: number|null;
    radial_minute?: number|null;
    concentric?: string|null;
    description?: string|null;
    type?: string|null;
}

export type Incident = {
    number?: number|null;
    event?: string|null;
    state?: string|null;
    priority?: number|null;
    summary?: string|null;
    created?: string|null;
    last_modified?: string|null;
    ranger_handles?: string[]|null;
    incident_types?: string[]|null;
    location?: EventLocation|null;
    report_entries?: ReportEntry[]|null;
    field_reports?: number[]|null;
}

export type FieldReport = {
    event?: string|null;
    number?: number|null;
    created?: string|null;
    summary?: string|null;
    incident?: number|null;
    report_entries?: ReportEntry[]|null;
}

export type FieldReportsByNumber = Record<number, FieldReport>;

export type EventData = {
    id: string,
    name: string,
}

export interface ReportEntry {
    id?: string|null;
    created?: string|null;
    author?: string|null;
    merged?: number|null,
    text?: string|null;
    system_entry?: boolean|null;
    stricken?: boolean|null;
    has_attachment?: boolean|null;
}

export type UnauthenticatedAuthInfo = {
    authenticated: false,
}

export type AuthenticatedAuthInfo = {
    authenticated: true,
    user: string,
    admin: boolean,
    event_access?: Record<string, AuthInfoEventAccess>,
}

export type AuthInfo = UnauthenticatedAuthInfo | AuthenticatedAuthInfo;

export type AuthInfoEventAccess = {
    readIncidents: boolean,
    writeIncidents: boolean,
    writeFieldReports: boolean,
    attachFiles: boolean,
}

// This is a simple wrapper to help with typing on BroadcastChannels. It's
// incomplete, e.g. no "addEventListener" implementation, so it may need
// expansion in the future.
interface BroadcastChannelTyped<T> extends EventTarget {
    postMessage(message: T): void;
    onmessage: ((this: BroadcastChannel, ev: MessageEvent<T>) => any) | null;
}

export type IncidentBroadcast = {
    // fields from SSE
    event_id?: string|null;
    incident_number?: number|null;
    // additional fields for use in BroadcastChannel
    update_all?: boolean;
}

export type FieldReportBroadcast = {
    // fields from SSE
    event_id?: string|null;
    field_report_number?: number|null;
    // additional fields for use in BroadcastChannel
    update_all?: boolean
}

interface EditMap {
    [index: string]: EditMap|string;
}

export type FetchRes<T> = {
    resp: Response|null;
    json: T|null;
    err: string|null;
}

interface DTAjax {
    reload(): void;
}

type DTData = Record<number, object>;

export interface DataTablesTable {
    row: any;
    rows: any;
    data(): DTData;
    search: any;
    page: any;
    draw(): unknown;
    ajax: DTAjax;
    processing(b: boolean): unknown;
}

// This is a minimal declaration of pieces of Bootstrap code on which we depend.
// See this repo for the full declaration:
// https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/bootstrap
declare namespace bootstrap {
    class Modal {
        constructor(element: string | Element, options?: any);
        toggle(relatedTarget?: HTMLElement): void;
    }
}
