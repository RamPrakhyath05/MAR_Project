import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from controller import Robot
from std_msgs.msg import Bool, Float64MultiArray
from sensor_msgs.msg import Image
import math


class MavicDriver(Node):
    def __init__(self, robot):
        super().__init__('mavic_driver')
        self.robot = robot
        self.timestep = int(robot.getBasicTimeStep())

        # Motors
        self.front_left  = robot.getDevice('front left propeller')
        self.front_right = robot.getDevice('front right propeller')
        self.rear_left   = robot.getDevice('rear left propeller')
        self.rear_right  = robot.getDevice('rear right propeller')

        self.motors = [self.front_left, self.front_right, self.rear_left, self.rear_right]

        for m in self.motors:
            m.setPosition(float('inf'))
            m.setVelocity(0.0)

        # Sensors
        self.imu  = self.get_device('inertial unit')
        self.gps  = self.get_device('gps')
        self.gyro = self.get_device('gyro')

        for s in [self.imu, self.gps, self.gyro]:
            if s:
                s.enable(self.timestep)

        # Camera
        self.camera = self.robot.getDevice('camera')
        if self.camera:
            self.camera.enable(self.timestep * 5)
        self.camera_counter = 0
        self.camera_skip = 2

        self.image_pub = self.create_publisher(Image, '/drone/camera', 10)

        # Constants (tuned stable)
        self.K_VERTICAL_THRUST = 68.5
        self.K_VERTICAL_OFFSET = 0.6
        self.K_VERTICAL_P      = 4.5
        self.K_ROLL_P          = 50.0
        self.K_PITCH_P         = 30.0

        # State
        self.target_altitude = 0.0 # Start at 0.0 to stay on ground
        self.target_yaw = 0.0
        self.initialized = False
        self.killed = True  # Start killed/disarmed for safety

        # Disturbances (inputs)
        self.roll_disturbance  = 0.0
        self.pitch_disturbance = 0.0
        self.yaw_disturbance   = 0.0

        # ROS
        self.create_subscription(Twist, '/drone/cmd_vel', self.cmd_callback, 10)
        self.create_subscription(Bool, '/drone/kill', self.kill_callback, 10)

        self.telem_pub = self.create_publisher(
            Float64MultiArray, '/drone/telemetry', 10)

        self.get_logger().info('🚁 Mavic Driver Ready')

    # -------- SAFE DEVICE --------
    def get_device(self, name):
        dev = self.robot.getDevice(name)
        if dev is None:
            self.get_logger().error(f"Device '{name}' NOT FOUND")
            raise RuntimeError(f"Missing device: {name}")
        return dev

    def limit(self, v):
        return max(0.0, min(600.0, v))

    def clamp(self, v, lo, hi):
        return max(lo, min(hi, v))

    # -------- INPUT --------
    def cmd_callback(self, msg):
        if self.killed:
            return

        self.pitch_disturbance = -msg.linear.x * 2.0
        self.roll_disturbance  =  msg.linear.y * 1.5
        self.yaw_disturbance   = -msg.angular.z * 1.5

        # Only allow altitude change if motors are active
        self.target_altitude += msg.linear.z * 0.05
        self.target_altitude = self.clamp(self.target_altitude, 0.0, 5.0)

    def kill_callback(self, msg):
        self.killed = msg.data
        if self.killed:
            self.get_logger().warn("🛑 MOTORS DISARMED")
            self.target_altitude = 0.0 # Force target to ground on kill
        else:
            self.get_logger().info("✅ MOTORS ARMED")
            # When arming, ensure target_altitude starts at current ground level
            self.target_altitude = 0.0

    # -------- MAIN LOOP --------
    def run(self):
        # stabilization delay
        while self.robot.step(self.timestep) != -1:
            if self.robot.getTime() > 1.0:
                break

        self.get_logger().info("Drone ready for arming (G)")

        while self.robot.step(self.timestep) != -1:
            rclpy.spin_once(self, timeout_sec=0)

            if self.killed:
                for m in self.motors:
                    m.setVelocity(0.0)
                continue

            roll, pitch, yaw = self.imu.getRollPitchYaw()
            altitude = self.gps.getValues()[2]
            gx, gy, gz = self.gyro.getValues()

            # Initialize yaw reference once
            if not self.initialized:
                self.target_yaw = yaw
                self.initialized = True

            # -------- TELEMETRY --------
            msg = Float64MultiArray()
            msg.data = [float(altitude), float(roll), float(pitch), float(yaw)]
            self.telem_pub.publish(msg)

            # -------- CAMERA -----------
            if self.camera:
                self.camera_counter += 1
                if self.camera_counter >= self.camera_skip:
                    self.camera_counter = 0
                    img = self.camera.getImage()
                    width = self.camera.getWidth()
                    height = self.camera.getHeight()
                    c_msg = Image()
                    c_msg.height = height
                    c_msg.width = width
                    c_msg.encoding = 'bgra8'
                    c_msg.data = img
                    c_msg.step = width * 4
                    self.image_pub.publish(c_msg)

            # -------- CONTROL --------

            # Attitude
            roll_input  = self.K_ROLL_P  * self.clamp(roll,  -1, 1) + gx + self.roll_disturbance
            pitch_input = self.K_PITCH_P * self.clamp(pitch, -1, 1) + gy + self.pitch_disturbance

            # Yaw (proper stabilization)
            yaw_error = self.target_yaw - yaw
            yaw_error = math.atan2(math.sin(yaw_error), math.cos(yaw_error))
            yaw_input = yaw_error * 2.0 + gz * 0.5 + self.yaw_disturbance

            # Altitude Logic: Stay on ground if target is 0
            # Remove the hover offset if we haven't taken off yet
            current_offset = self.K_VERTICAL_OFFSET if self.target_altitude > 0.1 else 0.0
            
            diff = self.clamp(self.target_altitude - altitude + current_offset, -1, 1)
            vertical_input = self.K_VERTICAL_P * (diff ** 3)

            # -------- MOTOR MIX --------
            fl = self.K_VERTICAL_THRUST + vertical_input - roll_input + pitch_input - yaw_input
            fr = self.K_VERTICAL_THRUST + vertical_input + roll_input + pitch_input + yaw_input
            rl = self.K_VERTICAL_THRUST + vertical_input - roll_input - pitch_input + yaw_input
            rr = self.K_VERTICAL_THRUST + vertical_input + roll_input - pitch_input - yaw_input

            # -------- APPLY --------
            self.front_left.setVelocity(self.limit(fl))
            self.front_right.setVelocity(-self.limit(fr))
            self.rear_left.setVelocity(-self.limit(rl))
            self.rear_right.setVelocity(self.limit(rr))


def main():
    rclpy.init()
    robot = Robot()
    driver = MavicDriver(robot)
    driver.run()
    rclpy.shutdown()


if __name__ == '__main__':
    main()