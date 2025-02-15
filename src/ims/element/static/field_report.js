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
let fieldReport = null;

async function initFieldReportPage() {
    await loadBody();
    disableEditing();
    await loadAndDisplayFieldReport();

    // for a new field report
    if (fieldReport.number == null) {
        $("#field_report_summary").focus();
    }

    // Warn the user if they're about to navigate away with unsaved text.
    window.addEventListener("beforeunload", function (e) {
        if (document.getElementById("report_entry_add").value !== "") {
            e.preventDefault();
        }
    });

    // Updates...it's fine to ignore the returned promise here
    requestEventSourceLock();

    const fieldReportChannel = new BroadcastChannel(fieldReportChannelName);
    fieldReportChannel.onmessage = async function (e) {
        const number = e.data["field_report_number"];
        const event = e.data["event_id"]
        const updateAll = e.data["update_all"];

        if (updateAll || (event === eventID && number === fieldReportNumber)) {
            console.log("Got field report update: " + number);
            await loadAndDisplayFieldReport();
        }
    }

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
            $("#helpModal").modal("toggle");
        }
        // a --> jump to add a new report entry
        if (e.key === "a") {
            e.preventDefault();
            // Scroll to report_entry_add field
            $("html, body").animate({scrollTop: $("#report_entry_add").offset().top}, 500);
            $("#report_entry_add").focus();
        }
        // h --> toggle showing system entries
        if (e.key.toLowerCase() === "h") {
            document.getElementById("history_checkbox").click();
        }
        // n --> new field report
        if (e.key.toLowerCase() === "n") {
            window.open("./new", '_blank').focus();
        }
    });
    document.getElementById("helpModal").addEventListener("keydown", function(e) {
        if (e.key === "?") {
            $("#helpModal").modal("toggle");
        }
    });
    $("#report_entry_add")[0].addEventListener("keydown", function (e) {
        const submitEnabled = !$("#report_entry_submit").hasClass("disabled");
        if (submitEnabled && (e.ctrlKey || e.altKey) && e.key === "Enter") {
            submitReportEntry();
        }
    });
}

// Set the user-visible error information on the page to the provided string.
function setErrorMessage(msg) {
    console.error(msg);
    msg = `Error: (Cause: ${msg})`;
    document.getElementById("error_info").classList.remove("hidden");
    document.getElementById("error_text").textContent = msg;
}

function clearErrorMessage() {
    document.getElementById("error_info").classList.add("hidden");
    document.getElementById("error_text").textContent = "";
}

//
// Load field report
//

// returns {err: error|null}
async function loadFieldReport() {
    let number;
    if (fieldReport == null) {
        // First time here.  Use page JavaScript initial value.
        number = fieldReportNumber;
    } else {
        // We have an incident already.  Use that number.
        number = fieldReport.number;
    }

    if (number == null) {
        fieldReport = {
            "number": null,
            "created": null,
        };
    } else {
        const {json, err} = await fetchJsonNoThrow(
            urlReplace(url_fieldReports) + number)
        if (err != null) {
            disableEditing();
            const message = "Failed to load field report: " + error;
            console.error(message);
            setErrorMessage(message);
            return {err: message};
        }
        fieldReport = json;
    }
    return {err: null};
}

// returns void
async function loadAndDisplayFieldReport() {
    const {err} = await loadFieldReport();

    if (fieldReport == null || err != null) {
        const message = "Field report failed to load";
        console.log(message);
        setErrorMessage(message);
        return;
    }

    drawTitle();
    drawNumber();
    drawIncident();
    drawSummary();
    toggleShowHistory();
    drawReportEntries(fieldReport.report_entries);
    clearErrorMessage();

    $("#report_entry_add").on("input", reportEntryEdited);

    if (editingAllowed) {
        enableEditing();
    }
}


//
// Populate page title
//

function drawTitle() {
    document.title = fieldReportAsString(fieldReport);
}


//
// Populate field report number
//

function drawNumber() {
    let number = fieldReport.number;
    if (number == null) {
        number = "(new)";
    }
    $("#field_report_number").text(number);
}

//
// Populate incident number or show "create incident" button
//

function drawIncident() {
    $("#incident_number").text("Please include in Summary");
    // New Field Report. There can be no Incident
    if (fieldReport.number == null) {
        return;
    }
    // If there's an attached Incident, then show a link to it
    if (fieldReport.incident != null) {
        const incidentURL = urlReplace(url_viewIncidentNumber).replace("<number>", fieldReport.incident);
        const $a = $("<a>", {href: incidentURL});
        $a.text(fieldReport.incident);
        $("#incident_number").text("").append($a);
    }
    // If there's no attached Incident, show a button for making
    // a new Incident
    if (fieldReport.incident == null && canWriteIncidents) {
        $("#create_incident").removeClass("hidden");
    } else {
        $("#create_incident").addClass("hidden");
    }
}


//
// Populate field report summary
//

function drawSummary() {
    if (fieldReport.summary) {
        $("#field_report_summary").val(fieldReport.summary);
        $("#field_report_summary").attr("placeholder", "");
        return;
    }

    $("#field_report_summary")[0].removeAttribute("value");
    const summarized = summarizeIncident(fieldReport);
    if (summarized) {
        // only replace the placeholder if it would be nonempty
        $("#field_report_summary").attr("placeholder", summarized);
    }
}


//
// Editing
//

// returns {err: error|null}
async function sendEdits(edits) {
    const number = fieldReport.number;
    let url = urlReplace(url_fieldReports);

    if (number == null) {
        // We're creating a new field report.
        const required = [];
        for (const key of required) {
            if (edits[key] == null) {
                edits[key] = fieldReport[key];
            }
        }
    } else {
        // We're editing an existing field report.
        edits.number = number;
        url += number;
    }

    const {resp, json, err} = await fetchJsonNoThrow(url, {
        body: edits,
    })
    if (err != null) {
        const message = `Failed to apply edit: ${err}`;
        console.log(message);
        await loadAndDisplayFieldReport();
        setErrorMessage(message);
        return {err: message}
    }
    if (number == null) {
        // We created a new field report.
        // We need to find out the created field report number so that
        // future edits don't keep creating new resources.

        let newNumber = resp.headers.get("X-IMS-Field-Report-Number")
        // Check that we got a value back
        if (newNumber == null) {
            return {err: "No X-IMS-Field-Report-Number header provided."};
        }

        newNumber = parseInt(newNumber);
        // Check that the value we got back is valid
        if (isNaN(newNumber)) {
            return {err: "Non-integer X-IMS-Field-Report-Number header provided: " + newNumber};
        }

        // Store the new number in our field report object
        fieldReportNumber = fieldReport.number = newNumber;

        // Update browser history to update URL
        drawTitle();
        window.history.pushState(
            null, document.title,
            urlReplace(url_viewFieldReports) + newNumber
        );
    }

    await loadAndDisplayFieldReport();
    return {err: null};
}


async function editSummary() {
    await editFromElement($("#field_report_summary"), "summary");
}

//
// Make a new incident and attach this Field Report to it
//

async function makeIncident() {
    // Create the new incident
    {
        const incidentsURL = urlReplace(url_incidents);

        const authors = [];
        if (fieldReport.report_entries?.length > 0) {
            authors.push(fieldReport.report_entries[0].author);
        }
        let {resp, err} = await fetchJsonNoThrow(incidentsURL, {
            body:{
                "summary": fieldReport.summary,
                "ranger_handles": authors,
            },
        })
        if (err != null) {
            disableEditing();
            setErrorMessage(`Failed to create incident: ${err}`);
            return;
        }
        fieldReport.incident = parseInt(resp.headers.get("X-IMS-Incident-Number"));
    }

    // Attach this FR to that new incident
    {
        const attachToIncidentUrl =
            `${urlReplace(url_fieldReports)}${fieldReport.number}` +
            `?action=attach;incident=${fieldReport.incident}`;
        let {err} = await fetchJsonNoThrow(attachToIncidentUrl, {
            body: {},
        });
        if (err != null) {
            disableEditing();
            setErrorMessage(`Failed to attach field report: ${err}`);
            return;
        }
    }
    console.log("Created and attached to new incident " + fieldReport.incident);
    await loadAndDisplayFieldReport();
}


// The success callback for a report entry strike call.
async function onStrikeSuccess() {
    await loadAndDisplayFieldReport();
    clearErrorMessage();
}
