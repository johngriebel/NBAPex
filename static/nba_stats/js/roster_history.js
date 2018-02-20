var tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);
$('#roster-date-div').datepicker({
    toggleActive: true
});
$('.combobox').combobox();

$("#get_roster_button").click(function(){
    var date = $("#roster-date").val();
    console.log("Date: " + date);
    var team_id = $("#teams").val();
    console.log("Team ID: " + team_id.toString());

    $.ajax({
        url: '/nba_stats/ajax/get_team_roster_history/',
        type: 'GET',
        data: {
            'team_id': team_id,
            'date': date
        },
        dataType: 'json',
        success: function(data){
            var maxWidth = $(window).width() * 0.85;
            console.log("Window width " + maxWidth.toString());
            var svg = d3.select("svg");
            svg.selectAll("circle").remove();
            svg.selectAll("line").remove();

            var circle = svg.selectAll("circle")
                .data(data.nodes, function(d) { return d; });

            circle.enter().append("circle")
                .style("fill", function(d) {return d.color;})
                .attr("cy", function(d) { return d.y_pos * 35 + 30;})
                .attr("cx", function(d){var xPos = (d.x_pos * maxWidth) + 30;
                                            console.log(xPos);
                                            return xPos;})
                .attr("r", function(d) { return d.duration; })
                .on("mouseover", function(d) {
                    tooltip.transition()
                       .duration(200)
                       .style("opacity", .9);
                    tooltip.html(d.player + "<br/>" +
                                 d.team + "<br/>" +
                                 d.acquired_via + "<br/>" +
                                 d.acquisition_date + "<br/>" +
                                 d.end_date)
                   .style("left", (d3.event.pageX + 5) + "px")
                   .style("top", (d3.event.pageY - 28) + "px");
                    })
                .on("mouseout", function(d) {
                    tooltip.transition()
                   .duration(500)
                   .style("opacity", 0);
                });

            var lines = svg.selectAll("line")
                .data(data.links, function(d){return d;});
            lines.enter().append("line").style("stroke", function(d){return d.color})
                         .attr("x1", function(d){var xPos = (d.x1 * maxWidth) + 30;
                                                 console.log(xPos);
                                                 return xPos;})
                         .attr("y1", function(d) { return d.y1 * 35 + 30;})
                         .attr("x2", function(d) {var xPos = (d.x2 * maxWidth) + 30;
                                                 console.log(xPos);
                                                 return xPos;})
                         .attr("y2", function(d) { return d.y2 * 35 + 30;})
                         .attr("stroke-width", 3)
                         .on("mouseover", function(d) {
                             tooltip.transition()
                                .duration(200)
                                .style("opacity", .9);
                             tooltip.html(d.player + "<br/>" +
                                          d.date + "<br/>" +
                                          d.description)
                            .style("left", (d3.event.pageX + 5) + "px")
                            .style("top", (d3.event.pageY - 28) + "px");
                             })
                         .on("mouseout", function(d) {
                             tooltip.transition()
                            .duration(500)
                            .style("opacity", 0);
                         });



            /*var rosterDiv = $("#roster_table_div");
            var tableHtml = "<table id='roster_table' class='table'><thead><tr><th>Player</th><th>Joined</th><th>Left</th></tr></thead>";
            var tbodyHtml = "<tbody>";
            data.forEach(function(entry){
                var rowStr = ("<tr><td>" + entry.player + "</td><td>" +
                entry.acquisition_date + "</td><td>" + entry.end_date + "</td></tr>");
                tbodyHtml += rowStr;
            });
            tbodyHtml += "</tbody>";
            tableHtml += tbodyHtml;
            tableHtml += "</table>";
            rosterDiv.append(tableHtml);*/
        }
    });

});