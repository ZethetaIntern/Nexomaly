"""Real-time transaction simulator for WebSocket streaming."""
import random, numpy as np
from datetime import datetime

MERCHANTS_NORMAL = ["Amazon","Walmart","Target","Best Buy","Apple Store","Shell Gas",
                    "Starbucks","Delta Airlines","Hilton Hotels","Uber","Netflix",
                    "Spotify","McDonald's","Costco","Home Depot","Walgreens","CVS"]
MERCHANTS_RISKY  = ["Casino Royal","CryptoBridge","PawnShop Plus","LoanShark Finance",
                    "Unknown Vendor","Wire Transfer Co","OffshoreBank","DarkMarket"]
CATEGORIES_N = ["food","clothing","utilities","retail","healthcare"]
CATEGORIES_R = ["gambling","crypto","travel","electronics"]
LOCATIONS_N  = ["New York, US","San Francisco, US","Chicago, US","London, UK",
                "Tokyo, JP","Austin, US","Seattle, US","Miami, US","Boston, US"]
LOCATIONS_R  = ["offshore","anonymous","Unknown Location","Unverified"]
USERS        = [f"USR-{str(i).zfill(4)}" for i in range(1, 201)]

def generate_transaction() -> dict:
    is_anomalous = random.random() < 0.25
    if is_anomalous:
        profile = random.choice(["high_amount","risky_merchant","night_offshore","combo"])
        if profile == "high_amount":
            return dict(user_id=random.choice(USERS),
                        amount=round(random.uniform(5000,50000),2),
                        merchant=random.choice(MERCHANTS_NORMAL+MERCHANTS_RISKY),
                        category="electronics", location=random.choice(LOCATIONS_N))
        elif profile == "risky_merchant":
            return dict(user_id=random.choice(USERS),
                        amount=round(random.uniform(200,8000),2),
                        merchant=random.choice(MERCHANTS_RISKY),
                        category=random.choice(CATEGORIES_R),
                        location=random.choice(LOCATIONS_N))
        elif profile == "night_offshore":
            return dict(user_id=random.choice(USERS),
                        amount=round(random.uniform(500,5000),2),
                        merchant=random.choice(MERCHANTS_RISKY),
                        category=random.choice(CATEGORIES_R),
                        location=random.choice(LOCATIONS_R))
        else:
            return dict(user_id=random.choice(USERS),
                        amount=round(random.uniform(3000,30000),2),
                        merchant=random.choice(MERCHANTS_RISKY),
                        category=random.choice(CATEGORIES_R),
                        location=random.choice(LOCATIONS_R))
    return dict(user_id=random.choice(USERS),
                amount=round(float(np.random.lognormal(5.0,0.7)),2),
                merchant=random.choice(MERCHANTS_NORMAL),
                category=random.choice(CATEGORIES_N),
                location=random.choice(LOCATIONS_N))
