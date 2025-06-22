"""
User and authentication related views
"""
from .common_imports import *
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


# Django Web Views

class CustomLoginView(FormView):
    """Custom login view"""
    template_name = 'registration/login.html'
    form_class = CustomLoginForm
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        return super().form_valid(form)


class CustomSignUpView(FormView):
    """Custom signup view"""
    template_name = 'registration/signup.html'
    form_class = CustomSignUpForm
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        user = form.save()
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1']
        )
        login(self.request, user)
        return super().form_valid(form)


class CustomLogoutView(TemplateView):
    """Custom logout view"""
    template_name = 'registration/logged_out.html'


@method_decorator(login_required, name='dispatch')
class ProfileEditView(FormView):
    """Profile edit view"""
    template_name = 'accounts/profile_edit.html'
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
        context['upcoming_sessions'] = TRPGSession.objects.filter(
            participants=self.request.user,
            date__gte=timezone.now()
        ).order_by('date')[:5]
        
        context['recent_sessions'] = TRPGSession.objects.filter(
            participants=self.request.user,
            date__lt=timezone.now()
        ).order_by('-date')[:5]
        
        # Get social accounts
        context['social_accounts'] = SocialAccount.objects.filter(
            user=self.request.user
        )
        
        return context


# Development/Demo Views

def demo_login_page(request):
    """Demo login page for development"""
    providers = [
        {'name': 'Google', 'id': 'google'},
        {'name': 'Twitter', 'id': 'twitter'},
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
    elif provider == 'twitter':
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