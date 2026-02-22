"""
Synthetic Data Generator for a Tango-like Live-Streaming Platform.

Generates realistic data for: users, streamers, streams, gifts,
gift_transactions, subscriptions, chat_messages, user_sessions,
ab_experiments, ab_assignments, ab_events.

Usage:
    python scripts/data_generator.py
"""

import os
import json
import random
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

try:
    from faker import Faker
except ImportError:
    print("Install faker: pip install faker")
    raise

# --------------- configuration ---------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

NUM_USERS = 10_000
NUM_STREAMERS = 500
NUM_STREAMS = 20_000
NUM_GIFT_TRANSACTIONS = 200_000
NUM_SUBSCRIPTIONS = 15_000
NUM_CHAT_MESSAGES = 300_000
NUM_USER_SESSIONS = 500_000

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

fake = Faker()
Faker.seed(SEED)

# Date range: 2 years of history
DATE_START = datetime(2024, 1, 1)
DATE_END = datetime(2025, 12, 31)
TOTAL_DAYS = (DATE_END - DATE_START).days

COUNTRIES = [
    "US", "GB", "DE", "FR", "BR", "IN", "TR", "EG", "SA", "AE",
    "MX", "CO", "AR", "PH", "ID", "NG", "KE", "ZA", "PK", "JP",
]
COUNTRY_WEIGHTS = [
    18, 8, 6, 5, 7, 10, 5, 4, 4, 3,
    4, 3, 3, 5, 4, 3, 2, 2, 3, 1,
]

PLATFORMS = ["ios", "android", "web"]
PLATFORM_WEIGHTS = [40, 50, 10]

GENDERS = ["M", "F", "Other"]
GENDER_WEIGHTS = [45, 48, 7]

CATEGORIES = ["music", "talk_show", "gaming", "dance", "cooking",
              "fitness", "art", "education", "other"]
CATEGORY_WEIGHTS = [20, 15, 20, 15, 8, 7, 5, 5, 5]

TIERS = ["bronze", "silver", "gold", "diamond"]

SUBSCRIPTION_PLANS = {
    "basic": 4.99,
    "premium": 9.99,
    "vip": 14.99,
}

STREAM_TITLES_TEMPLATES = [
    "🎵 {category} vibes — come hang!",
    "Late night {category} session 🔥",
    "{category} stream — let's go!",
    "Chill {category} with me ✨",
    "🎉 Special {category} stream!",
    "Daily {category} — day {day}",
    "{category} marathon 🏆",
    "Good morning {category} ☀️",
    "Weekend {category} party 🎊",
    "Ask me anything — {category} edition",
]

# --------------- gift catalog ---------------
GIFT_CATALOG = [
    # (name, coin_cost, category, animation_type)
    ("Rose", 10, "basic", "standard"),
    ("Heart", 20, "basic", "standard"),
    ("Thumbs Up", 5, "basic", "standard"),
    ("Star", 50, "basic", "animated"),
    ("Kiss", 30, "basic", "standard"),
    ("Fireworks", 100, "premium", "animated"),
    ("Sports Car", 500, "premium", "animated"),
    ("Crown", 200, "premium", "animated"),
    ("Diamond Ring", 1000, "luxury", "full_screen"),
    ("Yacht", 2000, "luxury", "full_screen"),
    ("Private Jet", 5000, "luxury", "full_screen"),
    ("Castle", 10000, "luxury", "full_screen"),
    ("Carnival Float", 300, "event_special", "full_screen"),
    ("Snowflake", 80, "event_special", "animated"),
    ("Dragon", 1500, "event_special", "full_screen"),
]

COINS_PER_USD = 100  # 100 coins = $1 USD


def random_date(start: datetime, end: datetime) -> datetime:
    """Return a random datetime between start and end."""
    delta = end - start
    secs = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=secs)


def weighted_random_date(start: datetime, end: datetime) -> datetime:
    """Bias towards more recent dates (exponential growth pattern)."""
    t = random.betavariate(2, 5)  # skew towards earlier, but we'll invert
    t = 1 - t  # now skews towards later
    delta = end - start
    return start + timedelta(seconds=int(t * delta.total_seconds()))


def peak_hour_bias() -> int:
    """Return an hour biased towards evening peak times."""
    weights = [
        1, 1, 0.5, 0.5, 0.5, 1, 2, 3,   # 0-7
        4, 4, 5, 5, 6, 6, 5, 5,          # 8-15
        7, 8, 10, 12, 14, 12, 8, 4,      # 16-23
    ]
    return random.choices(range(24), weights=weights, k=1)[0]


def generate_users():
    """Generate user records."""
    print(f"Generating {NUM_USERS} users...")
    users = []
    usernames_seen = set()

    for uid in range(1, NUM_USERS + 1):
        while True:
            uname = fake.user_name()[:20] + str(uid)
            if uname not in usernames_seen:
                usernames_seen.add(uname)
                break

        reg_date = random_date(DATE_START, DATE_END)
        country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
        gender = random.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0]
        platform = random.choices(PLATFORMS, weights=PLATFORM_WEIGHTS, k=1)[0]
        age = int(np.clip(np.random.normal(28, 8), 13, 65))

        users.append({
            "user_id": uid,
            "username": uname,
            "email": f"user{uid}@{fake.free_email_domain()}",
            "country": country,
            "gender": gender,
            "age": age,
            "registration_date": reg_date.strftime("%Y-%m-%d"),
            "is_streamer": 0,  # will be updated later
            "coin_balance": random.randint(0, 5000),
            "account_status": random.choices(
                ["active", "suspended", "deleted"],
                weights=[92, 5, 3], k=1
            )[0],
            "platform": platform,
        })
    return users


def generate_streamers(users):
    """Pick a subset of users as streamers and create streamer profiles."""
    print(f"Generating {NUM_STREAMERS} streamers...")
    streamer_user_ids = random.sample(range(1, NUM_USERS + 1), NUM_STREAMERS)

    # Mark users as streamers
    for u in users:
        if u["user_id"] in streamer_user_ids:
            u["is_streamer"] = 1

    streamers = []
    for sid, uid in enumerate(streamer_user_ids, start=1):
        user = users[uid - 1]
        category = random.choices(CATEGORIES, weights=CATEGORY_WEIGHTS, k=1)[0]
        follower_count = int(np.random.pareto(1.5) * 200) + 10
        follower_count = min(follower_count, 500_000)

        # Tier based on followers
        if follower_count > 50000:
            tier = "diamond"
        elif follower_count > 10000:
            tier = "gold"
        elif follower_count > 2000:
            tier = "silver"
        else:
            tier = "bronze"

        streamers.append({
            "streamer_id": sid,
            "user_id": uid,
            "display_name": fake.first_name() + "_" + random.choice(
                ["live", "official", "tv", "show", "music", "vibes", "star"]
            ),
            "category": category,
            "tier": tier,
            "follower_count": follower_count,
            "total_earnings": 0.0,  # will be computed after transactions
            "country": user["country"],
            "joined_date": user["registration_date"],
            "is_verified": 1 if tier in ("gold", "diamond") else random.choice([0, 0, 0, 1]),
        })
    return streamers


def generate_streams(streamers):
    """Generate live-stream sessions."""
    print(f"Generating {NUM_STREAMS} streams...")
    streams = []
    streamer_ids = [s["streamer_id"] for s in streamers]
    # Weight popular streamers more heavily
    streamer_weights = [s["follower_count"] for s in streamers]

    for stid in range(1, NUM_STREAMS + 1):
        sid = random.choices(streamer_ids, weights=streamer_weights, k=1)[0]
        streamer = streamers[sid - 1]
        category = streamer["category"]

        start = random_date(DATE_START, DATE_END)
        # Adjust to peak hours
        hour = peak_hour_bias()
        start = start.replace(hour=hour, minute=random.randint(0, 59))

        duration = int(np.clip(np.random.lognormal(3.5, 0.8), 5, 480))
        end = start + timedelta(minutes=duration)

        base_viewers = max(1, streamer["follower_count"] // 50)
        peak = int(np.clip(np.random.lognormal(math.log(base_viewers + 1), 0.7),
                           1, base_viewers * 3))
        avg_v = max(1, int(peak * random.uniform(0.3, 0.8)))

        day_num = (start - DATE_START).days
        title_template = random.choice(STREAM_TITLES_TEMPLATES)
        title = title_template.format(category=category.replace("_", " ").title(),
                                      day=day_num % 365 + 1)

        streams.append({
            "stream_id": stid,
            "streamer_id": sid,
            "title": title,
            "category": category,
            "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": duration,
            "peak_viewers": peak,
            "avg_viewers": avg_v,
            "total_gifts_value": 0,  # will be updated
            "status": "ended",
        })
    return streams


def generate_gift_transactions(users, streamers, streams, gifts):
    """Generate gift transactions with whale behaviour (power-law)."""
    print(f"Generating {NUM_GIFT_TRANSACTIONS} gift transactions...")
    transactions = []

    non_streamer_ids = [u["user_id"] for u in users if u["is_streamer"] == 0]
    # Create whale distribution: ~2% of users send ~50% of gifts
    num_whales = max(1, len(non_streamer_ids) // 50)
    whales = set(random.sample(non_streamer_ids, num_whales))

    sender_weights = []
    for uid in non_streamer_ids:
        if uid in whales:
            sender_weights.append(50)
        else:
            sender_weights.append(1)

    stream_ids = [s["stream_id"] for s in streams]
    stream_map = {s["stream_id"]: s for s in streams}

    gift_ids = list(range(len(gifts)))
    # Cheap gifts sent more often
    gift_weights = [1.0 / (g["coin_cost"] ** 0.3) for g in gifts]

    for txid in range(1, NUM_GIFT_TRANSACTIONS + 1):
        sender = random.choices(non_streamer_ids, weights=sender_weights, k=1)[0]
        stream_id = random.choice(stream_ids)
        stream = stream_map[stream_id]
        receiver = stream["streamer_id"]

        gift_idx = random.choices(gift_ids, weights=gift_weights, k=1)[0]
        gift = gifts[gift_idx]

        # Whales send more expensive gifts and higher quantity
        if sender in whales:
            quantity = random.choices([1, 2, 5, 10, 50, 100],
                                     weights=[20, 25, 25, 15, 10, 5], k=1)[0]
        else:
            quantity = random.choices([1, 1, 1, 2, 3],
                                     weights=[60, 15, 10, 10, 5], k=1)[0]

        total_coins = gift["coin_cost"] * quantity
        usd_value = round(total_coins / COINS_PER_USD, 2)

        # Transaction time within the stream window
        st = datetime.strptime(stream["start_time"], "%Y-%m-%d %H:%M:%S")
        et = datetime.strptime(stream["end_time"], "%Y-%m-%d %H:%M:%S")
        sent_at = random_date(st, et)

        transactions.append({
            "transaction_id": txid,
            "sender_id": sender,
            "receiver_id": receiver,
            "stream_id": stream_id,
            "gift_id": gift["gift_id"],
            "quantity": quantity,
            "total_coins": total_coins,
            "usd_value": usd_value,
            "sent_at": sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    # Aggregate gifts value per stream
    for tx in transactions:
        stream_map[tx["stream_id"]]["total_gifts_value"] += tx["total_coins"]

    return transactions


def generate_subscriptions(users, streamers):
    """Generate subscription records with churn patterns."""
    print(f"Generating {NUM_SUBSCRIPTIONS} subscriptions...")
    subscriptions = []
    non_streamer_ids = [u["user_id"] for u in users if u["is_streamer"] == 0]
    streamer_ids = [s["streamer_id"] for s in streamers]
    streamer_weights = [s["follower_count"] for s in streamers]

    plans = list(SUBSCRIPTION_PLANS.keys())
    plan_weights = [50, 35, 15]

    for subid in range(1, NUM_SUBSCRIPTIONS + 1):
        uid = random.choice(non_streamer_ids)
        sid = random.choices(streamer_ids, weights=streamer_weights, k=1)[0]
        plan = random.choices(plans, weights=plan_weights, k=1)[0]
        price = SUBSCRIPTION_PLANS[plan]

        start = random_date(DATE_START, DATE_END).strftime("%Y-%m-%d")
        start_dt = datetime.strptime(start, "%Y-%m-%d")

        # Churn: ~30% cancel within 1 month, ~50% within 3 months
        churn_roll = random.random()
        if churn_roll < 0.30:
            end_dt = start_dt + timedelta(days=random.randint(7, 30))
            is_active = 0
        elif churn_roll < 0.50:
            end_dt = start_dt + timedelta(days=random.randint(31, 90))
            is_active = 0
        elif churn_roll < 0.65:
            end_dt = start_dt + timedelta(days=random.randint(91, 180))
            is_active = 0
        else:
            end_dt = None
            is_active = 1

        subscriptions.append({
            "subscription_id": subid,
            "user_id": uid,
            "streamer_id": sid,
            "plan": plan,
            "price_usd": price,
            "start_date": start,
            "end_date": end_dt.strftime("%Y-%m-%d") if end_dt else None,
            "is_active": is_active,
            "auto_renew": 1 if is_active else random.choice([0, 1]),
            "cancelled_at": end_dt.strftime("%Y-%m-%d") if end_dt and not is_active else None,
        })
    return subscriptions


def generate_chat_messages(users, streams):
    """Generate chat messages during streams."""
    print(f"Generating {NUM_CHAT_MESSAGES} chat messages...")
    messages = []
    user_ids = [u["user_id"] for u in users]
    stream_entries = [(s["stream_id"], s["start_time"], s["end_time"]) for s in streams]

    chat_texts = [
        "🔥🔥🔥", "Love this!", "Amazing!", "You're so talented!",
        "How long have you been streaming?", "Greetings from {country}!",
        "First time here, love it!", "Can you play my request?",
        "LOL 😂", "So cool!", "Keep going!", "❤️❤️❤️",
        "Wow!", "This is lit!", "Hello everyone!", "Hi from chat!",
        "Best stream ever!", "Can you say hi to me?", "GG!",
        "Sending love!", "You're the best!", "🎉🎉🎉",
        "Subscribed!", "Just gifted!", "How are you?",
        "This is incredible", "Been watching for hours",
        "My favourite streamer", "Good vibes only ✨",
        "Let's gooooo!", "🚀🚀🚀", "So entertaining!",
    ]

    for mid in range(1, NUM_CHAT_MESSAGES + 1):
        uid = random.choice(user_ids)
        sid, st_str, et_str = random.choice(stream_entries)
        st = datetime.strptime(st_str, "%Y-%m-%d %H:%M:%S")
        et = datetime.strptime(et_str, "%Y-%m-%d %H:%M:%S")
        sent_at = random_date(st, et)

        text = random.choice(chat_texts).format(
            country=random.choice(COUNTRIES)
        )

        is_superchat = 1 if random.random() < 0.03 else 0
        superchat_amount = random.choice([50, 100, 200, 500]) if is_superchat else 0

        messages.append({
            "message_id": mid,
            "stream_id": sid,
            "user_id": uid,
            "message_text": text,
            "is_superchat": is_superchat,
            "superchat_amount": superchat_amount,
            "sent_at": sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return messages


def generate_user_sessions(users):
    """Generate app session events."""
    print(f"Generating {NUM_USER_SESSIONS} user sessions...")
    sessions = []
    user_ids = [u["user_id"] for u in users]

    for sessid in range(1, NUM_USER_SESSIONS + 1):
        uid = random.choice(user_ids)
        start = random_date(DATE_START, DATE_END)
        hour = peak_hour_bias()
        start = start.replace(hour=hour, minute=random.randint(0, 59))

        duration = int(np.clip(np.random.lognormal(5.5, 1.2), 30, 7200))
        end = start + timedelta(seconds=duration)

        user = users[uid - 1]

        sessions.append({
            "session_id": sessid,
            "user_id": uid,
            "session_start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "session_end": end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": duration,
            "platform": user["platform"],
            "pages_viewed": random.randint(1, 20),
            "streams_watched": random.choices(
                [0, 1, 2, 3, 5], weights=[30, 35, 20, 10, 5], k=1
            )[0],
            "gifts_sent": random.choices(
                [0, 0, 0, 1, 2, 3, 5], weights=[50, 15, 10, 10, 8, 5, 2], k=1
            )[0],
        })
    return sessions


def generate_ab_experiments():
    """Create two A/B experiment definitions."""
    print("Generating A/B experiments...")
    experiments = [
        {
            "experiment_id": 1,
            "experiment_name": "gift_animation_redesign",
            "description": "Test whether new animated gift effects increase the gift send rate",
            "hypothesis": "Users exposed to the new gift animations will send 10% more gifts per session",
            "primary_metric": "gifts_per_session",
            "start_date": "2025-06-01",
            "end_date": "2025-07-15",
            "status": "completed",
            "traffic_pct": 50.0,
        },
        {
            "experiment_id": 2,
            "experiment_name": "premium_tier_pricing",
            "description": "Test whether lowering premium subscription price from $14.99 to $9.99 increases conversion",
            "hypothesis": "Lower premium price will increase subscription conversion rate by 15%",
            "primary_metric": "subscription_conversion_rate",
            "start_date": "2025-08-01",
            "end_date": "2025-09-30",
            "status": "completed",
            "traffic_pct": 50.0,
        },
    ]
    return experiments


def generate_ab_assignments(users, experiments):
    """Assign users to experiment variants."""
    print("Generating A/B assignments...")
    assignments = []
    aid = 1

    for exp in experiments:
        # Select a subset of users (traffic_pct)
        eligible = [u for u in users if u["account_status"] == "active"]
        sample_size = int(len(eligible) * exp["traffic_pct"] / 100)
        selected = random.sample(eligible, sample_size)

        for u in selected:
            variant = random.choice(["control", "treatment"])
            assigned_at = random_date(
                datetime.strptime(exp["start_date"], "%Y-%m-%d"),
                datetime.strptime(exp["start_date"], "%Y-%m-%d") + timedelta(days=7)
            )
            assignments.append({
                "assignment_id": aid,
                "experiment_id": exp["experiment_id"],
                "user_id": u["user_id"],
                "variant": variant,
                "assigned_at": assigned_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
            aid += 1
    return assignments


def generate_ab_events(assignments, experiments):
    """Generate conversion events with a true lift for treatment groups."""
    print("Generating A/B events...")
    events = []
    eid = 1

    exp_map = {e["experiment_id"]: e for e in experiments}

    for a in assignments:
        exp = exp_map[a["experiment_id"]]
        exp_start = datetime.strptime(exp["start_date"], "%Y-%m-%d")
        exp_end = datetime.strptime(exp["end_date"], "%Y-%m-%d")

        if exp["experiment_id"] == 1:
            # Gift animation: control avg 2.0 gifts/session, treatment avg 2.3
            if a["variant"] == "control":
                rate = np.random.poisson(2.0)
            else:
                rate = np.random.poisson(2.3)  # ~15% lift

            # Each user has some number of sessions during the experiment
            num_sessions = random.randint(3, 20)
            for _ in range(num_sessions):
                gifts_sent = int(np.random.poisson(rate))
                ts = random_date(exp_start, exp_end)
                events.append({
                    "event_id": eid,
                    "experiment_id": exp["experiment_id"],
                    "user_id": a["user_id"],
                    "event_type": "gifts_per_session",
                    "event_value": float(gifts_sent),
                    "event_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                })
                eid += 1

        elif exp["experiment_id"] == 2:
            # Pricing: control 5% conversion, treatment 7% (~40% relative lift)
            if a["variant"] == "control":
                converted = 1 if random.random() < 0.05 else 0
            else:
                converted = 1 if random.random() < 0.07 else 0

            ts = random_date(exp_start, exp_end)
            events.append({
                "event_id": eid,
                "experiment_id": exp["experiment_id"],
                "user_id": a["user_id"],
                "event_type": "subscription_conversion",
                "event_value": float(converted),
                "event_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            })
            eid += 1

    return events


def main():
    """Generate all data and save as JSON files."""
    print("=" * 60)
    print("  Live-Streaming Platform — Synthetic Data Generator")
    print("=" * 60)

    # --- Users ---
    users = generate_users()

    # --- Streamers ---
    streamers = generate_streamers(users)

    # --- Gifts catalog ---
    gifts = []
    for i, (name, cost, cat, anim) in enumerate(GIFT_CATALOG, start=1):
        gifts.append({
            "gift_id": i,
            "gift_name": name,
            "coin_cost": cost,
            "category": cat,
            "animation_type": anim,
            "is_active": 1,
        })

    # --- Streams ---
    streams = generate_streams(streamers)

    # --- Gift Transactions ---
    gift_transactions = generate_gift_transactions(users, streamers, streams, gifts)

    # --- Subscriptions ---
    subscriptions = generate_subscriptions(users, streamers)

    # --- Chat Messages ---
    chat_messages = generate_chat_messages(users, streams)

    # --- User Sessions ---
    user_sessions = generate_user_sessions(users)

    # --- A/B Experiments ---
    ab_experiments = generate_ab_experiments()
    ab_assignments = generate_ab_assignments(users, ab_experiments)
    ab_events = generate_ab_events(ab_assignments, ab_experiments)

    # --- Update streamer earnings from transactions ---
    earnings = {}
    for tx in gift_transactions:
        sid = tx["receiver_id"]
        earnings[sid] = earnings.get(sid, 0) + tx["usd_value"]
    for s in streamers:
        s["total_earnings"] = round(earnings.get(s["streamer_id"], 0), 2)

    # --- Save to JSON ---
    datasets = {
        "users": users,
        "streamers": streamers,
        "gifts": gifts,
        "streams": streams,
        "gift_transactions": gift_transactions,
        "subscriptions": subscriptions,
        "chat_messages": chat_messages,
        "user_sessions": user_sessions,
        "ab_experiments": ab_experiments,
        "ab_assignments": ab_assignments,
        "ab_events": ab_events,
    }

    for name, data in datasets.items():
        path = DATA_DIR / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=None)  # compact for speed
        print(f"  ✓ {name}: {len(data):,} rows → {path.name}")

    print("\n✅ All data generated successfully!")
    total = sum(len(d) for d in datasets.values())
    print(f"   Total rows: {total:,}")


if __name__ == "__main__":
    main()
