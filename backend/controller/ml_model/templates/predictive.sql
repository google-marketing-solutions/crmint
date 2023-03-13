CREATE OR REPLACE TABLE `{{project_id}}.{{model_dataset}}.predictions` AS (
  SELECT
    {% if unique_id == 'user_id' %}
    user_id,
    {% endif %}
    user_pseudo_id,
    {% if type.classification %}
    (SELECT prob FROM UNNEST(predicted_label_probs)) AS probability,
    {% if label.is_conversion %}
    {{label.name}},
    {% endif %}
    {% endif %}
    predicted_label
  FROM ML.PREDICT(MODEL `{{project_id}}.{{model_dataset}}.model`, (
    WITH events AS (
      SELECT
        event_timestamp AS timestamp,
        event_name AS name,
        event_params AS params,
        user_id,
        user_pseudo_id,
        geo.country AS country,
        geo.city AS city,
        device.language AS language,
        device.category AS device_type,
        device.web_info.browser AS device_browser,
        device.operating_system AS device_os,
        traffic_source.medium AS taffic_source_medium,
        EXTRACT(HOUR FROM(TIMESTAMP_MICROS(user_first_touch_timestamp))) AS first_touch_hour
        FROM `{{project_id}}.{{ga4_dataset}}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN
          FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL {{timespan.predictive}} {{timespan.unit}})) AND
          FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
    ),
    first_values AS (
      SELECT * EXCEPT(row_num)
      FROM (
        SELECT
          {% if unique_id == 'user_id' %}
          user_id,
          {% endif %}
          user_pseudo_id,
          country,
          city,
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
          ROW_NUMBER() OVER (PARTITION BY {{unique_id}} ORDER BY timestamp ASC) AS row_num
        FROM events
        WHERE name = "user_engagement"
      )
      WHERE row_num = 1
    ),
    -- if the selected label is a google analytics event then pull these per user
    {% if label.source == 'GOOGLE_ANALYTICS' %}
    analytics_variables AS (
      SELECT
        fe.{{unique_id}},
        IFNULL(l.label, 0) AS label,
        l.date
      FROM first_engagement fe
      LEFT OUTER JOIN (
        SELECT
          {{unique_id}},
          1 AS label,
          MIN(date) AS date,
        FROM events AS e, UNNEST(params) AS params
        WHERE name = "{{label.name}}"
        AND params.key = "{{label.key}}"
        {% if 'string' in label.value_type %}
        AND COALESCE(params.value.string_value, params.value.int_value) NOT IN ("", "0", 0, NULL)
        {% else %}
        AND COALESCE(params.value.int_value, params.value.float_value, params.value.double_value, 0) > 0
        {% endif %}
        GROUP BY 1
      ) l
      ON fe.{{unique_id}} = l.{{unique_id}}
    ),
    {% endif %}
    {% if uses_first_party_data %}
    user_variables AS (
      SELECT
        fp.{{unique_id}},
        fp.event_name,
        -- inject the selected first party features
        {% for feature in features %}
        {% if feature.source == 'FIRST_PARTY' %}
        fp.{{feature.name}},
        {% endif %}
        {% endfor %}
        -- inject the selected first party label
        {% if label.source == 'FIRST_PARTY' %}
        fp.{{label.name}} AS label,
        fp.trigger_event_date,
        -- or inject the selected google analytics label
        {% elif label.source == 'GOOGLE_ANALYTICS' %}
        IFNULL(av.label, 0) AS label,
        COALESCE(fp.trigger_event_date, av.date) AS trigger_event_date,
        {% endif %}
      FROM `{{project_id}}.{{model_dataset}}.first_party` fp
      {% if label.source == 'GOOGLE_ANALYTICS' %}
      LEFT OUTER JOIN analytics_variables av
      ON fp.{{unique_id}} = av.{{unique_id}}
      {% endif %}
    ),
    {% else %}
    user_variables AS (
      SELECT * FROM analytics_variables
    ),
    {% endif %}
    user_aggregate_behavior AS (
      SELECT
        {{unique_id}},
        SUM((SELECT value.int_value FROM UNNEST(params) WHERE key = "engagement_time_msec")) AS engagement_time,
        SUM(IF(name = "user_engagement", 1, 0)) AS cnt_user_engagement,
        -- inject the selected google analytics features
        {% for feature in features %}
        {% if feature.source == 'GOOGLE_ANALYTICS' %}
        SUM(IF(name = "{{feature.name}}", 1, 0)) AS cnt_{{feature.name}},
        {% endif %}
        {% endfor %}
        SUM(IF(name = "page_view", 1, 0)) AS cnt_page_view
      FROM events AS e
      INNER JOIN user_variables AS uv
        ON e.{{unique_id}} = uv.{{unique_id}}
      WHERE (uv.label = 1 AND e.date <= uv.trigger_event_date)
      OR uv.label = 0
      GROUP BY 1
    ),
    SELECT
      fv.*,
      {% if label.is_conversion %}
      uv.label AS {{label.name}},
      {% endif %}
      uab.* EXCEPT ({{unique_id}}),
      uv.* EXCEPT({{unique_id}}, trigger_event_date)
    FROM first_values AS fv
    INNER JOIN user_aggregate_behavior AS uab
    ON fv.{{unique_id}} = uab.{{unique_id}}
    INNER JOIN user_variables AS uv
    ON fv.{{unique_id}} = uv.{{unique_id}}
    {% if type.classification %}
    WHERE label = 1
    {% endif %}
  ))
)