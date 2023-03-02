CREATE OR REPLACE TABLE `__PROJECT_ID__.__ML_MODEL_DATASET__.scores` AS (
  WITH max_date AS (
    SELECT SUBSTR(MAX(table_id), LENGTH('events_') + 1) AS latest
    FROM `__PROJECT_ID__.__GA4_DATASET__.__TABLES_SUMMARY__`
    WHERE table_id LIKE 'events_%'
  ),
  events AS (
    SELECT
      user_pseudo_id,
      event_name AS name,
      event_params AS params
    FROM `__PROJECT_ID__.__GA4_DATASET__.events_*`
    WHERE _TABLE_SUFFIX = FORMAT_DATE(
      '%Y%m%d',
      DATE_SUB(
        PARSE_DATE('%Y%m%d', (SELECT latest FROM max_date)),
        INTERVAL 1 DAY))
  ),
  visitors_with_score_yesterday AS (
    SELECT DISTINCT user_pseudo_id
    FROM events, UNNEST(params) AS params
    WHERE name = 'prop_score'
    AND params.value.string_value = 'Predicted_Value'
  ),
  visitors_needing_score_yesterday AS (
    SELECT DISTINCT user_pseudo_id
    FROM events
    WHERE user_pseudo_id NOT IN (
      SELECT user_pseudo_id
      FROM visitors_with_score_yesterday
    )
  ),
  prediction AS (
    SELECT
      user_pseudo_id,
      predicted_label,
      predicted_label * 100 AS final_score,
      NTILE(10) OVER (ORDER BY MIN(predicted_label) ASC) AS normalized_score
    FROM `__PROJECT_ID__.__ML_MODEL_DATASET__.predictions`
    GROUP BY 1,2,3
  )
  SELECT
    prediction.user_pseudo_id AS client_id,
    'prop_score' AS event_name,
    prediction.final_score AS score,
    prediction.normalized_score AS normalized_score,
    'Predicted_Value' AS type
  FROM prediction
  INNER JOIN visitors_needing_score_yesterday -- only predict scores for users that don't have one already
  ON prediction.user_pseudo_id = visitors_needing_score_yesterday.user_pseudo_id
  GROUP BY 1,2,3,4,5
  ORDER BY score DESC
)
