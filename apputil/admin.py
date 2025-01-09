from django.contrib import admin
from django.contrib.auth.forms import UserChangeForm,AdminPasswordChangeForm

from apputil.models import ApplicationUser,Dictionary

# Register your models here.
admin.site.register(ApplicationUser)
admin.site.register(Dictionary)


# class ApplicationUser(admin.ModelAdmin):
#     # code
#     form = UserChangeForm
#     change_password_form = AdminPasswordChangeForm
#     # code

