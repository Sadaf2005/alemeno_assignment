from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from .models import Customer, Loan
from .serializers import ViewLoanSerializer, CustomerLoanSerializer
import math
from datetime import datetime
from django.db.models import Sum
from decimal import Decimal
import pandas as pd

# --- Helper Functions ---

def calculate_credit_score(customer_id):
    # This is the most complex part[cite: 48]. You must define your own logic.
    # Here is a *sample* logic.
    score = 100
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        loans = Loan.objects.filter(customer=customer)

        # Component v: current_debt > approved_limit [cite: 57]
        if customer.current_debt > customer.approved_limit:
            return 0

        # Component i: Past Loans paid on time [cite: 50]
        total_emis = sum(loan.tenure for loan in loans)
        total_paid_on_time = sum(loan.emis_paid_on_time for loan in loans)
        if total_emis > 0:
            payment_ratio = total_paid_on_time / total_emis
            if payment_ratio < 0.8: score -= 30
            elif payment_ratio < 0.9: score -= 15
        
        # Component ii: No of loans taken in past [cite: 51]
        if loans.count() > 5:
            score -= 20

        # Component iii: Loan activity in current year [cite: 53]
        current_year_loans = loans.filter(start_date__year=datetime.now().year).count()
        if current_year_loans > 3:
            score -= 25

        # Component iv: Loan approved volume [cite: 55]
        # (This is vague, let's skip for this simple model)
        
        return max(score, 0) # Ensure score is not negative

    except Customer.DoesNotExist:
        return 0 # No customer, no score

def calculate_emi(principal, annual_rate, tenure_months):
    # Standard EMI formula based on P, r, n
    # The prompt mentions "compound interest"[cite: 38], but this EMI formula
    # is the standard for loan repayment.
    if tenure_months == 0: return 0
    if annual_rate == 0: return principal / tenure_months
    
    monthly_rate = (annual_rate / 100) / 12
    r = monthly_rate
    n = tenure_months
    
    emi = principal * r * (pow(1 + r, n)) / (pow(1 + r, n) - 1)
    return round(emi, 2)

def check_loan_eligibility(customer_id, loan_amount, interest_rate, tenure):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return {'approval': False, 'message': 'Customer not found'}

    credit_score = calculate_credit_score(customer_id)
    
    approval = False
    corrected_interest_rate = interest_rate
    
    # 1. Credit Score Check [cite: 58-63]
    if credit_score > 50:
        approval = True # [cite: 59]
    elif 30 < credit_score <= 50:
        if interest_rate > 12: approval = True # [cite: 60]
        else:
            approval = True
            corrected_interest_rate = 12.0 # Corrected rate [cite: 65-67]
    elif 10 < credit_score <= 30:
        if interest_rate > 16: approval = True # [cite: 62]
        else:
            approval = True
            corrected_interest_rate = 16.0
    else: # 10 >= credit_score
        approval = False # [cite: 63]
        return {'approval': False, 'message': 'Credit score too low'}

    # 2. EMI Check [cite: 64]
    new_emi = calculate_emi(loan_amount, corrected_interest_rate, tenure)
    
    # Find sum of EMIs for *current* loans (loans not yet ended)
    current_loans = Loan.objects.filter(customer=customer, end_date__gte=datetime.now().date())
    current_emis_sum = current_loans.aggregate(Sum('monthly_repayment'))['monthly_repayment__sum'] or 0

#    if (current_emis_sum + Decimal(str(new_emi))) > (Decimal(customer.monthly_salary) * Decimal('0.5')):
#        approval = False # [cite: 64]
#        return {'approval': False, 'message': 'Total EMI exceeds 50% of monthly salary'}

#     return {
#         'approval': approval,
#         'customer_id': customer_id,
#         'interest_rate': interest_rate,
#         'corrected_interest_rate': corrected_interest_rate,
#         'tenure': tenure,
#         'monthly_installment': new_emi
#     }
    if (current_emis_sum + Decimal(str(new_emi))) > (Decimal(customer.monthly_salary) * Decimal('0.5')):
        approval = False
        return {'approval': False, 'message': 'Total EMI exceeds 50% of monthly salary'}

    return {
        'approval': approval,
        'customer_id': customer_id,
        'interest_rate': interest_rate,
        'corrected_interest_rate': corrected_interest_rate,
        'tenure': tenure,
        'monthly_installment': new_emi
    # ... other key-value pairs
}


# --- API Views ---

class RegisterView(APIView):
    """
    API for /register [cite: 38]
    """
    def post(self, request):
        data = request.data
        monthly_income = data.get('monthly_income')
        
        # Calculate approved_limit [cite: 41]
        approved_limit = round((36 * monthly_income) / 100000) * 100000

        try:
            # Create a new customer. Note: We need a new unique customer_id.
            # We'll just auto-increment from the last one.
            last_customer = Customer.objects.order_by('-customer_id').first()
            new_customer_id = (last_customer.customer_id + 1) if last_customer else 1

            customer = Customer.objects.create(
                customer_id=new_customer_id,
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                age=data.get('age'),
                monthly_salary=monthly_income,
                phone_number=data.get('phone_number'),
                approved_limit=approved_limit
            )
            
            # Prepare response body [cite: 46]
            response_data = {
                "customer_id": customer.customer_id,
                "name": f"{customer.first_name} {customer.last_name}",
                "age": customer.age,
                "monthly_income": customer.monthly_salary,
                "approved_limit": customer.approved_limit,
                "phone_number": customer.phone_number
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CheckEligibilityView(APIView):
    """
    API for /check-eligibility [cite: 47]
    """
    def post(self, request):
        data = request.data
        result = check_loan_eligibility(
            data.get('customer_id'),
            data.get('loan_amount'),
            data.get('interest_rate'),
            data.get('tenure')
        )
        
        # Build response body [cite: 71]
        response_data = {
            "customer_id": result.get('customer_id'),
            "approval": result.get('approval'),
            "interest_rate": result.get('interest_rate'),
            "corrected_interest_rate": result.get('corrected_interest_rate') or result.get('interest_rate'),
            "tenure": result.get('tenure'),
            "monthly_installment": result.get('monthly_installment')
        }
        return Response(response_data, status=status.HTTP_200_OK)

class CreateLoanView(APIView):
    """
    API for /create-loan [cite: 72]
    """
    def post(self, request):
        data = request.data
        customer_id = data.get('customer_id')
        
        eligibility_result = check_loan_eligibility(
            customer_id,
            data.get('loan_amount'),
            data.get('interest_rate'),
            data.get('tenure')
        )
        
        loan_approved = eligibility_result.get('approval')
        message = eligibility_result.get('message', '')
        loan_id = None
        monthly_installment = None

        if loan_approved:
            try:
                customer = Customer.objects.get(customer_id=customer_id)
                
                # We need a new unique loan_id
                last_loan = Loan.objects.order_by('-loan_id').first()
                new_loan_id = (last_loan.loan_id + 1) if last_loan else 1
                
                new_loan = Loan.objects.create(
                    customer=customer,
                    loan_id=new_loan_id,
                    loan_amount=data.get('loan_amount'),
                    tenure=data.get('tenure'),
                    interest_rate=eligibility_result.get('corrected_interest_rate'),
                    monthly_repayment=eligibility_result.get('monthly_installment'),
                    emis_paid_on_time=0,
                    start_date=datetime.now().date(),
                    # Assuming tenure is in months to calculate end_date
                    end_date=datetime.now().date() + pd.DateOffset(months=data.get('tenure'))
                )
                
                # IMPORTANT: Update customer's current_debt
                customer.current_debt += data.get('loan_amount')
                customer.save()
                
                loan_id = new_loan.id # Use the auto-created primary key
                monthly_installment = new_loan.monthly_repayment
                message = "Loan approved and created successfully"
                
            except Exception as e:
                loan_approved = False
                message = f"Error creating loan: {str(e)}"
        
        # Build response body [cite: 78]
        response_data = {
            "loan_id": loan_id,
            "customer_id": customer_id,
            "loan_approved": loan_approved,
            "message": message,
            "monthly_installment": monthly_installment
        }
        return Response(response_data, status=status.HTTP_201_CREATED if loan_approved else status.HTTP_200_OK)


class ViewLoanView(generics.RetrieveAPIView):
    """
    API for /view-loan/<loan_id> [cite: 79]
    """
    queryset = Loan.objects.all()
    serializer_class = ViewLoanSerializer
    lookup_field = 'id' # We use the 'id' (PK) from the URL

class ViewCustomerLoansView(generics.ListAPIView):
    """
    API for /view-loans/<customer_id> [cite: 83]
    """
    serializer_class = CustomerLoanSerializer
    
    def get_queryset(self):
        customer_id = self.kwargs['customer_id']
        return Loan.objects.filter(customer__customer_id=customer_id)