#!/bin/bash
# =========================================
# DRONE CONTROL SYSTEM LAUNCHER
# =========================================

cd ~/MAR_Project || exit

# ── SET WEBOTS_HOME ──────────────────────
# Find webots installation
if [ -d "/usr/local/webots" ]; then
    export WEBOTS_HOME=/usr/local/webots
elif [ -d "/snap/webots/current" ]; then
    export WEBOTS_HOME=/snap/webots/current
else
    # Find it automatically
    WEBOTS_BIN=$(which webots)
    export WEBOTS_HOME=$(dirname $(dirname $WEBOTS_BIN))
fi
echo "WEBOTS_HOME set to: $WEBOTS_HOME"

# ── BUILD ────────────────────────────────
echo "Building workspace..."
colcon build --symlink-install
if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi
source install/setup.bash

# ── CLEAN OLD PROCESSES ──────────────────
echo "Cleaning old processes..."
pkill -f mavic_driver 2>/dev/null
pkill -f drone_gui 2>/dev/null
pkill -f webots 2>/dev/null
sleep 2

# ── LAUNCH WEBOTS ────────────────────────
echo "Launching Webots..."
WORLD_FILE=~/MAR_Project/install/drone_controller/share/drone_controller/worlds/drone_world.wbt
webots --batch "$WORLD_FILE" &
WEBOTS_PID=$!

# ── WAIT FOR WEBOTS ──────────────────────
echo "Waiting for Webots..."
for i in {1..20}; do
    if pgrep -f webots > /dev/null; then
        echo "Webots detected."
        break
    fi
    sleep 1
done
sleep 3

# ── LAUNCH MAVIC DRIVER ──────────────────
echo "Launching mavic driver..."
WEBOTS_HOME=$WEBOTS_HOME ros2 run drone_controller mavic_driver &
DRIVER_PID=$!
sleep 2

# ── LAUNCH GUI (Proper ROS 2 Run) ──
echo "Launching GUI..."
# Force software rendering for Intel iGPU stability
export LIBGL_ALWAYS_SOFTWARE=1
ros2 run drone_controller drone_gui &
GUI_PID=$!
sleep 2

# ── RUN CONTROLLER IN FOREGROUND ─────────
echo "========================================="
echo "DRONE CONTROL SYSTEM ACTIVE"
echo "========================================="
echo "GUI window should be open"
echo "Use the GUI or keyboard in this terminal"
echo "Press Ctrl+C to shutdown everything"
echo "========================================="

ros2 run drone_controller drone_controller

# ── SHUTDOWN ─────────────────────────────
echo "Shutting down..."
kill $GUI_PID 2>/dev/null
kill $DRIVER_PID 2>/dev/null
kill $WEBOTS_PID 2>/dev/null
pkill -f mavic_driver 2>/dev/null
pkill -f webots 2>/dev/null
echo "Done."
