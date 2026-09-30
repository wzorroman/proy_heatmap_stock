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

  /** Dibuja (o redibuja) un gráfico ECharts en el contenedor `elId`. */
  window.renderChart = function (elId, option, theme) {
    const el = document.getElementById(elId);
    if (!el || typeof echarts === "undefined") {
      return null;
    }
    if (charts[elId]) {
      charts[elId].dispose();
    }
    const chart = echarts.init(el, theme || "dark");
    chart.setOption(option);
    charts[elId] = chart;
    return chart;
  };

  /** Destruye una instancia concreta (evita fugas al reemplazar paneles). */
  window.disposeChart = function (elId) {
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
