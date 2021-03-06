/*!
 *
 * Derived from:
 * jQuery jCombo Plugin
 * Carlos De Oliveira
 * cardeol@gmail.com
 * Latest Release: Sep 2011
 *
 * Mar 2012
 * Changes made by lundberg@nordu.net.
 *
 */
(function($) {
    $.fn.jCombo = function(url, user_options) {
        var default_options = {
                parent: "",
                selected_value : "0",
                parent_value : "",
                initial_text: "-- Please Select --",
                end_value_field: ""
        };
        $(this).on('change', function() {
            if(obj.val()!="0") {
                $(user_options.end_value_field).val(obj.val());
            }
        });
        var user_options = $.extend(default_options, user_options);
        var obj = $(this);
        $(this).hide();
        if(user_options.parent!="") {
            var $parent = $(user_options.parent);
            $parent.removeAttr("disabled");
            $parent.bind('change',  function(e) {
                obj.attr("disabled", true);
                if($(this).val()!="0" && $(this).val()!="") {
                    obj.removeAttr("disabled");
                    obj.show();
                }
                __fill(obj,
                       url,
                       $(this).val(),
                       user_options.initial_text,
                       user_options.selected_value);
            });
        }
        if (user_options.parent_value!="") {
            __fill(obj,url,user_options.parent_value,user_options.initial_text,user_options.selected_value);
        }
        function __fill($obj,$url,$id,$initext,$inival) {
            $.ajax({
                type: "GET",
                dataType:"json",
                url: $url.replace("{id}", $id),
                success: function(j){
                    var choices = '';
                    if (j.length == 0) {
                        choices += '<option value="0">' + "-- Empty List --" + '</option>';
                        $obj.html(choices);
                        $obj.attr("disabled", true);
                    } else {
                        if($initext!="" && $initext!=null) {
                            choices += '<option value="0">' + $initext + '</option>';
                            $obj.removeAttr("disabled");
                        }
                        for (var i = 0; i < j.length; i++) {
                            selected = (j[i][0]==$inival)?' selected="selected"':'';
                            c = j[i];
                            choices += '<option value="' + c[0] + '"' +
                            selected + '>' + c[1] +
                            '</option>';
                        }
                        $obj.html(choices);
                    }
                    $obj.trigger("change");
                }
            });
        }
    }
})(jQuery);
