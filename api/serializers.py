from rest_framework import serializers
from .models import Customer, Loan

# Serializer for the /view-loan/ endpoint [cite: 82]
class CustomerNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['customer_id', 'first_name', 'last_name', 'phone_number', 'age']

class ViewLoanSerializer(serializers.ModelSerializer):
    customer = CustomerNestedSerializer()
    loan_id = serializers.IntegerField(source='id') # Use 'id' from the model [cite: 82]
    monthly_installment = serializers.DecimalField(source='monthly_repayment', max_digits=10, decimal_places=2)

    class Meta:
        model = Loan
        fields = ['loan_id', 'customer', 'loan_amount', 'interest_rate', 'monthly_installment', 'tenure']

# Serializer for the /view-loans/ endpoint [cite: 87]
class CustomerLoanSerializer(serializers.ModelSerializer):
    loan_id = serializers.IntegerField(source='id')
    monthly_installment = serializers.DecimalField(source='monthly_repayment', max_digits=10, decimal_places=2)
    repayments_left = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = ['loan_id', 'loan_amount', 'interest_rate', 'monthly_installment', 'repayments_left']

    def get_repayments_left(self, obj):
        # Calculates remaining EMIs [cite: 87]
        return obj.tenure - obj.emis_paid_on_time