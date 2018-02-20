var splitTypeGroupSetMap = {'normal': ['Overall', 'Location', 'Pre/Post All-Star',
                                       'Wins/Losses', 'Days Rest', 'Month', 'Starting Position'],
                            'shooting': ['Overall', 'Shot Distance (5ft)', 'Shot Distance (8ft)',
                                         'Shot Area', 'Assisted By', 'Assisted Shot',
                                         'Shot Type Summary', 'Shot Type Detail']};

// TODO: Make it sp that Overall only shows seasons the player was actually in the league. Hmm.
var groupSetGroupValueMap = {'Overall': ['1996-97', '1997-98', '1998-99', '1999-00', '2000-01', '2001-02', '2002-03', '2003-04', '2004-05', '2005-06', '2006-07', '2007-08', '2008-09', '2009-10', '2010-11', '2011-12', '2012-13', '2013-14', '2014-15', '2015-16', '2016-17'],
                             'Location': ['Home', 'Road'],
                             'Pre/Post All-Star': ['Pre All-Star', 'Post All-Star', 'Playoffs', 'N/A'],
                             'Wins/Losses': ['Wins', 'Losses'],
                             'Days Rest': ['0 Days Rest', '1 Days Rest', '2 Days Rest', '3 Days Rest', '4 Days Rest', '5 Days Rest', '6+ Days Rest'],
                             'Month': ['October', 'November', 'December', 'January', 'February', 'March', 'April', 'May', 'June'],
                             'Starting Position': ['Starters', 'Bench'],
                             'Shot Distance (5ft)': ['Less Than 5 ft.', '5-9 Ft.', '10-14 ft.', '15-19 ft.', '20-24 ft.', '25-29 ft.', '30-34 ft.', '35-39 ft.', '40+ ft.'],
                             'Shot Distance (8ft)': ['Less Than 8 ft.', '8-16 ft.', '16-24 ft.', '24+ ft.', 'Back Court Shot'],
                             'Shot Area': ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Above the Break 3', 'Right Corner 3'],
                             'Shot Type Summary': ['Alley Oop', 'Dunk', 'Tip Shot','Layup', 'Finger Roll', 'Hook Shot', 'Bank Shot', 'Jump Shot', 'Fadeaway'],
                             'Shot Type Detail': ['Alley Oop Dunk Shot', 'Alley Oop Layup shot', 'Cutting Dunk Shot', 'Cutting Finger Roll Layup Shot', 'Cutting Layup Shot', 'Driving Bank Hook Shot', 'Driving Bank shot', 'Driving Dunk Shot', 'Driving Finger Roll Layup Shot', 'Driving Finger Roll Shot', 'Driving Floating Bank Jump Shot', 'Driving Floating Jump Shot', 'Driving Hook Shot', 'Driving Jump shot', 'Driving Layup Shot', 'Driving Reverse Dunk Shot', 'Driving Reverse Layup Shot', 'Driving Slam Dunk Shot', 'Dunk Shot', 'Fadeaway Bank shot', 'Fadeaway Jump Shot', 'Finger Roll Layup Shot', 'Finger Roll Shot', 'Floating Jump shot', 'Follow Up Dunk Shot', 'Hook Bank Shot', 'Hook Shot', 'Jump Bank Hook Shot', 'Jump Bank Shot', 'Jump Hook Shot', 'Jump Shot', 'Layup Shot', 'No Shot', 'Pullup Bank shot', 'Pullup Jump shot', 'Putback Dunk Shot', 'Putback Layup Shot', 'Putback Reverse Dunk Shot', 'Putback Slam Dunk Shot', 'Reverse Dunk Shot', 'Reverse Layup Shot', 'Reverse Slam Dunk Shot', 'Running Alley Oop Dunk Shot', 'Running Alley Oop Layup Shot', 'Running Bank Hook Shot', 'Running Bank shot', 'Running Dunk Shot', 'Running Finger Roll Layup Shot', 'Running Finger Roll Shot', 'Running Hook Shot', 'Running Jump Shot', 'Running Layup Shot', 'Running Pull-Up Jump Shot', 'Running Reverse Dunk Shot', 'Running Reverse Layup Shot', 'Running Slam Dunk Shot', 'Running Tip Shot', 'Slam Dunk Shot', 'Step Back Bank Jump Shot', 'Step Back Jump shot', 'Tip Dunk Shot', 'Tip Layup Shot', 'Tip Shot', 'Turnaround Bank Hook Shot', 'Turnaround Bank shot', 'Turnaround Fadeaway Bank Jump Shot', 'Turnaround Fadeaway shot', 'Turnaround Finger Roll Shot', 'Turnaround Hook Shot', 'Turnaround Jump Shot']};

function seasonButtonClick(){
    $(".panel-body").collapse("hide");
    $("#regular_season_per_game_table").collapse("show");
    $("#season_panel").collapse("show");
}



function seasonType(){
    var perModeSelect = $("#season_per_mode_select");
    var seasonTypeSelect = $("#season_type_select");
    var perMode = perModeSelect.val();
    var seasonType = seasonTypeSelect.val();
    $(".table").collapse("hide");
    var tableID = "#" + seasonType + "_" + perMode + "_table";
    console.log(tableID);
    var toShow = $(tableID);
    console.log(toShow.html());
    toShow.collapse("show");

}

function splitButtonClick(){
    var splitPanel = $("#split_panel");
    var selectionDiv = $("#split_selection_div");
    $("#split_data_div").html("");
    // Just setting the defaults here
    var selectionDivHTML = '';
    var seasonSelectHTML = '<select id="split_season_id_select" class="form-control">';
    for (var year = entityObj.to_year; year >= entityObj.from_year; year--){
        console.log(year);
        var season = null;
        if (year == 1999){
            season = "1999-00";
        }
        else{
            var suffix = (year + 1).toString().substring(2);
            season = year.toString() + "-" + suffix;
        }
        seasonSelectHTML += '<option value="' + year.toString() + '">' + season + '</option>';
    }
    seasonSelectHTML += '</select>';
    selectionDivHTML += seasonSelectHTML;

    var measureTypeSelectHTML = '<select id="split_measure_type_select" class="form-control" onchange="splitType(this);">';
    measureTypeSelectHTML += '<option value="Traditional">Traditional</option>';
    measureTypeSelectHTML += '<option value="Advanced">Advanced</option>';
    measureTypeSelectHTML += '<option value="Misc">Miscellaneous</option>';
    measureTypeSelectHTML += '<option value="Usage">Usage</option>';
    measureTypeSelectHTML += '<option value="Scoring">Scoring</option>';
    measureTypeSelectHTML += '<option value="Shooting">Shooting</option>';
    measureTypeSelectHTML += '</select>';
    selectionDivHTML += measureTypeSelectHTML;


    var seasonTypeSelectHTML = '<select id="split_season_type_select" class="form-control">';
    seasonTypeSelectHTML += '<option value="Regular Season">Regular Season</option>';
    seasonTypeSelectHTML += '<option value="Playoffs">Playoffs</option>';
    seasonTypeSelectHTML += "</select>";
    selectionDivHTML += seasonTypeSelectHTML;

    var perModeSelectHTML = '<select id="split_per_mode_select" class="form-control">';
    perModeSelectHTML += '<option value="PerGame">Per Game</option>';
    perModeSelectHTML += '<option value="Totals">Totals</option>';
    perModeSelectHTML += '<option value="Per36">Per 36</option>';
    perModeSelectHTML += '<option value="Per100">Per 100 Possessions</option>';
    perModeSelectHTML += '</select>';
    selectionDivHTML += perModeSelectHTML;

    var groupSetSelectHTML = '<select id="split_group_set_select" class="form-control" onchange="groupSetChange(this);">';
    $.each(splitTypeGroupSetMap.normal, function(key, val){
       groupSetSelectHTML += '<option value="' + val + '">'+ val + '</option>';
    });
    groupSetSelectHTML += '</select>';
    selectionDivHTML += groupSetSelectHTML;

    var groupValueSelectHTML = '<select id="split_group_value_select" class=form-control>';
    $.each(groupSetGroupValueMap.Overall, function(key, val){
        groupValueSelectHTML += '<option value="' + val + '">'+ val + '</option>';
    });
    groupValueSelectHTML += '</select>';
    selectionDivHTML += groupValueSelectHTML;

    selectionDivHTML += '<button id="get_splits_button" type="button" class="btn btn-default" onclick="getSplits();">Get Splits</button>';

    selectionDiv.html(selectionDivHTML);

    var seasonPanel = $("#season_panel");
    seasonPanel.collapse("hide");
    splitPanel.collapse("show");
}

function splitType(self){
    var selectedSplitType = $(self).val();
    console.log(selectedSplitType);
    var groupSetSelect = $("#split_group_set_select");
    var htmlString = "";
    if (selectedSplitType == "Shooting"){
        $.each(splitTypeGroupSetMap.shooting, function(key, val){
            htmlString += '<option value="' + val + '">'+ val + '</option>';
        });
    }
    else{
        $.each(splitTypeGroupSetMap.normal, function(key, val){
            htmlString += '<option value="' + val + '">'+ val + '</option>';
        });
    }
    groupSetSelect.html(htmlString);
    groupSetChange(groupSetSelect);
}

function groupSetChange(self){
    var selectedGroupSet = $(self).val();
    console.log(selectedGroupSet);
    var groupValueSelect = $("#split_group_value_select");
    var htmlString = "";
    $.each(groupSetGroupValueMap[selectedGroupSet], function(key, val){
        htmlString += '<option value="' + val + '">'+ val + '</option>';
    });
    groupValueSelect.html(htmlString);
}

function getSplits(){

    var seasonId = $("#split_season_id_select").val();
    var splitType = $("#split_measure_type_select").val();
    var seasonType = $("#split_season_type_select").val();
    var perMode = $("#split_per_mode_select").val();
    var groupSet = $("#split_group_set_select").val();
    var groupValue = $("#split_group_value_select").val();
    console.log(splitType, seasonType, perMode, groupSet, groupValue);

    var ajaxURL = '/nba_stats/ajax/get_' + model + '_splits';

    console.log(entityObj);

    $.ajax({
        url: ajaxURL,
        type: 'GET',
        data: {
            'entity_id': entityObj['id'],
            'season_id': seasonId,
            'split_type': splitType,
            'season_type': seasonType,
            'per_mode': perMode,
            'group_set': groupSet,
            'group_value': groupValue
        },
        dataType: 'json',
        success: function (data) {
            var splitTableDiv = $("#split_data_div");
            var tableHTML = '<table id="split_data_table" class="table table-striped">';
            tableHTML += "<thead><tr>";
            $.each(data.model_fields, function(idx, fieldObj){
               tableHTML += "<th>" + fieldObj.display_value + "</th>";
            });
            tableHTML += "</tr></thead><tbody>";
            $.each(data.splits, function(idx, splitObj){
                tableHTML += "<tr>";
              $.each(data.model_fields, function (subIdx, fieldObj) {
                  tableHTML += '<td>' + splitObj[fieldObj.field_name] + '</td>';
              });
              tableHTML += '</tr>';
            });
            tableHTML += '</tbody></table>';
            splitTableDiv.html(tableHTML);
        }
    });
}