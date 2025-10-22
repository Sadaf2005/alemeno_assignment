# from celery import shared_task
# import pandas as pd
# from .models import Customer, Loan
# from datetime import datetime

# @shared_task
# def ingest_customer_data():
#     # I am assuming your file is named 'customer_data.xlsx'
#     # If it's a CSV, you might need pd.read_csv('customer_data.xlsx - Sheet1.csv')
#     df = pd.read_excel('customer_data.xlsx')
    
#     for _, row in df.iterrows():
#         Customer.objects.update_or_create(
#             # Use the header from your file: 'Customer ID'
#             customer_id=row['Customer ID'],  # CHANGED
#             defaults={
#                 # Match all keys to your file's headers
#                 'first_name': row['First Name'],            # CHANGED
#                 'last_name': row['Last Name'],              # CHANGED
#                 'age': row['Age'],                          # CHANGED (and added)
#                 'phone_number': row['Phone Number'],        # CHANGED
#                 'monthly_salary': row['Monthly Salary'],    # CHANGED
#                 'approved_limit': row['Approved Limit'],    # CHANGED
#                 # 'current_debt' was removed because it's not in your file
#                 # The model default=0 will be used instead.
#             }
#         )
#     return "Customer data ingested"

# @shared_task
# def ingest_loan_data():
#     df = pd.read_excel('loan_data.xlsx')
#     for _, row in df.iterrows():
#         try:
#             # This MUST match the customer ID header in your loan file
#             # It's very likely 'Customer ID' just like in the other file.
#             customer = Customer.objects.get(customer_id=row['Customer'])  # CHANGED
            
#             Loan.objects.update_or_create(
#                 # WARNING: Check this header in your 'loan_data.xlsx' file
#                 loan_id=row['Loan ID'],
#                 defaults={
#                     'customer': customer,
#                     # WARNING: Check all these headers in your 'loan_data.xlsx' file
#                     'loan_id':row['Loan Id'],
#                     'loan_amount': row['Loan Amount'],
#                     'tenure': row['Tenure'],
#                     'interest_rate': row['Interest Rate'],
#                     'monthly_repayment': row['Monthly Payment'],
#                     'emis_paid_on_time': row['EMIs paid on time'],
#                     'start_date': row['Date of Approval'],
#                     'end_date': row['End Date']
#                 }
#             )
#         except Customer.DoesNotExist:
#             # Also change this key to match
#             print(f"Customer with id {row['Customer ID']} not found.")  # CHANGED
            
#     return "Loan data ingested"



from celery import shared_task
from celery.utils.log import get_task_logger
import pandas as pd
from .models import Customer, Loan
from datetime import datetime
from pathlib import Path
import os

logger = get_task_logger(__name__)

def _project_file_path(filename):
    # try cwd, then project root (two parents up from this file), then absolute path
    candidates = [
        Path.cwd() / filename,
        Path(__file__).resolve().parents[2] / filename,
        Path(filename)
    ]
    for p in candidates:
        if p.exists():
            return p
    # fallback to original name (will raise by pandas if missing)
    return Path(filename)

def _normalize(s: str) -> str:
    return "".join(e for e in str(s).lower() if e.isalnum())

def _find_column(df, candidates):
    # candidates: list of possible header strings
    col_map = { _normalize(c): c for c in df.columns }
    for cand in candidates:
        norm = _normalize(cand)
        if norm in col_map:
            return col_map[norm]
    return None

@shared_task
def ingest_customer_data(filename='data/customer_data.xlsx'):
    path = _project_file_path(filename)
    logger.info("Reading customer file: %s", path)
    df = pd.read_excel(path)
    created = updated = 0

    for _, row in df.iterrows():
        # try to find columns robustly
        customer_id_col = _find_column(df, ['Customer ID', 'Customer', 'customer_id', 'customer id'])
        first_col = _find_column(df, ['First Name', 'first_name', 'Firstname', 'first name'])
        last_col = _find_column(df, ['Last Name', 'last_name', 'Lastname', 'last name'])
        age_col = _find_column(df, ['Age', 'age'])
        phone_col = _find_column(df, ['Phone Number', 'Phone', 'phone_number', 'phone'])
        salary_col = _find_column(df, ['Monthly Salary', 'MonthlySalary', 'monthly_salary', 'salary'])
        approved_col = _find_column(df, ['Approved Limit', 'approved_limit', 'ApprovedLimit'])

        if not customer_id_col:
            logger.error("Customer ID column not found in %s", filename)
            return "Failed: customer id column missing"

        data = {
            'first_name': row[first_col] if first_col and pd.notna(row[first_col]) else '',
            'last_name': row[last_col] if last_col and pd.notna(row[last_col]) else '',
            'age': int(row[age_col]) if age_col and pd.notna(row[age_col]) else None,
            'phone_number': str(row[phone_col]) if phone_col and pd.notna(row[phone_col]) else '',
            'monthly_salary': pd.to_numeric(row[salary_col], errors='coerce') if salary_col else None,
            'approved_limit': pd.to_numeric(row[approved_col], errors='coerce') if approved_col else None,
        }

        obj, created_flag = Customer.objects.update_or_create(
            customer_id=row[customer_id_col],
            defaults=data
        )
        if created_flag:
            created += 1
        else:
            updated += 1

    logger.info("Customer ingestion finished: %d created, %d updated", created, updated)
    return f"Customer data ingested: {created} created, {updated} updated"

@shared_task
def ingest_loan_data(filename='data/loan_data.xlsx'):
    path = _project_file_path(filename)
    logger.info("Reading loan file: %s", path)
    df = pd.read_excel(path)
    created = updated = skipped = 0

    # Prepare column resolution once (use df.columns)
    # We'll attempt multiple common header names for each field
    for _, row in df.iterrows():
        # find customer id col
        customer_col = _find_column(df, ['Customer ID', 'Customer', 'customer_id', 'customer id'])
        loan_id_col = _find_column(df, ['Loan ID', 'LoanId', 'loan_id', 'Loan Id', 'loan id'])
        loan_amount_col = _find_column(df, ['Loan Amount', 'Amount', 'loan_amount', 'loan amount'])
        tenure_col = _find_column(df, ['Tenure', 'tenure'])
        interest_col = _find_column(df, ['Interest Rate', 'Interest', 'interest_rate'])
        monthly_pay_col = _find_column(df, ['Monthly Payment', 'MonthlyPayment', 'monthly_repayment', 'monthly payment', 'Monthly Payment'])
        emis_on_time_col = _find_column(df, ['EMIs paid on time', 'EMIs Paid On Time', 'emis_paid_on_time', 'emis paid on time'])
        start_date_col = _find_column(df, ['Date of Approval', 'Start Date', 'start_date', 'date'])
        end_date_col = _find_column(df, ['End Date', 'end_date'])

        if not customer_col:
            logger.error("Customer ID column not found in %s", filename)
            return "Failed: customer id column missing"

        raw_customer_id = row[customer_col]
        if pd.isna(raw_customer_id):
            logger.warning("Skipping row with empty customer id: %s", row.to_dict())
            skipped += 1
            continue

        # find customer instance
        try:
            customer = Customer.objects.get(customer_id=raw_customer_id)
        except Customer.DoesNotExist:
            logger.warning("Customer with id %s not found. Skipping loan row.", raw_customer_id)
            skipped += 1
            continue

        # resolve values safely
        loan_id_val = row[loan_id_col] if loan_id_col and pd.notna(row[loan_id_col]) else None
        if loan_id_val is None:
            logger.warning("Skipping loan row for customer %s because loan id missing", raw_customer_id)
            skipped += 1
            continue

        defaults = {
            'customer': customer,
            'loan_amount': pd.to_numeric(row[loan_amount_col], errors='coerce') if loan_amount_col else None,
            'tenure': int(row[tenure_col]) if tenure_col and pd.notna(row[tenure_col]) else None,
            'interest_rate': pd.to_numeric(row[interest_col], errors='coerce') if interest_col else None,
            'monthly_repayment': pd.to_numeric(row[monthly_pay_col], errors='coerce') if monthly_pay_col else None,
            'emis_paid_on_time': int(row[emis_on_time_col]) if emis_on_time_col and pd.notna(row[emis_on_time_col]) else None,
            'start_date': pd.to_datetime(row[start_date_col], errors='coerce') if start_date_col else None,
            'end_date': pd.to_datetime(row[end_date_col], errors='coerce') if end_date_col else None,
        }

        obj, created_flag = Loan.objects.update_or_create(
            loan_id=loan_id_val,
            defaults=defaults
        )
        if created_flag:
            created += 1
        else:
            updated += 1

    logger.info("Loan ingestion finished: %d created, %d updated, %d skipped", created, updated, skipped)
    return f"Loan data ingested: {created} created, {updated} updated, {skipped} skipped"
