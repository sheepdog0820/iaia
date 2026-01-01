"""
User and authentication related views
"""
from .common_imports import *
from django.contrib.auth import logout as auth_logout
from django.conf import settings
from django.contrib.sites.models import Site
from django.views import View
from allauth.socialaccount.models import SocialApp
from .base_views import BaseViewSet
from .mixins import UserOwnershipMixin, ErrorHandlerMixin


class UserViewSet(viewsets.ModelViewSet):
    """User management ViewSet"""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.action == 'list':
            return CustomUser.objects.filter(id=self.request.user.id)
        return CustomUser.objects.all()
    
    @action(detail=True, methods=['get'])
    def friends(self, request, pk=None):
        """Get user's friends"""
        user = self.get_object()
        friends = Friend.objects.filter(user=user)
        serializer = FriendSerializer(friends, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def groups(self, request, pk=None):
        """Get user's groups"""
        user = self.get_object()
        memberships = GroupMembership.objects.filter(user=user)
        serializer = GroupMembershipSerializer(memberships, many=True)
        return Response(serializer.data)


class FriendViewSet(viewsets.ModelViewSet):
    """Friend management ViewSet"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return FriendDetailSerializer
        return FriendSerializer
    
    def get_queryset(self):
        return Friend.objects.filter(user=self.request.user).select_related('friend')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProfileView(APIView):
    """User profile API view"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddFriendView(APIView):
    """Add friend API view"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            friend_username = request.data.get('username')
            friend = User.objects.get(username=friend_username)
            
            # Check if already friends
            if Friend.objects.filter(user=request.user, friend=friend).exists():
                return Response(
                    {'error': 'Already friends'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create friendship
            Friend.objects.create(user=request.user, friend=friend)
            return Response({'success': True}, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


def _is_placeholder(value, placeholders):
    return not value or value in placeholders


def _ensure_social_apps():
    providers = set(SocialApp.objects.filter(
        provider__in=['google', 'twitter_oauth2']
    ).values_list('provider', flat=True))
    site = Site.objects.get_current()

    google_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
    google_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')
    google_placeholders = {'your-google-client-id', 'your-google-client-secret'}
    if not _is_placeholder(google_client_id, google_placeholders) and not _is_placeholder(google_secret, google_placeholders):
        google_app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': google_client_id,
                'secret': google_secret
            }
        )
        if not created:
            updated = False
            if google_app.client_id != google_client_id:
                google_app.client_id = google_client_id
                updated = True
            if google_app.secret != google_secret:
                google_app.secret = google_secret
                updated = True
            if updated:
                google_app.save(update_fields=['client_id', 'secret'])
        if site not in google_app.sites.all():
            google_app.sites.add(site)
        providers.add('google')

    twitter_client_id = getattr(settings, 'TWITTER_CLIENT_ID', '')
    twitter_secret = getattr(settings, 'TWITTER_CLIENT_SECRET', '')
    twitter_placeholders = {'your-twitter-client-id', 'your-twitter-client-secret'}
    if not _is_placeholder(twitter_client_id, twitter_placeholders) and not _is_placeholder(twitter_secret, twitter_placeholders):
        twitter_app, created = SocialApp.objects.get_or_create(
            provider='twitter_oauth2',
            defaults={
                'name': 'X',
                'client_id': twitter_client_id,
                'secret': twitter_secret
            }
        )
        if not created:
            updated = False
            if twitter_app.client_id != twitter_client_id:
                twitter_app.client_id = twitter_client_id
                updated = True
            if twitter_app.secret != twitter_secret:
                twitter_app.secret = twitter_secret
                updated = True
            if updated:
                twitter_app.save(update_fields=['client_id', 'secret'])
        if site not in twitter_app.sites.all():
            twitter_app.sites.add(site)
        providers.add('twitter_oauth2')

    return providers


# Django Web Views

class CustomLoginView(FormView):
    """Custom login view"""
    template_name = 'account/login.html'
    form_class = CustomLoginForm
    success_url = reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        """Add social login configuration flags to context"""
        context = super().get_context_data(**kwargs)
        providers = _ensure_social_apps()
        context['google_configured'] = 'google' in providers
        context['twitter_configured'] = 'twitter_oauth2' in providers
        context['social_login_available'] = bool(providers)
        return context

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        return super().form_valid(form)


class CustomSignUpView(FormView):
    """Custom signup view"""
    template_name = 'account/signup.html'
    form_class = CustomSignUpForm
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        user = form.save()

        # Ensure allauth EmailAddress is in sync for email login & email management.
        try:
            from allauth.account.models import EmailAddress

            EmailAddress.objects.update_or_create(
                user=user,
                email=user.email,
                defaults={
                    'primary': True,
                    # Email verification is disabled in settings, so mark as verified.
                    'verified': True,
                },
            )
        except Exception:
            pass

        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1']
        )
        login(self.request, user)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add social login configuration flags to context"""
        context = super().get_context_data(**kwargs)
        providers = _ensure_social_apps()
        context['google_configured'] = 'google' in providers
        context['twitter_configured'] = 'twitter_oauth2' in providers
        context['social_login_available'] = bool(providers)
        return context


class CustomLogoutView(View):
    """Custom logout view"""

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        return redirect('home')

    def post(self, request, *args, **kwargs):
        auth_logout(request)
        return redirect('home')


@method_decorator(login_required, name='dispatch')
class ProfileEditView(FormView):
    """Profile edit view"""
    template_name = 'account/profile_edit.html'
    form_class = ProfileEditForm
    success_url = reverse_lazy('dashboard')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'プロフィールが更新されました。')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """User dashboard view"""
    template_name = 'account/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's sessions
        from schedules.models import TRPGSession
        from django.db.models import Q, Sum

        sessions_qs = TRPGSession.objects.filter(
            Q(participants=self.request.user) | Q(gm=self.request.user)
        ).distinct()

        current_year = timezone.now().year
        sessions_this_year_qs = sessions_qs.filter(date__year=current_year)
        total_minutes = sessions_this_year_qs.aggregate(total=Sum('duration_minutes'))['total'] or 0

        context['sessions_this_year'] = sessions_this_year_qs.count()
        context['total_hours'] = round(total_minutes / 60, 1)
        context['group_count'] = GroupMembership.objects.filter(user=self.request.user).count()
        context['friend_count'] = Friend.objects.filter(user=self.request.user).count()

        context['upcoming_sessions'] = TRPGSession.objects.filter(
            Q(participants=self.request.user) | Q(gm=self.request.user),
            date__gte=timezone.now()
        ).distinct().order_by('date')[:5]
        
        context['recent_sessions'] = TRPGSession.objects.filter(
            Q(participants=self.request.user) | Q(gm=self.request.user),
            date__lt=timezone.now()
        ).distinct().order_by('-date')[:5]
        
        # Get social accounts
        social_accounts = SocialAccount.objects.filter(user=self.request.user)
        context['social_accounts'] = social_accounts
        context['social_login_connected'] = social_accounts.filter(
            provider__in=['google', 'twitter_oauth2']
        ).exists()
        context['email_missing'] = not bool(self.request.user.email)
        
        return context


@method_decorator(login_required, name='dispatch')
class AccountDeleteView(TemplateView):
    template_name = 'account/account_delete.html'

    def post(self, request, *args, **kwargs):
        user = request.user

        confirm = (request.POST.get('confirm') or '').strip().lower()
        password = request.POST.get('password') or ''

        if confirm != 'delete':
            messages.error(request, '確認のため、入力欄に「DELETE」と入力してください。')
            return redirect('account_delete')

        if user.has_usable_password():
            if not user.check_password(password):
                messages.error(request, 'パスワードが正しくありません。')
                return redirect('account_delete')

        # Logout first so the session does not reference a deleted user.
        auth_logout(request)
        user.delete()

        messages.success(request, 'アカウントを削除しました。ご利用ありがとうございました。')
        return redirect('home')


# Development/Demo Views

def demo_login_page(request):
    """Demo login page for development"""
    providers = [
        {'name': 'Google', 'id': 'google'},
        {'name': 'X', 'id': 'twitter_oauth2'},
    ]
    
    return render(request, 'accounts/demo_login.html', {
        'providers': providers,
        'demo_mode': True
    })


def mock_social_login(request, provider):
    """Mock social login for development"""
    if provider == 'google':
        user, created = User.objects.get_or_create(
            username='google_demo_user',
            defaults={
                'email': 'demo@google.com',
                'first_name': 'Google',
                'last_name': 'Demo',
                'nickname': 'Google Demo User'
            }
        )
    elif provider == 'twitter_oauth2':
        user, created = User.objects.get_or_create(
            username='twitter_demo_user',
            defaults={
                'email': 'demo@twitter.com',
                'first_name': 'Twitter',
                'last_name': 'Demo',
                'nickname': 'Twitter Demo User'
            }
        )
    else:
        messages.error(request, f'Unknown provider: {provider}')
        return redirect('demo_login')
    
    # Create or get social account
    social_account, created = SocialAccount.objects.get_or_create(
        user=user,
        provider=provider,
        defaults={'uid': f'{provider}_demo_uid'}
    )
    
    # Log in the user
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f'{provider.title()}でログインしました（デモモード）')
    
    return redirect('dashboard')
