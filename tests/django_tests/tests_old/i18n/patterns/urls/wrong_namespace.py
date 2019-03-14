from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

view = TemplateView.as_view(template_name='dummy.html')

app_name = 'account'
urlpatterns = i18n_patterns(
    url(_(r'^register/$'), view, name='register'),
)
