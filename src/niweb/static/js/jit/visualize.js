var labelType, useGradients, nativeTextSupport, animate;

(function() {
  var ua = navigator.userAgent,
      iStuff = ua.match(/iPhone/i) || ua.match(/iPad/i),
      typeOfCanvas = typeof HTMLCanvasElement,
      nativeCanvasSupport = (typeOfCanvas == 'object' || typeOfCanvas == 'function'),
      textSupport = nativeCanvasSupport
        && (typeof document.createElement('canvas').getContext('2d').fillText == 'function');
  //I'm setting this based on the fact that ExCanvas provides text support for IE
  //and that as of today iPhone/iPad current text support is lame
  labelType = (!nativeCanvasSupport || (textSupport && !iStuff))? 'Native' : 'HTML';
  nativeTextSupport = labelType == 'Native';
  useGradients = nativeCanvasSupport;
  animate = !(iStuff || !nativeCanvasSupport);
})();

var Log = {
  elem: false,
  write: function(text){
    if (!this.elem)
      this.elem = document.getElementById('log');
    this.elem.innerHTML = text;
    this.elem.style.left = (500 - this.elem.offsetWidth / 2) + 'px';
  }
};

function loadGraph(fd, json, root_id){
    // load JSON data.
    fd.loadJSON(json);
    // compute positions incrementally and animate.
    fd.computeIncremental({
    iter: 40,
    property: 'end',
    onStep: function(perc){
      Log.write(perc + '% loaded...');
    },
    onComplete: function(){
        Log.write('done');
        fd.animate({
            modes: ['linear'],
            //transition: $jit.Trans.Elastic.easeOut,
            transition: $jit.Trans.Circ.easeInOut,
            duration: 1000
        });
        //Build the right column relations list.
        //This is done by collecting the information (stored in the data property)
        //for all the nodes adjacent to the centered node.
        var node = fd.graph.getNode(root_id);
        //Hardcoded URL...needs to be fixed
        var slug = node.data["node_type"].replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase();
        var html = "<h4><a href=\"/visualize/" + slug + "/" + node.data["node_handle"] + "/\">" + node.name + "</a></h4><b>Relationships:</b>";
        html += "<ul>";
        node.eachAdjacency(function(adj){
            var child = adj.nodeTo;
            if (child.id == node.id) {
                child = adj.nodeFrom;
            }
            if (child.data) {
                var rel = adj.data.relationship;
                html += "<li>" + child.name + " " + "<div class=\"relation\">(relationship: " + rel + ")</div></li>";
            }
        });
        html += "</ul>";
        $jit.id('inner-details').innerHTML = html;
    }
    });
    // end
}

function init(json){
    // init ForceDirected
    var fd = new $jit.ForceDirected({
    //id of the visualization container
    injectInto: 'infovis',
    //'width': 800,
    'width': ($(window).width() / 2),
    'height':600,
    //Enable zooming and panning
    //by scrolling and DnD
    Navigation: {
      enable: true,
      //Enable panning events only if we're dragging the empty
      //canvas (and not a node).
      panning: 'avoid nodes',
      zooming: 10 //zoom speed. higher is more sensible
    },
    // Change node and edge styles such as
    // color and width.
    // These properties are also set per node
    // with dollar prefixed data-properties in the
    // JSON structure.
    Node: {
      overridable: true
    },
    Edge: {
      overridable: true
    },
    //Native canvas text styling
    Label: {
      overridable: true,
      type: labelType, //Native or HTML
      size: 10,
      style: 'bold',
      color: '#000'
    },
    //Add Tips
    Tips: {
      enable: true,
      onShow: function(tip, node) {
        //count connections
        //var count = 0;
        //node.eachAdjacency(function() { count++; });
        //display node info in tooltip
        tip.innerHTML = "<div class=\"tip-title\"><b>" + node.name + "</b></div>"
          + "<div class=\"tip-text\"></div>";
      }
    },
    // Add node events
    Events: {
      enable: true,
      //Change cursor style when hovering a node
      onMouseEnter: function() {
        fd.canvas.getElement().style.cursor = 'move';
      },
      onMouseLeave: function() {
        fd.canvas.getElement().style.cursor = '';
      },
      //Update node positions when dragged
      onDragMove: function(node, eventInfo, e) {
          var pos = eventInfo.getPos();
          node.pos.setc(pos.x, pos.y);
          fd.plot();
      },
      //Implement the same handler for touchscreens
      onTouchMove: function(node, eventInfo, e) {
        $jit.util.event.stop(e); //stop default touchmove event
        this.onDragMove(node, eventInfo, e);
      },
      //Add also a click handler to nodes
      onClick: function(node) {
        if(!node) return;
        // Build the right column relations list.
        // This is done by traversing the clicked node connections.
        //var html = "<h4>" + node.name + "</h4><b> connections:</b><ul><li>",
        //    list = [];
        //node.eachAdjacency(function(adj){
        // list.push(adj.nodeTo.name);
        //});
        //append connections information
        //$jit.id('inner-details').innerHTML = html + list.join("</li><li>") + "</li></ul>";
        var slug = node.data["node_type"].replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase();
        var json_url = "/visualize/" + slug + "/" + node.data["node_handle"] + ".json"
        //var node_url = "/visualize/" + slug + "/" + node.data["node_handle"] + "/"
        $.getJSON(json_url, function(data) {
            if ($('#add_to_graph:checked').val() !== undefined) {
                json = json.concat(data);
                loadGraph(fd, json, node.id);
            } else {
                var new_json = json.concat(data);
                loadGraph(fd, new_json, node.id);
            }
        });
        //window.open(node_url, "_self")
        //$jit.id('inner-details').innerHTML = json_url
      }
    },
    //Number of iterations for the FD algorithm
    iterations: 200,
    //Edge length
    levelDistance: 130,
    // Add text to the labels. This method is only triggered
    // on label creation and only for DOM labels (not native canvas ones).
    onCreateLabel: function(domElement, node){
      domElement.innerHTML = node.name;
      var style = domElement.style;
      style.fontSize = "0.8em";
      style.color = "#ddd";
    },
    // Change node styles when DOM labels are placed
    // or moved.
    onPlaceLabel: function(domElement, node){
      var style = domElement.style;
      var left = parseInt(style.left);
      var top = parseInt(style.top);
      var w = domElement.offsetWidth;
      style.left = (left - w / 2) + 'px';
      style.top = (top + 10) + 'px';
      style.display = '';
    }
    });

    return fd
};
