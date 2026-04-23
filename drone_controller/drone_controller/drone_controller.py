import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Float64MultiArray

import sys
import tty
import termios
import threading
import time


class DroneController(Node):
    def __init__(self):
        super().__init__('drone_controller')

        self.cmd_pub = self.create_publisher(Twist, '/drone/cmd_vel', 10)
        self.kill_pub = self.create_publisher(Bool, '/drone/kill', 10)

        self.create_subscription(
            Float64MultiArray,
            '/drone/telemetry',
            self.telemetry_callback,
            10
        )

        self.altitude = 0.0
        self.motors_armed = False
        self.landing_active = False

        # ---------------- PRINT ALL CONTROLS ----------------
        print("\n" + "="*40)
        print("       DRONE MASTER CONTROLLER")
        print("="*40)
        print(" G         : ARM/DISARM MOTORS")
        print(" T         : TAKEOFF")
        print(" SPACE     : LAND (SLOW DESCEND)")
        print("-" * 40)
        print(" W / S     : FORWARD / BACKWARD")
        print(" A / D     : STRAFE LEFT / RIGHT")
        print(" Q / E     : ROTATE LEFT / RIGHT")
        print(" UP / DOWN : INCREASE / DECREASE ALTITUDE")
        print("-" * 40)
        print(" CTRL + C  : SHUTDOWN SYSTEM")
        print("="*40 + "\n")

        self.get_logger().info('Controller Initialized and Waiting...')

        threading.Thread(target=self.keyboard_loop, daemon=True).start()

    # ---------------- TELEMETRY ----------------
    def telemetry_callback(self, msg):
        if len(msg.data) >= 1:
            self.altitude = msg.data[0]

    # ---------------- KEY INPUT ----------------
    def get_key(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
            if key == '\x1b':
                key += sys.stdin.read(2)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return key

    def keyboard_loop(self):
        while rclpy.ok():
            key = self.get_key()
            self.get_logger().info(f'KEY PRESSED: {repr(key)}')
            self.handle_key(key)

    # ---------------- KEY HANDLER ----------------
    def handle_key(self, key):
        twist = Twist()

        # -------- ARM / DISARM (STAY ON GROUND) --------
        if key == 'g':
            if self.altitude <= 0.35:
                self.motors_armed = not self.motors_armed

                # Reset target altitude to 0.0 before arming so it doesn't fly up
                reset_twist = Twist()
                reset_twist.linear.z = -5.0 # Force target to floor
                self.cmd_pub.publish(reset_twist)
                time.sleep(0.1)

                msg = Bool()
                msg.data = not self.motors_armed # True = Kill, False = Start
                self.kill_pub.publish(msg)

                if self.motors_armed:
                    self.get_logger().info('Motors ARMED - Waiting on ground.')
                else:
                    self.get_logger().info('Motors DISARMED.')
            else:
                self.get_logger().warn('CANNOT TOGGLE: Drone is airborne!')
            return

        # -------- TAKEOFF --------
        if key == 't':
            if not self.motors_armed:
                self.get_logger().warn('Motors not armed! Press G first.')
                return

            if self.altitude > 0.5:
                self.get_logger().warn('Already airborne.')
                return

            self.get_logger().info('Takeoff started...')
            # Threaded to prevent blocking movement
            threading.Thread(target=self.execute_takeoff).start()
            return

        # -------- LAND --------
        if key == ' ':
            if self.altitude < 0.1:
                self.get_logger().info('Already on ground.')
                return
            self.get_logger().warn('Initiating Landing Sequence...')
            threading.Thread(target=self.land).start()
            return

        # -------- MOVEMENT (YOUR CUSTOM SIGNS) --------
        if not self.motors_armed or self.landing_active:
            return

        if key == 'w':
            twist.linear.x = -1.0
        elif key == 's':
            twist.linear.x = 1.0
        elif key == 'a':
            twist.linear.y = -1.0
        elif key == 'd':
            twist.linear.y = 1.0
        elif key == '\x1b[A': # Up Arrow
            twist.linear.z = 1.0
        elif key == '\x1b[B': # Down Arrow
            twist.linear.z = -1.0
        elif key == 'q':
            twist.angular.z = -1.0
        elif key == 'e':
            twist.angular.z = 1.0
        elif key == '\x03': # Ctrl+C
            raise SystemExit

        self.cmd_pub.publish(twist)

    def execute_takeoff(self):
        twist = Twist()
        for _ in range(20):
            twist.linear.z = 0.6
            self.cmd_pub.publish(twist)
            time.sleep(0.1)
        self.get_logger().info('Takeoff Complete. Hovering.')

    # ---------------- LANDING ----------------
    def land(self):
        self.landing_active = True
        
        # stabilize
        self.cmd_pub.publish(Twist())
        time.sleep(0.5)

        # descend slowly
        descend = Twist()
        descend.linear.z = -0.2
        start = time.time()

        while self.altitude > 0.15:
            if time.time() - start > 12: # Safety timeout
                break
            self.cmd_pub.publish(descend)
            time.sleep(0.1)

        # kill motors once very low
        msg = Bool()
        msg.data = True
        self.kill_pub.publish(msg)

        self.motors_armed = False
        self.landing_active = False
        self.get_logger().info('Landed and motors stopped.')


def main(args=None):
    rclpy.init(args=args)
    node = DroneController()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()