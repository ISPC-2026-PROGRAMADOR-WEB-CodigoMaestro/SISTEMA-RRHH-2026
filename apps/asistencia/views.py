"""Vistas de control de asistencia."""
from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.permissions import OperarPersonal
from apps.empleados.models import Empleado

from .models import (
    AsignacionJornada,
    Feriado,
    Jornada,
    Marcacion,
    RegistroAsistencia,
    Turno,
)
from .serializers import (
    AsignacionJornadaSerializer,
    CerrarDiaSerializer,
    FeriadoSerializer,
    ImportarMarcacionesSerializer,
    JornadaSerializer,
    MarcacionSerializer,
    RegistroAsistenciaSerializer,
    TurnoSerializer,
)
from .services import (
    cerrar_dia,
    consolidar_dia,
    importar_marcaciones,
    registrar_marcacion,
)
from drf_spectacular.utils import OpenApiResponse, extend_schema
from django.utils import timezone


class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['activo']
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'hora_inicio']


class JornadaViewSet(viewsets.ModelViewSet):
    queryset = Jornada.objects.select_related('empleado', 'turno')
    serializer_class = JornadaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['empleado', 'turno', 'dia_semana', 'activa', 'es_predeterminada']
    search_fields = ['empleado__legajo', 'empleado__apellido', 'turno__nombre']
    ordering_fields = ['nombre', 'dia_semana', 'vigencia_desde']


class AsignacionJornadaViewSet(viewsets.ModelViewSet):
    queryset = AsignacionJornada.objects.select_related('empleado', 'jornada')
    serializer_class = AsignacionJornadaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['empleado', 'jornada']
    search_fields = ['empleado__legajo', 'empleado__apellido', 'jornada__nombre']
    ordering_fields = ['empleado__apellido', 'jornada__nombre']


class FeriadoViewSet(viewsets.ModelViewSet):
    queryset = Feriado.objects.all()
    serializer_class = FeriadoSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['fecha']
    search_fields = ['nombre']
    ordering_fields = ['fecha', 'nombre']


class RegistroAsistenciaViewSet(viewsets.ModelViewSet):
    queryset = RegistroAsistencia.objects.select_related('empleado', 'cargado_por')
    serializer_class = RegistroAsistenciaSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['empleado', 'tipo', 'justificado', 'fecha']
    search_fields = ['empleado__legajo', 'empleado__apellido']
    ordering_fields = ['fecha', 'minutos_tardanza', 'minutos_extra']
    ordering = ['-fecha']

    def perform_create(self, serializer):
        serializer.save(cargado_por=self.request.user)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Resumen de ausentismo por empleado (para informes)."""
        qs = self.filter_queryset(self.get_queryset())
        resumen = (
            qs.values('empleado__legajo', 'empleado__apellido', 'empleado__nombre')
            .annotate(
                total_registros=Count('id'),
                ausencias=Count('id', filter=Q(tipo=RegistroAsistencia.Tipo.AUSENTE)),
                tardanzas=Count('id', filter=Q(tipo=RegistroAsistencia.Tipo.TARDANZA)),
                minutos_tardanza=Sum('minutos_tardanza'),
                minutos_extra=Sum('minutos_extra'),
            )
            .order_by('empleado__apellido')
        )
        return Response(list(resumen))

    @extend_schema(
        request=CerrarDiaSerializer,
        responses={
            200: OpenApiResponse(description='Resumen del cierre diario.'),
            400: OpenApiResponse(description='La fecha indicada no es válida.'),
        },
    )
    @action(detail=False, methods=['post'], url_path='cerrar-dia')
    def cerrar_dia(self, request):
        """Cierra un día; por omisión, cierra el día anterior."""
        texto_fecha = request.data.get('fecha')
        if texto_fecha:
            try:
                fecha = date.fromisoformat(texto_fecha)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'La fecha debe tener el formato YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            fecha = timezone.localdate() - timedelta(days=1)
        return Response(cerrar_dia(fecha))


class MarcacionViewSet(viewsets.ModelViewSet):
    queryset = Marcacion.objects.select_related('empleado', 'cargado_por')
    serializer_class = MarcacionSerializer
    permission_classes = [permissions.IsAuthenticated, OperarPersonal]
    filterset_fields = ['empleado', 'tipo', 'origen', 'fecha_hora']
    search_fields = ['empleado__legajo', 'empleado__apellido']
    ordering_fields = ['fecha_hora', 'tipo', 'origen']
    ordering = ['-fecha_hora']
    http_method_names = ['get', 'post', 'head', 'options']
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, serializer):
        marcacion = serializer.save(
            origen=Marcacion.Origen.MANUAL,
            cargado_por=self.request.user,
        )
        consolidar_dia(
            marcacion.empleado,
            timezone.localtime(marcacion.fecha_hora).date(),
        )

    @extend_schema(
        request=None,
        responses={
            201: MarcacionSerializer,
            400: OpenApiResponse(description='El usuario no tiene legajo o debe esperar.'),
        },
    )
    @action(
        detail=False,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
    )
    def marcar(self, request):
        """Fichaje del usuario autenticado con la hora del servidor."""
        try:
            empleado = request.user.empleado
        except (Empleado.DoesNotExist, AttributeError):
            return Response(
                {'detail': 'Tu usuario no está vinculado a un legajo de empleado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            marcacion = registrar_marcacion(
                empleado,
                Marcacion.Origen.WEB,
                ip=request.META.get('REMOTE_ADDR'),
                cargado_por=request.user,
            )
        except ValidationError as exc:
            detalle = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detalle}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            MarcacionSerializer(marcacion).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        responses={
            200: OpenApiResponse(description='Estado de marcaciones de hoy y próxima acción.'),
            400: OpenApiResponse(description='El usuario no tiene legajo asociado.'),
        },
    )
    @action(
        detail=False,
        methods=['get'],
        url_path='mi-estado',
        permission_classes=[permissions.IsAuthenticated],
    )
    def mi_estado(self, request):
        """Devuelve el estado del fichaje del usuario para el día local actual."""
        try:
            empleado = request.user.empleado
        except (Empleado.DoesNotExist, AttributeError):
            return Response(
                {'detail': 'Tu usuario no está vinculado a un legajo de empleado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        hoy = timezone.localdate()
        inicio = timezone.make_aware(
            datetime.combine(hoy, time.min),
            timezone.get_current_timezone(),
        )
        fin = timezone.make_aware(
            datetime.combine(hoy + timedelta(days=1), time.min),
            timezone.get_current_timezone(),
        )
        marcaciones = Marcacion.objects.filter(
            empleado=empleado,
            fecha_hora__gte=inicio,
            fecha_hora__lt=fin,
        ).order_by('fecha_hora')
        datos = list(marcaciones)
        tiene_entrada = any(m.tipo == Marcacion.Tipo.ENTRADA for m in datos)
        tiene_salida = any(m.tipo == Marcacion.Tipo.SALIDA for m in datos)
        return Response({
            'fecha': hoy,
            'marcaciones': MarcacionSerializer(datos, many=True).data,
            'falta_salida': tiene_entrada and not tiene_salida,
            'proxima_accion': (
                Marcacion.Tipo.SALIDA if tiene_entrada else Marcacion.Tipo.ENTRADA
            ),
        })

    @extend_schema(
        request=ImportarMarcacionesSerializer,
        responses={
            200: OpenApiResponse(description='Resumen de la importación.'),
            400: OpenApiResponse(description='Archivo inválido o fuera de límites.'),
        },
    )
    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
    )
    def importar(self, request):
        """Importa marcaciones desde un CSV o XLSX."""
        entrada = ImportarMarcacionesSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            resumen = importar_marcaciones(
                entrada.validated_data['archivo'],
                request.user,
            )
        except ValidationError as exc:
            detalle = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            return Response({'detail': detalle}, status=status.HTTP_400_BAD_REQUEST)
        return Response(resumen)
