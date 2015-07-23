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



   var $tables = $("table[data-tablesort]")
   $tables.each(function(){
        var $table = $(this).DataTable(
        {
            "paging": false,
            "order": [],
            "dom": "lrti"
        });
        if($tables.length > 1) {
            $("input[data-tablefilter="+this.id+"]").on('keyup', function(){
                $table.search(this.value).draw();
            });
        }else{
            $("input[data-tablefilter]").on('keyup', function(){
                $table.search(this.value).draw();
            });

        }
    });
});
