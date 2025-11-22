from django.db import models


class Departament(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class InventoryUser(models.Model):
    # ---- roluri ----
    ROLE_ADMIN = "admin"
    ROLE_STAFF = "staff"
    ROLE_VIEWER = "viewer"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_STAFF, "Staff"),
        (ROLE_VIEWER, "Viewer"),
    ]


    username = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    departament = models.ForeignKey(
        Departament,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )


    role = models.CharField(
        max_length=16,
        choices=ROLE_CHOICES,
        default=ROLE_VIEWER,
        help_text="Role in the inventory application (admin / staff / viewer).",
    )


    allowed_locations = models.CharField(
        max_length=255,
        blank=True,
        help_text="List of locations that the user is allowed to edit (comma separated, ex: IAS,FRA,QRO).",
    )

    def __str__(self):
        return self.username



    def _parsed_locations(self):

        if not self.allowed_locations:
            return set()
        return {
            part.strip().lower()
            for part in self.allowed_locations.split(",")
            if part.strip()
        }

    def can_edit_device(self, device) -> bool:

        if device is None or not getattr(device, "location", None):
            return False


        if self.role == self.ROLE_ADMIN:
            return True


        if self.role == self.ROLE_VIEWER:
            return False


        allowed = self._parsed_locations()
        return device.location.lower() in allowed


class Device(models.Model):
    DEVICE_TYPES = [
        ("pc", "PC"),
        ("laptop", "Laptop"),
        ("server", "Server"),
        ("vm", "VM"),
    ]

    STATUS_CHOICES = [
        ("deployed", "Deployed"),
        ("spare", "Spare"),
        ("repair", "In repair"),
        ("scrapped", "Casat"),
    ]

    hostname = models.CharField(max_length=100, unique=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="deployed")
    departament = models.ForeignKey(
        Departament,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_user = models.ForeignKey(
        InventoryUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
    )

    serial_number = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=100, blank=True)

    mac_address = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    purchase_date = models.DateField(blank=True, null=True)
    warranty_expiry = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.hostname


class SessionLog(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    user = models.ForeignKey(
        InventoryUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )

    login_time = models.DateTimeField()
    logout_time = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    @property
    def duration_seconds(self):
        if self.logout_time and self.login_time:
            return int((self.logout_time - self.login_time).total_seconds())
        return None

    def __str__(self):
        return f"{self.device} - {self.user} - {self.login_time}"
