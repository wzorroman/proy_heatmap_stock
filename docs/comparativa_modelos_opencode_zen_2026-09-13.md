# Comparativa de Modelos Free en OpenCode Zen para Programación

**Fecha**: 2026-09-13  
**Fuentes**: [OpenCode Zen Docs](https://opencode.ai/docs/zen/), [models.dev](https://models.dev), documentación oficial de cada proveedor (Xiaomi, Meta, NVIDIA, InclusionAI)

---

## Resumen de Costos

| Modelo | Input/1M | Output/1M | Cache Read/1M | Costo Aprox. (USD) |
|---|---|---|---|---|
| **Big Pickle** | Free | Free | Free | **$0** |
| **MiMo-V2.5 Free** | Free | Free | Free | **$0** |
| **Ling 3.0 Flash Fin Free** | Free | Free | Free | **$0** |
| **Nemotron 3 Ultra Free** | Free | Free | Free | **$0** |
| **Nemotron 3.5 Lightning Free** | Free | Free | Free | **$0** |
| **Muse Spark 1.3 Contributor Free** | Free | Free | Free | **$0** |

> Todos los modelos listados son **100% gratuitos** durante el periodo de prueba. Los costos en USD son $0 para todos.

---

## Detalles por Modelo

### 1. Big Pickle

| Característica | Valor |
|---|---|
| **Proveedor** | OpenCode Zen (stealth — identidad no confirmada) |
| **Parámetros** | Desconocido (se sospecha GLM-4.6 de Zhipu AI o infraestructura DeepSeek) |
| **Contexto** | 200K tokens |
| **Output máximo** | 32K tokens |
| **Razonamiento** | Sí |
| **Tool Calling** | Sí |
| **Output Structured** | Sí |
| **Modalidad** | Texto |
| **SWE Atlas QnA** | 50.8% (63/124) — supera a todos los modelos open en scaffold Mini-SWE-Agent |
| **Comparable a** | Claude Sonnet 4.5/4.6 en coding |
| **Privacidad** | Datos pueden usarse para mejorar el modelo durante periodo free |

### 2. MiMo-V2.5 Free (Xiaomi)

| Característica | Valor |
|---|---|
| **Proveedor** | Xiaomi |
| **Arquitectura** | Sparse MoE — 310B total, 15B activos |
| **Contexto** | 1M tokens |
| **Output máximo** | 128K tokens |
| **Razonamiento** | Sí (deep thinking) |
| **Tool Calling** | Sí |
| **Multimodal** | Texto, imagen, video, audio |
| **Coding Agent (SWE-Bench)** | 71.8 (vs Claude Opus 4.6: 77.1) |
| **MiMo Coding Bench** | 62.3 |
| **Terminal-Bench 2.0** | 56.1 |
| **Entrenado en** | 48T tokens |
| **Comparable a** | Claude Opus 4.6 en tareas agentic diarias |
| **Privacidad** | Datos pueden usarse para mejorar el modelo durante periodo free |

### 3. Ling 3.0 Flash Fin Free (InclusionAI/Ant Group)

| Característica | Valor |
|---|---|
| **Proveedor** | InclusionAI (Ant Group) |
| **Arquitectura** | Hybrid-linear MoE — 124B total, 5.1B activos |
| **Contexto** | 262K tokens |
| **Output máximo** | 32K tokens |
| **Razonamiento** | Sí (thinking mode por defecto) |
| **Tool Calling** | Sí |
| **Velocidad** | 345-374 tokens/segundo |
| **Intelligence Index** | 38 (Artificial Analysis) |
| **Especialización** | Finanzas (versión Fin) — también fuerte en coding y math |
| **Comparable a** | Modelo eficiente de bajo costo; más rápido que competidores similares |
| **Privacidad** | Datos pueden usarse para mejorar el modelo durante periodo free |

### 4. Nemotron 3 Ultra Free (NVIDIA)

| Característica | Valor |
|---|---|
| **Proveedor** | NVIDIA |
| **Arquitectura** | LatentMoE — 550B total, 55B activos |
| **Contexto** | 1M tokens |
| **Output máximo** | No especificado |
| **Razonamiento** | Sí (frontier reasoning) |
| **Tool Calling** | Sí |
| **SWE-Bench Verified** | 71.9 (BF16) / 69.7 (NVFP4) |
| **Terminal-Bench 2.0** | 54% (56.4 BF16) |
| **PinchBench** | 90-91% |
| **TauBench V3 Airline** | 81.5% |
| **Entrenado en** | 20T tokens |
| **Comparable a** | Frontier-class — mejor modelo open de NVIDIA para agentes |
| **Privacidad** | Trial use — NVIDIA puede loggear para mejorar productos. **NO enviar datos personales/confidenciales** |

### 5. Nemotron 3.5 Lightning Free (NVIDIA)

| Característica | Valor |
|---|---|
| **Proveedor** | NVIDIA |
| **Arquitectura** | Hybrid Mamba-Transformer MoE — 30B total, 3B activos |
| **Contexto** | 262K tokens |
| **Output máximo** | No especificado |
| **Razonamiento** | Sí |
| **Tool Calling** | Sí |
| **MMLU Pro** | 81.94 |
| **GPQA Diamond** | 75.44 |
| **Velocidad** | 4x más throughput que modelos similares |
| **Uso ideal** | Capa de ejecución de agentes de alto volumen |
| **Comparable a** | Modelo pequeño ultrarrápido para ejecución rutinaria de agentes |
| **Privacidad** | Trial use — NVIDIA puede loggear para mejorar productos. **NO enviar datos personales/confidenciales** |

### 6. Muse Spark 1.3 Contributor Free (Meta)

| Característica | Valor |
|---|---|
| **Proveedor** | Meta |
| **Contexto** | 1M tokens |
| **Output máximo** | No especificado |
| **Razonamiento** | Sí (xhigh disponible; max próximamente) |
| **Tool Calling** | Sí |
| **Multimodal** | Texto, imagen, video (input) |
| **Terminal-Bench 2.1** | ~82.9% (vs Opus 5: 86.7%) |
| **Efficiency** | ~25% menos tokens, ~20% menos tool calls que v1.2 |
| **Intelligence Index** | 61 (xhigh) — más bajo costo por tarea que cualquier modelo medido |
| **Comparable a** | Competitivo con GPT-5.6 Sol; cerca de Claude Opus 5 |
| **Privacidad** | **Meta usa prompts y completions para entrenar modelos futuros** (Contributor tier) |

---

## Tabla Comparativa de Capacidades para Programación

| Modelo | Contexto | Coding Benchmark | Velocidad | Razonamiento | Multimodal | Open Weights |
|---|---|---|---|---|---|---|
| **Big Pickle** | 200K | SWE Atlas 50.8% | — | Sí | No | No |
| **MiMo-V2.5 Free** | 1M | SWE 71.8, Terminal 56.1 | — | Sí | Sí | Sí |
| **Ling 3.0 Flash Fin** | 262K | SWE Pro fuerte | 345+ t/s | Sí | No | Sí |
| **Nemotron 3 Ultra** | 1M | SWE 71.9 | Rápido | Sí | No | Sí |
| **Nemotron 3.5 Lightning** | 262K | — | 4x más rápido | Sí | No | Sí |
| **Muse Spark 1.3** | 1M | Terminal ~82.9% | 235 t/s | Sí | Sí | No (próximamente) |

---

## Recomendaciones por Caso de Uso

| Caso de Uso | Mejor Opción | Alternativa |
|---|---|---|
| **Coding agente de alto nivel** | MiMo-V2.5 Free o Nemotron 3 Ultra | Muse Spark 1.3 Contributor |
| **Ejecución rápida de tareas rutinarias** | Nemotron 3.5 Lightning | Ling 3.0 Flash Fin |
| **Tareas que requieren contexto largo** | MiMo-V2.5 Free (1M) o Nemotron 3 Ultra (1M) | Muse Spark 1.3 (1M) |
| **Análisis financiero + coding** | Ling 3.0 Flash Fin | — |
| **Uso diario sin preocuparse por costo** | Big Pickle | cualquiera de los free |
| **Máxima calidad sin límites de datos** | MiMo-V2.5 Free (open weights) | Nemotron 3 Ultra (open weights) |

---

## Advertencias Importantes

1. **Periodo limitado**: Todos los modelos free son temporales. Los precios cambiarán cuando termine el periodo de prueba.
2. **Privacidad**: Big Pickle, MiMo-V2.5 Free, Ling 3.0 y Muse Spark Contributor usan datos para entrenamiento. Nemotron free endpoints loggean uso. **No usar con código sensible/confidencial**.
3. **Identidad de Big Pickle**: No confirmada oficialmente — puede cambiar sin aviso.
4. **Muse Spark 1.3 Contributor**: Solo el tier Contributor es free; el Standard cuesta $1.25/$4.25 por 1M tokens.
5. **NVIDIA Nemotron**: Los endpoints free son para trial — revisar términos de NVIDIA antes de uso en producción.

---

## Comparativa con Modelos de Pago (Referencia)

Para referencia, los precios de los modelos equivalentes de pago en OpenCode Zen:

| Modelo Pago | Input/1M | Output/1M | Notas |
|---|---|---|---|
| Claude Opus 5 | $5.00 | $25.00 | Frontier coding |
| Claude Sonnet 5 | $2.00 | $10.00 | Buen balance costo/calidad |
| GPT 5.6 Sol | $2.00 | $10.00 | Coding fuerte (50% descuento hasta Sep 18) |
| GPT 5.1 Codex | $1.07 | $8.50 | Especializado en código |
| DeepSeek V4 Flash | $0.14 | $0.28 | Muy económico |
| MiniMax M3 | $0.30 | $1.20 | Alternativa económica |
| Muse Spark 1.3 (Standard) | $1.25 | $4.25 | Equivalente paid del Contributor free |
