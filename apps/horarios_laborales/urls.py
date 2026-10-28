from rest_framework.routers import DefaultRouter

from .views import HorarioDiarioViewSet


router = DefaultRouter()
router.register('horarios-diarios', HorarioDiarioViewSet, basename='horario-diario')

urlpatterns = router.urls
