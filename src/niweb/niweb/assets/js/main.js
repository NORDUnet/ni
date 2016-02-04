$(document).ready(function() {

  // Handle async loading (e.g. og history)
  function async_load(url, trigger,target) {
    var $trigger = $(trigger);
    $trigger.one("click", function(){
      $.get(url, function(data){
        $(target).html(data);
      }, "html");
    });
  }

  $("[data-async-load]").each(function(idx){
    var url = $(this).data("async-load");
    var target = $(this).data("async-load-target");
    async_load(url,this,target);
  });



  // Utility
  var debounce = function(fn, _delay) {
    var last_call;
    var delay = _delay || 200;
    return function(args) {
      var that = this;
      if (last_call) {
        clearTimeout(last_call)
      }
      last_call = setTimeout(function(){
        fn.apply(that, args);
      }, delay);
    }
  }

  // Handle datatables (sorting, searching)
   var $tables = $("table[data-tablesort]")
   $tables.each(function(){
        var $table = $(this).DataTable(
        {
            "paging": false,
            "order": [],
            "dom": "lrti",
            columnDefs: [
                   { type: 'natural', targets: '_all'}
            ]
        });
        if($tables.length > 1) {
            $("input[data-tablefilter="+this.id+"]").on('keyup', 
              debounce(function(){
                $table.search(this.value).draw();
            }));
        }else{
            $("input[data-tablefilter]").on('keyup', debounce(function(){
                $table.search(this.value).draw();
            }));

        }
    });


  // Dynamic ports
    var insertAfter = function insertBefore(elm, existing) {
      existing.parentNode.insertBefore(elm, existing.nextSibling);
    }

    //Change to generic add extra?
    var createAddPorts = function createAddPorts($dynPort) {
      var $panel = document.createElement("div");
      $panel.classList.add("control-group");

      var $add = document.createElement("button");
      $add.classList.add("btn","btn-primary");
      $add.textContent = "Add port";
      $add.onclick = function(e) {
        e.preventDefault();
        //Closure access to $panel
        var $org = $panel.previousSibling;
        var $copy = $org.cloneNode(true);
        $copy.removeAttribute("data-dynamic-ports");
        
        if ($copy.hasChildNodes()) {
          var child;
          for (var i=0; i< $copy.children.length; i++) {
            child = $copy.children[i];
            child.removeAttribute("id");
            if ($org.children[i].selectedIndex) {
              child.selectedIndex = $org.children[i].selectedIndex;
            }
          }
        }

        var $del = document.createElement("a");
        $del.textContent = "Remove";
        $del.href="#remove";
        $del.onclick = function(e) {
          e.preventDefault();
          this.parentNode.parentNode.removeChild(this.parentNode);
        }
        //Remove old remove link - since clone does not copy it
        var $old = $copy.querySelector("[href='#remove']")
        if ($old) {
          $old.parentNode.removeChild($old);
        }
        $copy.appendChild($del);
        insertAfter($copy, $org);
        //focus that input
        toFocus = $copy.querySelector("input:first-child");
        toFocus.focus();
        lastchar = toFocus.value.length * 2;
        toFocus.setSelectionRange(lastchar, lastchar);
      }

      

      //Add button to dom
      $panel.appendChild($add);
      insertAfter($panel, $dynPort)
    }

    //Add to pages where needed
    var $dynPorts = document.querySelectorAll("[data-dynamic-ports]");
    //So nodeList is not an array :(
    for (var i=0; i < $dynPorts.length; i++) {
      createAddPorts($dynPorts[i]);
    }


    /****
     * Dismiss/remove button
     ****/

    var $toRemove = document.querySelectorAll("[data-removable]");

    var $removeTemplate = document.createElement("a");
    $removeTemplate.textContent = "x";
    $removeTemplate.href="#remove"
    $removeTemplate.classList.add("removeBtn");

    for (var i=0; i < $toRemove.length; i++) {
      var $target = $toRemove[i];

      var $btn = $removeTemplate.cloneNode(true);
      $btn.onclick = function(e) {
        e.preventDefault();
        var $parent = e.target.parentNode;
        $parent.parentNode.removeChild($parent)
      }
      $target.appendChild($btn);
    }
});
