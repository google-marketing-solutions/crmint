CREATE OR REPLACE MODEL `{{project_id}}.{{model_dataset}}.predictive_model`
OPTIONS (
  MODEL_TYPE = "{{type.name}}",
  -- inject the selected hyper parameters
  {% for param in hyper_parameters %}
  {% if is_number(param.value) %}
  {{param.name}} = {{param.value}},
  {% elif is_bool(param.value) %}
  {{param.name}} = {{param.value.upper()}},
  {% else %}
  {{param.name}} = "{{param.value}}",
  {% endif %}
  {% endfor %}
  INPUT_LABEL_COLS = ["label"]
) AS
WITH
{% if input.source.includes_first_party %}
first_party_variables AS (
  SELECT
    {% for feature in first_party.features %}
    {{feature.name}},
    {% endfor %}
    {% if first_party.label %}
    {{first_party.label.name}} AS label,
    {% endif %}
    {% if first_party.first_value %}
    {{first_party.first_value.name}} AS first_value,
    {% endif %}
    {% if first_party.trigger_date %}
    {{first_party.trigger_date.name}} AS trigger_date,
    {% endif %}
    {{first_party.unique_id}} AS unique_id
  FROM `{{project_id}}.{{input.parameters.first_party_dataset}}.{{input.parameters.first_party_table}}`
),
{% endif %}
{% if input.source.includes_google_analytics %}
events AS (
  SELECT
    event_timestamp AS timestamp,
    CAST(event_date AS DATE FORMAT "YYYYMMDD") AS date,
    event_name AS name,
    event_params AS params,
    {{google_analytics.unique_id}} AS unique_id,
    geo.country AS country,
    geo.region AS region,
    device.language AS language,
    device.category AS device_type,
    device.operating_system AS device_os,
    device.web_info.browser AS device_browser,
    traffic_source.source AS traffic_source,
    traffic_source.medium AS traffic_medium,
    EXTRACT(HOUR FROM(TIMESTAMP_MICROS(user_first_touch_timestamp))) AS first_touch_hour
  FROM `{{project_id}}.{{ga4_dataset}}.events_*`
  WHERE _TABLE_SUFFIX BETWEEN
    FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {{timespan.training_start}} DAY)) AND
    FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {{timespan.training_end}} DAY))
  {% if type.is_classification %}
  -- get 90% of the events in this time-range (the other 10% is used to calculate conversion values)
  AND MOD(ABS(FARM_FINGERPRINT({{google_analytics.unique_id}})), 100) < 90
  {% endif %}
  AND LOWER(platform) = "web"
  -- limit events to ids within first party dataset (avoids processing data that gets filtered later anyways)
  {% if input.source.includes_first_party %}
  AND {{google_analytics.unique_id}} IN (
    SELECT unique_id FROM first_party_variables
  )
  {% endif %}
),
-- pull together a list of first engagements and associated metadata that will be useful for the model
first_engagement AS (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT
      unique_id,
      country,
      region,
      language,
      traffic_source,
      traffic_medium,
      device_type,
      device_os,
      device_browser,
      CASE
        WHEN first_touch_hour >= 1 AND first_touch_hour < 6 THEN "night_1_6"
        WHEN first_touch_hour >= 6 AND first_touch_hour < 11 THEN "morning_6_11"
        WHEN first_touch_hour >= 11 AND first_touch_hour < 14 THEN "lunch_11_14"
        WHEN first_touch_hour >= 14 AND first_touch_hour < 17 THEN "afternoon_14_17"
        WHEN first_touch_hour >= 17 AND first_touch_hour < 19 THEN "dinner_17_19"
        WHEN first_touch_hour >= 19 AND first_touch_hour < 22 THEN "evening_19_23"
        WHEN first_touch_hour >= 22 OR first_touch_hour = 0 THEN "latenight_23_1"
      END AS daypart,
      ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY timestamp ASC) AS row_num
    FROM events
    WHERE name = "user_engagement"
  )
  WHERE row_num = 1
),
{% if google_analytics.label or google_analytics.first_value or google_analytics.trigger_event %}
analytics_variables AS (
  SELECT
    fe.unique_id,
    {% if google_analytics.label %}
    IFNULL(l.label, 0) AS label,
    {% endif %}
    {% if google_analytics.first_value or google_analytics.trigger_event or (type.is_regression and not first_party.trigger_date) %}
    {% if type.is_regression %}
    IFNULL(t.value, 0) AS first_value,
    {% endif %}
    t.date AS trigger_date
    {% else %}
    l.date AS trigger_date
    {% endif %}
  FROM first_engagement fe
  {% if google_analytics.label %}
  LEFT OUTER JOIN (
    SELECT
      e.unique_id,
      {% if type.is_classification %}
      1 AS label,
      {% elif type.is_regression %}
      SUM(COALESCE(params.value.int_value, params.value.float_value, params.value.double_value, 0)) AS label,
      {% endif %}
      MIN(e.date) AS date
    FROM events AS e, UNNEST(params) AS params
    WHERE name = "{{google_analytics.label.name}}"
    AND params.key = "{{google_analytics.label.key}}"
    {% if 'string' in google_analytics.label.value_type %}
    AND COALESCE(params.value.string_value, CAST(params.value.int_value AS STRING)) NOT IN ("", "0", NULL)
    {% else %}
    AND COALESCE(params.value.int_value, params.value.float_value, params.value.double_value, 0) > 0
    {% endif %}
    GROUP BY 1
  ) l
  ON fe.unique_id = l.unique_id
  {% endif %}
  {% if google_analytics.first_value or google_analytics.trigger_event or (type.is_regression and not first_party.trigger_date) %}
  LEFT OUTER JOIN (
    SELECT
      e.unique_id,
      e.date,
      {% if type.is_regression %}
      COALESCE(params.value.int_value, params.value.float_value, params.value.double_value, 0) AS value,
      {% endif %}
      ROW_NUMBER() OVER (PARTITION BY e.unique_id ORDER BY e.timestamp ASC) AS row_num
    FROM events AS e, UNNEST(params) AS params
    WHERE name = "{{google_analytics.trigger_date.name}}"
    AND params.key = "{{google_analytics.trigger_date.key}}"
    {% if type.is_regression %}
    AND COALESCE(params.value.int_value, params.value.float_value, params.value.double_value, 0) > 0
    {% endif %}
  ) t
  ON fe.unique_id = t.unique_id
  AND t.row_num = 1
  {% endif %}
),
{% endif %}
user_variables AS (
  {% if input.source.includes_first_party and (google_analytics.label or google_analytics.first_value or google_analytics.trigger_event) %}
  SELECT
    fpv.*,
    av.* EXCEPT(unique_id)
  FROM first_party_variables fpv
  INNER JOIN analytics_variables av
  ON fpv.unique_id = av.unique_id
  {% elif google_analytics.label or google_analytics.first_value or google_analytics.trigger_event %}
  FROM analytics_variables
  {% elif input.source.includes_first_party %}
  FROM first_party_variables
  {% endif %}
),
aggregate_behavior AS (
  SELECT
    e.unique_id,
    SUM((SELECT value.int_value FROM UNNEST(e.params) WHERE key = "engagement_time_msec")) AS engagement_time,
    SUM(IF(e.name = "user_engagement", 1, 0)) AS cnt_user_engagement,
    SUM(IF(e.name = "scroll", 1, 0)) AS cnt_scroll,
    SUM(IF(e.name = "session_start", 1, 0)) AS cnt_session_start,
    SUM(IF(e.name = "first_visit", 1, 0)) AS cnt_first_visit,
    -- inject the selected google analytics features
    {% for feature in google_analytics.features %}
    SUM(IF(e.name = "{{feature.name}}", 1, 0)) AS cnt_{{feature.name}},
    {% endfor %}
    SUM(IF(e.name = "page_view", 1, 0)) AS cnt_page_view
  FROM events AS e
  INNER JOIN user_variables AS uv
    ON e.unique_id = uv.unique_id
  WHERE (uv.label > 0 AND e.date <= uv.trigger_date)
  OR uv.label = 0
  GROUP BY 1
),
training_dataset AS (
  SELECT
    fe.*,
    ab.* EXCEPT(unique_id),
    uv.* EXCEPT(unique_id, trigger_date)
  FROM first_engagement AS fe
  INNER JOIN aggregate_behavior AS ab
  ON fe.unique_id = ab.unique_id
  INNER JOIN user_variables AS uv
  ON fe.unique_id = uv.unique_id
)
{% elif input.source.includes_first_party %}
training_dataset AS (
  SELECT * FROM first_party_variables
)
{% endif %}
{% if type.is_classification or not (google_analytics.first_value or google_analytics.trigger_event or (google_analytics.label and not first_party.trigger_date)) %}
SELECT * EXCEPT(unique_id)
{% elif type.is_regression %}
SELECT
  * EXCEPT(unique_id, label),
  (label - first_value) AS label
{% endif %}
FROM training_dataset
{% if class_imbalance > 1 %}
WHERE label > 0
UNION ALL
SELECT * EXCEPT(unique_id)
FROM training_dataset
WHERE label = 0
AND MOD(ABS(FARM_FINGERPRINT(unique_id)), 100) <= ((1 / {{class_imbalance}}) * 100)
{% endif %}
