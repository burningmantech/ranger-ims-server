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

async function initPage() {
    detectTouchDevice();
    await loadAndDrawIncidentTypes();
}


async function loadAndDrawIncidentTypes() {
    await loadIncidentTypes();
    drawIncidentTypes();
}


let incidentTypes = null;
let incidentTypesVisible = null;

async function loadIncidentTypes() {
    let errOne, errTwo;
    [{json: incidentTypesVisible, err: errOne}, {json: incidentTypes, err: errTwo}] =
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
        return {err: message}
    }
    return {err: null};
}


let _incidentTypesTemplate = null;
let _entryTemplate = null;

function drawIncidentTypes() {
    const container = $("#incident_types_container");

    if (_incidentTypesTemplate == null) {
        _incidentTypesTemplate = container.children(".incident_types:first");

        _entryTemplate = _incidentTypesTemplate
            .find(".list-group:first")
            .children(".list-group-item:first")
            ;
    }

    updateIncidentTypes();
}


function updateIncidentTypes() {
    const incidentTypesElement = $("#incident_types");

    const entryContainer = incidentTypesElement.find(".list-group:first");

    entryContainer.empty();

    for (const incidentType of incidentTypes) {
        const entryItem = _entryTemplate.clone();

        if (incidentTypesVisible.indexOf(incidentType) === -1) {
            entryItem.addClass("item-hidden")
        } else {
            entryItem.addClass("item-visible")
        }

        const safeIncidentType = textAsHTML(incidentType);
        entryItem.append(safeIncidentType);
        entryItem.attr("value", safeIncidentType);

        entryContainer.append(entryItem);
    }
}


async function addIncidentType(sender) {
    const {err} = await sendIncidentTypes({"add": [sender.value]});
    if (err == null) {
        sender.value = "";
    }
    await loadAndDrawIncidentTypes();
}


function removeIncidentType(sender) {
    alert("Remove unimplemented");
}


async function showIncidentType(sender) {
    await sendIncidentTypes({"show": [$(sender).parent().attr("value")]});
    await loadAndDrawIncidentTypes();
}


async function hideIncidentType(sender) {
    await sendIncidentTypes({"hide": [$(sender).parent().attr("value")]});
    await loadAndDrawIncidentTypes();
}


async function sendIncidentTypes(edits) {
    const {err} = await fetchJsonNoThrow(url_incidentTypes, {
        body: edits,
    });
    if (err == null) {
        return {err: null};
    }
    const message = `Failed to edit incident types:\n${JSON.stringify(err)}`;
    console.log(message);
    window.alert(message);
    return {err: err};
}
