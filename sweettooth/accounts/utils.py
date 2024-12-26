from django.contrib.auth.decorators import user_passes_test

def is_normal_user(user):
    return user.is_authenticated and not user.is_superuser

def user_login_required(view_func):
    decorated_view_func = user_passes_test(
        is_normal_user,
        login_url='login'
    )(view_func)
    return decorated_view_func
