import time
import requests
import pandas as pd

BASE = "https://www.fema.gov/api/open/v3"
PAGE = 10000

def fetch(entity, filt, select=None, out=None):
    params = {"$top": PAGE, "$skip": 0, "$filter": filt, "$orderby": "id"}
    if select:
        params["$select"] = ",".join(select)
    rows = []
    while True:
        r = requests.get(f"{BASE}/{entity}", params=params, timeout=120)
        r.raise_for_status()
        batch = r.json()[entity]
        if not batch:
            break
        rows.extend(batch)
        print(entity, len(rows))
        params["$skip"] += PAGE
        time.sleep(0.2)
    df = pd.DataFrame(rows)
    if out:
        df.to_parquet(out, index=False)
    return df

# Claims: 2009 onwards, one state to test (Delaware is small)
claims = fetch("NfipClaims", "state eq 'DE' and yearOfLoss ge 2009",
               out="claims_DE.parquet")

# Policies: filter on state only, then cut dates in pandas
pol = fetch("NfipPolicies", "propertyState eq 'DE'", out="policies_DE.parquet")
pol["policyEffectiveDate"] = pd.to_datetime(pol["policyEffectiveDate"])
pol = pol[pol["policyEffectiveDate"] < "2025-01-01"]