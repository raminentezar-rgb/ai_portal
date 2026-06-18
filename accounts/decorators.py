from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def check_credits(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to use this tool.")
            return redirect('accounts:login')
            
        if request.method == 'POST':
            if not request.user.userprofile.is_pro and request.user.userprofile.credits <= 0:
                messages.warning(request, "You have run out of credits. Please upgrade your plan or buy more credits.")
                return redirect('pricing')
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def deduct_credit(user):
    if not user.userprofile.is_pro and user.userprofile.credits > 0:
        user.userprofile.credits -= 1
        user.userprofile.save()
