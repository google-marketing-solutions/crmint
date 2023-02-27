CREATE OR REPLACE MODEL `__PROJECT_ID__.__ML_MODEL_DATASET__.model`
OPTIONS (
  MODEL_TYPE = "__ML_MODEL_TYPE__",
  INPUT_LABEL_COLS = ['label'],
  __ML_MODEL_HYPER_PARAMTERS__
) AS
WITH events AS (
  SELECT
    event_timestamp AS timestamp,
    event_date AS date,
    event_name AS name,
    event_params AS params,
    user_pseudo_id,
    geo.country AS country,
    geo.city AS city,
    device.language AS language,
    device.category AS device_type,
    device.operating_system AS device_os,
    device.web_info.browser AS device_browser,
    traffic_source.source AS traffic_source,
    traffic_source.medium AS traffic_medium,
    EXTRACT(HOUR FROM(TIMESTAMP_MICROS(user_first_touch_timestamp))) AS first_touch_hour
    FROM `__PROJECT_ID__.__GA4_DATASET__.events_*`
    WHERE _TABLE_SUFFIX BETWEEN
      FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 + __ML_MODEL_TIMESPAN_MONTHS__ MONTH)) AND
      FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH))
),
first_values AS (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT
      -- all of these first value features don't need to be organized (they can be freetext)?
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
      ROW_NUMBER() OVER (PARTITION BY user_pseudo_id ORDER BY timestamp ASC) AS row_num
    FROM events
    WHERE name = "user_engagement"
  )
  WHERE row_num = 1
),
__ML_MODEL_USER_LABELS__
-- ga4 event label values
user_labels AS (
  SELECT
    user_pseudo_id,
    IFNULL(label, 0) AS label,
    date
  FROM first_values
  LEFT JOIN (
    SELECT
      user_pseudo_id,
      1 AS label,
      MIN(date) AS date,
    FROM events AS e, UNNEST(params) AS params
    WHERE name = "__ML_MODEL_LABEL_NAME__"
    AND params.key = "__ML_MODEL_LABEL_KEY__"
    AND __ML_MODEL_LABEL_VALUE_STATEMENT__
    GROUP BY user_pseudo_id
  ) labels
  ON first_values.user_pseudo_id = labels.user_pseudo_id
),
-- 1pd features and labels
user_labels AS (
  SELECT
    user_id,
    user_pseudo_id,
    event_name,
    -- will need to have something in the UI to allow the user to select this "date" field for 1pd
    __ML_MODEL_FIRST_PARTY_DATE__ AS date,
    __ML_MODEL_FEATURES__
    __ML_MODEL_LABEL_NAME__ AS label
  FROM `__PROJECT_ID__.__ML_MODEL_DATASET__.first_party`
)
user_aggregate_behavior AS (
  SELECT
    user_pseudo_id,
    SUM((SELECT value.int_value FROM UNNEST(params) WHERE key = "engagement_time_msec")) AS engagement_time,
    SUM(IF(name = "page_view", 1, 0)) AS cnt_page_view, -- what features should be defaulted here if any?
    SUM(IF(name = "user_engagement", 1, 0)) AS cnt_user_engagement,
    __ML_MODEL_FEATURES__
  FROM events AS e
  INNER JOIN user_labels AS ul
    ON e.user_pseudo_id = ul.user_pseudo_id
  -- does this logic apply always?
  -- if not why does the label being 1 only apply to event data less than the min_date for just GA4 data?
  WHERE (ul.label = 1 AND e.date <= ul.date)
  OR ul.label = 0
  GROUP BY user_pseudo_id
),
training_dataset AS (
  SELECT
    fv.*,
    uab.* EXCEPT(user_pseudo_id),
    ul.* EXCEPT(user_pseudo_id, date)
  FROM first_values AS fv
  INNER JOIN user_aggregate_behavior AS uab
  ON fv.user_pseudo_id = uab.user_pseudo_id
  INNER JOIN user_labels AS ul
  ON fv.user_pseudo_id = ul.user_pseudo_id
)
SELECT * EXCEPT(user_pseudo_id)
FROM training_dataset
WHERE label = 1
UNION ALL
SELECT * EXCEPT(user_pseudo_id)
FROM training_dataset
WHERE label = 0
-- randomly select a certain percentage of the 0 labels based on skew factor
AND MOD(ABS(FARM_FINGERPRINT(user_pseudo_id)), __ML_MODEL_SKEW_FACTOR__) = IF(RAND() < 0.5, 0, 1)
