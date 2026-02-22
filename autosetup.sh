#!/usr/bin/env bash
set -euo pipefail

# ========= USER CONFIG (only change if you want) =========
REPO_RAW_BASE="https://raw.githubusercontent.com/BorgEAJ/SoundSpiralDM/main"
FILES_TO_HOME=("DynamountREv2.py" "DynamountREv2_helper.py" "oled.py")

VENV_NAME="venv"                     # will be created at ~/${VENV_NAME}
SERVICE_NAME="oled"                  # systemd service name: oled.service
KOHVEETIA_CMD="/usr/local/bin/kohveetia"
# =========================================================

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo:"
  echo "  sudo bash $0"
  exit 1
fi

# Figure out the real user (so this works even when run via sudo)
REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || true)}"
if [[ -z "${REAL_USER}" || "${REAL_USER}" == "root" ]]; then
  echo "Couldn't determine non-root user. Run as:"
  echo "  sudo -u <user> bash $0   (or use sudo normally from that user)"
  exit 1
fi

HOME_DIR="$(getent passwd "${REAL_USER}" | cut -d: -f6)"
VENV_DIR="${HOME_DIR}/${VENV_NAME}"

echo "==> User: ${REAL_USER}"
echo "==> Home: ${HOME_DIR}"
echo "==> Venv: ${VENV_DIR}"
echo

echo "==> Updating OS packages"
apt update
apt -y upgrade

echo "==> Installing OS dependencies"
apt install -y \
  python3-full python3-venv python3-pip \
  libopenblas0 \
  libjpeg-dev zlib1g-dev libfreetype6-dev \
  i2c-tools \
  curl git

echo "==> Enabling I2C + Serial (non-interactive raspi-config)"
# Enable I2C
raspi-config nonint do_i2c 0
# Disable serial login shell (1 = disable login console)
raspi-config nonint do_serial_cons 1
# Enable serial hardware (0 = enable UART)
raspi-config nonint do_serial_hw 0

echo "==> Creating venv (if missing)"
if [[ ! -d "${VENV_DIR}" ]]; then
  sudo -u "${REAL_USER}" python3 -m venv "${VENV_DIR}"
fi

echo "==> Upgrading pip tooling in venv"
sudo -u "${REAL_USER}" "${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

echo "==> Installing Python libraries into venv"
sudo -u "${REAL_USER}" "${VENV_DIR}/bin/python" -m pip install \
  numpy sshkeyboard PyTmcStepper RPi.GPIO pyserial \
  adafruit-circuitpython-ssd1306 pillow gpiozero bitstring \
  TMC-2209-Raspberry-Pi

echo "==> Downloading your Python files to home directory"
cd "${HOME_DIR}"
for f in "${FILES_TO_HOME[@]}"; do
  echo "    - ${f}"
  sudo -u "${REAL_USER}" curl -fsSL -o "${HOME_DIR}/${f}" "${REPO_RAW_BASE}/${f}"
done
chown "${REAL_USER}:${REAL_USER}" "${HOME_DIR}/"*.py

echo "==> Optional: auto-activate venv for interactive shells (~/.bashrc)"
BASHRC="${HOME_DIR}/.bashrc"
ACTIVATE_LINE="source ${VENV_DIR}/bin/activate"
if ! grep -Fq "${ACTIVATE_LINE}" "${BASHRC}"; then
  {
    echo
    echo "# Auto-activate venv"
    echo "${ACTIVATE_LINE}"
  } >> "${BASHRC}"
  chown "${REAL_USER}:${REAL_USER}" "${BASHRC}"
  echo "    Added venv activation to ${BASHRC}"
else
  echo "    Already present in ${BASHRC}"
fi

echo "==> Fix UART device permissions (if ttyAMA0 is root-only)"
# If /dev/ttyAMA0 exists and is too strict, add a udev rule so users in dialout can access it
if [[ -e /dev/ttyAMA0 ]]; then
  PERM_LINE="$(stat -c '%a %U %G' /dev/ttyAMA0 2>/dev/null || true)"
  if [[ "${PERM_LINE}" == "600 root root" || "${PERM_LINE}" == "600 root root" ]]; then
    echo "    Detected /dev/ttyAMA0 is 0600 root:root -> adding udev rule"
    cat > /etc/udev/rules.d/99-ttyama0.rules <<'EOF'
KERNEL=="ttyAMA0", GROUP="dialout", MODE="0660"
EOF
    udevadm control --reload-rules
    udevadm trigger --name-match=ttyAMA0 || true
  else
    echo "    /dev/ttyAMA0 permissions look OK (${PERM_LINE})"
  fi
else
  echo "    /dev/ttyAMA0 not present (OK on some configs)"
fi

echo "==> Ensure user is in dialout (UART access)"
usermod -a -G dialout "${REAL_USER}"

echo "==> Creating systemd service for OLED: ${SERVICE_NAME}.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=OLED Status Display
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${REAL_USER}
WorkingDirectory=${HOME_DIR}
ExecStart=${VENV_DIR}/bin/python ${HOME_DIR}/oled.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "==> Creating command: kohveetia"
cat > "${KOHVEETIA_CMD}" <<EOF
#!/bin/bash
exec ${VENV_DIR}/bin/python ${HOME_DIR}/DynamountREv2.py
EOF
chmod +x "${KOHVEETIA_CMD}"

echo
echo "✅ DONE"
echo
echo "Installed files:"
for f in "${FILES_TO_HOME[@]}"; do
  echo "  ${HOME_DIR}/${f}"
done
echo
echo "OLED service:"
echo "  systemctl status ${SERVICE_NAME}"
echo "  journalctl -u ${SERVICE_NAME} -f"
echo
echo "Run Dynamount with:"
echo "  kohveetia"
echo
echo "⚠️ Reboot recommended (groups + serial/i2c):"
echo "  sudo reboot"
