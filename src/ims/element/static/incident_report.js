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

function initIncidentReportPage() {
    function loadedIncidentReport() {
        // Scroll to incident_report_add field
        $("html, body").animate({ scrollTop: $("#incident_report_add").offset().top }, 500);
        $("#incident_report_add").focus();

        // Warn the user if they're about to navigate away with unsaved text.
        window.addEventListener('beforeunload', function (e) {
            if (document.getElementById("incident_report_add").value !== '') {
                e.preventDefault();
            }
        });
    }

    function loadedBody() {
        disableEditing();
        loadAndDisplayIncidentReport(loadedIncidentReport);

        var command = false;

        function addFieldKeyDown() {
            var keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode == 17 || keyCode == 18) {
                command = true;
            }

            // console.warn(keyCode);
        }

        function addFieldKeyUp() {
            var keyCode = event.keyCode;

            // 17 = control, 18 = option
            if (keyCode == 17 || keyCode == 18) {
                command = false;
                return;
            }

            // 13 = return
            if (command && keyCode == 13) {
                submitReportEntry();
            }
        }

        $("#incident_report_add")[0].onkeydown = addFieldKeyDown;
        $("#incident_report_add")[0].onkeyup   = addFieldKeyUp;
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
// Load incident report
//

var incidentReport = null;

function loadIncidentReport(success) {
    var number = null;
    if (incidentReport == null) {
        // First time here.  Use page JavaScript initial value.
        number = incidentReportNumber;
    } else {
        // We have an incident already.  Use that number.
        number = incidentReport.number;
    }

    function ok(data, status, xhr) {
        incidentReport = data;

        if (success != undefined) {
            success();
        }
    }

    function fail(error, status, xhr) {
        disableEditing();
        var message = "Failed to load field report";
        console.error(message + ": " + error);
        setErrorMessage(message);
    }

    if (number == null) {
        ok({
            "number": null,
            "created": null,
        });
    } else {
        var url = urlReplace(url_incidentReports) + number;
        jsonRequest(url, null, ok, fail);
    }
}


function loadAndDisplayIncidentReport(success) {
    function loaded() {
        if (incidentReport == null) {
            var message = "Field report failed to load";
            console.log(message);
            setErrorMessage(message);
            return;
        }

        drawTitle();
        drawNumber();
        drawSummary();
        drawReportEntries(incidentReport.report_entries);
        clearErrorMessage();

        $("#incident_report_add").on("input", reportEntryEdited);

        if (editingAllowed) {
            enableEditing();
        }

        if (success != undefined) {
            success();
        }
    }

    loadIncidentReport(loaded);
}


//
// Populate page title
//

function drawTitle() {
    document.title = incidentReportAsString(incidentReport);
}


//
// Populate field report number
//

function drawNumber() {
    var number = incidentReport.number;
    if (number == null) {
        number = "(new)";
    }
    $("#incident_report_number").text(number);
}


//
// Populate field report summary
//

function drawSummary() {
    var summary = incidentReport.summary;

    if (summary == undefined || summary == "") {
        $("#incident_report_summary")[0].removeAttribute("value");
        $("#incident_report_summary").attr(
            "placeholder", summarizeIncident(incidentReport)
        );
    } else {
        $("#incident_report_summary").val(summary);
        $("#incident_report_summary").attr("placeholder", "");
    }
}


//
// Editing
//

function sendEdits(edits, success, error) {
    var number = incidentReport.number
    var url = urlReplace(url_incidentReports);

    if (number == null) {
        // We're creating a new field report.
        var required = [];
        for (var i in required) {
            var key = required[i];
            if (edits[key] == undefined) {
                edits[key] = incidentReport[key];
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

            newNumber = xhr.getResponseHeader("X-IMS-Incident-Report-Number")
            // Check that we got a value back
            if (newNumber == null) {
                fail(
                    "No X-IMS-Incident-Report-Number header provided.",
                    status, xhr
                );
                return;
            }

            newNumber = parseInt(newNumber);
            // Check that the value we got back is valid
            if (isNaN(newNumber)) {
                fail(
                    "Non-integer X-IMS-Incident-Report-Number header provided:" +
                    newNumber,
                    status, xhr
                );
                return;
            }

            // Store the new number in our incident object
            incidentReport.number = newNumber;

            // Update browser history to update URL
            drawTitle();
            window.history.pushState(
                null, document.title,
                urlReplace(url_viewIncidentReports) + newNumber
            );
        }

        success();
        loadAndDisplayIncidentReport();
    }

    function fail(requestError, status, xhr) {
        var message = "Failed to apply edit";
        console.log(message + ": " + requestError);
        error();
        loadAndDisplayIncidentReport();
        setErrorMessage(message);
    }

    jsonRequest(url, edits, ok, fail);
}


function editSummary() {
    editFromElement($("#incident_report_summary"), "summary");
}
