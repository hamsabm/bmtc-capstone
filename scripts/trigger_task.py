"""Helper script to trigger the task with delta data."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.db import execute, query

print("Inserting delta row...")
execute([
    (
        """INSERT INTO BMTC_DW.TRIP.TRIP_DATA
            (TRIP_ID, BUS_ID, ROUTE_ID, DRIVER_ID, CONDUCTOR_ID, TRIP_DATE,
             SCHEDULED_START, ACTUAL_START, ACTUAL_END, DELAY_MINUTES, PASSENGER_COUNT,
             DISTANCE_KM, TRIP_STATUS)
        SELECT COALESCE(MAX(TRIP_ID), 0) + 1, 1, 1, 1, 13, CURRENT_DATE(),
               CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), NULL, 0, 10, 15.0, 'COMPLETED'
        FROM BMTC_DW.TRIP.TRIP_DATA""",
        None
    )
])

print("Executing task...")
execute([("EXECUTE TASK BMTC_DW.TRIP.TASK_REFRESH_TRIP_SUMMARY", None)])

print("Waiting 10 seconds for task completion...")
time.sleep(10)

hist = query("""
    SELECT STATE, SCHEDULED_TIME, COMPLETED_TIME, ERROR_MESSAGE
    FROM TABLE(BMTC_DW.INFORMATION_SCHEMA.TASK_HISTORY(TASK_NAME => 'TASK_REFRESH_TRIP_SUMMARY', RESULT_LIMIT => 5))
    ORDER BY SCHEDULED_TIME DESC
""")
print(hist)
