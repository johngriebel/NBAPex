$('#roster_date_div').datepicker().on("changeDate", function(e){
    var newDate = e.date;
    // It *feels* like we should be using the getUTC*() methods, but I'm not sure.
    // Time is confusing.
    var year = newDate.getFullYear();
    var month = newDate.getMonth() + 1;
    var day = newDate.getDate();
    var dateStr = year.toString() + "/" + month.toString() + "/" + day.toString();
    window.location.href = window.location.origin + viewTeamBaseURL + dateStr;
});



var curPlayer = null;
var origButton = null;
var origTableRow = null;

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

$("#roster_div").collapse();
function movePlayerButtonClicked(button){
    var myButton = $(button);
    if (curPlayer === null){
        $(".btn-roster").prop('disabled', true);
        curPlayer = {'playerId': myButton.attr("data-player-id"),
                     'playerPosition': myButton.attr('data-player-position')};
        origTableRow = myButton.parent().parent();
        origButton = myButton;
        var eligClasses = myButton.attr("class").split(/\s+/);
        console.log(eligClasses);
        $.each(eligClasses, function(idx, item){
            if (item.substring(0,4) === "elig"){
                console.log(item);
                $("." + item).prop('disabled', false);
            }
        });
    }
    else if (curPlayer['playerId'] == myButton.attr("data-player-id")){
        console.log("Reset the buttons");
        curPlayer = null;
        origTableRow = null;
        myButton = null;
        $(".btn-roster").prop('disabled', false);
    }
    else {
        // A button has been clicked that != myButton.
        // I have a feeling we're going to get infinite recursion here
        console.log("Do roster swapping stuff.");
        console.log("first player id", curPlayer);
        var secondPlayer = {'playerId': myButton.attr("data-player-id"),
                            'playerPosition': myButton.attr('data-player-position')};
        var secondTableRow = myButton.parent().parent();
        console.log("second player id", secondPlayer);
        var date = $(".datepicker").datepicker("getDate").toISOString();
        console.log("Date: " + date);

        $.ajax({
            url: ajaxURL,
            type: 'POST',
            data: {
                'firstPlayer': JSON.stringify(curPlayer),
                'secondPlayer': JSON.stringify(secondPlayer),
                'date': date
            },
            dataType: 'json',
            success: function(data){
                if (data.success) {
                    var firstPosition = origButton.attr("data-player-position");
                    var secondPosition = myButton.attr("data-player-position");
                    origButton.attr("data-player-position", secondPosition);
                    myButton.attr("data-player-position", firstPosition);

                    var origPosDisplay = origTableRow.find(".td-player-position");
                    var origDisplay = origPosDisplay.text();
                    var secondPosDisplay = secondTableRow.find(".td-player-position");
                    origPosDisplay.text(secondPosDisplay.text());
                    secondPosDisplay.text(origDisplay);

                    var origHTML = origTableRow.html();
                    origTableRow.html(secondTableRow.html());
                    secondTableRow.html(origHTML);

                    curPlayer = null;
                    origTableRow = null;
                    myButton = null;
                    $(".btn-roster").prop('disabled', false);

                    var alertHTML = '<div class="alert alert-success alert-dismissible" role="alert">';
                    alertHTML += '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>';
                    alertHTML += "Roster successfully updated!</div>";
                    $("#alert_div").html(alertHTML);
                }

            }
        });
    }
}