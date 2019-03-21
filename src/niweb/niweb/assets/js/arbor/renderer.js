(function() {
    Renderer = function(canvas) {
        var canvas = $(canvas).get(0)
        var ctx = canvas.getContext("2d");
        var gfx = arbor.Graphics(canvas);
        var particleSystem = null;
        var clickPath = [];
        var undoStack = [];
        var orgColor = {};

        var that = {
            init: function(system) {
                particleSystem = system;
                if (canvas.width === 300 && canvas.height === 150) { // Size when width and height are not specified?
                    ctx.canvas.width  = window.innerWidth;
                    ctx.canvas.height = window.innerHeight;
                }
                particleSystem.screenSize(canvas.width, canvas.height);
                that.initMouseHandling();
            },
            redraw: function() {
                if (!particleSystem) {
                    return;
                }
                gfx.clear(); // convenience ƒ: clears the whole canvas rect
                // draw the nodes & save their bounds for edge drawing
                var nodeBoxes = {};
                particleSystem.eachNode(function(node, pt) {
                    // node: {mass:#, p:{x,y}, name:"", data:{}}
                    // pt:   {x:#, y:#}  node position in screen coords
                    // determine the box size and round off the coords if we'll be
                    // drawing a text label (awful alignment jitter otherwise...)
                    var label = node.data.label || "";
                    var w = ctx.measureText("" + label).width + 12;
                    if (!("" + label).match(/^[ \t]*$/)) {
                        pt.x = Math.floor(pt.x);
                        pt.y = Math.floor(pt.y);
                    } else {
                        label = null;
                    }

                    // draw a rectangle centered at pt
                    var color = node.data.color ? node.data.color : "rgba(0,0,0,.2)";

                    if (node.data.shape == 'dot') {
                        ctx.fillStyle = color;
                        gfx.oval(pt.x - w / 2, pt.y - w / 2, w, w, {
                            fill: ctx.fillStyle
                        });
                        nodeBoxes[node.name] = [pt.x - w / 2, pt.y - w / 2, w, w];
                    } else {
                        ctx.fillStyle = color;
                        gfx.rect(pt.x - w / 2, pt.y - 11, w, 22, 3, {
                            fill: ctx.fillStyle
                        });
                        nodeBoxes[node.name] = [pt.x - w / 2, pt.y - 11, w, 22];
                    }

                    // draw the text
                    if (label && ctx) {
                        ctx.font = "12px Helvetica";
                        ctx.textAlign = "center";
                        ctx.fillStyle = "white";
                        if (node.data.color == 'none') {
                            ctx.fillStyle = '#333333';
                        }
                        ctx.fillText(label || "", pt.x, pt.y + 5);
                    }
                });

                // draw the edges
                particleSystem.eachEdge(function(edge, pt1, pt2) {
                    // edge: {source:Node, target:Node, length:#, data:{}}
                    // pt1:  {x:#, y:#}  source position in screen coords
                    // pt2:  {x:#, y:#}  target position in screen coords
                    var label = edge.data.label ? $.trim(edge.data.label) : '';
                    var weight = edge.data.weight;
                    var color = edge.data.color;

                    // don't draw links to self
                    if (edge.source.name == edge.target.name) return;

                    // find the start point
                    var tail = intersect_line_box(pt1, pt2, nodeBoxes[edge.source.name]);
                    var head = intersect_line_box(tail, pt2, nodeBoxes[edge.target.name]);

                    ctx.save();
                    ctx.beginPath();
                    ctx.lineWidth = (!isNaN(weight)) ? parseFloat(weight) : 1;
                    if (ctx) {
                        ctx.strokeStyle = (color) ? color : "#cccccc";
                        ctx.fillStyle = 'rgba(0,0,0,0)';
                    }
                    ctx.moveTo(tail.x, tail.y);
                    ctx.lineTo(head.x, head.y);
                    ctx.stroke();
                    ctx.restore();

                    // draw an arrowhead if this is a -> style edge
                    if (edge.data.directed) {
                        ctx.save();
                        // move to the head position of the edge we just drew
                        var wt = !isNaN(weight) ? parseFloat(weight) : 1;
                        var arrowLength = 10 + wt;
                        var arrowWidth = 3 + wt;
                        if (ctx) {
                            ctx.fillStyle = (color) ? color : "#cccccc";
                        }
                        ctx.translate(head.x, head.y);
                        ctx.rotate(Math.atan2(head.y - tail.y, head.x - tail.x));

                        // delete some of the edge that's already there (so the point isn't hidden)
                        ctx.clearRect(-arrowLength / 2, -wt / 2, arrowLength / 2, wt)

                        // draw the chevron
                        ctx.beginPath();
                        ctx.moveTo(-arrowLength, arrowWidth);
                        ctx.lineTo(0, 0);
                        ctx.lineTo(-arrowLength, -arrowWidth);
                        ctx.lineTo(-arrowLength * 0.8, -0);
                        ctx.closePath();
                        ctx.fill();
                        ctx.restore();
                    }
                    // draw the text
                    if (label != '' && ctx) {
                        mid_x = (tail.x + head.x) / 2;
                        mid_y = (tail.y + head.y) / 2;
                        ctx.save();
                        ctx.font = "12px Helvetica";
                        ctx.textAlign = "center";
                        ctx.lineWidth = 4;
                        ctx.strokeStyle = 'rgba(255,255,255,1)';
                        ctx.strokeText(label, mid_x, mid_y);
                        ctx.fillStyle = "black";
                        ctx.fillText(label, mid_x, mid_y);
                        ctx.restore();
                    }
                });
            },
            undoSavePoint: function() {
                var data = {nodes:[]};
                // {id: {"color": "", "label": "", "url": ""}}
                particleSystem.eachNode(function(node, pt) {
                    data.nodes.push(node._id);
                });
                undoStack.push(data);
            },
            undo: function() {
                var data = undoStack.pop();
                if (!data) {
                  console.log("Already at oldest state");
                }else if (data.hasOwnProperty('cleanup')) {
                  particleSystem.graft(data);
                }else{
                  clickPath.pop();
                  particleSystem.prune(function(node, from, to) {
                      try {
                          if(data.nodes.indexOf(node._id) === -1) {
                              return true
                          }
                      } catch(ex) {
                          console.log("No previous state saved.")
                      }
                  });
                }
            },
            cleanup: function() {
              var data = {
                nodes: {},
                edges: {},
                cleanup: true,
              }
              particleSystem.prune(function(node, from, to) {
                // save state
                data.nodes[node.name] = node.data;
                data.edges[node.name] = {};
                from.from.forEach(function(edg) {
                  data.edges[node.name][edg.target.name] = edg.data;
                });
                // Restore colors
                if (orgColor[node.name]) {
                  particleSystem.tweenNode(node, 2, {color: orgColor[node.name]});
                }
                // check if node should be removed
                return ! node.fixed;
              });
              undoStack.push(data);
            },
            initMouseHandling: function() {
                // no-nonsense drag and drop (thanks springy.js)
                selected = null;
                nearest = null;
                var dragged = null;
                // set up a handler object that will initially listen for mousedowns then
                // for moves and mouseups while dragging
                var handler = {
                    dblclicked: function(e) {
                        var pos = $(canvas).offset();
                        _mouseP = arbor.Point(e.pageX - pos.left, e.pageY - pos.top);
                        selected = particleSystem.nearest(_mouseP);
                        clickPath.push(selected.node.name);
                        if (!orgColor[selected.node.name]) {
                          orgColor[selected.node.name] = selected.node.data.color;
                        }
                        if (selected.node !== null) {
                            that.undoSavePoint();
                            $.getJSON('/visualize/' + selected.node.name + '.json', function(json) {
                                particleSystem.graft(json);
                            });
                            for(var i = 0; i < clickPath.length; i += 1) {
                                var node = particleSystem.getNode(clickPath[i]);
                                particleSystem.tweenNode(node, 2, {color:"black"});
                            }
                        }
                    },
                    clicked: function(e) {
                        var pos = $(canvas).offset();
                        _mouseP = arbor.Point(e.pageX - pos.left, e.pageY - pos.top);
                        selected = nearest = dragged = particleSystem.nearest(_mouseP);

                        if (dragged.node !== null) {
                            dragged.node.fixed = true;
                            var nName, nLevel;
                            //n = dragged.node;
                            //$("#debug").append("<li>" + n["name"] + "</li>")
                            //console.log( dragged.node.p.x, dragged.node.p.y )
                        }
                        data = selected.node.data;
                        $("#clicked_node").html("Go to <a href=\"" + data["url"] + "\">" + data["label"] + "</a>.");
                        $(canvas).bind('mousemove', handler.dragged);
                        $(window).bind('mouseup', handler.dropped);
                        return false
                    },
                    dragged: function(e) {
                        var old_nearest = nearest && nearest.node._id;
                        var pos = $(canvas).offset();
                        var s = arbor.Point(e.pageX - pos.left, e.pageY - pos.top);

                        if (!nearest) return;
                        if (dragged !== null && dragged.node !== null) {
                            var p = particleSystem.fromScreen(s);
                            dragged.node.p = p;
                        }

                        return false
                    },

                    dropped: function(e) {
                        if (dragged === null || dragged.node === undefined) return;
                        if (dragged.node !== null) dragged.node.fixed = true;
                        dragged.node.tempMass = 1000;
                        dragged = null;
                        selected = null;
                        $(canvas).unbind('mousemove', handler.dragged);
                        $(window).unbind('mouseup', handler.dropped);
                        _mouseP = null;
                        return false;
                    }
                };
                $(canvas).mousedown(handler.clicked);
                $(canvas).bind('dblclick', handler.dblclicked);
            }
        };

        // helpers for figuring out where to draw arrows (thanks springy.js)
        var intersect_line_line = function(p1, p2, p3, p4) {
                var denom = ((p4.y - p3.y) * (p2.x - p1.x) - (p4.x - p3.x) * (p2.y - p1.y));
                if (denom === 0) return false // lines are parallel
                var ua = ((p4.x - p3.x) * (p1.y - p3.y) - (p4.y - p3.y) * (p1.x - p3.x)) / denom;
                var ub = ((p2.x - p1.x) * (p1.y - p3.y) - (p2.y - p1.y) * (p1.x - p3.x)) / denom;

                if (ua < 0 || ua > 1 || ub < 0 || ub > 1) return false
                return arbor.Point(p1.x + ua * (p2.x - p1.x), p1.y + ua * (p2.y - p1.y));
            };

        var intersect_line_box = function(p1, p2, boxTuple) {
                var p3 = {
                    x: boxTuple[0],
                    y: boxTuple[1]
                },
                    w = boxTuple[2],
                    h = boxTuple[3]

                var tl = {
                    x: p3.x,
                    y: p3.y
                };
                var tr = {
                    x: p3.x + w,
                    y: p3.y
                };
                var bl = {
                    x: p3.x,
                    y: p3.y + h
                };
                var br = {
                    x: p3.x + w,
                    y: p3.y + h
                };

                return intersect_line_line(p1, p2, tl, tr) || intersect_line_line(p1, p2, tr, br) || intersect_line_line(p1, p2, br, bl) || intersect_line_line(p1, p2, bl, tl) || false
            };

        return that
    }
})();
