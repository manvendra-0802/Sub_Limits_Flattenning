import requests
import json
import pandas as pd
import time

LEAF_LEVELS={"product", "item", "qr_product", "leaf_group", "reimbursement_mapping"}
API_BASE="https://protect.immunityhealth.me/api"
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiYjkwZWM5MjQ2ZDBhNmQ0MWIzNmNmZjJhNzc5NWIzODAxODk0YWJhNmRiYTg4ZDFlZjYzMDFjZDkwZjIwZTFmZDgwYzQ0MTIyYTIxNWEyMDYiLCJpYXQiOjE3NDEzNTgwOTUuMzg5MzkzLCJuYmYiOjE3NDEzNTgwOTUuMzg5Mzk1LCJleHAiOjE4OTkxMjQ0OTUuMzc2MjgxLCJzdWIiOiI2OTMiLCJzY29wZXMiOltdfQ.ju06wzwaMuCHQ4DrQVj1LwkHTvrLub3TSO84q-JpoOYnIoP1SrdJ9jZVA6XdU4Mq84dRsH6f4_UBnp8muxLlNnXYThXy7iPTx1Ti0vbpAoJs6fdC1w_zuTsli44xe2fFZyYCWkzTex8iBKcTM2zveiWBi0UOo5aQ80XPfLpf_xrJnbfxFmQdsnCsWIx89mPrnASEqFtmperyD-MPyvj-qxLXmHEBViPD3JyWkEHVkRz75jzsEfiGywo8CgwVIqyE7S0oHp1RgUv8oxi1GQrFsOrEdh7mFL2z4w0JNqhmHrsfYv_q0fkDCxCOtVEdxnk5hFYonZeGsXfuoLg2LbBa5riaj0JlQApszEYXfYsTm7QfomVeo38OAloKpfjLbXKUfsgnc4IMWbJBFb2d2nsN_vTT8_EdceANJ-fiMzZ_djQUS4wEnN86AkJ6DWBp0I1v2IyyB7poDLkblb6sXSj0X-zM6UNIgwheT2_8bBuEgk-R5snqKnTzIt0GCKHh8A6wN1pmNKG6uGYl00bhrIlSReP5gsBbwn1sdvW2lEipKCoOyCrokv_lt7afEn2F9h-5cjeqOjzehXmM0coJZV0HAgET9ybYkZhjLCkanNep35Y2U3YedAObssMTKK_6AjON1v1Xsz2h26GdLa9p__QfOGqA-62ktKUd2YR0uo_h8h0"

def api_call():
    headers={
        "Content-Type":"application/json",
        "Authorization":f"Bearer {TOKEN}"
    }

    payload={
        "plan_order_id": "AHPOUID1178735PID84SR1",
        "filters": {
            "services": []
        },
        "reimbursements_only": "0",
        "qr_transactions_only": "0"
    }

    response=requests.post(
        f"{API_BASE}/plan/get_plan_limits_filters",
        headers=headers,
        json=payload
    )

    if response.ok:
        return response.json()
    else:
        print("Error fetching plan filters:", response.status_code)
        print(response.text)
        return {}

# flatten services (with subtypes and nested childern values)
def flatten_services(services):
    flat=[]
    for service in services:
        sub_types=service.get("sub_types", [])
        if sub_types:
            for subtype in sub_types:
                flat.append({
                    "label": f"{service.get('label')} - {subtype.get('label')}",
                    "reimbursement_mapping_id": subtype.get("reimbursement_mapping_id"),
                    "subcategory_mapping_id": subtype.get("subcategory_mapping_id")
                })
        else:
            flat.append({
                "label": service.get("label"),
                "reimbursement_mapping_id": service.get("reimbursement_mapping_id"),
                "subcategory_mapping_id": service.get("subcategory_mapping_id")
            })
        # Recurse into nested 'values'
        if "values" in service:
            flat.extend(flatten_services(service["values"]))
    return flat

# Helper: fetch total_limit for a service by calling filtered API
def fetch_total_limit(plan_order_id, label, subcat_id, reimb_id):
    url=f"{API_BASE}/plan/get_plan_limits_filters"
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload={
        "plan_order_id": plan_order_id,
        "filters": {
            "services":[
                {
                    "label": label,
                    "id": subcat_id,
                    "subcategory_mapping_id": subcat_id,
                    "reimbursement_mapping_id": reimb_id
                }
            ]
        },
        "reimbursements_only": "0",
        "qr_transactions_only": "0"
    }

    try:
        response=requests.post(url, headers=headers, json=payload)
        if response.ok:
            data=response.json()
            return data.get("jsonData", {}).get("limits", {}).get("total_limit", None)
        else:
            print(f"Limit fetch failed for {label} ({subcat_id})-{response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching limit for {label}:", e)
        return None

def extract_cartesian_product(filter_json):
    json_data=filter_json.get("jsonData")
    main_plan_limit=json_data["limits"]["total_limit"]

    if isinstance(json_data, list):
        if not json_data:
            raise ValueError("jsonData list is empty")
        json_data=json_data[0]

    if not isinstance(json_data, dict):
        raise ValueError("jsonData is not a dictionary")

    plan_order_id=json_data.get("plan_order_id")
    services=[]
    beneficiaries=[]

    for f in json_data.get("filters", []):
        if f.get("label") == "Services":
            services = flatten_services(f.get("values", []))
        elif f.get("label") == "Beneficiary":
            beneficiaries = f.get("values", [])

    print(f"Found {len(services)} services × {len(beneficiaries)} beneficiaries")

    # Dedupeing services before calling limit API
    unique_services = {(s["label"], s["reimbursement_mapping_id"], s["subcategory_mapping_id"]) for s in services}
    limit_map={}

    print("Fetching total_limit for each unique service...")
    for label, reimb_id, subcat_id in unique_services:
        limit=fetch_total_limit(plan_order_id, label, subcat_id, reimb_id)
        limit_map[(label, reimb_id)] = limit
        print(f"  ↳ {label}: ₹{limit}")
        time.sleep(0.3)

    cartesian_rows = []
    for ben in beneficiaries:
        for srv in services:
            label = srv["label"]
            reimb_id = srv["reimbursement_mapping_id"]
            total_limit = limit_map.get((label, reimb_id))

            cartesian_rows.append({
                "relation": ben.get("relation"),
                "gender": ben.get("gender"),
                "name": ben.get("name"),
                "plan_order_id": plan_order_id,
                "service_label": label,
                "reimbursement_mapping_id": reimb_id,
                "limit": total_limit,
                "main_plan_limit":main_plan_limit
            })

    return pd.DataFrame(cartesian_rows)

def main():
    filters_data=api_call()

    print("\nGenerating cartesian product-")
    try:
        df_cartesian=extract_cartesian_product(filters_data)
    except ValueError as e:
        print(f"Error: {e}")
        return

    print("\nCARTESIAN PRODUCT GENERATED:")
    print(df_cartesian.head())

    df_cartesian.to_csv("CP_FINAL.csv", index=False)
    print("File saved-:cartesian_product.csv")

if __name__ == "__main__":
    main()