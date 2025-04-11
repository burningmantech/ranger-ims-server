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

declare let url_incidentTypes: string;

declare global {
    interface Window {
        createIncidentType: (el: HTMLInputElement)=>Promise<void>;
        deleteIncidentType: (el: HTMLElement)=>void;
        showIncidentType: (el: HTMLElement)=>Promise<void>;
        hideIncidentType: (el: HTMLElement)=>Promise<void>;
    }
}

//
// Initialize UI
//

initAdminTypesPage();

async function initAdminTypesPage(): Promise<void> {
    const initResult = await ims.commonPageInit();
    if (!initResult.authInfo.authenticated) {
        ims.redirectToLogin();
        return;
    }

    window.createIncidentType = createIncidentType;
    window.deleteIncidentType = deleteIncidentType;
    window.showIncidentType = showIncidentType;
    window.hideIncidentType = hideIncidentType;

    await loadAndDrawIncidentTypes();

    ims.enableEditing();
}


async function loadAndDrawIncidentTypes(): Promise<void> {
    await loadAllIncidentTypes();
    drawAllIncidentTypes();
}


let adminIncidentTypes: string[]|null = null;
let incidentTypesVisible: string[]|null = null;

async function loadAllIncidentTypes(): Promise<{err:string|null}> {
    let errOne: string|null, errTwo: string|null;
    [{json: incidentTypesVisible, err: errOne}, {json: adminIncidentTypes, err: errTwo}] =
        await Promise.all([
            ims.fetchJsonNoThrow<string[]>(url_incidentTypes, {
                headers: {"Cache-Control": "no-cache"},
            }),
            ims.fetchJsonNoThrow<string[]>(url_incidentTypes + "?hidden=true", {
                headers: {"Cache-Control": "no-cache"},
            }),
        ]);
    if (errOne != null || errTwo != null) {
        const message = "Failed to load incident types:\n" + errOne + "," + errTwo;
        console.error(message);
        window.alert(message);
        return {err: message};
    }
    return {err: null};
}


let _incidentTypesTemplate: Element|null = null;
let _entryTemplate: Element|null = null;

function drawAllIncidentTypes(): void {
    const container: HTMLElement = document.getElementById("incident_types_container")!;

    if (_incidentTypesTemplate == null) {
        _incidentTypesTemplate = container.getElementsByClassName("incident_types")[0]!;

        _entryTemplate = _incidentTypesTemplate!
            .getElementsByClassName("list-group")[0]!
            .getElementsByClassName("list-group-item")[0]!;
    }

    updateIncidentTypes();
}


function updateIncidentTypes(): void {
    const incidentTypesElement: HTMLElement = document.getElementById("incident_types")!;

    const entryContainer = incidentTypesElement.getElementsByClassName("list-group")[0]!;

    entryContainer.replaceChildren();

    for (const incidentType of adminIncidentTypes??[]) {
        const entryItem = _entryTemplate!.cloneNode(true) as HTMLElement;

        if (incidentTypesVisible!.indexOf(incidentType) === -1) {
            entryItem.classList.add("item-hidden");
        } else {
            entryItem.classList.add("item-visible");
        }

        const safeIncidentType = ims.textAsHTML(incidentType);
        entryItem.append(safeIncidentType);
        entryItem.setAttribute("value", safeIncidentType);

        entryContainer.append(entryItem);
    }
}


async function createIncidentType(sender: HTMLInputElement): Promise<void> {
    const {err} = await sendIncidentTypes({"add": [sender.value]});
    if (err == null) {
        sender.value = "";
    }
    await loadAndDrawIncidentTypes();
}


function deleteIncidentType(_sender: HTMLElement) {
    alert("Remove unimplemented");
}


async function showIncidentType(sender: HTMLElement): Promise<void> {
    await sendIncidentTypes({"show": [
        sender.parentElement!.getAttribute("value")!]});
    await loadAndDrawIncidentTypes();
}


async function hideIncidentType(sender: HTMLElement): Promise<void> {
    await sendIncidentTypes({"hide": [
        sender.parentElement!.getAttribute("value")!]});
    await loadAndDrawIncidentTypes();
}

interface AdminTypesEdits {
    add?: string[];
    show?: string[];
    hide?: string[];
}

async function sendIncidentTypes(edits: AdminTypesEdits): Promise<{err:string|null}> {
    const {err} = await ims.fetchJsonNoThrow(url_incidentTypes, {
        body: JSON.stringify(edits),
    });
    if (err == null) {
        return {err: null};
    }
    const message = `Failed to edit incident types:\n${JSON.stringify(err)}`;
    console.log(message);
    window.alert(message);
    return {err: err};
}
