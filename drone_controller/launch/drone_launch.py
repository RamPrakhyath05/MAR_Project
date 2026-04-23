import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    package_dir = get_package_share_directory('drone_controller')
    world_file = os.path.join(package_dir, 'worlds', 'drone_world.wbt')

    webots = ExecuteProcess(
        cmd=['webots', '--batch', world_file],
        output='screen'
    )

    mavic_driver = Node(
        package='drone_controller',
        executable='mavic_driver',
        name='mavic_driver',
        output='screen'
    )

    drone_controller = ExecuteProcess(
        cmd=['gnome-terminal', '--', 'bash', '-c',
             'source /opt/ros/humble/setup.bash && '
             'source ~/MAR_Project/install/setup.bash && '
             'ros2 run drone_controller drone_controller; exec bash'],
        output='screen'
    )

    drone_gui = ExecuteProcess(
        cmd=['gnome-terminal', '--', 'bash', '-c',
             'source /opt/ros/humble/setup.bash && '
             'source ~/MAR_Project/install/setup.bash && '
             'ros2 run drone_controller drone_gui; exec bash'],
        output='screen'
    )

    return LaunchDescription([
        webots,
        mavic_driver,
        drone_controller,
        drone_gui,
    ])