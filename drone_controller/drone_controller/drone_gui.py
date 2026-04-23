import tkinter as tk
import math
import threading
import rclpy
import numpy as np
import time

from std_msgs.msg import Bool, Float64MultiArray
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from PIL import Image as PILImage, ImageTk


class DroneGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Drone Telemetry Dashboard")
        self.root.geometry("420x650")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Telemetry
        self.altitude = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

        self.killed = False

        # Camera control
        self.gui_counter = 0

        # ROS
        rclpy.init()
        self.node = rclpy.create_node('drone_gui')

        self.node.create_subscription(
            Float64MultiArray, '/drone/telemetry', self.telem_callback, 10)

        self.node.create_subscription(
            Image, '/drone/camera', self.camera_callback, 10)

        self.kill_publisher = self.node.create_publisher(Bool, '/drone/kill', 10)
        self.cmd_pub = self.node.create_publisher(Twist, '/drone/cmd_vel', 10)
        self.motors_armed = False

        # ROS thread
        self._ros_running = True
        threading.Thread(target=self._ros_spin, daemon=True).start()

        # GUI
        self.build_gui()
        self.root.after(100, self.update_gui)
        self.root.mainloop()

    # ---------------- ROS ----------------
    def _ros_spin(self):
        while self._ros_running:
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def _on_close(self):
        self._ros_running = False
        try:
            self.node.destroy_node()
            rclpy.shutdown()
        except Exception:
            pass
        self.root.destroy()

    # ---------------- TELEMETRY ----------------
    def telem_callback(self, msg):
        if len(msg.data) >= 4:
            self.altitude = msg.data[0]
            self.roll = msg.data[1]
            self.pitch = msg.data[2]
            self.yaw = msg.data[3]

    # ---------------- CAMERA ----------------
    def camera_callback(self, msg):
        self.gui_counter += 1

        if self.gui_counter % 4 != 0:
            return

        try:
            img = np.frombuffer(msg.data, dtype=np.uint8)
            img = img.reshape((msg.height, msg.width, 4))

            img = img[:, :, :3]
            img = img[:, :, ::-1]

            pil_img = PILImage.fromarray(img)
            tk_img = ImageTk.PhotoImage(pil_img)

            self.root.after(0, self._update_camera, tk_img)

        except Exception:
            pass

    def _update_camera(self, tk_img):
        self.camera_label.configure(image=tk_img)
        self.camera_label.image = tk_img

    # ---------------- GUI ----------------
    def build_gui(self):
        tk.Label(self.root, text="DRONE TELEMETRY",
                 font=("Helvetica", 18, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(pady=10)

        self.status_label = tk.Label(self.root,
                                     text="SYSTEM ONLINE",
                                     font=("Helvetica", 11, "bold"),
                                     bg="#313244", fg="#a6e3a1",
                                     width=30, height=2)
        self.status_label.pack(pady=10)

        self.alt_label = tk.Label(self.root, text="ALT: 0.00 m",
                                 fg="white", bg="#1e1e2e")
        self.alt_label.pack()

        self.roll_label = tk.Label(self.root, text="ROLL: 0°",
                                  fg="white", bg="#1e1e2e")
        self.roll_label.pack()

        self.pitch_label = tk.Label(self.root, text="PITCH: 0°",
                                   fg="white", bg="#1e1e2e")
        self.pitch_label.pack()

        self.yaw_label = tk.Label(self.root, text="YAW: 0°",
                                 fg="white", bg="#1e1e2e")
        self.yaw_label.pack(pady=5)

        self.camera_label = tk.Label(self.root, bg="#1e1e2e")
        self.camera_label.pack(pady=10)

        tk.Button(self.root,
                  text="ARM / DISARM MOTORS",
                  command=self.toggle_motors,
                  bg="#89b4fa",
                  fg="black",
                  width=22,
                  height=2).pack(pady=5)

        tk.Button(self.root,
                  text="TAKEOFF",
                  command=self.takeoff,
                  bg="#a6e3a1",
                  fg="black",
                  width=22,
                  height=2).pack(pady=5)

        tk.Button(self.root,
                  text="LAND",
                  command=self.land,
                  bg="#f38ba8",
                  fg="black",
                  width=22,
                  height=2).pack(pady=10)

    # ---------------- LANDING ----------------
    def land(self):
        if self.killed:
            return

        self.killed = True
        self.status_label.config(text="LANDING...", fg="#f9e2af")

        threading.Thread(target=self._landing_sequence, daemon=True).start()

    def _landing_sequence(self):
        twist = Twist()

        for _ in range(8):
            self.cmd_pub.publish(Twist())
            self._sleep(0.08)

        twist.linear.z = -0.2
        start_time = time.time()

        while self.altitude > 0.3:
            if time.time() - start_time > 10:
                break

            self.cmd_pub.publish(twist)
            self._sleep(0.1)

        for _ in range(5):
            self.cmd_pub.publish(Twist())
            self._sleep(0.1)

        msg = Bool()
        msg.data = True
        self.kill_publisher.publish(msg)

        self.root.after(0, self._final_kill_ui)

    # ---------------- MOTORS ----------------
    def toggle_motors(self):
        if self.altitude > 0.07:
            self.status_label.config(
                text="Cannot toggle motors: Not on ground",
                fg="#f38ba8")
            return

        self.motors_armed = not self.motors_armed

        msg = Bool()
        msg.data = not self.motors_armed

        self.kill_publisher.publish(msg)

        state = "ARMED" if self.motors_armed else "DISARMED"
        self.status_label.config(text=f"Motors {state}", fg="#a6e3a1")

    # ---------------- TAKEOFF ----------------
    def takeoff(self):
        if not self.motors_armed:
            self.status_label.config(text="Motors not armed", fg="#f38ba8")
            return

        if self.altitude > 0.5:
            self.status_label.config(text="Already airborne", fg="#f38ba8")
            return

        if self.altitude > 0.07:
            self.status_label.config(text="Not stable on ground", fg="#f38ba8")
            return

        self.status_label.config(text="TAKING OFF...", fg="#a6e3a1")

        threading.Thread(target=self._takeoff_thread, daemon=True).start()

    def _takeoff_thread(self):
        twist = Twist()

        for _ in range(20):
            twist.linear.z = 0.6
            self.cmd_pub.publish(twist)
            time.sleep(0.1)

        self.root.after(0, lambda:
            self.status_label.config(text="AIRBORNE", fg="#a6e3a1"))

    # ---------------- UTILS ----------------
    def _sleep(self, duration):
        time.sleep(duration)

    def _final_kill_ui(self):
        self.status_label.config(text="LANDED", fg="#f38ba8")

    # ---------------- UPDATE LOOP ----------------
    def update_gui(self):
        self.alt_label.config(text=f"ALT: {self.altitude:.2f} m")
        self.roll_label.config(text=f"ROLL: {math.degrees(self.roll):.2f}°")
        self.pitch_label.config(text=f"PITCH: {math.degrees(self.pitch):.2f}°")
        self.yaw_label.config(text=f"YAW: {math.degrees(self.yaw):.2f}°")

        self.root.after(100, self.update_gui)


def main():
    DroneGUI()


if __name__ == '__main__':
    main()
