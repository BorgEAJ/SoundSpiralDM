import time
import socket
import subprocess

import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# ===== OLED CONFIG (same as your working example) =====
oled_reset = digitalio.DigitalInOut(board.D4)

WIDTH = 128
HEIGHT = 32
i2c = board.I2C()
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3C, reset=oled_reset)

# Clear display.
oled.fill(0)
oled.show()

# Create drawing objects
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

REFRESH_SECONDS = 10.0


def get_hostname() -> str:
    return socket.gethostname()


def get_wlan_ip() -> str:
    """Prefer wlan0 IPv4. Returns 'no-ip' if not available."""
    try:
        ip = subprocess.check_output(
            ["bash", "-lc", r"ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return ip if ip else "no-ip"
    except Exception:
        return "no-ip"
    
def get_uptime():
    with open("/proc/uptime", "r") as f:
        seconds = float(f.readline().split()[0])

    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    #s = int(seconds % 60)

    return f"{h:02}:h {m:02}:min"



while True:
    host = get_hostname()
    ip = get_wlan_ip()
    uptime = get_uptime()

    # Clear buffer
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)

    draw.text((0, 0), f"HostName: {host}", font=font, fill=255)
    draw.text((0, 10), f"WiFi: {ip}", font=font, fill=255)
    draw.text((0, 22), f"UpTime: {uptime}", font=font, fill=255)

    oled.image(image)
    oled.show()

    time.sleep(REFRESH_SECONDS)

