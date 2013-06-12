<script language="javascript" type="text/javascript" src="{{ STATIC_URL }}js/jquery/jquery.jeditable.mini.js"></script>
<script language="javascript" type="text/javascript" src="{{ STATIC_URL }}js/jquery/jquery.json-2.4.min.js"></script>
<script>
        // Editable list
        function makeEditable()
        {
            $('.editable').editable(function(value, settings)
            {
                /* Debug

                 console.log(this);
                 console.log(value);
                 console.log(settings);
                 */
                return(value);
            });
        }
        function makeDelable()
        {
            $('a.delete').click(function(e)
            {
                e.preventDefault();
                $(this).parent().parent().remove();
                saveList();
            });
        }
        function loadList()
        {
            var list = $.parseJSON($('#id_responsible_persons').val());
            $(list).each(function(i, item) {
                addItem(item);
            });
        }
        function saveList()
        {
            var list = [];
            $('.editable').each(function(i, item) {
                list.push($(item).html());
            });
            $('#id_responsible_persons').val($.toJSON(list));

        }
        function addItem(itemName)
        {
            $("#responsible").append('<div class="row"><div class="span2"><span class="editable">' + itemName + '</span></div><div class="span1"><a class="btn btn-mini delete"><i class="icon-minus"></i></a></div></div>');
            makeEditable();
            makeDelable();
        }
        loadList();
        makeEditable();
        makeDelable();
        // Disable Enter key in the text input so to now submit form when trying to add item
        $('input[name=addresp]').keypress(function (e) {
            var code = (e.keyCode ? e.keyCode : e.which);
            if (code === 13) {
                var item = $('input[name=addresp]');
                addItem(item.val());
                item.val('');
                saveList();
            }
            return (code != 13);
        });
        $('a#add').click(function(e)
        {
            e.preventDefault();
            var item = $('input[name=addresp]');
            addItem(item.val());
            item.val('');
            saveList();
        });
</script>

<div id="responsible"></div>
<br><br>
<div class="input-append">
    <input class="input-large" type="text" name="addresp" placeholder="Responsible"/>
    <a id="add" class="btn" type="button"><i class="icon-plus"></i></a>
</div>
<span class="help-block">{{ form.responsible_persons.help_text }}</span>

