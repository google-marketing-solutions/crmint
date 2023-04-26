CREATE OR REPLACE TABLE `{{project_id}}.{{model_dataset}}.output` AS (
  WITH prior_table AS (
    SELECT SPLIT(MAX(table_id), 'events_')[OFFSET(1)] AS suffix
    FROM `{{project_id}}.{{ga4_dataset}}.__TABLES_SUMMARY__`
    WHERE table_id LIKE 'events_%'
    AND table_id NOT IN (
      SELECT MAX(table_id) FROM `{{project_id}}.{{ga4_dataset}}.__TABLES_SUMMARY__`)
  ),
  events AS (
    SELECT
      {{unique_id}},
      event_name AS name,
      event_params AS params
    FROM `{{project_id}}.{{ga4_dataset}}.events_*`
    WHERE _TABLE_SUFFIX = (SELECT suffix FROM prior_table)
  ),
  users_with_score AS (
    SELECT DISTINCT
      {{unique_id}}
    FROM events, UNNEST(params) AS params
    WHERE name = 'prop_score'
    AND params.value.string_value = 'Predicted_Value'
  ),
  users_without_score AS (
    SELECT DISTINCT
      {{unique_id}}
    FROM events
    WHERE {{unique_id}} NOT IN (
      SELECT {{unique_id}} FROM users_with_score)
  ),
  {% if type.is_classification %}
  prepared_predictions AS (
    SELECT DISTINCT
      {% if unique_id == 'user_id' %}
      p.user_id,
      {% endif %}
      p.user_pseudo_id AS client_id,
      cv.value,
      p.probability * 100 AS score,
    FROM `{{project_id}}.{{model_dataset}}.predictions` p
    LEFT OUTER JOIN `{{project_id}}.{{model_dataset}}.conversion_values` cv
    ON p.propability BETWEEN cv.probability_range_start AND cv.probability_range_end
  ),
  {% elif type.is_regression %}
  prepared_predictions AS (
    SELECT DISTINCT
      {% if unique_id == 'user_id' %}
      user_id,
      {% endif %}
      user_pseudo_id AS client_id,
      predicted_label AS value,
      predicted_label AS revenue
    FROM `{{project_id}}.{{model_dataset}}.predictions`
  ),
  {% endif %}
  consolidated_output AS (
    SELECT
      p.*,
      'prop_score' AS event_name,
      'Predicted_Value' AS type
    FROM prepared_predictions p
    INNER JOIN users_without_score wos
    ON p.{{unique_id}} = wos.{{unique_id}}
  )
  SELECT *
  FROM consolidated_output
)
