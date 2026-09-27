"""SQL used in the project. Cleaning checks first, then analysis. All run on fitbit.db (SQLite)."""

CLEANING = {
    "Users and date range per table": """
SELECT 'daily_activity' AS tbl, COUNT(DISTINCT Id) AS users, COUNT(*) AS rows, MIN(ActivityDate) AS first_day, MAX(ActivityDate) AS last_day FROM daily_activity
UNION ALL SELECT 'sleep_day', COUNT(DISTINCT Id), COUNT(*), MIN(SleepDay), MAX(SleepDay) FROM sleep_day
UNION ALL SELECT 'weight_log', COUNT(DISTINCT Id), COUNT(*), MIN(Date), MAX(Date) FROM weight_log
UNION ALL SELECT 'hourly', COUNT(DISTINCT Id), COUNT(*), MIN(ActivityDate), MAX(ActivityDate) FROM hourly;""",

    "Duplicate check (daily activity)": """
SELECT Id, ActivityDate, COUNT(*) AS n
FROM daily_activity GROUP BY Id, ActivityDate HAVING n > 1;""",

    "Blank / negative check": """
SELECT
  SUM(TotalSteps IS NULL) AS null_steps, SUM(Calories IS NULL) AS null_calories,
  MIN(TotalSteps) AS min_steps, MIN(TotalDistance) AS min_distance, MIN(Calories) AS min_calories,
  MAX(TotalSteps) AS max_steps, MAX(Calories) AS max_calories
FROM daily_activity;""",

    "Non-wear days (1440 sedentary minutes)": """
SELECT COUNT(*) AS non_wear_days,
       SUM(TotalSteps = 0) AS with_zero_steps,
       SUM(Calories = 0) AS with_zero_calories,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM daily_activity), 1) AS pct_of_days
FROM daily_activity WHERE SedentaryMinutes = 1440;""",

    "Sleep duplicates removed": """
SELECT COUNT(*) AS rows_loaded, COUNT(DISTINCT Id || SleepDay) AS unique_user_days FROM sleep_day;""",

    "Weight: manual vs automatic, fat filled": """
SELECT IsManualReport, COUNT(*) AS entries, COUNT(DISTINCT Id) AS users, COUNT(Fat) AS fat_filled
FROM weight_log GROUP BY IsManualReport;""",
}

ANALYSIS = {
    "1. Average activity by weekday": """
SELECT weekday, ROUND(AVG(TotalSteps)) AS avg_steps, ROUND(AVG(Calories)) AS avg_calories,
       ROUND(AVG(ActiveMinutes)) AS avg_active_min, ROUND(AVG(SedentaryMinutes)) AS avg_sedentary_min
FROM daily_clean GROUP BY weekday ORDER BY weekday;""",

    "2. User segments by average daily steps": """
WITH u AS (SELECT Id, AVG(TotalSteps) AS avg_steps, AVG(Calories) AS avg_cal, COUNT(*) AS days FROM daily_clean GROUP BY Id)
SELECT CASE WHEN avg_steps < 5000 THEN '1 Sedentary (<5k)'
            WHEN avg_steps < 7500 THEN '2 Lightly active (5k-7.5k)'
            WHEN avg_steps < 10000 THEN '3 Fairly active (7.5k-10k)'
            ELSE '4 Very active (10k+)' END AS segment,
       COUNT(*) AS users, ROUND(AVG(avg_steps)) AS avg_steps, ROUND(AVG(avg_cal)) AS avg_calories
FROM u GROUP BY segment ORDER BY segment;""",

    "3. Share of the day in each activity level": """
SELECT ROUND(AVG(SedentaryMinutes)) AS sedentary_min, ROUND(AVG(LightlyActiveMinutes)) AS light_min,
       ROUND(AVG(FairlyActiveMinutes)) AS fair_min, ROUND(AVG(VeryActiveMinutes)) AS very_min,
       ROUND(100.0 * AVG(SedentaryMinutes) / 1440, 1) AS pct_sedentary
FROM daily_clean;""",

    "4. Calories burned by step bucket": """
SELECT CASE WHEN TotalSteps < 5000 THEN '1 <5k' WHEN TotalSteps < 10000 THEN '2 5k-10k'
            WHEN TotalSteps < 15000 THEN '3 10k-15k' ELSE '4 15k+' END AS step_bucket,
       COUNT(*) AS days, ROUND(AVG(Calories)) AS avg_calories
FROM daily_clean GROUP BY step_bucket ORDER BY step_bucket;""",

    "5. Average steps by hour of day": """
SELECT Hour, ROUND(AVG(StepTotal), 1) AS avg_steps, ROUND(AVG(Calories), 1) AS avg_calories
FROM hourly GROUP BY Hour ORDER BY Hour;""",

    "6. Sleep summary by weekday": """
SELECT CASE strftime('%w', SleepDay) WHEN '0' THEN '7 Sun' WHEN '1' THEN '1 Mon' WHEN '2' THEN '2 Tue'
            WHEN '3' THEN '3 Wed' WHEN '4' THEN '4 Thu' WHEN '5' THEN '5 Fri' ELSE '6 Sat' END AS weekday,
       ROUND(AVG(TotalMinutesAsleep) / 60.0, 2) AS avg_hours_asleep,
       ROUND(AVG(TotalTimeInBed) / 60.0, 2) AS avg_hours_in_bed,
       ROUND(100.0 * SUM(TotalMinutesAsleep) / SUM(TotalTimeInBed), 1) AS sleep_efficiency_pct
FROM sleep_day GROUP BY weekday ORDER BY weekday;""",

    "7. Sleep vs activity (joined on user + day)": """
SELECT CASE WHEN a.TotalSteps < 5000 THEN '1 <5k steps' WHEN a.TotalSteps < 10000 THEN '2 5k-10k steps' ELSE '3 10k+ steps' END AS steps_bucket,
       COUNT(*) AS nights, ROUND(AVG(s.TotalMinutesAsleep) / 60.0, 2) AS avg_hours_asleep
FROM daily_clean a JOIN sleep_day s ON a.Id = s.Id AND a.ActivityDate = s.SleepDay
GROUP BY steps_bucket ORDER BY steps_bucket;""",

    "8. Tracker usage: days worn per user": """
SELECT CASE WHEN days >= 28 THEN '1 Consistent (28+ days)' WHEN days >= 20 THEN '2 Regular (20-27)' ELSE '3 Occasional (<20)' END AS usage,
       COUNT(*) AS users
FROM (SELECT Id, COUNT(*) AS days FROM daily_clean GROUP BY Id) GROUP BY usage ORDER BY usage;""",

    "9. Feature usage: who uses sleep and weight": """
SELECT (SELECT COUNT(DISTINCT Id) FROM daily_activity) AS activity_users,
       (SELECT COUNT(DISTINCT Id) FROM sleep_day) AS sleep_users,
       (SELECT COUNT(DISTINCT Id) FROM weight_log) AS weight_users;""",

    "10. Wear-time trend over the month (weekly)": """
SELECT strftime('%W', ActivityDate) AS week_no, COUNT(DISTINCT Id) AS users_worn,
       ROUND(AVG(TotalSteps)) AS avg_steps
FROM daily_clean GROUP BY week_no ORDER BY week_no;""",
}
