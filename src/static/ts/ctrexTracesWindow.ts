class CounterexTracesWindow extends BaseTracesWindow {
  firstNegRow: any = null;

  addData(data: dataT): void {
    // For now support only positive/negative counterexamples
    assert (data[1].length === 0);
    let classes = [ "true", "false", "inductive" ];
    let lbls = [];

    for (let i in data[0]) {
      let data_id = this.data[0].length;
      let col_id = 0;
      let curRow = $(
          "<tr class='traces-row' id='" + data_id + "'>" +
            data[0][i].map(el =>
              "<td class='" + classes[0]  + "' id='" + data_id + "_" + col_id++ + "'>" + el + "</td>").join("") +
            "<td class='temp_expr_eval'>&nbsp</td>" +
          "</tr>");
      this.data[0].push(data[0][i]);
      if (this.firstNegRow) {
        $(this.firstNegRow).insertBefore(curRow);
      } else {
        $("table#lvl_table tbody").append(curRow);
      }
      this.dataMap[0][data_id] = curRow;
    }

    let directCtrex : any[] = data[2];
    for (let i in directCtrex) {
      let data_id = this.data[2].length;
      let col_id = 0;
      console.log(directCtrex[i])
      let curRow = $(
          "<tr class='traces-row' id='neg_" + data_id + "'>" +
            directCtrex[i].map(el =>
              "<td class='" + classes[1]  + "' id='" + data_id + "_" + col_id++ + "'>" + el + "</td>").join("") +
            "<td class='temp_expr_eval'>&nbsp</td>" +
          "</tr>");
      if (this.firstNegRow == null) {
        this.firstNegRow = curRow;
      }
      this.data[2].push(directCtrex[i]);
      $("table#lvl_table tbody").append(curRow);
      this.dataMap[2][data_id] = curRow;
    }
    das.reflowAll();
  }

  clearNegRows(): void {
    this.firstNegRow = null;
    for (let i in this.dataMap[2]) {
      $(this.dataMap[2][i]).remove();
    }
    this.dataMap[2] = [];
    this.data[2] = [];
  }

  evalResult(res: resT): void {
    if (res.hasOwnProperty("data")) {
      let resD = <resDataT>res;

      for (let type in resD.data) {
        for (let i in resD.data[type]) {
          let datum = resD.data[type][i];
          let row = this.dataMap[type][i];
          this.setResultCell(row, datum);
        }
      }
    } else if (res.hasOwnProperty("clear")) {
      $(".temp_expr_eval").html("");
      $(".traces-row td.temp_expr_eval").removeClass("true");
      $(".traces-row td.temp_expr_eval").removeClass("false");
    }
    das.reflowAll();
  }

  setVariables(lvl: Level): void {
    this.clearNegRows();
    super.setVariables(lvl);
  }
}

