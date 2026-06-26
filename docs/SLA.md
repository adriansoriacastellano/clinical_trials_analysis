# Documento de Requerimientos y Arquitectura Lógica

## Sección A — Requerimientos de Negocio (completar en Fase 1)

* **Objetivo Principal:** Identificar qué factores — fase del ensayo, tipo de patrocinador, área terapéutica, tamaño y país — determinan si un ensayo clínico registrado en ClinicalTrials.gov llega a completarse o se abandona/suspende.

* **Origen de los Datos:** API pública de ClinicalTrials.gov v2. Endpoint REST sin autenticación. URL base: `https://clinicaltrials.gov/api/v2/studies`. Ingesta única para el período 2010-2024.

* **Granularidad del Modelo Final:** Un ensayo clínico. Cada fila es un estudio único identificado por su NCT ID.

* **Glosario de KPIs:**
  * **Tasa de finalización:** `COUNT(ensayos_completados) / COUNT(total_ensayos)`
  * **Tasa de abandono:** `COUNT(ensayos_terminados + suspendidos + retirados) / COUNT(total_ensayos)`
  * **Duración media del ensayo:** `AVG(fecha_fin_real - fecha_inicio_real)` en días, solo para ensayos completados
  * **Tamaño medio del ensayo:** `AVG(enrollment_count)`
  * **Tasa de finalización por fase:** `COUNT(completados_fase_X) / COUNT(total_fase_X)` para fases I, II, III, IV
  * **Tasa de finalización por tipo de patrocinador:** `COUNT(completados_sponsor_tipo) / COUNT(total_sponsor_tipo)` (Industry, NIH, Other)
  * **Tasa de finalización por área terapéutica:** Para las top 10 áreas con más ensayos
  * **Distribución de estados:** `COUNT` por cada `overall_status` (COMPLETED, TERMINATED, WITHDRAWN, SUSPENDED, etc.)

* **Frecuencia de actualización:** Proyecto de análisis histórico. Ingesta única para el período 2010-2024. No requiere actualización periódica.

* **Campos PII detectados:** No se detectan. ClinicalTrials.gov es una base de datos pública de estudios, no de pacientes. No contiene nombres, emails ni datos identificables de personas.

## Sección B — Arquitectura Técnica (completar en Fase 3, antes de marts)

* **Tabla Raw inspeccionada:** `raw.raw_clinical_trials` — 188,687 filas, 28 columnas. Fuente: API pública ClinicalTrials.gov v2 (sin autenticación).

* **Catálogo de columnas raw:**
  | Columna | Tipo | Contenido |
  |---|---|---|
  | `nct_id` | VARCHAR | ID único del ensayo (PK) |
  | `overall_status` | VARCHAR | Estado final (COMPLETED, TERMINATED, WITHDRAWN, SUSPENDED, RECRUITING...) |
  | `phases` | VARCHAR | Fases pipe-delimited (PHASE1\|PHASE2...) |
  | `lead_sponsor_class` | VARCHAR | Tipo de patrocinador (INDUSTRY, NIH, OTHER, OTHER_GOV...) |
  | `conditions` | VARCHAR | Condiciones/áreas terapéuticas pipe-delimited |
  | `countries` | VARCHAR | JSON array de países |
  | `enrollment_count` | BIGINT | Tamaño del ensayo (nulos presentes) |
  | `start_date` / `primary_completion_date` / `completion_date` | VARCHAR | Fechas en formato mixto (YYYY-MM-DD, YYYY-MM) |
  | `study_first_posted_date` | DATE | Fecha de publicación en CT.gov |
  | `primary_purpose` | VARCHAR | 100% nulo (no disponible en API v2) |
  | `intervention_types` | VARCHAR | JSON array de tipos de intervención |
  | `disposition_events` | VARCHAR | JSON array de eventos de disposición |

* **Esquema esperado de tablas marts:**
  * Tabla de hechos (`fct_clinical_trials`): Una fila por ensayo clínico (NCT ID), con métricas calculadas y claves foráneas a dimensiones.
  * Tablas de dimensiones (`dim_phase`, `dim_sponsor_type`, `dim_therapeutic_area`, `dim_country`, `dim_status`): Entidades descriptivas.

* **Criterio de Tie-out:** El conteo total de ensayos por `overall_status` en DuckDB debe coincidir exactamente con el visualizado en Power BI.

* **Campos PII confirmados:** Ninguno. Confirmado tras inspección del esquema raw: ClinicalTrials.gov no contiene datos de pacientes, solo metadatos de estudios.

## Sección C — Preguntas Analíticas

1. ¿Qué porcentaje de ensayos se completan vs. se abandonan y cómo ha evolucionado por año?
2. ¿Qué fases tienen mayor tasa de abandono?
3. ¿Los ensayos de la industria farmacéutica completan más que los académicos?
4. ¿Qué áreas terapéuticas concentran más abandonos?
5. ¿El tamaño del ensayo correlaciona con la probabilidad de completarse?
