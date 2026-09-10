from django.db import models

# Create your models here.
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

class Enquiry(models.Model):
    FORM_TYPES = [
        ("valuation", "Valuation Request"),
        ("contact", "General Contact"),
        ("property", "Property Enquiry"),
        ("blog", "Blog Enquiry"),
   ("newsletter", "Newsletter Subscription"),
]

    form_type = models.CharField(max_length=20, choices=FORM_TYPES)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    message = models.TextField(blank=True)

    # valuation-specific
    property_type = models.CharField(max_length=50, blank=True)

    # property-detail-page-specific
    property_slug = models.CharField(max_length=255, blank=True)
    property_name = models.CharField(max_length=255, blank=True)
    interest = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_to_brevo = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.form_type}] {self.name} - {self.email}"


 

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=500, unique=True, blank=True) 
    excerpt = models.TextField(max_length=300)
  
    content = CKEditor5Field('Text', config_name='default')
    image = models.ImageField(upload_to='blogs/', null=True, blank=True)
    
    meta_title = models.CharField(max_length=150)
    meta_description = models.TextField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    cta_heading = models.CharField(max_length=300, null=True, blank=True)
    cta_subheading = models.TextField(null=True, blank=True)
    cta_button_text = models.CharField(max_length=100, null=True, blank=True)
    cta_button_link = models.URLField(null=True, blank=True)
    

class FAQ(models.Model):
    blog = models.ForeignKey(BlogPost, related_name='faqs', on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    answer = models.TextField()

    def __str__(self):
        return self.question