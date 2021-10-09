function getJSON(form) {
    var formObj = {};
    var formArray = form.serializeArray();
    for (var i = 0; i < formArray.length; i++) {
        formObj[formArray[i]["name"]] = formArray[i]["value"];
    }
    return formObj;
}

$.ajaxSetup({
    dataType: "json",
    contentType: "application/json",
    method: "POST",
    error: function (jqXHR, status, error) {
        alert("Error: " + [status, error].filter(Boolean).join(", ") + "\nPlease try again.");
    }
});
