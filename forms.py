from django import forms
from .models import Device, InventoryUser


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "hostname",
            "device_type",
            "status",
            "departament",
            "assigned_user",
            "serial_number",
            "os",
            "location",
            "mac_address",
            "ip_address",
            "purchase_date",
            "warranty_expiry",
        ]


class UserPermissionsForm(forms.ModelForm):
    class Meta:
        model = InventoryUser
        fields = ["role", "allowed_locations"]
        widgets = {
            "role": forms.Select(attrs={"class": "form-control"}),
            "allowed_locations": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "IAS,FRA,QRO",
                }
            ),
        }
        help_texts = {
            "allowed_locations": "Comma-separated list, e.g. IAS,FRA,QRO. Staff can only edit devices in these locations.",
        }
