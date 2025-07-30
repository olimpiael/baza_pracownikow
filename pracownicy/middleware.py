from django.shortcuts import redirect

class SetPasswordAfterSocialMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.session.get('set_password_after_social'):
            if request.path not in ['/set_password', '/accounts/logout/']:
                return redirect('/set_password')
        response = self.get_response(request)
        return response
