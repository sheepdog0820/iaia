from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from oauth2_provider.models import get_application_model
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauth2_provider.views import AuthorizationView
from oauthlib.oauth2.rfc6749.errors import CustomOAuth2Error

from tableno_mcp.config import MCP_RESOURCE


def pilot_user(user):
    return bool(user and user.is_active and user.pk in settings.TABLENO_MCP_USER_IDS)


def pilot_client(application):
    return (
        application.client_id == settings.TABLENO_MCP_CLIENT_ID
        and application.client_type == application.CLIENT_PUBLIC
        and application.authorization_grant_type == application.GRANT_AUTHORIZATION_CODE
        and not application.skip_authorization
    )


class PilotOAuthValidator(OAuth2Validator):
    def _load_application(self, client_id, request):
        if client_id != settings.TABLENO_MCP_CLIENT_ID:
            return None
        application = super()._load_application(client_id, request)
        return application if application and pilot_client(application) else None

    def _validate_resource_uris(self, request, resources):
        if resources and resources != [MCP_RESOURCE]:
            raise CustomOAuth2Error(
                error="invalid_target", description="対象リソースを確認してください。", request=request
            )

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        return super().validate_code(client_id, code, client, request, *args, **kwargs) and pilot_user(request.user)

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        return super().validate_refresh_token(refresh_token, client, request, *args, **kwargs) and pilot_user(
            request.user
        )


@method_decorator(never_cache, name="dispatch")
class PilotAuthorizationView(AuthorizationView):
    template_name = "mcp/authorize.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not pilot_user(request.user):
            return HttpResponseForbidden("このアカウントではタブレノMCPを利用できません。")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.GET.getlist("resource") != [MCP_RESOURCE]:
            return HttpResponseBadRequest("対象リソースを確認してください。")
        if not request.GET.get("code_challenge") or request.GET.get("code_challenge_method") != "S256":
            return HttpResponseBadRequest("Codexから接続を開始してください。")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if form.cleaned_data["resource"] != MCP_RESOURCE:
            return HttpResponseBadRequest("対象リソースを確認してください。")
        if not form.cleaned_data["code_challenge"] or form.cleaned_data["code_challenge_method"] != "S256":
            return HttpResponseBadRequest("Codexから接続を開始してください。")
        client_id = form.cleaned_data["client_id"]
        application = get_application_model().objects.filter(client_id=client_id).first()
        if application is None or not pilot_client(application):
            return HttpResponseBadRequest("接続先アプリケーションを確認してください。")
        return super().form_valid(form)
