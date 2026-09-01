/* =========================================================================
   Calculadora de Distrato — lógica de cálculo da cláusula 11.2
   =========================================================================
   Regra de negócio (replicada da planilha de referência):

   1. término da fidelidade = data da instalação + N meses de fidelidade
   2. Se o cancelamento ocorrer NA ou APÓS essa data -> não há multa.
   3. Meses cheios faltantes = todos os meses civis completos entre o mês
      seguinte ao do cancelamento e o mês anterior ao do término da
      fidelidade (inclusive), agrupados por ano para exibição.
   4. Mês parcial (o mês do término da fidelidade) é cobrado
      proporcionalmente aos dias corridos daquele mês:
        - caso geral: do dia 1 até o dia do término da fidelidade
        - caso especial: se o cancelamento cair no MESMO mês do término
          da fidelidade, os dias parciais vão do dia do cancelamento até
          o dia do término (nunca do dia 1)
   5. soma das mensalidades faltantes = soma dos meses cheios + valor do
      mês parcial
   6. valor da quebra contratual = soma das mensalidades faltantes x
      percentual de multa da cláusula 11.2
   ========================================================================= */

const MESES_PT = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
];

function parseDateInput(value) {
  // value vem de <input type="date"> no formato YYYY-MM-DD
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function addMonths(date, months) {
  const d = new Date(date.getFullYear(), date.getMonth() + months, date.getDate());
  return d;
}

function daysInMonth(year, monthIndex0) {
  // monthIndex0: 0 = janeiro
  return new Date(year, monthIndex0 + 1, 0).getDate();
}

function formatBRL(value) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDatePt(date) {
  return date.toLocaleDateString("pt-BR");
}

/**
 * Executa o cálculo completo da quebra contratual.
 * @returns {object} resultado estruturado, pronto para exibir e imprimir em PDF
 */
function calcularDistrato({ dataInstalacao, fidelidadeMeses, dataCancelamento, mensalidade, percentualMulta }) {
  const terminoFidelidade = addMonths(dataInstalacao, fidelidadeMeses);

  if (dataCancelamento >= terminoFidelidade) {
    return {
      semMulta: true,
      terminoFidelidade
    };
  }

  const mesmoMes =
    dataCancelamento.getFullYear() === terminoFidelidade.getFullYear() &&
    dataCancelamento.getMonth() === terminoFidelidade.getMonth();

  // --- meses cheios ---
  const porAno = []; // [{ano, meses}]
  let totalMesesCheios = 0;

  if (!mesmoMes) {
    let cursor = new Date(dataCancelamento.getFullYear(), dataCancelamento.getMonth() + 1, 1);
    const limite = new Date(terminoFidelidade.getFullYear(), terminoFidelidade.getMonth(), 1); // exclusivo

    const contagemPorAno = {};
    while (cursor < limite) {
      const ano = cursor.getFullYear();
      contagemPorAno[ano] = (contagemPorAno[ano] || 0) + 1;
      totalMesesCheios++;
      cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    }
    Object.keys(contagemPorAno).sort().forEach((ano) => {
      porAno.push({ ano: Number(ano), meses: contagemPorAno[ano] });
    });
  }

  const valorMesesCheios = totalMesesCheios * mensalidade;

  // --- mês parcial (mês do término da fidelidade) ---
  const totalDiasMes = daysInMonth(terminoFidelidade.getFullYear(), terminoFidelidade.getMonth());
  let diasParciais;
  if (mesmoMes) {
    diasParciais = Math.max(0, terminoFidelidade.getDate() - dataCancelamento.getDate());
  } else {
    diasParciais = terminoFidelidade.getDate();
  }
  const valorParcial = (diasParciais / totalDiasMes) * mensalidade;

  const somaFaltantes = valorMesesCheios + valorParcial;
  const valorQuebra = somaFaltantes * (percentualMulta / 100);

  return {
    semMulta: false,
    terminoFidelidade,
    porAno,
    totalMesesCheios,
    valorMesesCheios,
    totalDiasMes,
    diasParciais,
    valorParcial,
    somaFaltantes,
    percentualMulta,
    valorQuebra,
    mesReferenciaParcial: MESES_PT[terminoFidelidade.getMonth()]
  };
}

/* =========================================================================
   Camada de UI
   ========================================================================= */

const form = document.getElementById("form-distrato");
const formError = document.getElementById("form-error");
const resultCard = document.getElementById("result-card");
const resultEmpty = document.getElementById("result-empty");
const resultBody = document.getElementById("result-body");
const breakdownBody = document.getElementById("breakdown-body");
const totalValorEl = document.getElementById("total-valor");
const btnPdf = document.getElementById("btn-pdf");

let ultimoResultado = null;
let ultimosDadosContrato = null;

form.addEventListener("submit", (event) => {
  event.preventDefault();
  formError.hidden = true;

  const dataInstalacaoRaw = document.getElementById("dataInstalacao").value;
  const dataCancelamentoRaw = document.getElementById("dataCancelamento").value;
  const fidelidadeMeses = Number(document.getElementById("fidelidadeMeses").value);
  const mensalidade = Number(document.getElementById("mensalidade").value);
  const percentualMulta = Number(document.getElementById("percentualMulta").value);

  if (!dataInstalacaoRaw || !dataCancelamentoRaw || !fidelidadeMeses || !mensalidade) {
    formError.textContent = "Preencha todos os campos obrigatórios (*) antes de calcular.";
    formError.hidden = false;
    return;
  }

  const dataInstalacao = parseDateInput(dataInstalacaoRaw);
  const dataCancelamento = parseDateInput(dataCancelamentoRaw);

  if (dataCancelamento < dataInstalacao) {
    formError.textContent = "A data de cancelamento não pode ser anterior à data de instalação.";
    formError.hidden = false;
    return;
  }

  const resultado = calcularDistrato({
    dataInstalacao,
    fidelidadeMeses,
    dataCancelamento,
    mensalidade,
    percentualMulta
  });

  ultimoResultado = resultado;
  ultimosDadosContrato = {
    nome: document.getElementById("nome").value.trim(),
    contrato: document.getElementById("contrato").value.trim(),
    dataInstalacao,
    dataCancelamento,
    fidelidadeMeses,
    mensalidade,
    percentualMulta
  };

  renderResultado(resultado);
});

form.addEventListener("reset", () => {
  resultCard.hidden = true;
  formError.hidden = true;
  ultimoResultado = null;
  ultimosDadosContrato = null;
});

function renderResultado(r) {
  resultCard.hidden = false;
  breakdownBody.innerHTML = "";

  if (r.semMulta) {
    resultBody.hidden = true;
    resultEmpty.hidden = false;
    resultEmpty.textContent =
      `O período de fidelidade termina em ${formatDatePt(r.terminoFidelidade)}, ` +
      `data igual ou anterior ao cancelamento informado. Não há multa da cláusula 11.2 a ser aplicada.`;
    return;
  }

  resultEmpty.hidden = true;
  resultBody.hidden = false;

  addRow(`Término do período de fidelidade`, formatDatePt(r.terminoFidelidade));

  r.porAno.forEach((item) => {
    addRow(`Meses completos faltantes em ${item.ano}`, `${item.meses} mês${item.meses > 1 ? "es" : ""}`);
  });

  if (r.totalMesesCheios > 0) {
    addRow(`Valor dos meses completos`, formatBRL(r.valorMesesCheios));
  }

  addRow(
    `Mês parcial (${r.mesReferenciaParcial})`,
    `${r.diasParciais} dia${r.diasParciais !== 1 ? "s" : ""} de ${r.totalDiasMes} — ${formatBRL(r.valorParcial)}`
  );

  addRow(`Soma das mensalidades faltantes`, formatBRL(r.somaFaltantes), true);
  addRow(`% de multa da cláusula 11.2`, `${r.percentualMulta.toLocaleString("pt-BR")}%`);

  totalValorEl.textContent = formatBRL(r.valorQuebra);
}

function addRow(label, value, subtotal = false) {
  const tr = document.createElement("tr");
  if (subtotal) tr.className = "subtotal";
  const tdLabel = document.createElement("td");
  tdLabel.textContent = label;
  const tdValue = document.createElement("td");
  tdValue.textContent = value;
  tr.appendChild(tdLabel);
  tr.appendChild(tdValue);
  breakdownBody.appendChild(tr);
}

/* =========================================================================
   Geração de PDF
   ========================================================================= */

btnPdf.addEventListener("click", () => {
  if (!ultimoResultado || ultimoResultado.semMulta) return;

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const r = ultimoResultado;
  const d = ultimosDadosContrato;

  const marginX = 56;
  let y = 64;

  doc.setFont("times", "normal");
  doc.setFontSize(18);
  doc.text("Cálculo de Distrato — Cláusula 11.2", marginX, y);

  y += 30;
  doc.setFontSize(11);
  doc.setTextColor(90, 90, 90);
  doc.text(`Emitido em ${formatDatePt(new Date())}`, marginX, y);
  doc.setTextColor(0, 0, 0);

  y += 30;
  doc.setDrawColor(200, 200, 200);
  doc.line(marginX, y, 539, y);
  y += 24;

  doc.setFontSize(12);
  if (d.nome) { doc.text(`Titular: ${d.nome}`, marginX, y); y += 18; }
  if (d.contrato) { doc.text(`Contrato nº: ${d.contrato}`, marginX, y); y += 18; }
  doc.text(`Data da instalação: ${formatDatePt(d.dataInstalacao)}`, marginX, y); y += 18;
  doc.text(`Fidelidade contratada: ${d.fidelidadeMeses} meses`, marginX, y); y += 18;
  doc.text(`Término do período de fidelidade: ${formatDatePt(r.terminoFidelidade)}`, marginX, y); y += 18;
  doc.text(`Data da solicitação de cancelamento: ${formatDatePt(d.dataCancelamento)}`, marginX, y); y += 18;
  doc.text(`Valor da mensalidade utilizada no cálculo: ${formatBRL(d.mensalidade)}`, marginX, y); y += 30;

  doc.setDrawColor(200, 200, 200);
  doc.line(marginX, y, 539, y);
  y += 24;

  doc.setFontSize(13);
  doc.text("Apuração", marginX, y);
  y += 22;
  doc.setFontSize(11);

  const linhas = [];
  r.porAno.forEach((item) => {
    linhas.push([`Meses completos faltantes em ${item.ano}`, `${item.meses} mês${item.meses > 1 ? "es" : ""}`]);
  });
  if (r.totalMesesCheios > 0) {
    linhas.push(["Valor dos meses completos", formatBRL(r.valorMesesCheios)]);
  }
  linhas.push([
    `Mês parcial (${r.mesReferenciaParcial})`,
    `${r.diasParciais} de ${r.totalDiasMes} dias — ${formatBRL(r.valorParcial)}`
  ]);
  linhas.push(["Soma das mensalidades faltantes", formatBRL(r.somaFaltantes)]);
  linhas.push(["% de multa da cláusula 11.2", `${r.percentualMulta.toLocaleString("pt-BR")}%`]);

  linhas.forEach(([label, value]) => {
    doc.text(label, marginX, y);
    doc.text(value, 539, y, { align: "right" });
    y += 20;
  });

  y += 14;
  doc.setDrawColor(0, 0, 0);
  doc.setLineWidth(1);
  doc.line(marginX, y, 539, y);
  y += 26;

  doc.setFontSize(13);
  doc.text("Valor da quebra contratual", marginX, y);
  doc.setFontSize(18);
  doc.text(formatBRL(r.valorQuebra), 539, y, { align: "right" });

  y += 50;
  doc.setFontSize(9);
  doc.setTextColor(120, 120, 120);
  doc.text(
    "Documento gerado automaticamente para fins de apoio ao cálculo. Confirme os dados contratuais antes do envio ao cliente.",
    marginX,
    y,
    { maxWidth: 483 }
  );

  const nomeArquivo = d.contrato
    ? `distrato-${d.contrato}.pdf`
    : `distrato-${new Date().toISOString().slice(0, 10)}.pdf`;

  doc.save(nomeArquivo);
});
