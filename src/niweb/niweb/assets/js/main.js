$(document).ready(function() {

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
});
