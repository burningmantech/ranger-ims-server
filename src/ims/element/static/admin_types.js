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
    try {
        await loadIncidentTypes();
        drawIncidentTypes();
    } catch (err) {
        // do nothing
    }
}


let incidentTypes = null;
let incidentTypesVisible = null;

async function loadIncidentTypes() {
    const headers = {"Cache-Control": "no-cache"};
    try {
        [incidentTypesVisible, incidentTypes] = await Promise.all([
            jsonRequestAsync(url_incidentTypes, null, headers),
            jsonRequestAsync(url_incidentTypes + "?hidden=true", null, headers),
        ]);
    } catch (error) {
        const message = "Failed to load incident types:\n" + error;
        console.error(message);
        window.alert(message);
        throw error;
    }
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
    try {
        await sendIncidentTypes(
            {"add": [sender.value]},
        );
    } catch (err) {
        await loadAndDrawIncidentTypes();
        return;
    }
    sender.value = "";
    await loadAndDrawIncidentTypes();
}


function removeIncidentType(sender) {
    alert("Remove unimplemented");
}


async function showIncidentType(sender) {
    await sendIncidentTypes(
        { "show": [$(sender).parent().attr("value")] },
    );
    await loadAndDrawIncidentTypes();
}


async function hideIncidentType(sender) {
    await sendIncidentTypes(
        { "hide": [$(sender).parent().attr("value")] },
    );
    await loadAndDrawIncidentTypes();
}


async function sendIncidentTypes(edits) {
    try {
        await jsonRequestAsync(url_incidentTypes, edits);
    } catch (err) {
        const message = `Failed to edit incident types:\n${JSON.stringify(err)}`;
        console.log(message);
        window.alert(message);
    }
}
