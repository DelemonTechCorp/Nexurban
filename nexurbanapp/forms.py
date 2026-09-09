from django import forms
from .models import Enquiry

class ValuationForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["name", "phone", "email", "property_type", "message"]

class ContactForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["name", "email", "phone", "message"]

class PropertyEnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["name", "email", "phone", "interest", "message", "property_slug", "property_name"]