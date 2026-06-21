import os
import shlex

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


DEFAULT_BAG = os.path.join(
    os.path.expanduser('~'), 'colcon_ws', 'src', 'summerschool_data', 'arche_loop_0.mcap')


def rviz_environment():
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime_dir:
        runtime_dir = f'/tmp/runtime-{os.getuid()}'
        os.makedirs(runtime_dir, mode=0o700, exist_ok=True)
        os.chmod(runtime_dir, 0o700)

    return {
        'XDG_RUNTIME_DIR': runtime_dir,
        'DBUS_FATAL_WARNINGS': '0',
        'NO_AT_BRIDGE': '1',
        'QT_ACCESSIBILITY': '0',
        'QT_QPA_PLATFORM': 'xcb',
        'QT_X11_NO_MITSHM': '1',
    }


def launch_setup(context):
    current_pkg = FindPackageShare('direct_lidar_inertial_odometry')

    pointcloud_topic = LaunchConfiguration('pointcloud_topic')
    imu_topic = LaunchConfiguration('imu_topic')
    rviz = LaunchConfiguration('rviz')
    bag = os.path.abspath(os.path.expanduser(LaunchConfiguration('bag').perform(context)))
    play_rate = LaunchConfiguration('play_rate').perform(context)
    read_ahead_queue_size = LaunchConfiguration('read_ahead_queue_size').perform(context)

    dlio_yaml_path = PathJoinSubstitution([current_pkg, 'cfg', 'dlio.yaml'])
    dlio_params_yaml_path = PathJoinSubstitution([current_pkg, 'cfg', 'params.yaml'])
    rviz_config_path = PathJoinSubstitution([current_pkg, 'launch', 'a2_front.rviz'])

    common_output_remappings = [
        ('map_pose', 'dlio/odom_node/map_pose'),
        ('map_pose_inverted', 'dlio/odom_node/map_pose_inverted'),
        ('odom', 'dlio/odom_node/odom'),
        ('pose', 'dlio/odom_node/pose'),
        ('path_map', 'dlio/odom_node/path_map'),
        ('path_odom', 'dlio/odom_node/path_odom'),
        ('path_map_prop', 'dlio/odom_node/path_map_prop'),
        ('kf_pose', 'dlio/odom_node/keyframes'),
        ('kf_cloud', 'dlio/odom_node/pointcloud/keyframe'),
        ('convex_registration_keyframes', 'dlio/odom_node/pointcloud/convex_registration_keyframes'),
        ('deskewed', 'dlio/odom_node/pointcloud/deskewed'),
        ('deskewed_not_transformed', 'dlio/odom_node/pointcloud/deskewed_not_transformed'),
        ('deskewed_and_transformed_to_map', '/registered_scan'),
        ('dynamic_removed', 'dlio/odom_node/pointcloud/dynamic_removed'),
        ('markers/velocity_linear', 'dlio/odom_node/markers/velocity_linear'),
        ('markers/velocity_angular', 'dlio/odom_node/markers/velocity_angular'),
        ('markers/correction', 'dlio/odom_node/markers/correction'),
        ('markers/degeneracy_directions', 'dlio/odom_node/markers/degeneracy_directions'),
        ('markers/convex_registration_voxels', 'dlio/odom_node/markers/convex_registration_voxels'),
    ]

    odom_node = Node(
        package='direct_lidar_inertial_odometry',
        executable='dlio_odom_node',
        output='screen',
        parameters=[
            dlio_yaml_path,
            dlio_params_yaml_path,
        ],
        remappings=[
            ('pointcloud', pointcloud_topic),
            ('imu', imu_topic),
            *common_output_remappings,
        ],
        respawn=False,
    )

    map_node = Node(
        package='direct_lidar_inertial_odometry',
        executable='dlio_map_node',
        output='screen',
        parameters=[
            dlio_yaml_path,
            dlio_params_yaml_path,
        ],
        remappings=[
            ('kf_cloud', 'dlio/odom_node/pointcloud/keyframe'),
            ('map', 'dlio/map_node/map'),
            ('map_pose', 'dlio/odom_node/map_pose'),
            ('dynamic_removed', 'dlio/odom_node/pointcloud/dynamic_removed'),
        ],
        respawn=False,
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='dlio_a2_front_rviz',
        arguments=['-d', rviz_config_path],
        output='screen',
        condition=IfCondition(rviz),
        parameters=[{'use_sim_time': True}],
        additional_env=rviz_environment(),
    )

    bag_play_cmd = (
        'echo "Playing bag. Focus this xterm and press SPACE to pause/resume."; '
        f'ros2 bag play {shlex.quote(bag)} '
        f'-r {shlex.quote(play_rate)} '
        '--clock '
        f'--read-ahead-queue-size {shlex.quote(read_ahead_queue_size)} '
        '--remap /tf:=/tf_bag; '
        'echo; echo "ros2 bag play exited. Press ENTER to close this xterm."; '
        'read'
    )

    bag_player_xterm = ExecuteProcess(
        cmd=[
            'xterm',
            '-T',
            'A2 front replay bag player',
            '-e',
            'bash',
            '-lc',
            bag_play_cmd,
        ],
        name='a2_replay_bag_xterm',
        output='screen',
    )

    return [
        odom_node,
        map_node,
        rviz_node,
        bag_player_xterm,
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'bag',
            default_value=DEFAULT_BAG,
            description='A2 bag or MCAP path to play in xterm.'),
        DeclareLaunchArgument(
            'play_rate',
            default_value='1.0',
            description='ros2 bag play rate.'),
        DeclareLaunchArgument(
            'read_ahead_queue_size',
            default_value='2000',
            description='ros2 bag play read-ahead queue size.'),
        DeclareLaunchArgument(
            'pointcloud_topic',
            default_value='/front_lidar/points',
            description='A2 front LiDAR PointCloud2 topic.'),
        DeclareLaunchArgument(
            'imu_topic',
            default_value='/front_lidar/imu',
            description='A2 front LiDAR IMU topic.'),
        DeclareLaunchArgument(
            'rviz',
            default_value='true',
            description='Launch RViz2 with the A2 front-lidar DLIO display config.'),
        OpaqueFunction(function=launch_setup),
    ])
