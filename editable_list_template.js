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
            $("#responsible").append('<div class="row"><div class="span2"><span class="editable">' + itemName + '</span></div><div class="span1"><a href="" class="delete label label-important">Delete</a></div></div>');
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
<div class="row">
<div class="span2">
    <input class="span2" type="text" name="addresp" />
</div>
<div class="span1">
    <a id="add" class="label label-success" href="">Add</a>
</div>
</div>
<span class="help-block">{{ form.responsible_persons.help_text }}</span>

