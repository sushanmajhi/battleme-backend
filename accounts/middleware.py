from django.utils.timezone import now

class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile:
                profile.last_seen = now()
                profile.save(update_fields=["last_seen"])
        return self.get_response(request)