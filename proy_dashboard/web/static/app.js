/*
 * app.js — utilidades de presentación (sin lógica de negocio).
 *
 * Las plantillas Jinja2 inyectan las `option` JSON; este módulo solo dibuja con
 * ECharts y re-inicializa los gráficos tras un swap de HTMX (ECharts no se
 * auto-monta). Ver ROADMAP §14.
 */

(function () {
  "use strict";

  const charts = {};
  const observers = {};

  /**
   * Reajusta el gráfico cuando cambia el tamaño de su contenedor.
   *
   * ECharts mide el contenedor al inicializar; tras un swap de HTMX el layout
   * aún no está asentado y queda un canvas angosto que nunca se corrige (la
   * recarga periódica tampoco dispara `window.resize`). Un ResizeObserver
   * reajusta en cuanto la celda alcanza su ancho real.
   */
  function watchResize(elId, el) {
    if (typeof ResizeObserver === "undefined") {
      requestAnimationFrame(function () {
        if (charts[elId]) { charts[elId].resize(); }
      });
      return;
    }
    if (observers[elId]) {
      observers[elId].disconnect();
    }
    const ro = new ResizeObserver(function () {
      if (charts[elId] && charts[elId].resize) {
        charts[elId].resize();
      }
    });
    ro.observe(el);
    observers[elId] = ro;
  }

  /** Dibuja (o redibuja) un gráfico ECharts en el contenedor `elId`. */
  window.renderChart = function (elId, option, theme) {
    const el = document.getElementById(elId);
    if (!el || typeof echarts === "undefined") {
      return null;
    }
    if (charts[elId]) {
      charts[elId].dispose();
      delete charts[elId];
    }
    const chart = echarts.init(el, theme || "dark");
    chart.setOption(option);
    charts[elId] = chart;
    watchResize(elId, el);
    return chart;
  };

  /** Destruye una instancia concreta (evita fugas al reemplazar paneles). */
  window.disposeChart = function (elId) {
    if (observers[elId]) {
      observers[elId].disconnect();
      delete observers[elId];
    }
    if (charts[elId]) {
      charts[elId].dispose();
      delete charts[elId];
    }
  };

  window.addEventListener("resize", function () {
    Object.keys(charts).forEach(function (id) {
      if (charts[id] && charts[id].resize) {
        charts[id].resize();
      }
    });
  });

  // Re-inicializa gráficos declarados con data-echart='{...}' tras un swap HTMX.
  document.addEventListener("htmx:afterSwap", function (event) {
    const root = (event.detail && event.detail.target) || document;
    root.querySelectorAll("[data-echart]").forEach(function (el) {
      try {
        renderChart(el.id, JSON.parse(el.getAttribute("data-echart")));
      } catch (err) {
        console.error("data-echart inválido en #" + el.id, err);
      }
    });
  });

  /** Resalta el símbolo seleccionado en el heatmap de confluencia (si existe). */
  function highlightConfluencia(symbol) {
    const chart = charts["chart-confluencia"];
    if (!chart || !symbol) {
      return;
    }
    const ticker = symbol.split(":").pop();
    const option = chart.getOption();
    const yAxis = option && option.yAxis && option.yAxis[0];
    const data = (yAxis && yAxis.data) || [];
    const idx = data.indexOf(ticker);

    chart.dispatchAction({ type: "downplay", seriesIndex: 0 });

    if (idx < 0) {
      chart.setOption({ graphic: [] }, { replaceMerge: ["graphic"] });
      return;
    }

    // Anillo nítido sobre los 3 círculos del símbolo
    [0, 1, 2].forEach(function (j) {
      chart.dispatchAction({ type: "highlight", seriesIndex: 0, dataIndex: idx * 3 + j });
    });

    // Banda sutil que resalta la fila completa (sin blur)
    let banda = [];
    try {
      const y = chart.convertToPixel({ yAxisIndex: 0 }, idx);
      const h = chart.getHeight() / Math.max(data.length, 1);
      banda = [
        {
          type: "rect",
          left: 0,
          top: y - h / 2,
          shape: { width: chart.getWidth(), height: h },
          style: { fill: "rgba(88, 166, 255, 0.10)" },
          silent: true,
          z: 0,
        },
      ];
    } catch (err) {
      banda = [];
    }
    chart.setOption({ graphic: banda }, { replaceMerge: ["graphic"] });
  }

  /** Resalta en el screener la fila del símbolo mostrado en el gráfico de velas. */
  function highlightScreenerRow(symbol) {
    if (!symbol) {
      return;
    }
    document.querySelectorAll(".screener-row").forEach(function (row) {
      if (row.getAttribute("data-symbol") === symbol) {
        row.classList.add("selected");
      } else {
        row.classList.remove("selected");
      }
    });
    highlightConfluencia(symbol);
  }

  /** Sincroniza el resaltado leyendo el símbolo actual del card de velas. */
  function syncScreenerSelection() {
    const card = document.getElementById("trading-velas-card");
    if (!card) {
      return;
    }
    const el = card.querySelector("[data-symbol]");
    if (el) {
      highlightScreenerRow(el.getAttribute("data-symbol"));
    }
  }

  document.addEventListener("click", function (event) {
    const row =
      event.target && event.target.closest ? event.target.closest(".screener-row") : null;
    if (row) {
      highlightScreenerRow(row.getAttribute("data-symbol"));
    }
  });

  document.addEventListener("htmx:afterSwap", syncScreenerSelection);
  document.addEventListener("DOMContentLoaded", syncScreenerSelection);

  // Carga del panel de health (Fase 0).
  document.addEventListener("DOMContentLoaded", function () {
    const health = document.getElementById("health");
    if (!health) {
      return;
    }
    fetch("/api/health")
      .then(function (response) { return response.json(); })
      .then(function (data) { health.textContent = JSON.stringify(data, null, 2); })
      .catch(function (err) { health.textContent = "health no disponible: " + err; });
  });
})();
