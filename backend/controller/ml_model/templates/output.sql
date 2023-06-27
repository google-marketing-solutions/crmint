DECLARE _LATEST_TABLE_SUFFIX STRING;
SET _LATEST_TABLE_SUFFIX = (
  SELECT MAX(SPLIT(table_id, 'events_')[OFFSET(1)])
  FROM `{{project_id}}.{{ga4_dataset}}.__TABLES_SUMMARY__`
  WHERE REGEXP_CONTAINS(table_id, r'^(events_[0-9]{8})$')
);

CREATE OR REPLACE TABLE `{{project_id}}.{{model_dataset}}.output` AS (
  WITH events AS (
    SELECT
      {{unique_id}},
      event_name AS name,
      event_timestamp AS timestamp,
      event_params AS params
    FROM `{{project_id}}.{{ga4_dataset}}.events_*`
    WHERE _TABLE_SUFFIX = _LATEST_TABLE_SUFFIX
    AND LOWER(platform) = 'web'
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
      p.user_pseudo_id,
      ROUND(MAX(cv.value), 4) AS value,
      MAX(cv.normalized_probability) AS normalized_score,
      MAX(p.probability) * 100 AS score,
    FROM `{{project_id}}.{{model_dataset}}.predictions` p
    LEFT OUTER JOIN `{{project_id}}.{{model_dataset}}.conversion_values` cv
    ON p.probability BETWEEN cv.probability_range_start AND cv.probability_range_end
    GROUP BY 1{% if unique_id == 'user_id' %},2{% endif %}
  ),
  {% elif type.is_regression %}
  prepared_predictions AS (
    SELECT DISTINCT
      {% if unique_id == 'user_id' %}
      user_id,
      {% endif %}
      user_pseudo_id,
      IF(predicted_label > 0, ROUND(predicted_label, 4), 0) AS value,
      IF(predicted_label > 0, ROUND(predicted_label, 4), 0) AS revenue
    FROM `{{project_id}}.{{model_dataset}}.predictions`
  ),
  {% endif %}
  {% if output.destination.is_google_analytics_mp_event %}
  consolidated_output AS (
    SELECT
      p.* EXCEPT(user_pseudo_id),
      p.user_pseudo_id AS client_id,
      'prop_score' AS event_name,
      'Predicted_Value' AS type
    FROM prepared_predictions p
    INNER JOIN users_without_score wos
    ON p.{{unique_id}} = wos.{{unique_id}}
  )
  {% elif output.destination.is_google_ads_offline_conversion %}
  gclids AS (
    SELECT * EXCEPT(row_num)
    FROM (
      SELECT
        {{unique_id}},
        params.value.string_value AS gclid,
        FORMAT_TIMESTAMP('%F %T%Ez', TIMESTAMP(TIMESTAMP_MICROS(timestamp))) AS datetime,
        ROW_NUMBER() OVER (PARTITION BY {{unique_id}} ORDER BY timestamp DESC) AS row_num
      FROM events, UNNEST(params) AS params
      WHERE name = 'page_view'
      AND params.key = 'gclid'
      AND COALESCE(params.value.string_value, '') != ''
    )
    WHERE row_num = 1
  ),
  consolidated_output AS (
    SELECT
      p.* EXCEPT(user_pseudo_id),
      p.user_pseudo_id AS client_id,
      g.gclid,
      g.datetime
    FROM prepared_predictions p
    INNER JOIN users_without_score wos
    ON p.{{unique_id}} = wos.{{unique_id}}
    INNER JOIN gclids g
    ON p.{{unique_id}} = g.{{unique_id}}
  )
  {% endif %}
  SELECT *
  FROM consolidated_output
)
