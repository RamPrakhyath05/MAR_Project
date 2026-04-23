from setuptools import setup
import os
from glob import glob

package_name = 'drone_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'worlds'),
            glob('worlds/*.wbt')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ramprakhyath',
    maintainer_email='ramprakhyath@todo.todo',
    description='Drone keyboard controller using ROS2 and Webots',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'drone_controller = drone_controller.drone_controller:main',
            'mavic_driver = drone_controller.mavic_driver:main',
            'drone_gui = drone_controller.drone_gui:main',
        ],
    },
)
