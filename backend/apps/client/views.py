from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.views import View
from django.db.models import Q
from django.contrib.auth import login
from django.urls import reverse_lazy
from apps.content.models import Category, DocumentVersion
from django.http import HttpResponse, Http404
import os
from django.conf import settings
from .forms import ClientRegistrationForm, SupportRequestForm
from asgiref.sync import async_to_sync
from apps.analytics.utils import log_interaction, log_search_query

class UserLoginView(LoginView):
    template_name = 'client/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        response = super().form_valid(form)
        async_to_sync(log_interaction)(
            django_user=self.request.user,
            action_type='web_login'
        )
        return response

class RegisterView(CreateView):
    template_name = 'client/register.html'
    form_class = ClientRegistrationForm
    success_url = reverse_lazy('client:home')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        
        # Notify admins
        from apps.bot.notifications import notify_admins_new_user
        from asgiref.sync import async_to_sync
        async_to_sync(notify_admins_new_user)(user, source="Web Registration")
        
        return redirect(self.success_url)

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'client/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Show root categories
        context['categories'] = Category.objects.filter(
            parent=None, 
            is_folder=True, 
            visible_in_bot=True
        ).order_by('order')
        return context

class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'client/category.html'
    context_object_name = 'category'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if hasattr(self, 'object') and self.object:
             async_to_sync(log_interaction)(
                django_user=request.user,
                action_type='web_view',
                path=f"cat:{self.object.id}"
            )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object
        
        # Subcategories
        context['subcategories'] = category.children.filter(
            is_folder=True, 
            visible_in_bot=True
        ).order_by('order')
        
        # Documents (Nodes with is_folder=False)
        context['documents'] = category.children.filter(
            is_folder=False, 
            visible_in_bot=True
        ).order_by('order')

        # Subscription status
        context['has_telegram'] = False
        context['is_subscribed'] = False
        
        if self.request.user.telegram_id:
            context['has_telegram'] = True
            from apps.bot.models import BotUser
            bot_user = BotUser.objects.filter(telegram_id=self.request.user.telegram_id).first()
            if bot_user:
                context['is_subscribed'] = bot_user.subscribed_categories.filter(id=category.id).exists()
        
        return context

class ToggleSubscriptionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        
        if not request.user.telegram_id:
            from django.contrib import messages
            messages.warning(request, "Для подписки на уведомления необходимо привязать Telegram-аккаунт.")
            return redirect('client:category', pk=pk)
            
        from apps.bot.models import BotUser
        bot_user = BotUser.objects.filter(telegram_id=request.user.telegram_id).first()
        
        if not bot_user:
            from django.contrib import messages
            messages.error(request, "Ваш Telegram-аккаунт не найден в базе данных бота. Пожалуйста, запустите бота еще раз.")
            return redirect('client:category', pk=pk)
            
        if bot_user.subscribed_categories.filter(id=category.id).exists():
            bot_user.subscribed_categories.remove(category)
            from django.contrib import messages
            messages.success(request, f"Вы успешно отписались от категории '{category.title}'.")
        else:
            bot_user.subscribed_categories.add(category)
            from django.contrib import messages
            messages.success(request, f"Вы успешно подписались на категорию '{category.title}'. Уведомления будут приходить в Telegram.")
            
        return redirect('client:category', pk=pk)

class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'client/document.html'
    context_object_name = 'document'
    
    def get_object(self, queryset=None):
        # Allow access only if it's a document node
        obj = super().get_object(queryset)
        if obj.is_folder:
            raise Http404("Not a document")
        return obj

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if hasattr(self, 'object') and self.object:
             async_to_sync(log_interaction)(
                django_user=request.user,
                action_type='web_view',
                path=f"doc:{self.object.id}"
            )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get latest version
        context['version'] = DocumentVersion.objects.filter(
            content_node=self.object
        ).order_by('-created_at').first()
        return context

class SearchView(LoginRequiredMixin, ListView):
    template_name = 'client/search.html'
    context_object_name = 'results'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        if not query:
            return Category.objects.none()
        
        return Category.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query),
            is_folder=False,
            visible_in_bot=True
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        query = request.GET.get('q')
        if query:
            count = 0
            # We can't easily get the count from the response context without being hacky
            # But we can re-evaluate or just trust the queryset length logic if we moved it.
            # Easiest is to log inside get_context_data where we have the object list?
            # Or just count here.
            # Actually, `self.object_list` is populated by `super().get()`.
            if hasattr(self, 'object_list'):
                count = self.object_list.count()
            
            async_to_sync(log_search_query)(
                django_user=request.user,
                query_text=query,
                results_count=count
            )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

from django.contrib import messages
from django.views.generic.edit import FormView

class SupportView(LoginRequiredMixin, FormView):
    template_name = 'client/support.html'
    form_class = SupportRequestForm
    success_url = reverse_lazy('client:home')

    def form_valid(self, form):
        # Create and save object
        support_request = form.save(commit=False)
        support_request.django_user = self.request.user
        support_request.save()
        
        # Notify admins
        from apps.bot.notifications import notify_admins_support_request
        # We can't await here easily without making the whole method sync_to_async or similar,
        # but notify_admins_support_request uses Celery task internally for sending.
        # However, it is an 'async def'. Let's use async_to_sync.
        from asgiref.sync import async_to_sync
        async_to_sync(notify_admins_support_request)(support_request)
        
        from apps.analytics.utils import log_interaction
        from asgiref.sync import async_to_sync
        async_to_sync(log_interaction)(
            user_id=None, 
            action_type="support_request", 
            path="web_form", 
            django_user=self.request.user
        )

        messages.success(self.request, "Ваше сообщение отправлено успешно! Мы свяжемся с вами.")
        return super().form_valid(form)
