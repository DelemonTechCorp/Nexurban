from django.contrib import admin
from django.utils.html import strip_tags
from .models import (
    BlogPost,
    FAQ,
)
# Register your models here.
from .models import Enquiry

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "form_type", "created_at", "sent_to_brevo")
    list_filter = ("form_type", "sent_to_brevo", "created_at")
    search_fields = ("name", "email", "phone")
    from django.contrib import admin



# ══════════════════════════════════════════════════════════════════
# BLOG
# ══════════════════════════════════════════════════════════════════

class FAQInline(admin.TabularInline):
    model = FAQ
    extra = 1


@admin.register(BlogPost)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'created_at', 'reading_time_display')
    list_filter = ('created_at',)
    search_fields = ('title', 'excerpt', 'meta_title', 'meta_description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at',)
    inlines = [FAQInline]

    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'image')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Call To Action', {
            'fields': ('cta_heading', 'cta_subheading', 'cta_button_text', 'cta_button_link'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )

    @admin.display(description='Reading Time')
    def reading_time_display(self, obj):
        word_count = len(strip_tags(obj.content).split())
        minutes = max(1, round(word_count / 200))  # ~200 words per minute
        return f"{minutes} min read"


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'blog')
    search_fields = ('question', 'answer')
    list_filter = ('blog',)