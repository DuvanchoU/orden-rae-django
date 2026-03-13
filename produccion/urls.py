from django.urls import path
from .views import ProduccionListView, ProduccionCreateView, ProduccionUpdateView, ProduccionDeleteView, ProduccionDetailView

app_name = 'produccion'

urlpatterns = [
    path('', ProduccionListView.as_view(), name='produccion_list'),
    path('nueva/', ProduccionCreateView.as_view(), name='produccion_create'),
    path('produccion/<int:pk>/', ProduccionDetailView.as_view(), name='produccion_detail'),
    path('<int:pk>/editar/', ProduccionUpdateView.as_view(), name='produccion_update'),
    path('<int:pk>/eliminar/', ProduccionDeleteView.as_view(), name='produccion_delete'),
]