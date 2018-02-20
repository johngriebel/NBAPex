$('.combobox').combobox();
var slider_html = "<input id='season-slider' type='text' class='slider span2' value='' data-slider-min='2001' data-slider-max='2016' data-slider-step='0.1' data-slider-value='2001' data-slider-orientation='horizontal' data-slider-selection='before' data-slider-tooltip='show'><br>";
/*
 * value accessor - returns the value to encode for a given data object.
 * scale - maps value to a visual display encoding, such as a pixel position.
 * map function - maps from data value to display value
 * axis - sets up axis
 */
var margin = {top: 20, right: 20, bottom: 30, left: 40},
              width = 500 - margin.left - margin.right,
              height = 940 - margin.top - margin.bottom;


// setup x
console.log("defined margin");
var xValue = function(d) { return d.loc_x;}, // data -> value
    xScale = d3.scaleLinear().range([0, width]), // value -> display
    xMap = function(d) { return xScale(xValue(d));}, // data -> display
    xAxis = d3.axisBottom().scale(xScale);
console.log("finished set up x");
// setup y
var yValue = function(d) { return d.loc_y;}, // data -> value
    yScale = d3.scaleLinear().range([height, 0]), // value -> display
    yMap = function(d) { return yScale(yValue(d));}, // data -> display
    yAxis = d3.axisLeft().scale(yScale);
console.log("finished set up y");
// setup fill color
var color = d3.scaleOrdinal(d3.schemeCategory10);

// add the graph canvas to the body of the webpage
var svg = d3.select("body").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

// add the tooltip area to the webpage
var tooltip = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

var x = d3.scaleBand().rangeRound([0, width]).padding(0.1),
    y = d3.scaleLinear().rangeRound([height, 0]);

var g = svg.append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

$("#fetch_data_button").click(function () {
    // eventually will be fetched from a dropdown/search or something
    var player_id = $("#players").val();
    var season_id = $("#seasons").val();
    $.ajax({
        url: '/nba_stats/ajax/get_player_shot_chart_data/',
        type: 'GET',
        data: {
            'player_id': player_id,
            'season_id': season_id
        },
        dataType: 'json',
        success: function(data){
            var xMin = d3.min(data, xValue);
            var xMax = d3.max(data, xValue);
            var yMin = d3.min(data, yValue);
            var yMax = d3.max(data, yValue);
            console.log("x min" + xMin.toString());
            console.log("x max" + xMax.toString());
            console.log("y min" + yMin.toString());
            console.log("y max" + yMax.toString());

              xScale.domain([-250, 250]);
              yScale.domain([-50, 890]);

              // x-axis
              svg.append("g")
                  .attr("class", "x axis")
                  .attr("transform", "translate(0," + height + ")")
                  .call(xAxis)
                .append("text")
                  .attr("class", "label")
                  .attr("x", width)
                  .attr("y", -6)
                  .style("text-anchor", "end")
                  .text("X");

              // y-axis
              svg.append("g")
                  .attr("class", "y axis")
                  .call(yAxis)
                .append("text")
                  .attr("class", "label")
                  .attr("transform", "rotate(-90)")
                  .attr("y", 6)
                  .attr("dy", ".71em")
                  .style("text-anchor", "end")
                  .text("Y");


              // draw dots
              svg.selectAll(".dot")
                  .data(data)
                .enter().append("circle")
                  .attr("class", function(shot_detail) {return "dot year-" + shot_detail.game_date.substring(0,4)})
                  .attr("r", 3.5)
                  .attr("cx", xMap)
                  .attr("cy", yMap).style("opacity", 0)
                  .attr("fill", function(shot_detail){
                                                        if (shot_detail.shot_made_flag){
                                                            return "#009933";
                                                        }
                                                        else {
                                                            return "#ff0000";
                                                        }
                                                    })
                  .on("mouseover", function(d) {
                      tooltip.transition()
                           .duration(200)
                           .style("opacity", .9);
                      tooltip.html(d.shot_made_flag + "<br/> (" + xValue(d)
                        + ", " + yValue(d) + ")")
                           .style("left", (d3.event.pageX + 5) + "px")
                           .style("top", (d3.event.pageY - 28) + "px");
                  })
                  .on("mouseout", function(d) {
                      tooltip.transition()
                           .duration(500)
                           .style("opacity", 0);
                  });
              d3.selectAll(".dot").attr("data-year", function(d) { return d.game_date.substring(0,4) });
              $("#body").append(slider_html);
              $('#season-slider').slider().on("slide", function(e){
                    var slider = $("#season-slider");
                    var sliderVals = slider.val().toString().split(".");
                    console.log("sliderVals" + sliderVals.toString());
                    var year = sliderVals[0];
                    var opac = 0.0;
                    if (sliderVals.length == 2){
                        opac = "0." + sliderVals[1];
                        opac = parseFloat(opac);
                    }
                    var dots = svg.selectAll(".dot");
                    console.log(year);
                    console.log(opac);
                    svg.selectAll(".dot").style("opacity", 0);
                    var thisYearDots = svg.selectAll(".year-" + year);
                    var nextYear = (parseInt(year) + 1).toString();
                    var nextYearDots = svg.selectAll(".year-" + nextYear);
                    if (typeof thisYearDots !== 'undefined') {
                        thisYearDots.style("opacity", 1 - opac);
                        nextYearDots.style("opacity", opac);
                        console.log("set the opacity");
                    }
              });
        }
    });
});