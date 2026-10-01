"""
Synthetic transaction data generator for FraudLens demo.

Generates ~50,000 transactions for ~300 customers with realistic fraud patterns.
All data is 100% synthetic — no real personal or financial data.

Fraud patterns (learnable but noisy):
  - High amount vs customer average + new device + foreign country + late night + burst velocity
  - Unusual merchant category for customer + large distance from home
  - Multiple small transactions in 1h (velocity burst)
"""

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
fake.seed_instance(SEED)

N_CUSTOMERS = 300
N_TRANSACTIONS = 50_000
FRAUD_RATE = 0.02  # 2% target; will be close after noise

MERCHANT_CATEGORIES = [
    "grocery", "electronics", "travel", "restaurant", "clothing",
    "fuel", "entertainment", "healthcare", "hotel", "online_retail",
    "jewelry", "gaming", "crypto_exchange", "money_transfer", "subscription",
]

COUNTRIES = [
    "US", "GB", "CA", "AU", "DE", "FR", "NG", "RO", "VN", "CN",
    "BR", "IN", "MX", "ZA", "UA", "RU", "TR", "PH", "ID", "TH",
]

# Higher-risk countries for fraud patterns (purely synthetic label)
RISK_COUNTRIES = {"NG", "RO", "VN", "UA", "RU", "PH"}


def generate_customers(n: int) -> pd.DataFrame:
    customers = []
    for cid in range(1, n + 1):
        home_country = random.choice(COUNTRIES)
        fav_categories = random.sample(MERCHANT_CATEGORIES, k=random.randint(3, 7))
        customers.append({
            "customer_id": f"C{cid:05d}",
            "home_country": home_country,
            "account_age_days": random.randint(30, 3650),
            "avg_amount_30d": round(random.uniform(20, 800), 2),
            "favorite_categories": fav_categories,
            "risk_profile": random.choices(["low", "medium", "high"], weights=[0.65, 0.25, 0.10])[0],
        })
    return pd.DataFrame(customers)


def _make_transaction(
    tx_id: int,
    customer: dict,
    timestamp: pd.Timestamp,
    is_fraud: bool,
    recent_tx_1h: int,
    recent_tx_24h: int,
) -> dict:
    """Build one transaction row with realistic feature values."""
    home = customer["home_country"]
    avg_amt = customer["avg_amount_30d"]

    if is_fraud:
        # Fraud patterns with noise
        use_pattern = random.random()

        if use_pattern < 0.35:
            # Pattern 1: high amount + new device + foreign + late night
            amount = round(avg_amt * random.uniform(4.0, 12.0), 2)
            country = random.choice([c for c in COUNTRIES if c != home])
            device_is_new = True
            hour = random.randint(0, 5)  # late night / early morning
            burst = random.randint(3, 8)
            merchant_cat = random.choice(["electronics", "jewelry", "crypto_exchange", "money_transfer"])

        elif use_pattern < 0.60:
            # Pattern 2: velocity burst + small amounts
            amount = round(random.uniform(1, 30), 2)
            country = random.choice([c for c in COUNTRIES if c in RISK_COUNTRIES] + [home])
            device_is_new = random.random() < 0.6
            hour = random.randint(10, 22)
            burst = random.randint(6, 15)
            merchant_cat = random.choice(["online_retail", "gaming", "subscription"])

        elif use_pattern < 0.80:
            # Pattern 3: foreign risk country + large amount
            amount = round(avg_amt * random.uniform(2.0, 8.0), 2)
            country = random.choice(list(RISK_COUNTRIES))
            device_is_new = random.random() < 0.5
            hour = random.randint(0, 23)
            burst = recent_tx_1h
            merchant_cat = random.choice(["money_transfer", "crypto_exchange", "travel", "hotel"])

        else:
            # Pattern 4: noisy fraud (harder to detect — edge cases)
            amount = round(avg_amt * random.uniform(1.5, 4.0), 2)
            country = home  # looks legit
            device_is_new = random.random() < 0.3
            hour = random.randint(8, 20)
            burst = random.randint(2, 5)
            merchant_cat = random.choice(customer["favorite_categories"])

        card_present = False
        distance_km = round(random.uniform(200, 8000), 1)

    else:
        # Legitimate transaction (with some suspicious-looking edge cases for realism)
        amount_multiplier = np.random.lognormal(mean=0.0, sigma=0.6)  # natural skew
        amount = round(min(avg_amt * amount_multiplier, avg_amt * 6), 2)
        amount = max(amount, 1.0)

        # Occasionally a legit txn looks suspicious
        is_edge_case = random.random() < 0.05
        country = home if random.random() < 0.80 else random.choice(COUNTRIES)
        device_is_new = is_edge_case and random.random() < 0.3
        hour = random.randint(0, 23)
        burst = recent_tx_1h if random.random() < 0.7 else random.randint(0, 3)
        merchant_cat = random.choice(customer["favorite_categories"])
        card_present = random.random() < 0.55
        distance_km = round(abs(np.random.normal(50, 80)), 1)

    is_foreign = int(country != home)
    amount_vs_avg = round(amount / max(avg_amt, 1), 3)

    return {
        "transaction_id": f"TX{tx_id:07d}",
        "customer_id": customer["customer_id"],
        "timestamp": timestamp,
        "amount": amount,
        "merchant_category": merchant_cat,
        "country": country,
        "customer_home_country": home,
        "is_foreign": is_foreign,
        "device_is_new": int(device_is_new),
        "hour_of_day": hour,
        "day_of_week": timestamp.dayofweek,
        "txns_last_1h": burst,
        "txns_last_24h": recent_tx_24h,
        "avg_amount_30d": avg_amt,
        "amount_vs_avg_ratio": amount_vs_avg,
        "distance_from_home_km": distance_km,
        "card_present": int(card_present),
        "account_age_days": customer["account_age_days"],
        "is_fraud": int(is_fraud),
    }


def generate_transactions(customers_df: pd.DataFrame, n: int) -> pd.DataFrame:
    customers = customers_df.to_dict("records")
    # build customer lookup
    cust_map = {c["customer_id"]: c for c in customers}

    transactions = []
    # Track velocity per customer (simplified: use running counters)
    cust_recent_1h: dict[str, list] = {c["customer_id"]: [] for c in customers}
    cust_recent_24h: dict[str, list] = {c["customer_id"]: [] for c in customers}

    # Spread transactions over 90 days
    start_ts = pd.Timestamp("2024-01-01")
    end_ts = pd.Timestamp("2024-04-01")
    total_seconds = int((end_ts - start_ts).total_seconds())

    # Decide which will be fraud (2% target)
    n_fraud = int(n * FRAUD_RATE)
    fraud_indices = set(random.sample(range(n), n_fraud))

    for i in range(n):
        cust = random.choice(customers)
        cid = cust["customer_id"]
        ts = start_ts + pd.Timedelta(seconds=random.randint(0, total_seconds))

        # Prune old velocity windows
        cutoff_1h = ts - pd.Timedelta(hours=1)
        cutoff_24h = ts - pd.Timedelta(hours=24)
        cust_recent_1h[cid] = [t for t in cust_recent_1h[cid] if t > cutoff_1h]
        cust_recent_24h[cid] = [t for t in cust_recent_24h[cid] if t > cutoff_24h]

        is_fraud = i in fraud_indices

        tx = _make_transaction(
            tx_id=i + 1,
            customer=cust,
            timestamp=ts,
            is_fraud=is_fraud,
            recent_tx_1h=len(cust_recent_1h[cid]),
            recent_tx_24h=len(cust_recent_24h[cid]),
        )
        transactions.append(tx)

        # Update velocity tracking
        cust_recent_1h[cid].append(ts)
        cust_recent_24h[cid].append(ts)

    df = pd.DataFrame(transactions)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def generate_demo_cases(customers_df: pd.DataFrame, n: int = 40) -> list[dict]:
    """
    Generate seeded demo cases: mix of clearly suspicious and borderline.
    These are precomputed so the demo loads instantly.
    """
    customers = customers_df.to_dict("records")
    cases = []
    ts_base = pd.Timestamp("2024-04-01 09:00:00")

    # 15 clearly suspicious
    for i in range(15):
        cust = customers[i % len(customers)]
        home = cust["home_country"]
        foreign = random.choice([c for c in COUNTRIES if c != home])
        ts = ts_base + pd.Timedelta(hours=i * 2)
        row = {
            "transaction_id": f"DEMO{i+1:03d}",
            "customer_id": cust["customer_id"],
            "timestamp": str(ts),
            "amount": round(cust["avg_amount_30d"] * random.uniform(5, 10), 2),
            "merchant_category": random.choice(["electronics", "crypto_exchange", "money_transfer"]),
            "country": foreign,
            "customer_home_country": home,
            "is_foreign": 1,
            "device_is_new": 1,
            "hour_of_day": random.randint(1, 4),
            "day_of_week": ts.dayofweek,
            "txns_last_1h": random.randint(4, 10),
            "txns_last_24h": random.randint(8, 20),
            "avg_amount_30d": cust["avg_amount_30d"],
            "amount_vs_avg_ratio": round(random.uniform(5, 10), 3),
            "distance_from_home_km": round(random.uniform(2000, 8000), 1),
            "card_present": 0,
            "account_age_days": cust["account_age_days"],
            "is_fraud": 1,
            "demo_label": "suspicious",
        }
        cases.append(row)

    # 15 clearly normal
    for i in range(15):
        cust = customers[(i + 15) % len(customers)]
        ts = ts_base + pd.Timedelta(hours=i * 3 + 1)
        row = {
            "transaction_id": f"DEMO{i+16:03d}",
            "customer_id": cust["customer_id"],
            "timestamp": str(ts),
            "amount": round(cust["avg_amount_30d"] * random.uniform(0.5, 1.5), 2),
            "merchant_category": random.choice(cust["favorite_categories"]),
            "country": cust["home_country"],
            "customer_home_country": cust["home_country"],
            "is_foreign": 0,
            "device_is_new": 0,
            "hour_of_day": random.randint(9, 18),
            "day_of_week": ts.dayofweek,
            "txns_last_1h": random.randint(0, 2),
            "txns_last_24h": random.randint(1, 5),
            "avg_amount_30d": cust["avg_amount_30d"],
            "amount_vs_avg_ratio": round(random.uniform(0.5, 1.5), 3),
            "distance_from_home_km": round(random.uniform(0, 50), 1),
            "card_present": 1,
            "account_age_days": cust["account_age_days"],
            "is_fraud": 0,
            "demo_label": "normal",
        }
        cases.append(row)

    # 10 borderline (ambiguous)
    for i in range(10):
        cust = customers[(i + 30) % len(customers)]
        home = cust["home_country"]
        ts = ts_base + pd.Timedelta(hours=i * 4 + 2)
        row = {
            "transaction_id": f"DEMO{i+31:03d}",
            "customer_id": cust["customer_id"],
            "timestamp": str(ts),
            "amount": round(cust["avg_amount_30d"] * random.uniform(2, 4), 2),
            "merchant_category": random.choice(["travel", "hotel", "electronics"]),
            "country": random.choice([c for c in COUNTRIES if c not in RISK_COUNTRIES and c != home]),
            "customer_home_country": home,
            "is_foreign": 1,
            "device_is_new": random.randint(0, 1),
            "hour_of_day": random.randint(20, 23),
            "day_of_week": ts.dayofweek,
            "txns_last_1h": random.randint(1, 3),
            "txns_last_24h": random.randint(2, 8),
            "avg_amount_30d": cust["avg_amount_30d"],
            "amount_vs_avg_ratio": round(random.uniform(2, 4), 3),
            "distance_from_home_km": round(random.uniform(300, 2000), 1),
            "card_present": 0,
            "account_age_days": cust["account_age_days"],
            "is_fraud": 0,  # legit travel edge cases
            "demo_label": "borderline",
        }
        cases.append(row)

    return cases


def main():
    out_dir = Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generating customers...")
    customers_df = generate_customers(N_CUSTOMERS)
    customers_df.to_csv(out_dir / "customers.csv", index=False)

    # Save favorite_categories as JSON string for CSV compat
    customers_export = customers_df.copy()
    customers_export["favorite_categories"] = customers_export["favorite_categories"].apply(json.dumps)
    customers_export.to_csv(out_dir / "customers.csv", index=False)
    print(f"  Saved {len(customers_df)} customers")

    print("Generating transactions...")
    txn_df = generate_transactions(customers_df, N_TRANSACTIONS)
    txn_df.to_parquet(out_dir / "transactions.parquet", index=False)
    txn_df.to_csv(out_dir / "transactions.csv", index=False)

    fraud_count = txn_df["is_fraud"].sum()
    fraud_pct = fraud_count / len(txn_df) * 100
    print(f"  Saved {len(txn_df)} transactions | Fraud: {fraud_count} ({fraud_pct:.2f}%)")

    print("Generating demo cases...")
    demo_cases = generate_demo_cases(customers_df, n=40)
    demo_df = pd.DataFrame(demo_cases)
    demo_df.to_json(out_dir / "demo_cases.json", orient="records", indent=2)
    print(f"  Saved {len(demo_cases)} demo cases")

    print("\nData generation complete. Output in data/raw/")


if __name__ == "__main__":
    main()
