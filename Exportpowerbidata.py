"""Export Power BI-ready CSVs from fitbit.db (created by build_db.py).
Run this after build_db.py, from the same folder as fitbit.db.
Output: powerbi_data/dim_users.csv, fact_daily.csv, fact_hourly.csv, weight_log.csv
"""
import sqlite3
import pandas as pd
import os

conn = sqlite3.connect("fitbit.db")
os.makedirs("powerbi_data", exist_ok=True)

# 1. dim_users: one row per user with segment + feature usage flags
users = pd.read_sql("""
WITH u AS (SELECT Id, AVG(TotalSteps) a, COUNT(*) DaysWorn FROM daily_clean GROUP BY Id)
SELECT u.Id, ROUND(a) AS AvgSteps, DaysWorn,
  CASE WHEN a<5000 THEN 'Sedentary (<5k)' WHEN a<7500 THEN 'Lightly active (5k-7.5k)'
       WHEN a<10000 THEN 'Fairly active (7.5k-10k)' ELSE 'Very active (10k+)' END AS Segment,
  CASE WHEN a<5000 THEN 1 WHEN a<7500 THEN 2 WHEN a<10000 THEN 3 ELSE 4 END AS SegmentOrder,
  (SELECT COUNT(*)>0 FROM sleep_day s WHERE s.Id=u.Id) AS TracksSleep,
  (SELECT COUNT(*)>0 FROM weight_log w WHERE w.Id=u.Id) AS LogsWeight
FROM u
""", conn)
users[["TracksSleep", "LogsWeight"]] = users[["TracksSleep", "LogsWeight"]].map(lambda v: "Yes" if v else "No")
users.to_csv("powerbi_data/dim_users.csv", index=False)

# 2. fact_daily: cleaned daily activity + same-day sleep
daily = pd.read_sql("""
SELECT d.Id, d.ActivityDate AS Date, substr(d.weekday,3) AS Weekday, CAST(substr(d.weekday,1,1) AS INT) AS WeekdayNum,
  d.TotalSteps, d.TotalDistance, d.VeryActiveMinutes, d.FairlyActiveMinutes, d.LightlyActiveMinutes, d.SedentaryMinutes,
  d.ActiveMinutes, d.Calories, s.TotalMinutesAsleep AS MinutesAsleep, s.TotalTimeInBed AS MinutesInBed
FROM daily_clean d LEFT JOIN sleep_day s ON s.Id=d.Id AND s.SleepDay=d.ActivityDate
""", conn)
daily.to_csv("powerbi_data/fact_daily.csv", index=False)

# 3. fact_hourly: hourly steps + calories + intensity
hourly = pd.read_sql("""
SELECT Id, ActivityDate AS Date, Hour, StepTotal AS Steps, Calories, TotalIntensity, AverageIntensity FROM hourly
""", conn)
hourly.to_csv("powerbi_data/fact_hourly.csv", index=False)

# 4. weight_log
weight = pd.read_sql("SELECT Id, Date, WeightKg, BMI, IsManualReport FROM weight_log", conn)
weight.to_csv("powerbi_data/weight_log.csv", index=False)

print(f"dim_users: {len(users)} rows")
print(f"fact_daily: {len(daily)} rows")
print(f"fact_hourly: {len(hourly)} rows")
print(f"weight_log: {len(weight)} rows")