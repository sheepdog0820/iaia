from django.shortcuts import render


def terms_view(request):
    return render(request, 'legal/terms.html')


def privacy_view(request):
    return render(request, 'legal/privacy.html')


def contact_view(request):
    return render(request, 'legal/contact.html')
