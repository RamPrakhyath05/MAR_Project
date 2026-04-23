# Autonomous Drone Control System (Webots + ROS 2)

## 📌 Overview
This project implements a **fully controllable quadrotor drone simulation** using **Webots** and **ROS 2 (Humble)**.

It features:
- Real-time drone control using keyboard input
- PID-based flight stabilization
- Telemetry visualization (altitude, roll, pitch, yaw)
- Live camera feed from the drone
- Safe motor control (arming, disarming, landing)

---

## 🧠 System Architecture

```

Keyboard Controller  --->  /drone/cmd_vel  --->  Mavic Driver (PID Control)
|
↓
Drone (Webots Simulation)
|
/drone/telemetry + /drone/camera
↓
GUI Dashboard

```

---

## ⚙️ Technologies Used

- **ROS 2 Humble**
- **Webots Simulator**
- **Python (rclpy)**
- **Tkinter (GUI)**
- **OpenCV / PIL (camera rendering)**

---

## 📂 Project Structure

```

MAR_Project/
├── drone_controller/
│   ├── drone_controller/       # Core nodes
│   │   ├── drone_controller.py
│   │   ├── mavic_driver.py
│   │   └── drone_gui.py
│   ├── launch/
│   │   └── drone_launch.py
│   ├── worlds/
│   │   └── drone_world.wbt
│   ├── package.xml
│   └── setup.py
├── run.sh                      # One-command launcher
└── README.md

````

---

## 🚀 How to Run

### 1. Clone the repository
```bash
git clone https://github.com/RamPrakhyath05/MAR_Project
cd MAR_Project
````

---

### 2. Build the workspace

```bash
colcon build --symlink-install
source install/setup.bash
```

---

### 3. Run the system

```bash
chmod +x run.sh
./run.sh
```

---

## 🎮 Controls

| Key       | Action                       |
| --------- | ---------------------------- |
| **G**     | Arm / Disarm motors          |
| **T**     | Takeoff                      |
| **W / S** | Forward / Backward           |
| **A / D** | Left / Right                 |
| **Q / E** | Rotate (Yaw)                 |
| **↑ / ↓** | Increase / Decrease altitude |
| **SPACE** | Landing                      |

---

## 🛡️ Safety Features

* Motors can only be toggled when the drone is near ground
* Takeoff is restricted when already airborne
* Controlled descent during landing
* Automatic motor cutoff after landing

---

## 📊 GUI Features

* Live altitude, roll, pitch, yaw display
* Real-time drone camera feed
* System status monitoring

---

## 🔧 Key Components

### 1. `mavic_driver.py`

* Core flight controller
* Handles PID stabilization
* Converts velocity commands into motor speeds

### 2. `drone_controller.py`

* Keyboard input node
* Sends movement commands via ROS topics

### 3. `drone_gui.py`

* Displays telemetry data
* Renders live camera feed

---

## 📈 Learning Outcomes

* ROS 2 topic-based communication
* Drone control and stabilization concepts
* Simulation using Webots
* Real-time UI integration with robotics systems

---

## 🧪 Future Improvements

* Autonomous navigation
* Waypoint tracking
* Obstacle avoidance
* SLAM integration
* Advanced PID tuning

---

## 👨‍💻 Author

**Team No. 14**
- **Ram Prakhyath Annamareddy (PES2UG23CS465)**
- **Rahul Senthil Kumar(PES2UG23CS909)**
- **Renikuntla Ashish Pavan(PES2UG23CS472)**
- **Rentala Shiva Naga Aditya(PES2UG23CS473)**

---

## 📜 License

MIT License

```
