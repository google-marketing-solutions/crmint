CREATE OR REPLACE TABLE `__PROJECT_ID__.__ML_MODEL_DATASET__.predictions` AS (
  SELECT
    user_pseudo_id,
    predicted_label
  FROM ML.PREDICT(MODEL `__PROJECT_ID__.__ML_MODEL_DATASET__.model`, (
    WITH events AS (
      SELECT
        event_timestamp AS timestamp,
        event_name AS name,
        event_params AS params,
        user_pseudo_id,
        geo.country AS country,
        geo.city AS city,
        device.language AS language,
        device.category AS device_type,
        device.web_info.browser AS device_browser,
        device.operating_system AS device_os,
        traffic_source.medium AS taffic_source_medium,
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
          user_pseudo_id,
          country,
          city,
          IF(device_type = "mobile", 1, 0) AS is_mobile,
          IF(device_type = "desktop", 1, 0) AS is_desktop,
          IF(device_type = "tablet", 1, 0) AS is_tablet,
          IF(taffic_source_medium = "cpc", 1, 0) AS is_paid_traffic,
          IF(taffic_source_medium = "none", 1, 0) AS is_none_traffic,
          IF(taffic_source_medium = "organic", 1, 0) AS is_organic_traffic,
          IF(taffic_source_medium = "referral", 1, 0) AS is_referral_traffic,
          IF(taffic_source_medium IN ("email","email_t","Email"), 1, 0) AS is_email,
          IF(taffic_source_medium  = "affiliate", 1, 0) AS is_affiliate,
          IF(taffic_source_medium  = "social", 1, 0) AS is_social,
          IF(taffic_source_medium NOT IN (
            "cpc","none","organic","referral","email","email_t","Email","afilliate","social",null
          ), 1, 0) AS is_other_traffic,
          IF(device_browser IN ("Chrome"), 1, 0) AS is_chrome,
          IF(device_browser IN ("Safari","Safari (in-app)"), 1, 0) AS is_safari,
          IF(device_browser IN ("Samsung Internet"), 1, 0) AS is_samsung_int,
          IF(device_browser IN ("Android Webview"), 1, 0) AS is_android_web,
          IF(device_browser IN ("Firefox"), 1, 0) AS is_firefox,
          IF(device_browser IN ("Edge"), 1, 0) AS is_edge,
          IF(device_browser IN ("Opera"), 1, 0) AS is_opera,
          IF(device_browser IN ("Amazon Silk"), 1, 0) AS is_amazon_silk,
          IF(device_browser IN ("Internet Explorer"), 1, 0) AS is_internet_explorer,
          IF(device_browser NOT IN (
            "Chrome","Safari","Safari (in-app)","Samsung Internet","Android Webview","Firefox","Edge","Opera","Amazon Silk","Internet Explorer"),
            1, 0) AS is_other_browser,
          IF(device_os IN ("Android"), 1, 0) AS is_android,
          IF(device_os IN ("iOS"), 1, 0) AS is_ios,
          IF(device_os IN ("Windows"), 1, 0) AS is_windows,
          IF(device_os IN ("Macintosh"), 1, 0) AS is_macintosh,
          IF(device_os NOT IN ("Android","Macintosh","iOS","Windows"), 1, 0) AS is_other_os,
          language,
          CASE
            WHEN first_touch_hour >= 1 AND first_touch_hour < 6 THEN "night_1_6"
            WHEN first_touch_hour >= 6 AND first_touch_hour < 11 THEN "morning_6_11"
            WHEN first_touch_hour >= 11 AND first_touch_hour < 14 THEN "lunch_11_14"
            WHEN first_touch_hour >= 14 AND first_touch_hour < 17 THEN "afternoon_14_17"
            WHEN first_touch_hour >= 17 AND first_touch_hour < 19 THEN "dinner_17_19"
            WHEN first_touch_hour >= 19 AND first_touch_hour < 22 THEN "evening_19_23"
            WHEN first_touch_hour >= 22 OR first_touch_hour = 0 THEN "latenight_23_1"
          END AS daypart,
          ROW_NUMBER() OVER (PARTITION BY user_pseudo_id ORDER BY timestamp DESC) AS row_num
        FROM events
        WHERE name = "user_engagement"
      )
      WHERE row_num = 1
    ),
    user_labels AS (
      SELECT DISTINCT
        user_pseudo_id,
        1 AS label
      FROM events, UNNEST(params) AS params
      WHERE name = "__ML_MODEL_LABEL_NAME__"
      AND params.key = "__ML_MODEL_LABEL_KEY__"
      AND __ML_MODEL_LABEL_VALUE_STATEMENT__
    ),
    user_aggregate_behavior AS (
      SELECT
        user_pseudo_id,
        SUM(IF(params.key = "engagement_time_msec", params.value.int_value, 0)) AS engagement_time,
        SUM(IF(name = "page_view", 1, 0)) AS cnt_page_view,
        SUM(IF(name = "user_engagement", 1, 0)) AS cnt_user_engagement,
        __ML_MODEL_FEATURES__
      FROM events, UNNEST(params) AS params
      GROUP BY user_pseudo_id
    )
    SELECT
      fv.*,
      uab.* EXCEPT (user_pseudo_id),
      IFNULL(ul.label, 0) AS label
    FROM first_values AS fv
    INNER JOIN user_aggregate_behavior AS uab
    ON fv.user_pseudo_id = uab.user_pseudo_id
    LEFT OUTER JOIN user_labels AS ul
    ON fv.user_pseudo_id = ul.user_pseudo_id
  ))
)
