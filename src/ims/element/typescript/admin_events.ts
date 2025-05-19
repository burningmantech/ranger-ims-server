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

import * as ims from "./ims.ts";

declare let url_acl: string;
declare let url_events: string;

declare global {
    interface Window {
        setValidity: (el: HTMLSelectElement)=>Promise<void>;
        addAccess: (el: HTMLInputElement)=>Promise<void>;
        addEvent: (el: HTMLInputElement)=>Promise<void>;
        removeAccess: (el: HTMLButtonElement)=>Promise<void>;
    }
}

//
// Initialize UI
//

initAdminEventsPage();

async function initAdminEventsPage(): Promise<void> {
    const initResult = await ims.commonPageInit();
    if (!initResult.authInfo.authenticated) {
        ims.redirectToLogin();
        return;
    }

    window.setValidity = setValidity;
    window.addEvent = addEvent;
    window.addAccess = addAccess;
    window.removeAccess = removeAccess;

    await loadAccessControlList();
    drawAccess();

    ims.enableEditing();
}

enum Validity {
    always = "always",
    onsite = "onsite",
}

interface Access {
    expression: string;
    validity: Validity;
}

const allAccessModes = ["readers", "writers", "reporters"] as const;
type AccessMode = typeof allAccessModes[number];
type EventAccess = Partial<Record<AccessMode, Access[]>>;
// key is event name
type EventsAccess = Record<string, EventAccess|null>;

let accessControlList: EventsAccess|null = null;

async function loadAccessControlList() : Promise<{err: string|null}> {
    // we don't actually need the response from this API, but we want to
    // invalidate the local HTTP cache in the admin's browser
    ims.fetchJsonNoThrow<ims.EventData[]>(url_events, {
        headers: {"Cache-Control": "no-cache"},
    });
    const {json, err} = await ims.fetchJsonNoThrow<EventsAccess>(url_acl, null);
    if (err != null) {
        const message = `Failed to load access control list: ${err}`;
        console.error(message);
        window.alert(message);
        return {err: message};
    }
    accessControlList = json;
    return {err: null};
}


let _accessTemplate : Element|null = null;
let _eventsEntryTemplate : Element|null = null;

function drawAccess(): void {
    const container: HTMLElement = document.getElementById("event_access_container")!;
    if (_accessTemplate == null) {
        _accessTemplate = container.getElementsByClassName("event_access")[0]!;
        _eventsEntryTemplate = _accessTemplate
            .getElementsByClassName("list-group")[0]!
            .getElementsByClassName("list-group-item")[0]!
        ;
    }

    container.replaceChildren();

    if (accessControlList == null) {
        return;
    }
    const events: string[] = Object.keys(accessControlList);
    for (const event of events) {
        for (const mode of allAccessModes) {
            const eventAccess = _accessTemplate.cloneNode(true) as HTMLElement;
            // Add an id to the element for future reference
            eventAccess.setAttribute("id", "event_access_" + event + "_" + mode);

            // Add to container
            container.append(eventAccess);

            updateEventAccess(event, mode);
        }
    }
}


function updateEventAccess(event: string, mode: AccessMode): void {
    if (accessControlList == null) {
        return;
    }
    const eventACL: EventAccess|null|undefined = accessControlList[event];
    if (eventACL == null) {
        return;
    }

    const eventAccess: HTMLElement = document.getElementById("event_access_" + event + "_" + mode)!;

    // Set displayed event name and mode
    eventAccess.getElementsByClassName("event_name")[0]!.textContent = event;
    eventAccess.getElementsByClassName("access_mode")[0]!.textContent = mode;

    const entryContainer = eventAccess.getElementsByClassName("list-group")[0]!;

    entryContainer.replaceChildren();

    for (const accessEntry of eventACL[mode]??[]) {
        const entryItem = _eventsEntryTemplate!.cloneNode(true) as HTMLElement;

        entryItem.append(accessEntry.expression);
        entryItem.setAttribute("value", accessEntry.expression);
        const validityField = entryItem.getElementsByClassName("access_validity")[0] as HTMLSelectElement;
        validityField.value = accessEntry.validity;

        entryContainer.append(entryItem);
    }
}


async function addEvent(sender: HTMLInputElement): Promise<void> {
    const event = sender.value.trim();
    const {err} = await ims.fetchJsonNoThrow(url_events, {
        body: JSON.stringify({
            "add": [event],
        }),
    });
    if (err != null) {
        const message = `Failed to add event: ${err}`;
        console.log(message);
        window.alert(message);
        await loadAccessControlList();
        drawAccess();
        ims.controlHasError(sender);
        return;
    }
    await loadAccessControlList();
    drawAccess();
    sender.value = "";  // Clear input field
}


async function addAccess(sender: HTMLInputElement): Promise<void> {
    const container: HTMLElement = sender.closest(".event_access")!;
    const event = container.getElementsByClassName("event_name")[0]!.textContent!;
    const mode = container.getElementsByClassName("access_mode")[0]!.textContent as AccessMode;
    const newExpression = sender.value.trim();

    if (newExpression === "") {
        return;
    }

    if (newExpression === "**") {
        const confirmed = confirm(
            "Double-wildcard '**' ACLs are no longer supported, so this ACL will have " +
            "no effect.\n\n" +
            "Proceed with doing something pointless?"
        );
        if (!confirmed) {
            sender.value = "";
            return;
        }
    }

    const validExpression = newExpression === "**" || newExpression === "*" ||
        newExpression.startsWith("person:") || newExpression.startsWith("position:") || newExpression.startsWith("team:");
    if (!validExpression) {
        const confirmed = confirm(
            "WARNING: '" + newExpression + "' does not look like a valid ACL " +
            "expression. Example expressions include 'person:Hubcap' for an individual, " +
            "'position:007' for a role, and 'team:Council' for a team. Wildcards are " +
            "supported as well, e.g. '*'\n\n" +
            "Proceed with firing footgun?"
        );
        if (!confirmed) {
            sender.value = "";
            return;
        }
    }

    let acl: Access[] = accessControlList![event]![mode]!.slice();

    // remove other acls for this mode for the same expression
    acl = acl.filter((v: Access): boolean => {return v.expression !== newExpression});

    const newVal: Access = {
        "expression": newExpression,
        "validity": Validity.always,
    };

    acl.push(newVal);

    const edits: EventsAccess = {};
    edits[event] = {};
    edits[event][mode] = acl;

    const {err} = await sendACL(edits);
    await loadAccessControlList();
    for (const mode of allAccessModes) {
        updateEventAccess(event, mode);
    }
    if (err != null) {
        ims.controlHasError(sender);
        return;
    }
    sender.value = "";  // Clear input field
}


async function removeAccess(sender: HTMLButtonElement): Promise<void> {
    const container: HTMLElement = sender.closest(".event_access")!;
    const event = container.getElementsByClassName("event_name")[0]!.textContent!;
    const mode = container.getElementsByClassName("access_mode")[0]!.textContent! as AccessMode;
    const expression = sender.parentElement!.getAttribute("value")!.trim();

    const acl: Access[] = accessControlList![event]![mode]!.slice();

    let foundIndex: number = -1;
    for (const [i, access] of acl.entries()) {
        if (access.expression === expression) {
            foundIndex = i;
            break;
        }
    }
    if (foundIndex < 0) {
        console.error("no such ACL: " + expression);
        return;
    }

    acl.splice(foundIndex, 1);

    const edits: EventsAccess = {};
    edits[event] = {};
    edits[event][mode] = acl;

    await sendACL(edits);
    await loadAccessControlList();
    for (const mode of allAccessModes) {
        updateEventAccess(event, mode);
    }
}

async function setValidity(sender: HTMLSelectElement): Promise<void> {
    const container: HTMLElement = sender.closest(".event_access")!;
    const event: string = container.getElementsByClassName("event_name")[0]!.textContent!;
    const mode = container.getElementsByClassName("access_mode")[0]!.textContent! as AccessMode;
    const expression = sender.parentElement!.getAttribute("value")!.trim();

    let acl: Access[] = accessControlList![event]![mode]!.slice();

    // remove other acls for this mode for the same expression
    acl = acl.filter((v: Access): boolean => {return v.expression !== expression});

    const newVal: Access = {
        "expression": expression,
        "validity": sender.value === "onsite" ? Validity.onsite : Validity.always,
    };

    acl.push(newVal);

    const edits: EventsAccess = {};
    edits[event] = {};
    edits[event][mode] = acl;

    const {err} = await sendACL(edits);
    await loadAccessControlList();
    for (const mode of allAccessModes) {
        updateEventAccess(event, mode);
    }
    if (err != null) {
        ims.controlHasError(sender);
        return;
    }
    sender.value = "";  // Clear input field
}


async function sendACL(edits: EventsAccess): Promise<{err:string|null}> {
    const {err} = await ims.fetchJsonNoThrow(url_acl, {
        body: JSON.stringify(edits),
    });
    if (err == null) {
        return {err: null};
    }
    const message = `Failed to edit ACL:\n${JSON.stringify(err)}`;
    console.log(message);
    window.alert(message);
    return {err: err};
}
