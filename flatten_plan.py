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
    
    return plan_tree

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

def main():
    plan_tree = api_call()
    print("Flattening plan tree-: ")

    if not plan_tree:
        print("Plan tree data is empty.")
        return

    flat_tree_rows = traverse_plan_tree(plan_tree, node_id=1)
    df_flattened_tree = pd.DataFrame(flat_tree_rows)

    print("\nFLATTENED PLAN TREE TABLE")
    print(df_flattened_tree.head())

    df_flattened_tree.to_csv("Flattened_Plan_Tree.csv", index=False)

if __name__ == "__main__":
    main()
