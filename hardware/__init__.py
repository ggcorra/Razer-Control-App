"""
Pacchetto hardware per il controllo del mouse Razer Viper V3 HyperSpeed.
"""

from .razer_protocol import (
    RAZER_VENDOR_ID,
    RAZER_VIPER_V3_HYPERSPEED_PID,
    build_razer_report,
    parse_battery_response,
    parse_charging_response,
    parse_dpi_response,
    parse_polling_rate_response
)
from .mouse_device import (
    RazerMouseDevice,
    DeviceError,
    DeviceNotFoundError,
    AccessDeniedError,
    ProtocolError
)
from .windows_hook import (
    send_mouse_click,
    send_mouse_wheel,
    send_key_stroke,
    send_key_combination,
    get_windows_pointer_speed,
    set_windows_pointer_speed
)

__all__ = [
    "RazerMouseDevice",
    "DeviceError",
    "DeviceNotFoundError",
    "AccessDeniedError",
    "ProtocolError",
    "send_mouse_click",
    "send_mouse_wheel",
    "send_key_stroke",
    "send_key_combination",
    "get_windows_pointer_speed",
    "set_windows_pointer_speed"
]
