{% if google_analytics.in_source %}
DECLARE _LATEST_TABLE_SUFFIX STRING;
SET _LATEST_TABLE_SUFFIX = (
  SELECT MAX(SPLIT(table_id, "events_")[OFFSET(1)])
  FROM `{{project_id}}.{{ga4_dataset}}.__TABLES_SUMMARY__`
  WHERE REGEXP_CONTAINS(table_id, r"^(events_[0-9]{8})$")
);
{% endif %}
CREATE OR REPLACE TABLE `{{project_id}}.{{model_dataset}}.output` AS (
  WITH
  {% if google_analytics.in_source %}
  events AS (
    SELECT
      {{google_analytics.unique_id.name}} AS unique_id,
      event_name AS name,
      event_timestamp AS timestamp,
      event_params AS params
    FROM `{{project_id}}.{{ga4_dataset}}.events_*`
    WHERE _TABLE_SUFFIX = _LATEST_TABLE_SUFFIX
    AND LOWER(platform) = "web"
  ),
  {% elif first_party.in_source %}
  first_party AS (
    SELECT
      {{first_party.unique_id.name}} AS unique_id,
      {% if first_party.gclid %}
      {{first_party.gclid.name}} AS gclid,
      {% endif %}
      {{first_party.trigger_date.name}} AS timestamp
    FROM `{{project_id}}.{{first_party.dataset}}.{{first_party.table}}`
    WHERE {{first_party.trigger_date.name}} BETWEEN
      DATETIME(DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)) AND
      DATETIME_SUB(DATETIME(CURRENT_DATE()), INTERVAL 1 SECOND)
  ),
  {% endif %}
  {% if type.is_classification %}
  prepared_predictions AS (
    SELECT DISTINCT
      p.unique_id,
      {% if google_analytics.in_source %}
      p.user_pseudo_id,
      p.user_id,
      {% endif %}
      ROUND(MAX(cv.value), 4) AS value,
      MAX(cv.normalized_probability) AS normalized_score,
      MAX(p.probability) * 100 AS score
    FROM `{{project_id}}.{{model_dataset}}.predictions` p
    LEFT OUTER JOIN `{{project_id}}.{{model_dataset}}.conversion_values` cv
    ON p.probability BETWEEN cv.probability_range_start AND cv.probability_range_end
    {% if google_analytics.in_source %}
    GROUP BY 1,2,3
    {% else %}
    GROUP BY 1
    {% endif %}
  ),
  {% elif type.is_regression %}
  prepared_predictions AS (
    SELECT DISTINCT
      unique_id,
      {% if google_analytics.in_source %}
      user_pseudo_id,
      user_id,
      {% endif %}
      IF(predicted_label > 0, ROUND(predicted_label, 4), 0) AS value,
      IF(predicted_label > 0, ROUND(predicted_label, 4), 0) AS revenue
    FROM `{{project_id}}.{{model_dataset}}.predictions`
  ),
  {% endif %}
  {% if output.destination.is_google_analytics_mp_event %}
  {% if google_analytics.in_source %}
  users_with_score AS (
    SELECT DISTINCT
      unique_id
    FROM events, UNNEST(params) AS params
    WHERE name = "prop_score"
    AND params.value.string_value = "Predicted_Value"
  ),
  users_without_score AS (
    SELECT DISTINCT
      unique_id
    FROM events
    WHERE unique_id NOT IN (
      SELECT unique_id FROM users_with_score)
  )
  {% endif %}
  SELECT
    p.* EXCEPT(unique_id{% if google_analytics.in_source %}, user_pseudo_id, user_id{% endif %}),
    {% if google_analytics.in_source and unique_id.is_user_id %}
    p.user_pseudo_id AS client_id,
    {% endif %}
    p.unique_id AS {{'user_id' if unique_id.is_user_id else 'client_id'}},
    "prop_score" AS event_name,
    "Predicted_Value" AS type
  FROM prepared_predictions p
  {% if google_analytics.in_source %}
  INNER JOIN users_without_score wos
  ON p.unique_id = wos.unique_id
  {% elif first_party.in_source %}
  INNER JOIN first_party fp
  ON p.unique_id = fp.unique_id
  {% endif %}
  {% elif output.destination.is_google_ads_offline_conversion %}
  gclids AS (
    {% if google_analytics.in_source %}
    SELECT * EXCEPT(row_num)
    FROM (
      SELECT
        unique_id,
        params.value.string_value AS gclid,
        FORMAT_TIMESTAMP("%F %T%Ez", TIMESTAMP(TIMESTAMP_MICROS(timestamp))) AS datetime,
        ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY timestamp DESC) AS row_num
      FROM events, UNNEST(params) AS params
      WHERE name = "page_view"
      AND params.key = "gclid"
      AND COALESCE(params.value.string_value, "") != ""
    )
    WHERE row_num = 1
    {% else %}
    SELECT
      unique_id,
      gclid,
      FORMAT_TIMESTAMP("%F %T%Ez", TIMESTAMP(timestamp)) AS datetime
    FROM first_party
    {% endif %}
  )
  SELECT
    p.*,
    g.gclid,
    g.datetime
  FROM prepared_predictions p
  INNER JOIN gclids g
  ON p.unique_id = g.unique_id
  {% endif %}
)
