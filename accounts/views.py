from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView


class SignUpView(CreateView):
    """Self-service account creation. Django's built-in LoginView/LogoutView
    handle the rest of authentication — no need to reinvent them."""

    form_class = UserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('leagues:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
