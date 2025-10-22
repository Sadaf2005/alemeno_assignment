# from django.db import models
from django.db import models

class Customer(models.Model):
    # Fields from customer_data.xlsx [cite: 16-22]
    customer_id = models.IntegerField(primary_key=True) # Using the one from the file as the ID
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.BigIntegerField() # Use BigIntegerField for phone [cite: 19]
    monthly_salary = models.IntegerField()
    approved_limit = models.IntegerField()
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # New fields from /register endpoint 
    age = models.IntegerField(null=True, blank=True) # null=True because old data doesn't have it

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Loan(models.Model):
    # Fields from loan_data.xlsx [cite: 26-34]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_id = models.IntegerField(unique=True) # The ID from the file
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure = models.IntegerField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_repayment = models.DecimalField(max_digits=10, decimal_places=2)
    emis_paid_on_time = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"Loan {self.loan_id} for {self.customer.first_name}"
