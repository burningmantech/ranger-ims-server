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

function initFieldReportPage() {
    function loadedFieldReport() {
        // for a new field report
        if (fieldReport.number == null) {
            $("#field_report_summary").focus();
        } else {
            // Scroll to report_entry_add field
            $("html, body").animate({scrollTop: $("#report_entry_add").offset().top}, 500);
            $("#report_entry_add").focus();
        }

        // Warn the user if they're about to navigate away with unsaved text.
        window.addEventListener('beforeunload', function (e) {
            if (document.getElementById("report_entry_add").value !== '') {
                e.preventDefault();
            }
        });
    }

    function loadedBody() {
        disableEditing();
        loadAndDisplayFieldReport(loadedFieldReport);

        let command = false;

        function addFieldKeyDown() {
            const keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode === 17 || keyCode === 18) {
                command = true;
            }

            // console.warn(keyCode);
        }

        function addFieldKeyUp() {
            const keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode === 17 || keyCode === 18) {
                command = false;
                return;
            }

            // 13 = return
            if (command && keyCode === 13) {
                submitReportEntry();
            }
        }

        $("#report_entry_add")[0].onkeydown = addFieldKeyDown;
        $("#report_entry_add")[0].onkeyup   = addFieldKeyUp;
    }

    loadBody(loadedBody);
}

// Set the user-visible error information on the page to the provided string.
function setErrorMessage(msg) {
    msg = "Error: Please reload this page. (Cause: " + msg + ")"
    $("#error_info").removeClass("hidden");
    $("#error_text").text(msg);
}

function clearErrorMessage() {
    $("#error_info").addClass("hidden");
    $("#error_text").text("");
}


//
// Load field report
//

function loadFieldReport(success) {
    let number = null;
    if (fieldReport == null) {
        // First time here.  Use page JavaScript initial value.
        number = fieldReportNumber;
    } else {
        // We have an incident already.  Use that number.
        number = fieldReport.number;
    }

    function ok(data, status, xhr) {
        fieldReport = data;

        if (success) {
            success();
        }
    }

    function fail(error, status, xhr) {
        disableEditing();
        const message = "Failed to load field report";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    if (number == null) {
        ok({
            "number": null,
            "created": null,
        });
    } else {
        const url = urlReplace(url_incidentReports) + number;
        jsonRequest(url, null, ok, fail);
    }
}


function loadAndDisplayFieldReport(success) {
    function loaded() {
        if (fieldReport == null) {
            const message = "Field report failed to load";
            console.log(message);
            setErrorMessage(message);
            return;
        }

        drawTitle();
        drawNumber();
        drawIncident();
        drawSummary();
        drawReportEntries(fieldReport.report_entries);
        clearErrorMessage();

        $("#report_entry_add").on("input", reportEntryEdited);

        if (editingAllowed) {
            enableEditing();
        }

        if (success) {
            success();
        }
    }

    loadFieldReport(loaded);
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

function sendEdits(edits, success, error) {
    const number = fieldReport.number;
    let url = urlReplace(url_incidentReports);

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

    function ok(data, status, xhr) {
        if (number == null) {
            // We created a new field report.
            // We need to find out the created field report number so that
            // future edits don't keep creating new resources.

            let newNumber = xhr.getResponseHeader("X-IMS-Field-Report-Number")
            // Check that we got a value back
            if (newNumber == null) {
                fail(
                    "No X-IMS-Field-Report-Number header provided.",
                    status, xhr
                );
                return;
            }

            newNumber = parseInt(newNumber);
            // Check that the value we got back is valid
            if (isNaN(newNumber)) {
                fail(
                    "Non-integer X-IMS-Field-Report-Number header provided:" +
                    newNumber,
                    status, xhr
                );
                return;
            }

            // Store the new number in our incident object
            fieldReport.number = newNumber;

            // Update browser history to update URL
            drawTitle();
            window.history.pushState(
                null, document.title,
                urlReplace(url_viewFieldReports) + newNumber
            );
        }

        success();
        loadAndDisplayFieldReport();
    }

    function fail(requestError, status, xhr) {
        const message = "Failed to apply edit";
        console.log(message + ": " + requestError);
        error();
        loadAndDisplayFieldReport();
        setErrorMessage(message);
    }

    jsonRequest(url, edits, ok, fail);
}


function editSummary() {
    editFromElement($("#field_report_summary"), "summary");
}

//
// Make a new incident and attach this Field Report to it
//

function makeIncident() {
    const incidentsURL = urlReplace(url_incidents);

    function createOk(data, status, xhr) {
        const newIncident = xhr.getResponseHeader("X-IMS-Incident-Number");
        fieldReport.incident = parseInt(newIncident);

        const url = (
            urlReplace(url_incidentReports) + fieldReport.number +
            "?action=attach;incident=" + newIncident
        );

        function attachOk(data, status, xhr) {
            console.log("Created and attached to new incident " + newIncident);
            loadAndDisplayFieldReport();
        }

        function attachFail(error, status, xhr) {
            disableEditing();
            const message = "Failed to attach field report";
            console.error(message + ": " + error);
            setErrorMessage(message);
        }

        jsonRequest(url, {}, attachOk, attachFail);
    }

    function createFail(error, status, xhr) {
        disableEditing();
        const message = "Failed to create incident";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    const authors = [];
    if (fieldReport.report_entries?.length > 0) {
        authors.push(fieldReport.report_entries[0].author);
    }

    jsonRequest(incidentsURL, {
        "summary": fieldReport.summary,
        "ranger_handles": authors,
        }, createOk, createFail,
    );
}
