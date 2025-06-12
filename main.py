import requests
import json
import pandas as pd

LEAF_LEVELS = {"product", "item", "qr_product", "leaf_group", "reimbursement_mapping"}
def api_call():
    API_BASE = "https://protect.immunityhealth.me/api"
    TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiYjkwZWM5MjQ2ZDBhNmQ0MWIzNmNmZjJhNzc5NWIzODAxODk0YWJhNmRiYTg4ZDFlZjYzMDFjZDkwZjIwZTFmZDgwYzQ0MTIyYTIxNWEyMDYiLCJpYXQiOjE3NDEzNTgwOTUuMzg5MzkzLCJuYmYiOjE3NDEzNTgwOTUuMzg5Mzk1LCJleHAiOjE4OTkxMjQ0OTUuMzc2MjgxLCJzdWIiOiI2OTMiLCJzY29wZXMiOltdfQ.ju06wzwaMuCHQ4DrQVj1LwkHTvrLub3TSO84q-JpoOYnIoP1SrdJ9jZVA6XdU4Mq84dRsH6f4_UBnp8muxLlNnXYThXy7iPTx1Ti0vbpAoJs6fdC1w_zuTsli44xe2fFZyYCWkzTex8iBKcTM2zveiWBi0UOo5aQ80XPfLpf_xrJnbfxFmQdsnCsWIx89mPrnASEqFtmperyD-MPyvj-qxLXmHEBViPD3JyWkEHVkRz75jzsEfiGywo8CgwVIqyE7S0oHp1RgUv8oxi1GQrFsOrEdh7mFL2z4w0JNqhmHrsfYv_q0fkDCxCOtVEdxnk5hFYonZeGsXfuoLg2LbBa5riaj0JlQApszEYXfYsTm7QfomVeo38OAloKpfjLbXKUfsgnc4IMWbJBFb2d2nsN_vTT8_EdceANJ-fiMzZ_djQUS4wEnN86AkJ6DWBp0I1v2IyyB7poDLkblb6sXSj0X-zM6UNIgwheT2_8bBuEgk-R5snqKnTzIt0GCKHh8A6wN1pmNKG6uGYl00bhrIlSReP5gsBbwn1sdvW2lEipKCoOyCrokv_lt7afEn2F9h-5cjeqOjzehXmM0coJZV0HAgET9ybYkZhjLCkanNep35Y2U3YedAObssMTKK_6AjON1v1Xsz2h26GdLa9p__QfOGqA-62ktKUd2YR0uo_h8h0"


    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }

    get_plan_filters_url = f"{API_BASE}/plan/get_plan_limits_filters"

    get_plan_filters_payload ={
        "plan_order_id": "AHPOUID1178735PID84SR1",
        "filters": {
            "services": [
                
            ]
        },
        "reimbursements_only": "0",
        "qr_transactions_only": "0"
    }

    filters_response = requests.post(
        get_plan_filters_url,
        headers=headers,
        json=get_plan_filters_payload
    )

    if filters_response.ok:
        filters_data = filters_response.json()
        print("filters_data keys:", filters_data.keys())
        print("filters_data['jsonData'] type:", type(filters_data.get("jsonData")))

    else:
        print("Error fetching plan filters:", filters_response.status_code)
        print(filters_response.text)
        filters_data = {}

    create_plan_tree_url = f"{API_BASE}/plan/debugging/create_plan_tree_p2c"

    create_plan_tree_payload = {
        "plan_id": 85
    }

    tree_response = requests.post(
        create_plan_tree_url,
        headers=headers,
        json=create_plan_tree_payload
    )

    if tree_response.ok:
        tree_data = tree_response.json()
    else:
        print("Error fetching plan tree:", tree_response.status_code)
        print(tree_response.text)

    plan_tree = tree_data["jsonData"]
    
    return plan_tree,filters_data

# Flatten Plan Tree
def extract_limit_value(data):
    limit=data.get("limit")
    if isinstance(limit, dict):
        return limit.get("limit_value")
    return None

def extract_limit_value2(node):
    limit = node.get("limit")
    if isinstance(limit, dict):
        return limit.get("limit_value")
    return None

def extract_transaction_limit(node):
    attributes = node.get("attributes", {})
    if isinstance(attributes, dict):
        return attributes.get("transaction_limit")
    return None


def traverse_plan_tree(tree, node_id, parent_desc=None, level_num=0,
                               inherited_limit=None, inherited_limit_type='inherited'):
    node = tree.get(str(node_id), {})
    node_level = node.get("level")

    if node_level == "plan":
        plan_type = "root"
    elif node_level == "product_group":
        plan_type = "middle"
    elif node_level in LEAF_LEVELS:
        plan_type = "leaf"
    else:
        plan_type = "unknown"

    # own vs inherited limit
    own_limit = extract_limit_value(node)
    if own_limit is not None:
        final_limit = own_limit
        limit_type = "self"
    else:
        final_limit = inherited_limit
        limit_type = "inherited"


    relations=[]

    for member in node.get("covered_members", []):
        relation = member.get("relation")
        if relation and relation not in relations:
            relations.append(relation)


    row = {
        "unique_id": node.get("unique_id"),
        "limit_value": final_limit,
        "limit_type": limit_type,
        "children": node.get("children", []),
        "mapping_table_name": node.get("mapping_table_name"),
        "master_table_name":node.get("master_table_name"),
        "transaction_limit": extract_transaction_limit(node),
        "type":node.get("level"),
        "type_id":node.get("level_id"),
        "long_desc": node.get("long_desc"),
        "parent_plan": parent_desc,
        "plan_type": plan_type,
        "level": level_num,
        "covered_dependants":relations
    }

    rows = [row]

    for child_id in node.get("children", []):
        rows.extend(
            traverse_plan_tree(
                tree,
                child_id,
                parent_desc=node.get("long_desc"),
                level_num=level_num + 1,
                inherited_limit=final_limit,
                inherited_limit_type=limit_type
            )
        )

    return rows

# Cartesian Product Table
def flatten_services(services):
    flat = []
    for service in services:
        # If sub-types exist, create rows for each sub-type under this service
        sub_types = service.get("sub_types", [])
        if sub_types:
            for subtype in sub_types:
                flat.append({
                    "label": f"{service.get('label')} - {subtype.get('label')}",
                    "reimbursement_mapping_id": subtype.get("reimbursement_mapping_id"),
                    "total_limit": service.get("total_limit") 
                })
        else:
            # Regular service with no sub-types
            flat.append({
                "label": service.get("label"),
                "reimbursement_mapping_id": service.get("reimbursement_mapping_id"),
                "total_limit": service.get("total_limit")
            })

        # Recursively flatten nested 'values' list
        if "values" in service:
            flat.extend(flatten_services(service["values"]))
    return flat

def extract_cartesian_product(filter_json):
    # Validate top-level structure
    if not isinstance(filter_json, dict):
        raise ValueError("filters_data is not a dict")

    json_data = filter_json.get("jsonData")
    
    # If json_data is a list, assume we want the first entry
    if isinstance(json_data, list):
        if not json_data:
            raise ValueError("jsonData list is empty")
        json_data = json_data[0]

    if not isinstance(json_data, dict):
        raise ValueError("jsonData is not a dictionary after processing")

    services = []
    beneficiaries = []

    for f in json_data.get("filters", []):
        if f.get("label") == "Services":
            services = flatten_services(f.get("values", []))
        elif f.get("label") == "Beneficiary":
            beneficiaries = f.get("values", [])

    total_limit = json_data.get("limits", {}).get("total_limit")
    plan_order_id = json_data.get("plan_order_id")

    cartesian_rows = []
    for ben in beneficiaries:
        for srv in services:
            cartesian_rows.append({
                "relation": ben.get("relation"),
                "gender": ben.get("gender"),
                "name": ben.get("name"),
                "plan_order_id": plan_order_id,
                "service_label": srv.get("label"),
                "reimbursement_mapping_id": srv.get("reimbursement_mapping_id"),
                "total_limit": total_limit
            })

    return pd.DataFrame(cartesian_rows)


# def extract_cartesian_product(filter_json):
#     services=[]
#     beneficiaries=[]

#     for f in filter_json["jsonData"]["filters"]:
#         if f["label"]=="Services":
#             services=flatten_services(f["values"])
#         elif f["label"]=="Beneficiary":
#             beneficiaries=f["values"]

#     total_limit=filter_json["jsonData"]["limits"]["total_limit"]
#     plan_order_id=filter_json["jsonData"]["plan_order_id"]
#     cartesian_rows=[]
#     for ben in beneficiaries:
#         for srv in services:
#             cartesian_rows.append({
#                 "relation":ben.get("relation"),
#                 "gender":ben.get("gender"),
#                 "name":ben.get("name"),
#                 "plan_order_id":plan_order_id,
#                 "service_label":srv.get("label"),
#                 "reimbursement_mapping_id": srv.get("reimbursement_mapping_id"),
#                 "total_limit": total_limit
#             })

#     return pd.DataFrame(cartesian_rows)

def main():
    plan_tree, filters_data = api_call()
    print("Flattening plan tree-: ")

    if not plan_tree:
        print("Plan tree data is empty.")
        return

    flat_tree_rows = traverse_plan_tree(plan_tree, node_id=1)
    df_flattened_tree = pd.DataFrame(flat_tree_rows)

    print("Generating cartesian product...")
    try:
        df_cartesian = extract_cartesian_product(filters_data)
    except ValueError as e:
        print(f"Error in extracting cartesian product: {e}")
        return

    print("\nCARTESIAN PRODUCT TABLE")
    print(df_cartesian.head())

    print("\nFLATTENED PLAN TREE TABLE")
    print(df_flattened_tree.head())

    df_cartesian.to_csv("cartesian_product_finally.csv", index=False)
    df_flattened_tree.to_csv("flattened_plan_tree_finally.csv", index=False)



if __name__ == "__main__":
    main()

