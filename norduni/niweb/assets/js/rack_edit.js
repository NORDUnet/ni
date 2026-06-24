
(function () {
  let $placement_edit = document.querySelectorAll("[data-placement-edit]");
  let order = Array.from($placement_edit);
  
  function movePosition($elm) {
    let pos = $elm.value;
      let $block = $elm.parentNode.parentNode;
      let $next = order.find($candidate => {
        return $elm != $candidate && parseInt($candidate.value) < pos;
      });
  
      if ($next != $elm) {
        if ($next) {
          $next = $next.parentNode.parentNode;
        }else {
          $next = order[order.length -1].parentNode.parentNode.nextSibling;
        }
  
        let $super_block = $block.parentNode;
        $super_block.removeChild($block);
        $super_block.insertBefore($block, $next);
        order = Array.from(document.querySelectorAll("[data-placement-edit]"));
        $elm.dataset.positionPrev = pos;
      }
  }
  
  function postPosition(handle_id, pos) {
    return new Promise((resolve, reject) => {
      let xhr = new XMLHttpRequest();
      let csrf = document.querySelector("[name=csrfmiddlewaretoken]").value;
  
      xhr.open("POST", 'node/'+handle_id+'/position/'+pos, true);
      xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
      xhr.setRequestHeader("X-CSRFToken", csrf);
  
      xhr.onload = () => {
        if (xhr.status == 200) {
           resolve(JSON.parse(xhr.responseText));
        }else{
          reject(xhr.statusText);
        }
      }
      xhr.onerror = () => {reject(xhr.statusText);}
      xhr.send();
    });
  }
  
  
  $placement_edit.forEach($elm => {
    $elm.dataset.positionPrev = $elm.value;
    $elm.addEventListener("blur", e => {
      let pos = parseInt(e.target.value);
      let prev = parseInt(e.target.dataset.positionPrev);
      let handle_id = e.target.dataset.placementEdit;
      if (isNaN(pos) || prev == pos) {
        return;
      }
      // Try to update position
      postPosition(handle_id, pos).then((resp) => {
        if (resp['success']) {
          movePosition(e.target);
        }else{
          console.log("Could not update", handle_id, "position");
        }
      }).catch((error) => {console.log("Unable to update node position: "+error)});
    });
  });
})();
