import pytest
import pandas as pd
from datetime import timedelta
from app import assign_aging_bucket

# 1. Test assign_aging_bucket for every bucket
@pytest.mark.parametrize("days,expected", [
    (-1,    "Overdue"),
    (0,     "0–30 days"),
    (15,    "0–30 days"),
    (30,    "0–30 days"),
    (31,    "31–60 days"),
    (60,    "31–60 days"),
    (61,    "61–90 days"),
    (90,    "61–90 days"),
    (91,    ">90 days"),
    (150,   ">90 days"),
])
def test_assign_aging_bucket(days, expected):
    assert assign_aging_bucket(days) == expected

# 2. Test amount_due calculation
def compute_amount_due(total, paid, credit):
    return total - paid - credit

@pytest.mark.parametrize("total,paid,credit,expected", [
    (100, 0,   0,    100),
    (100, 50,  0,     50),
    (100, 0,   25,    75),
    (100, 30,  20,    50),
    (100, 120, 0,    -20),   # overpaid
    (100, 50,  60,    -10),  # paid + credit > total
])
def test_amount_due(total, paid, credit, expected):
    assert compute_amount_due(total, paid, credit) == expected

# 3. Edge case: missing due_date → days_to_due NaN
def test_assign_bucket_nan():
    with pytest.raises(TypeError):
        assign_aging_bucket(float("nan"))

# 4. DataFrame integration test
def test_dataframe_amount_and_bucket():
    today = pd.Timestamp.today().normalize()
    df = pd.DataFrame({
        "bill_id":     ["A", "B", "C"],
        "vendor_name": ["X", "Y", "Z"],
        "due_date":    [today - timedelta(days=5), today + timedelta(days=20), today + timedelta(days=100)],
        "total":       [100, 200, 300],
        "total_paid":  [20, 50, 0],
        "total_credit":[10, 0,  100]
    })
    df["amount_due"]   = df["total"] - df["total_paid"] - df["total_credit"]
    df["days_to_due"]  = (df["due_date"] - today).dt.days
    df["aging_bucket"] = df["days_to_due"].apply(assign_aging_bucket)

    # Check amount_due values
    assert df.loc[0, "amount_due"] == 70
    assert df.loc[1, "amount_due"] == 150
    assert df.loc[2, "amount_due"] == 200

    # Check aging buckets
    assert df.loc[0, "aging_bucket"] == "Overdue"
    assert df.loc[1, "aging_bucket"] == "0–30 days"
    assert df.loc[2, "aging_bucket"] == ">90 days"
