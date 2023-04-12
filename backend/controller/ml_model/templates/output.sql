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
      event_name AS name
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
  {% if label.is_score %}
  prepared_predictions AS (
    SELECT DISTINCT
      {% if unique_id == 'user_id' %}
      p.user_id,
      {% endif %}
      p.user_pseudo_id AS client_id,
      {% if label.is_conversion %}
      p.{{label.name}},
      {% else %}
      p.predicted_label * {{ 100 if label.is_percentage else 1 }} AS value,
      {% endif %}
      p.predicted_label * {{ 100 if label.is_percentage else 1 }} AS score,
      NTILE(10) OVER (ORDER BY p.predicted_label ASC) AS normalized_score
    FROM `{{project_id}}.{{model_dataset}}.predictions` p
    INNER JOIN users_without_score wos
    ON p.{{unique_id}} = wos.{{unique_id}}
    {% if unique_id == 'user_id' %}
    GROUP BY 1,2,3,4
    {% else %}
    GROUP BY 1,2,3
    {% endif %}
    ORDER BY score DESC
  ),
  {% if label.is_conversion %}
  conversion_rate AS (
    SELECT
      normalized_score,
      (SUM({{label.name}}) / COUNT(normalized_score)) * {{label.average_value}} AS value
    FROM prepared_predictions
    GROUP BY 1
  ),
  {% endif %}
  {% elif label.is_revenue %}
  prepared_predictions AS (
    SELECT DISTINCT
      {% if unique_id == 'user_id' %}
      p.user_id,
      {% endif %}
      p.user_pseudo_id AS client_id,
      p.predicted_label AS value,
      p.predicted_label AS revenue
    FROM `{{project_id}}.{{model_dataset}}.predictions` p
    INNER JOIN users_without_score wos
    ON p.{{unique_id}} = wos.{{unique_id}}
    ORDER BY revenue DESC
  ),
  {% endif %}
  consolidated_output AS (
    SELECT
      p.*,
      {% if label.is_conversion %}
      cr.value,
      {% endif %}
      'prop_score' AS event_name,
      'Predicted_Value' AS type
    FROM prepared_predictions p
    {% if label.is_conversion %}
    LEFT OUTER JOIN conversion_rate cr
    ON p.normalized_score = cr.normalized_score
    {% endif %}
  )
  SELECT *
  FROM consolidated_output
)
