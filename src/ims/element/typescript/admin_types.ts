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

async function initAdminTypesPage(): Promise<void> {
    detectTouchDevice();
    await loadAndDrawIncidentTypes();
}


async function loadAndDrawIncidentTypes(): Promise<void> {
    await loadAllIncidentTypes();
    drawAllIncidentTypes();
}


let adminIncidentTypes: string[] = [];
let incidentTypesVisible: string[] = [];

async function loadAllIncidentTypes(): Promise<{err:string|null}> {
    let errOne: string|null, errTwo: string|null;
    [{json: incidentTypesVisible, err: errOne}, {json: adminIncidentTypes, err: errTwo}] =
        await Promise.all([
            fetchJsonNoThrow(url_incidentTypes, {
                headers: {"Cache-Control": "no-cache"},
            }),
            fetchJsonNoThrow(url_incidentTypes + "?hidden=true", {
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


let _incidentTypesTemplate: object|null = null;
let _entryTemplate: any = null;

function drawAllIncidentTypes(): void {
    // @ts-ignore JQuery
    const container = $("#incident_types_container");

    if (_incidentTypesTemplate == null) {
        _incidentTypesTemplate = container.children(".incident_types:first");

        _entryTemplate = _incidentTypesTemplate!
            // @ts-ignore JQuery
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    updateIncidentTypes();
}


function updateIncidentTypes(): void {
    // @ts-ignore JQuery
    const incidentTypesElement = $("#incident_types");

    const entryContainer = incidentTypesElement.find(".list-group:first");

    entryContainer.empty();

    for (const incidentType of adminIncidentTypes??[]) {
        const entryItem = _entryTemplate.clone();

        if (incidentTypesVisible.indexOf(incidentType) === -1) {
            entryItem.addClass("item-hidden");
        } else {
            entryItem.addClass("item-visible");
        }

        const safeIncidentType = textAsHTML(incidentType);
        entryItem.append(safeIncidentType);
        entryItem.attr("value", safeIncidentType);

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


function deleteIncidentType(sender: HTMLElement) {
    alert("Remove unimplemented");
}


async function showIncidentType(sender: HTMLElement): Promise<void> {
    await sendIncidentTypes({"show": [
        // @ts-ignore
        $(sender).parent().attr("value")]});
    await loadAndDrawIncidentTypes();
}


async function hideIncidentType(sender: HTMLElement): Promise<void> {
    await sendIncidentTypes({"hide": [
        // @ts-ignore
        $(sender).parent().attr("value")]});
    await loadAndDrawIncidentTypes();
}

interface Edits {
    add?: string[];
    show?: string[];
    hide?: string[];
}

async function sendIncidentTypes(edits: Edits): Promise<{err:string|null}> {
    const {err} = await fetchJsonNoThrow(url_incidentTypes, {
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
