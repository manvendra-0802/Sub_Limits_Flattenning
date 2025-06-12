#SUB-LIMITS FLATTENING

##cartesian_product.py-:
1. It helps create a cartesian_product of Beneficiary x Services at plan_order_id level.
2. It order to create the cartesian_product for a given **plan_order_id** in the **cartesian_product.py** file replace the **plan_order_id** in the **payload** variable.

payload={
        "plan_order_id": "place your plan_order_id here",
        "filters": {
            "services": []
        },
        "reimbursements_only": "0",
        "qr_transactions_only": "0"
    }
