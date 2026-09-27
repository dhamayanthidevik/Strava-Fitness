"""Build fitbit.db from the raw CSVs: load -> convert dates -> drop duplicates -> create cleaned view.
Run:  python build_db.py   (the CSV files must be in the same folder)"""
import sqlite3
import pandas as pd

conn = sqlite3.connect("fitbit.db")
D = "%m/%d/%Y"
DT = "%m/%d/%Y %I:%M:%S %p"

# 1. Daily activity (dailyCalories / dailySteps / dailyIntensities are subsets of this file)
da = pd.read_csv("dailyActivity_merged.csv")
da["ActivityDate"] = pd.to_datetime(da["ActivityDate"], format=D).dt.strftime("%Y-%m-%d")
da.drop_duplicates().to_sql("daily_activity", conn, if_exists="replace", index=False)

# 2. Sleep (3 exact duplicate rows are dropped)
sd = pd.read_csv("sleepDay_merged.csv").drop_duplicates()
sd["SleepDay"] = pd.to_datetime(sd["SleepDay"], format=DT).dt.strftime("%Y-%m-%d")
sd.to_sql("sleep_day", conn, if_exists="replace", index=False)

# 3. Weight
w = pd.read_csv("weightLogInfo_merged.csv")
w["Date"] = pd.to_datetime(w["Date"], format=DT).dt.strftime("%Y-%m-%d")
w.to_sql("weight_log", conn, if_exists="replace", index=False)

# 4. Hourly steps + calories + intensity merged into one table
h = pd.read_csv("hourlySteps_merged.csv")
for f in ["hourlyCalories_merged.csv", "hourlyIntensities_merged.csv"]:
    h = h.merge(pd.read_csv(f), on=["Id", "ActivityHour"], how="left")
t = pd.to_datetime(h["ActivityHour"], format=DT)
h["ActivityDate"] = t.dt.strftime("%Y-%m-%d")
h["Hour"] = t.dt.hour
h.drop(columns="ActivityHour").to_sql("hourly", conn, if_exists="replace", index=False)

# 5. Cleaned view. Non-wear day = 1440 sedentary minutes (tracker recorded no movement or was not worn)
conn.executescript("""
DROP VIEW IF EXISTS daily_clean;
CREATE VIEW daily_clean AS
SELECT *,
  CASE strftime('%w', ActivityDate) WHEN '0' THEN '7 Sun' WHEN '1' THEN '1 Mon' WHEN '2' THEN '2 Tue'
       WHEN '3' THEN '3 Wed' WHEN '4' THEN '4 Thu' WHEN '5' THEN '5 Fri' ELSE '6 Sat' END AS weekday,
  VeryActiveMinutes + FairlyActiveMinutes + LightlyActiveMinutes AS ActiveMinutes
FROM daily_activity
WHERE SedentaryMinutes < 1440;
""")
conn.commit()

for tbl in ["daily_activity", "daily_clean", "sleep_day", "weight_log", "hourly"]:
    print(tbl, conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0], "rows")
