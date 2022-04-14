$(document).ready(function() {
    setInterval(function() {
        $.get("/live_price", function(entries) {
        var color
        if (parseInt(entries["user"], 10) > parseInt(entries["price"], 10)){color="color:red"}else{color="color:green"}
        console.log(entries);
        console.log(entries["Symbol"]);
        var text = `<table class="table table-striped">
  <thead>
    <tr>

      <th scope="col">COIN</th>
      <th scope="col">MARKET PRICE</th>
      <th scope="col">USER PRICE</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b>${entries["Symbol"]}</b></td>
      <td><b>${entries["price"]}</b></td>
      <td style=${color}><b>${entries["user"]}</b></td>
    </tr>
   </tbody>
   </table>`
        document.getElementById("log").innerHTML = text;
        });
    }, 1000);
});

