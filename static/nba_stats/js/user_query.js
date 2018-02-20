/**
 * Created by johngriebel on 3/1/17.
 */

var fields = {};
var currentlySelectedModel = "";
var NUM_OPS = {'gt': ">",
               'gte': ">=",
               'exact': "=",
               "neq": "!=",
               'lt': "<",
               'lte': "<="};

var CHAR_OPS = {'istartswith': "Begins with",
                'iendswith': "Ends with",
                'icontains': "Contains",
                'iexact': "equals (Not case-sensitive)"};
var exportData = null;

var svg = d3.select("svg"),
    width = +svg.attr("width"),
    height = +svg.attr("height");

var color = d3.scaleOrdinal(d3.schemeCategory20);

var simulation = d3.forceSimulation()
    .force("link", d3.forceLink().id(function(d) { return d.id; }))
    .force("charge", d3.forceManyBody())
    .force("center", d3.forceCenter(width / 2, height / 2));

var tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);

function setFieldsDropdown() {
    var model = $("#model").val();
    console.log(model);
    $.ajax({
        url: '/nba_stats/ajax/get_related_models/',
        type: 'GET',
        data: {
            'model': model
        },
        dataType: 'json',
        success: function (data) {
            /*
            $(".model-option").each(function(){
                var option = $(this).attr("value");
                var idx = $.inArray(option, data.related);
                console.log(option + " " + idx.toString());
                if (idx == -1){
                    $(this).prop('disabled', true);
                }
                else{
                    $(this).prop('disabled', false);
                }
            });
            */
            fields = data.fields;
            drawGraph(data);
            console.log("Back from grawGraph call")
        }
    });
}

function drawGraph(data){
    console.log("In draw graph");
    svg.selectAll("circle").remove();
    svg.selectAll("line").remove();
    var nodes = data.nodes;
    var links = data.links;
    var fields = data.fields;
    var link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(links)
        .enter().append("line")
        .attr("stroke-width", function(d) { return Math.sqrt(d.value); });

    console.log("appended links");

    var node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(nodes)
        .enter().append("circle")
        // Perhaps adjust radius according to size of table? (PBP would be HUUUUGE).
        // Or maybe num of fields?
        .attr("r", 10)
        .attr("fill", function(d) { return color(d.group); })
        .on("mouseover", function(d) {
                    tooltip.transition()
                       .duration(200)
                       .style("opacity", .9);
                    tooltip.html(d.id)
                   .style("left", (d3.event.pageX + 5) + "px")
                   .style("top", (d3.event.pageY - 28) + "px");
                    })
        .on("mouseout", function(d) {
            tooltip.transition()
           .duration(500)
           .style("opacity", 0);
        })
        .on("click", function(d){
            console.log("Circle clicked!");
            console.log(d);
            var myFields = fields[d.id];
            addFieldsCheckboxes(myFields);
            currentlySelectedModel = d.id;
            console.log(currentlySelectedModel);
        })
        .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended));

    console.log("appended nodes");

    node.append("title")
      .text(function(d) { return d.id; });

    console.log("Added title");

    simulation
      .nodes(nodes)
      .on("tick", ticked);

    console.log("back from simulation.nodes call");

    simulation.force("link")
      .links(links);

    console.log("back from simulation.links call");

    function ticked() {
    link
        .attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    node
        .attr("cx", function(d) { return d.x; })
        .attr("cy", function(d) { return d.y; });
    }

    console.log("back from ticked definition");

}

function dragstarted(d) {
  if (!d3.event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(d) {
  d.fx = d3.event.x;
  d.fy = d3.event.y;
}

function dragended(d) {
  if (!d3.event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}


function addFieldsCheckboxes(fieldsToAdd){
    var fieldsDiv = $("#all_fields_div");
    var checkboxContainer = fieldsDiv.find("#all_fields_container");
    var htmlString = "";
    if (checkboxContainer.html() == null){
        console.log("Found that checkbox container doesn't exist yet");
        htmlString += '<div id="all_fields_container" class="container" style="overflow:scroll; height: 150px">';
    }

    $.each(fieldsToAdd, function(){
        var fieldObj = this;
        var checkBoxHtml = '<input class="field-checkbox" type="checkbox" id="chkbox_' + fieldObj.model_name + "__";
        checkBoxHtml += fieldObj.field_name + '"/>' + fieldObj.model_name + "." + fieldObj.display_value + "<br/>";
        htmlString += checkBoxHtml;
    });
    if (checkboxContainer.html() == null){
        htmlString += "</div>";
        fieldsDiv.append(htmlString);
    }
    else{
        checkboxContainer.append(htmlString)
    }
}

function createFieldSelector(availFields){
    // TODO: Need to make sure the fields are sorted by correct order.
    // Right now they seem to be ordered alphabetically by model name
    var fieldSelect = '<select class="field-selector" onchange="addOpAndInput(this);"><option></option>';
    $.each(availFields, function(){
        console.log(this);
        var field = this;
        var htmlString = '<option value="';
        htmlString += field.model_name + "__" + field.field_name + '"';
        htmlString += 'class="db-type-' + field.field_type + '">';
        htmlString += field.model_name + "." + field.display_value;
        htmlString += "</option>";
        fieldSelect += htmlString

    });
    fieldSelect += "</select>";
    return fieldSelect;
}

function createOperatorSelector(fieldId, fieldType){
    console.log(fieldType);
    var opSelect = '<select class="op-selector" id="operator_"' + fieldId +'>';
    var operators = null;
    if (fieldType == "Char"){
        operators = CHAR_OPS;
    }
    else if (fieldType == "Integer" || fieldType == "Float"){
        operators = NUM_OPS;
    }
    console.log("field type " + fieldType);
    $.each(operators, function(key, value){
        console.log(key, value);
        var htmlString = '<option value="' + key + '">';
        htmlString += value + '</option>';
        opSelect += htmlString;
    });
    opSelect += "</select>";
    return opSelect;
}

function createFieldInput(fieldId, fieldType){
    var inputType = "text";
    if (fieldType == "Integer" || fieldType == "Float"){
        inputType = "number";
    }
    return '<input class="filter-input" id="input_"'+ fieldId + ' type="' + inputType + '">';
}

function addOpAndInput(sel){
    var selector = $(sel);
    var filterDiv = selector.parent();
    var selectedField = selector.children().filter(":selected");
    var fieldId = selectedField.attr("value");
    var fieldClass = selectedField.attr("class").substring(8);
    var opSelect = createOperatorSelector(fieldId, fieldClass);
    var fieldInput = createFieldInput(fieldId, fieldClass);
    filterDiv.append(opSelect);
    filterDiv.append(fieldInput);
}

function createResultsTable(data){
    var tableHTML = '<table id="qry_result_table" class="table table-responsive table-hover">';
    data = JSON.parse(data);
    var headersComplete = false;
    $.each(data, function(){
        console.log(headersComplete);
        console.log(!headersComplete);
        if (!headersComplete){
            var headersHTML = "<thead><tr>"
        }
        var rowHTML = "<tr>";
        $.each(this, function(key, value){
            if (!headersComplete){
                headersHTML += "<th>" + key + "</th>";
            }
            var val = "";
            if (value != null){
                val = value.toString();
            }
            rowHTML += "<td>" + val + "</td>";
        });
        if (!headersComplete){
            headersHTML += "</tr></thead>";
            tableHTML += headersHTML + "<tbody>";
            headersComplete = true;
        }
        rowHTML += "</tr>";
        tableHTML += rowHTML;
    });
    tableHTML += "</tbody></table>";
    return tableHTML;
}

function removeFilter(button) {
    var filterDiv = $(button).parent();
    filterDiv.remove();
}

function createExportForm(data){
    var formHTML = '<form id="export_data_form">';
    formHTML += '<div class="radio"><label><input type="radio" name="format_options" id="export_csv_radio" value="csv" checked>CSV</label></div>';
    formHTML += '<div class="radio"><label><input type="radio" name="format_options" id="export_json_radio" value="json">JSON</label></div>';
    formHTML += '<div class="radio"><label><input type="radio" name="format_options" id="export_xml_radio" value="xml">XML</label></div>';
    formHTML += '<button type="button" class="btn btn-default" id="export_data" onclick="exportUserQuery();">Export</button>';
    formHTML += '</form>';
    return formHTML;

}

function exportUserQuery(){
    console.log(exportData);
    var format = $('input[name=format_options]:checked', '#export_data_form').val();
    window.location.href = "/nba_stats/download_user_query_results/" + format;
}

$("#add_filter_button").click(function(e){
    var newFilterDiv = $('<div class="col-md6 filter-div"><button type="button" class="btn btn-default remove-filter" onclick="removeFilter(this);">X</button></div>');
    var fieldsToAdd = fields[currentlySelectedModel];
    var newSelect = $(createFieldSelector(fieldsToAdd));
    newFilterDiv.append(newSelect);
    $("#all_filters_div").append(newFilterDiv);
});

$("#send_user_query").click(function(){
    console.log("send user query clicked");
    var model = $("#model").val();
    var filtersDiv = $("#all_filters_div");
    var filters = filtersDiv.find(".filter-div");
    var filtersList = [];
    var fieldsWanted = [];
    var checkedBoxes = $('.field-checkbox:checkbox:checked');
    console.log(checkedBoxes.length);
    $.each(checkedBoxes, function(){
        var idString = $(this).attr("id");
        var modelField = idString.substring(7);
       console.log(modelField);
       fieldsWanted.push(modelField);
    });
    filters.each(function(){
        var div = $(this);
        var fieldSelect = div.find(".field-selector");
        var opSelect = div.find(".op-selector");
        var input = div.find(".filter-input");

        var tableField = fieldSelect.val();
        var operator  = opSelect.val();
        var inputVal = input.val();
        var filterObj = {'table_field': tableField,
                         'operator': operator,
                         'input_val': inputVal};
        filtersList.push(filterObj);
    });
    console.log("About to make AJAX call");
    $.ajax({
        url: '/nba_stats/ajax/send_user_query/',
        type: 'GET',
        data: {
            'primary_model_name': model,
            'filters_list': JSON.stringify(filtersList),
            'fields_wanted': JSON.stringify(fieldsWanted)
        },
        dataType: 'json',
        success: function (data) {
            exportData = data;
            var formHTML = createExportForm(data);
            var tableHTML = createResultsTable(data);
            var resultDivHTML = formHTML + "<br/>" + tableHTML;
            $("#results_div").html(resultDivHTML);
        }
    });
});
