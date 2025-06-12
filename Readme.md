# SUB-LIMITS FLATTENING

## cartesian_product.py-:
1. It helps create a cartesian_product of Beneficiary x Services at plan_order_id level.
2. It order to create the cartesian_product for a given **plan_order_id** in the **cartesian_product.py** file replace the **plan_order_id** in the **payload** variable.

payload={<br>
        "plan_order_id": "place your plan_order_id here",<br>
        "filters": {<br>
            "services": []<br>
        },<br>
        "reimbursements_only": "0",<br>
        "qr_transactions_only": "0"<br>
}<br>

Run the following command in the terminal - **python cartesian_product.py**. <br>
This will generate your data file - **Cartesian_Product.csv**. <br>

## flatten_plan.py
1. It helps to flatten a plan tree structure data into tabular structure data.
2. Replace **plan_id** in the **create_plan_tree_payload** variable inside **flatten_plan.py** file.

```python
    create_plan_tree_payload = 
    {
        "plan_id": 85
    }
```

Run the following command in the terminal - **python flatten_plan.py**. <br>
This will generate your data file - **Flattened_Plan_Tree.csv**. <br>