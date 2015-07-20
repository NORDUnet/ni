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



  var $table = $("table[data-tablesort]").DataTable(
        {
            "paging": false,
            "order": [],
            "dom": "lrti"
        });
  if ($table) {
    $("input[data-tablefilter]").on('keyup', function(){
        $table.search(this.value).draw();
    });
  }
});
