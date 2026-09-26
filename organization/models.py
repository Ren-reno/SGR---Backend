from django.contrib.auth.models import User
from django.db import models


class Delegation(models.Model):
    """Antes Delegacion (Decisión 13: renombrado a inglés + separación en
    apps). Campos: nombre -> name, ambito -> scope, estado -> is_active
    (BooleanField real, no un status de texto -- por eso is_active y no
    "status")."""
    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=150)
    scope = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Position(models.Model):
    """Antes Cargo (Decisión 13)."""
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    """Antes Funcionario (Decisión 13). id_institucional -> institutional_id,
    delegacion -> delegation, cargo -> position, nombre -> name,
    estado -> is_active."""
    institutional_id = models.CharField(max_length=20, primary_key=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='employee'
    )
    delegation = models.ForeignKey(
        Delegation, on_delete=models.PROTECT, related_name='employees'
    )
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name='employees'
    )
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
