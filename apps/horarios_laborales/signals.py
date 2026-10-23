from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import HorarioDiario, HorarioPredeterminado


def _recalcular_asistencias(empleado_id, fecha):
    from apps.asistencia.services import recalcular_asistencias

    recalcular_asistencias(empleado_id, fecha)


@receiver(pre_save, sender=HorarioDiario)
def guardar_clave_anterior_horario(sender, instance, **kwargs):
    if instance.pk is None:
        instance._clave_anterior_horario = None
        return
    instance._clave_anterior_horario = sender.objects.filter(
        pk=instance.pk,
    ).values_list('empleado_id', 'fecha').first()


@receiver(post_save, sender=HorarioDiario)
def recalcular_al_guardar_horario(sender, instance, **kwargs):
    clave_actual = (instance.empleado_id, instance.fecha)
    clave_anterior = getattr(instance, '_clave_anterior_horario', None)
    if clave_anterior and clave_anterior != clave_actual:
        _recalcular_asistencias(*clave_anterior)
    _recalcular_asistencias(*clave_actual)


@receiver(pre_delete, sender=HorarioDiario)
def guardar_clave_horario_borrado(sender, instance, **kwargs):
    instance._clave_horario_borrado = (instance.empleado_id, instance.fecha)


@receiver(post_delete, sender=HorarioDiario)
def recalcular_al_borrar_horario(sender, instance, **kwargs):
    clave = getattr(instance, '_clave_horario_borrado', None)
    if clave:
        _recalcular_asistencias(*clave)


def _recalcular_desde(empleado_id, fecha):
    from apps.asistencia.models import RegistroAsistencia

    registros = RegistroAsistencia.objects.filter(
        empleado_id=empleado_id,
        fecha__gte=fecha,
    ).select_related('empleado')
    for registro in registros.iterator():
        registro.save()


@receiver(pre_save, sender=HorarioPredeterminado)
def guardar_clave_anterior_predeterminado(sender, instance, **kwargs):
    if instance.pk is None:
        instance._clave_anterior_predeterminado = None
        return
    instance._clave_anterior_predeterminado = sender.objects.filter(
        pk=instance.pk,
    ).values_list('empleado_id', 'vigente_desde').first()


@receiver(post_save, sender=HorarioPredeterminado)
def recalcular_al_guardar_predeterminado(sender, instance, **kwargs):
    clave_actual = (instance.empleado_id, instance.vigente_desde)
    clave_anterior = getattr(
        instance,
        '_clave_anterior_predeterminado',
        None,
    )
    if clave_anterior and clave_anterior != clave_actual:
        _recalcular_desde(*clave_anterior)
    _recalcular_desde(*clave_actual)


@receiver(pre_delete, sender=HorarioPredeterminado)
def guardar_clave_predeterminado_borrado(sender, instance, **kwargs):
    instance._clave_predeterminado_borrado = (
        instance.empleado_id,
        instance.vigente_desde,
    )


@receiver(post_delete, sender=HorarioPredeterminado)
def recalcular_al_borrar_predeterminado(sender, instance, **kwargs):
    clave = getattr(instance, '_clave_predeterminado_borrado', None)
    if clave:
        _recalcular_desde(*clave)
