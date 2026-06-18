from django.shortcuts import render

def home(request):
    return render(request, 'core/index.html')

def pricing(request):
    return render(request, 'core/pricing.html')
