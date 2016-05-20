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
// HTML encoding
//

// It seems ridiculous that this isn't standard in JavaScript
// It is certainly ridiculous to involve the DOM, but on the other hand, the
// browser will implement this correctly, and any solution using .replace()
// will be buggy.  And this will be fast.  But still, this is weak.

var _domTextAreaForHaxxors = document.createElement("textarea")

// Convert text to HTML.
function textAsHTML(text) {
  _domTextAreaForHaxxors.textContent = text;
  return _domTextAreaForHaxxors.innerHTML;
}

// Convert HTML to text.
function htmlAsText(html) {
  _domTextAreaForHaxxors.innerHTML = html;
  return _domTextAreaForHaxxors.textContent;
}


//
// Errors
///

function ValueError(message) {
  this.name = "ValueError";
  this.message = message || "Invalid Value";
  this.stack = (new Error()).stack;
}
ValueError.prototype = Object.create(Error.prototype);
ValueError.prototype.constructor = ValueError;


//
// Arrays
//

// Build an array from a range.
function range(start, end, step) {
  if (step == undefined) {
    step = 1;
  } else if (step == 0) {
    throw new ValueError("step = 0");
  }

  return Array(end - start)
    .join(0)
    .split(0)
    .map(function(val, i) { return (i * step) + start} )
    ;
}


//
// Request making
//

function jsonRequest(url, jsonOut, success, error) {
    function ok(data, status, xhr) {
        if (success != undefined) {
            success(data, status, xhr);
        }
    }

    function fail(xhr, status, requestError) {
        if (error != undefined) {
            error(requestError, status, xhr);
        }
    }

    var args = {
        "url": url,
        "method": "GET",
        "dataType": "json",
        "success": ok,
        "error": fail,
    }

    if (jsonOut) {
        var jsonText = null
        if (typeof(jsonOut) == "string") {
          jsonText = jsonOut;
        } else {
          jsonText = JSON.stringify(jsonOut);
        }

        args["method"] = "POST";
        args["contentType"] = "application/json";
        args["data"] = jsonText;
    }

    $.ajax(args);
}



//
// Generic string formatting
//

// Pad a string representing an integer to two digits.
function padTwo(value) {
  if (value == undefined) {
    return "?";
  }

  value = value.toString();

  if (value.length == 1) {
    return "0" + value;
  }

  return value;
}


// Format a date using a compact form.
function shortFormatDate(date) {
  return moment(date).format("M/D@h:mm z");
}


// Convert a minute (0-60) into a value used by IMS form inputs.
// That is: round to the nearest multiple of 5 and pad to two digits.
function normalizeMinute(minute) {
  minute = Math.round(minute / 5) * 5;
  while (minute > 60) {
    minute -= 60;
  }
  return padTwo(minute);
}


//
// Elements
//

// Create a <time> element from a date.
function timeElement(date) {
  date = moment(date);
  var timeStampContainer = jQuery(
    "<time />", {"datetime": date.toISOString()}
  );
  timeStampContainer.text(date.toString());
  return timeStampContainer;
}


// Disable an element
function disable(element) {
    element.attr("disabled", "");
}


// Enable an element
function enable(element) {
    element.removeAttr("disabled");
}


// Disable editing for an element
function disableEditing() {
    disable($(".form-control"));
}


// Enable editing for an element
function enableEditing() {
    enable($(".form-control"));
}


// Add an error indication to a control
function controlHasError(element) {
    element.parent().addClass("has-error");
}


// Add a success indication to a control
function controlHasSuccess(element, clearTimeout) {
    element.parent().addClass("has-success");
    if (clearTimeout != undefined) {
        element.delay("1000").queue(function() {controlClear(element)});
    }
}


// Clear error/success indication from a control
function controlClear(element) {
    var parent = element.parent();
    parent.removeClass("has-error");
    parent.removeClass("has-success");
}


//
// Load HTML body template.
//

function loadBody(success) {
    function complete() {
        if (success != undefined) {
            success();
        }
    }

    $("body").load(pageTemplateURL, complete);
}


//
// Controls
//

// Select an option element with a given value from a given select element.
function selectOptionWithValue(select, value) {
  select
    .children("option")
    .prop("selected", false)
    ;

  select
    .children("option[value='" + value + "']")
    .prop("selected", true)
    ;
}


//
// Incident data
//

// Look up the name of a priority given its number (1-5).
function priorityNameFromNumber(number) {
  switch (number) {
    case 1: return "High";
    case 2: return "High";
    case 3: return "Normal";
    case 4: return "Low";
    case 5: return "Low︎";
    default:
      console.warn("Unknown incident priority number: " + number);
      return undefined;
  }
}


// Look up the glyph for a priority given its number (1-5).
function priorityIconFromNumber(number) {
  switch (number) {
    case 1: return '<span class="glyphicon glyphicon-arrow-up">';
    case 2: return '<span class="glyphicon glyphicon-arrow-up">';
    case 3: return '<span class="glyphicon glyphicon-minus">';
    case 4: return '<span class="glyphicon glyphicon-arrow-down">';
    case 5: return '<span class="glyphicon glyphicon-arrow-down">';
    default:
      console.warn("Unknown incident priority number: " + number);
      return undefined;
  }
}


// Look up a state's name given its ID.
function stateNameFromID(stateID) {
  switch (stateID) {
    case "new"       : return "New";
    case "on_hold"   : return "On Hold";
    case "dispatched": return "Dispatched";
    case "on_scene"  : return "On Scene";
    case "closed"    : return "Closed";
    default:
      console.warn("Unknown incident state ID: " + stateID);
      return undefined;
  }
}


// Look up a state's sort key given its ID.
function stateSortKeyFromID(stateID) {
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


// Look up a concentric street's name given its ID.
function concentricStreetFromID(streetID) {
  if (streetID == undefined) {
    return undefined;
  }

  var name = concentricStreetNameByID[streetID];
  if (name == undefined) {
    console.warn("Unknown street ID: " + streetID);
    name = undefined;
  }
  return name;
}


// Return the state ID for a given incident.
function stateForIncident(incident) {
  // Data from 2014+ should have incident.state set.
  if (incident.state != undefined) {
    return incident.state;
  }

  // 2013 data had multiple overloaded timestamps instead.
  if (incident.closed != undefined) {
    return "closed";
  }
  if (incident.on_scene != undefined) {
    return "on_scene";
  }
  if (incident.dispatched != undefined) {
    return "dispatched";
  }
  if (incident.created != undefined) {
    return "new";
  }

  console.warn("Unknown state for incident: " + incident);
  return undefined;
}


// Return a summary for a given incident.
function summarizeIncident(incident) {
  var summary = incident.summary;
  var reportEntries = incident.report_entries;

  if (summary == undefined) {
    if (reportEntries == undefined) {
      console.warn("No summary provided.");
      return "";
    }
    else {
      // Get the first line of the first report entry.
      for (var i in reportEntries) {
        var lines = reportEntries[i].text.split("\n");

        for (var j in lines) {
          var line = lines[j];
          if (line != undefined && line != "") {
            return summary;
          }
        }
      }
    }

    console.warn("No summary provided and no report entry text.");
    return "";
  }

  return summary;
}


// Return all user-entered report text for a given incident.
function reportTextFromIncident(incident) {
  var texts = [];

  if (incident.summary != undefined) {
    texts.push(incident.summary);
  }

  var reportEntries = incident.report_entries;

  for (var i in reportEntries) {
    var reportEntry = reportEntries[i];

    // Skip system entries
    if (reportEntry.system_entry) {
      continue;
    }

    var text = reportEntry.text;

    if (text != undefined) {
      texts.push(text);
    }
  }

  var text = texts.join("");

  return text;
}


// Return a short description for a given location.
function shortDescribeLocation(location) {
  if (location == undefined) {
    return undefined;
  }

  var locationBits = [];

  if (location.name != undefined) {
    locationBits.push(location.name);
  }

  switch (location.type) {
    case undefined:
      // Fall through to "text" case
    case "text":
      break;
    case "garett":
      locationBits.push(" (");
      locationBits.push(padTwo(location.radial_hour));
      locationBits.push(":");
      locationBits.push(padTwo(location.radial_minute));
      locationBits.push("@");
      locationBits.push(concentricStreetFromID(location.concentric));
      locationBits.push(")");
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

function renderPriority(priorityNumber, type, incident) {
  switch (type) {
    case "display":
      return priorityIconFromNumber(priorityNumber);
    case "filter":
      return priorityNameFromNumber(priorityNumber);
    case "type":
    case "sort":
      return priorityNumber;
  }
  return undefined;
}

function renderDate(date, type, incident) {
  switch (type) {
    case "display":
      return textAsHTML(shortFormatDate(date));
    case "filter":
      return shortFormatDate(date);
    case "type":
    case "sort":
      return moment(date);
  }
  return undefined;
}

function renderState(state, type, incident) {
  if (state == undefined) {
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

function renderLocation(data, type, incident) {
  if (data == undefined) {
    data = "";
  }
  switch (type) {
    case "display":
      return textAsHTML(shortDescribeLocation(data));
    case "filter":
    case "sort":
      return shortDescribeLocation(data);
    case "type":
      return "";
  }
  return undefined;
}

function renderSummary(data, type, incident) {
  switch (type) {
    case "display":
      return textAsHTML(summarizeIncident(incident));
    case "sort":
      return summarizeIncident(incident);
    case "filter":
      return reportTextFromIncident(incident);
    case "type":
      return "";
  }
  return undefined;
}
