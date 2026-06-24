# Direct LiDAR-Inertial Odometry: Lightweight LIO with Continuous-Time Motion Correction

#### [[ IEEE ICRA ](https://ieeexplore.ieee.org/document/10160508)] [[ arXiv ](https://arxiv.org/abs/2203.03749)] [[ Video ](https://www.youtube.com/watch?v=4-oXjG8ow10)] [[ Presentation ](https://www.youtube.com/watch?v=Hmiw66KZ1tU)]

DLIO is a new lightweight LiDAR-inertial odometry algorithm with a novel coarse-to-fine approach in constructing continuous-time trajectories for precise motion correction. It features several algorithmic improvements over its predecessor, [DLO](https://github.com/vectr-ucla/direct_lidar_odometry), and was presented at the IEEE International Conference on Robotics and Automation (ICRA) in London, UK in 2023.

<br>
<p align='center'>
    <img src="./doc/img/dlio.png" alt="drawing" width="720"/>
</p>

## Current Repository Features

This branch is a ROS 2 DLIO pipeline with several additions on top of the original odometry core:

- ROS 2 launch files for generic DLIO and A2 front-lidar live/replay setups.
- A simple `a2_front_replay.launch.py` that starts DLIO and opens an xterm bag player.
- Online LiDAR-only dynamic object filtering with a clean-room M-detector-style backend.
- Dynamic-removed point accumulation in the map node for saving `dynamic_points.pcd`.
- Automatic run-state CSV export and plot generation for pose, twist, and estimated IMU biases.
- Early IMU unit detection and auto-scaling before DLIO calibration. This handles IMUs that publish acceleration in `g` and angular velocity in `deg/s` instead of ROS-standard `m/s^2` and `rad/s`.
- RViz launch environment fixes for common container/X11 DBus and Qt issues.

## Getting Started (Step By Step)

New to ROS 2 or this repo? Start here. The lab runs everything inside a ROS 2
Jazzy environment; in our case that is the perception Docker container. In the
commands below, `<workspace>` is the colcon workspace root that contains this
package in its `src/` directory. In the lab container, that is usually
`/home/ttuna/colcon_ws`.

### 1. Open the environment

This package is developed and run inside the lab's perception container. Open a
shell in it:

```bash
docker exec -it ros2jazzy-perception bash
```

(If you run ROS 2 Jazzy natively instead, skip this step — everything below is
the same.)

### 2. Source ROS 2 and the workspace

"Sourcing" a `setup.bash` just adds packages to your shell's search path so that
`ros2 ...` can find them. You always source **two** files, in this order:

```bash
# (a) the ROS 2 system install — gives you ros2, rviz2, ros2 bag, etc.
source /opt/ros/jazzy/setup.bash

# (b) this workspace's build output — gives you DLIO and its launch files
source <workspace>/install/setup.bash
```

You must re-source in **every new terminal**. Tip: put both lines in your
`~/.bashrc` so they run automatically.

### 3. Build (first time only, or after editing C++)

```bash
cd <workspace>
source /opt/ros/jazzy/setup.bash
colcon build --packages-select direct_lidar_inertial_odometry --symlink-install
source install/setup.bash
```

`--symlink-install` links the config and launch files into the install space, so
**edits to YAML / launch files take effect with no rebuild** — you only rebuild
after changing C++ code under `src/`.

> Build it as a plain Release (the default). Do **not** add sanitizer flags such
> as `-fsanitize=undefined`: they make the node run several times slower and can
> abort it mid-run.

### 4. Run it — A2 replay

Start DLIO, RViz, and an xterm bag player:

```bash
source /opt/ros/jazzy/setup.bash
source <workspace>/install/setup.bash
ros2 launch direct_lidar_inertial_odometry a2_front_replay.launch.py \
  bag:=/home/ttuna/colcon_ws/src/summerschool_data/arche_loop_0.mcap
```

For bag paths that contain spaces, quote the whole `bag:=...` value:

```bash
ros2 launch direct_lidar_inertial_odometry a2_front_replay.launch.py \
  bag:="/media/ttuna/RSS2026/A2 bags/challenge_1_0.mcap"
```

Focus the xterm and press SPACE to pause/resume playback.

Details: [Replay An MCAP End-To-End](#replay-an-mcap-end-to-end).

### 5. Save your map

Call the map service while DLIO is still running:

```bash
ros2 service call /save_pcd direct_lidar_inertial_odometry/srv/SavePCD "{}"
```

Open `/tmp/dlio_maps/clean_map.pcd` or `/tmp/dlio_maps/dlio_map.pcd` in
CloudCompare or `pcl_viewer`.

The rest of this README is the detailed reference: manual two-terminal runs,
saving maps on demand, tuning the dynamic filter, etc.

## Sensor Inputs

DLIO expects:

- LiDAR: `sensor_msgs/msg/PointCloud2`
- IMU: `sensor_msgs/msg/Imu`

The generic launch remaps these internal topic names:

- `pointcloud`
- `imu`

The A2 front-lidar launch uses:

- `/front_lidar/points`
- `/front_lidar/imu`

For best accuracy, set the LiDAR and IMU extrinsics in [cfg/dlio.yaml](./cfg/dlio.yaml). The LiDAR and IMU must be time-synchronized. If the bag or driver publishes IMU acceleration in `g`, the new unit checker can correct it before calibration, but it cannot fix bad time synchronization.

## Configuration Reference

All provided DLIO launches load [cfg/dlio.yaml](./cfg/dlio.yaml) and
[cfg/params.yaml](./cfg/params.yaml). Launch arguments and inline launch
parameters can override values from those files. With `--symlink-install`,
YAML and launch-file edits do not require a rebuild; C++ edits still do.

### Launch Arguments

| Launch file | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `dlio.launch.py` | `rviz` | `true` | Starts RViz with `launch/dlio.rviz`. |
| `dlio.launch.py` | `use_sim_time` | `false` | Set `true` when playing a bag with `--clock`. |
| `dlio.launch.py` | `pointcloud_topic` | `/lidar_points` | Input `sensor_msgs/msg/PointCloud2` topic. |
| `dlio.launch.py` | `imu_topic` | `/lidar_imu` | Input `sensor_msgs/msg/Imu` topic. |
| `a2_front_replay.launch.py` | `bag` | `/media/ttuna/RSS2026/A2 bags/challenge_1_0.mcap` | Bag or MCAP opened in the xterm player. |
| `a2_front_replay.launch.py` | `play_rate` | `1.0` | Playback speed passed to `ros2 bag play -r`. |
| `a2_front_replay.launch.py` | `read_ahead_queue_size` | `2000` | Bag-player read-ahead queue. Increase for bursty storage. |
| `a2_front_replay.launch.py` | `pointcloud_topic` | `/front_lidar/points` | A2 front LiDAR point cloud input. |
| `a2_front_replay.launch.py` | `imu_topic` | `/front_lidar/imu` | A2 front LiDAR IMU input. |
| `a2_front_replay.launch.py` | `rviz` | `true` | Starts RViz with `launch/a2_front.rviz`. |
| `a2_front_live.launch.py` | `pointcloud_topic` | `/front_lidar/points` | Live A2 front LiDAR point cloud input. |
| `a2_front_live.launch.py` | `imu_topic` | `/front_lidar/imu` | Live A2 front LiDAR IMU input. |
| `a2_front_live.launch.py` | `state_estimation_topic` | `/state_estimation` | Live odometry output topic for the robot stack. |
| `a2_front_live.launch.py` | `registered_scan_topic` | `/registered_scan` | Registered scan output for the robot stack and RViz. |
| `a2_front_live.launch.py` | `use_sim_time` | `false` | Keep `false` for live sensors; set `true` only for bag replay. |
| `a2_front_live.launch.py` | `dynamic_filter_enabled` | `true` | Enables the online LiDAR dynamic-object filter. |
| `a2_front_live.launch.py` | `dynamic_filter_max_range` | `10.0` | Dynamic detection/removal range in meters. |
| `a2_front_live.launch.py` | `num_threads` | `4` | OpenMP worker count for GICP and deskewing. |
| `a2_front_live.launch.py` | `pointcloud_queue_size` | `50` | LiDAR input queue depth for transient processing spikes. |
| `a2_front_live.launch.py` | `map_crop_enabled` | `true` | Crops the accumulated map around the robot for live memory control. |
| `a2_front_live.launch.py` | `rviz` | `false` | Starts RViz with `launch/a2_front.rviz` when set `true`. |

### Core Parameters

| Parameter | Default in this repo | Meaning |
| --- | --- | --- |
| `version` | `1.1.1` | DLIO config/version label printed by the odom node. |
| `adaptive` | `true` | Enables adaptive keyframe/correspondence tuning from scene spaciousness and density. |
| `adaptive/spaciousness/min`, `adaptive/spaciousness/max` | `0.25`, `4.0` | Bounds for adaptive keyframe spacing. |
| `adaptive/density/factor_min`, `adaptive/density/factor_max` | `0.5`, `2.0` | Bounds for adaptive GICP correspondence distance scaling. |
| `use_sim_time` | `true` in `params.yaml`; generic/live launches override from `use_sim_time` | Use ROS time from `/clock`. Required for bag replay with `--clock`; normally `false` for live sensors. |
| `frames/odom` | `dlio_odom` | Local odometry frame used by DLIO. |
| `frames/baselink` | `base_link` | Robot body frame. |
| `frames/lidar` | `front_lidar_link` | LiDAR frame name used for transforms. |
| `frames/imu` | `imu_link` | IMU frame name used for transforms. |
| `extrinsics/baselink2imu/t`, `extrinsics/baselink2imu/R` | set in `dlio.yaml` | Translation and row-major rotation from `base_link` to IMU. Update for each sensor rig. |
| `extrinsics/baselink2lidar/t`, `extrinsics/baselink2lidar/R` | set in `dlio.yaml` | Translation and row-major rotation from `base_link` to LiDAR. Update for each sensor rig. |
| `pointcloud/deskew` | `true` | Uses IMU motion to deskew each LiDAR scan when per-point timing is available. |
| `pointcloud/voxelize` | `true` | Applies voxel filtering before registration and map-keyframe creation. |
| `pointcloud/queueSize` | code fallback `5`; live launch overrides to `50` | LiDAR subscription queue depth. Increase only if callbacks lag behind incoming scans. |
| `odom/num_threads` | `8`; live launch overrides to `4` | OpenMP worker count for GICP and deskewing. Use conservative values on the robot. |
| `odom/preprocessing/cropBoxFilter/size` | `0.5` m | Self-filter half-size. Points inside the cube around the sensor are removed. |
| `odom/preprocessing/voxelFilter/res` | `0.15` m | Scan/keyframe voxel size used before registration and mapping. Smaller keeps detail and costs more CPU. |
| `odom/keyframe/threshD` | `10.0` m | Translation threshold for adding a new keyframe. Lower creates denser maps/submaps. |
| `odom/keyframe/threshR` | `5.0` deg | Rotation threshold for adding a new keyframe. |
| `odom/submap/keyframe/knn` | `10` | Nearest keyframes included in the registration submap. |
| `odom/submap/keyframe/kcv` | `10` | Convex-hull keyframes included in the registration submap. |
| `odom/submap/keyframe/kcc` | `10` | Concave-hull keyframes included in the registration submap. |
| `odom/gicp/minNumPoints` | `32` | Minimum points needed before registration/keyframe logic proceeds. |
| `odom/gicp/kCorrespondences` | `7` | Neighbor count used for GICP covariance/correspondence estimation. |
| `odom/gicp/maxCorrespondenceDistance` | `0.5` m | Maximum correspondence distance. Larger can help sparse scans but risks bad matches. |
| `odom/gicp/maxIterations` | `64` | Maximum GICP optimizer iterations. |
| `odom/gicp/transformationEpsilon` | `0.005` | GICP translation convergence tolerance. |
| `odom/gicp/rotationEpsilon` | `0.001` | GICP rotation convergence tolerance. |
| `odom/gicp/initLambdaFactor` | `1e-6` | Initial damping factor for NanoGICP. Usually leave unchanged. |
| `odom/gicp/degeneracy/enabled` | `false` | Enables translation-degeneracy checks from scan normal spread. |
| `odom/gicp/degeneracy/trans_eig_abs_threshold` | `50.0` | Eigenvalue threshold for weak translation directions. |
| `odom/gicp/degeneracy/reset_consecutive_count` | `10` | Consecutive degenerate scans before triggering reset behavior. |
| `odom/restart/geometry_gate/enabled` | `false` | Gates post-reset reinitialization on local geometry richness. |
| `odom/restart/geometry_gate/min_eigenvalue` | `100.0` | Minimum geometry eigenvalue accepted by the restart gate. |
| `odom/geo/Kp`, `odom/geo/Kv`, `odom/geo/Kq` | `5.10`, `4.52`, `4.0` | Geometric observer position, velocity, and attitude gains. Tune carefully. |
| `odom/geo/Kab`, `odom/geo/Kgb` | `2.25`, `1.0` | Accelerometer and gyro bias adaptation gains. |
| `odom/geo/abias_max`, `odom/geo/gbias_max` | `5.0`, `0.5` | Bias anti-windup clamps in `m/s^2` and `rad/s`. |

### Mapping And Saving Parameters

| Parameter or request field | Default | Meaning |
| --- | --- | --- |
| `map/sparse/leafSize` | `0.10` m | Voxel size used by the map node when accumulating keyframes. Also the default `SavePCD` leaf size. |
| `map/dense/filtered` | `false` | When `true`, publishes the voxel-filtered scan as the dense map view; when `false`, publishes the deskewed scan. |
| `map/waitUntilMove` | `false` | If `true`, suppresses cloud publishing until the platform has moved about `0.1` m. |
| `map/crop/enabled` | `false`; live launch default is `true` | Crops the stored map around the robot. Good for live memory control; disable for full-mission saved maps. |
| `map/crop/box_size` | `20.0` m | Edge length of the crop cube centered on the robot. |
| `map/crop/padding` | `2.0` m | Extra crop margin to reduce churn between periodic crops. |
| `map/crop/period_sec` | `2.0` s | Periodic crop interval. If enabled with a non-positive period, cropping is done on publish. |
| `map/save_dynamic_removed/enabled` | `false` | Lets the map node subscribe to removed dynamic points and save dynamic-point PCDs. |
| `SavePCD.leaf_size` | `<= 0` means `map/sparse/leafSize` | Per-call save voxel size. Use a positive value to override. |
| `SavePCD.save_path` | empty means `/tmp/dlio_maps` | Output directory for `dlio_map.pcd`, `clean_map.pcd`, and `save_summary.txt`. |

### Dynamic Filter Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `dynamic_filter/enabled` | `true` | Enables the online M-detector-style LiDAR dynamic-object filter. |
| `dynamic_filter/force_removed_cloud_output` | `false` | Forces removed-point cloud generation even before subscriber discovery. Useful for deterministic `dynamic_points.pcd`. |
| `dynamic_filter/voxel_size` | `0.20` m | Voxel memory resolution for dynamic/static evidence. Smaller keeps sharper detail and uses more memory. |
| `dynamic_filter/min_range` | `1.0` m | Minimum range for dynamic detection/removal. Closer finite points pass to the clean map unchanged. |
| `dynamic_filter/max_range` | `8.0` m; live launch overrides to `10.0` | Maximum range for dynamic detection/removal. Farther finite points pass to the clean map unchanged. |
| `dynamic_filter/warmup_scans` | `8` | Number of scans to collect before making confident dynamic decisions. |
| `dynamic_filter/static_score_threshold` | `2` | Static voxel support needed to veto removal near stable structure. |
| `dynamic_filter/static_window_scans` | `5` | Time window, in scans, for static support accumulation. |
| `dynamic_filter/max_age_scans` | `300` | Maximum age of voxel-memory evidence before pruning. |
| `dynamic_filter/local_radius` | `30.0` m | Radius around the robot kept in voxel memory. Keep this at least as large as `max_range`. |
| `dynamic_filter/m_detector/projection/rows` | `128` | Range-image rows. The A2/JT-128 setup uses LiDAR ring as row. |
| `dynamic_filter/m_detector/projection/cols` | `900` | Range-image azimuth columns. |
| `dynamic_filter/m_detector/projection/use_ring_field` | `true` | Uses the point `ring` field for projection when available. |
| `dynamic_filter/m_detector/projection/use_point_timestamp` | `true` | Uses per-point timestamps for projection fallback when useful. |
| `dynamic_filter/m_detector/history_duration` | `0.8` s | Temporal depth-map history duration. Longer is more static-preserving. |
| `dynamic_filter/m_detector/max_history_frames` | `8` | Maximum temporal frames kept for comparison. |
| `dynamic_filter/m_detector/frame_duration` | `0.1` s | Time bucket size for temporal history frames. |
| `dynamic_filter/m_detector/min_history_votes` | `4` | Minimum temporal votes needed for a depth event. Higher is more conservative. |
| `dynamic_filter/m_detector/case_depth_margin` | `0.28` m | Depth-event sensitivity margin. Larger reduces false positives. |
| `dynamic_filter/m_detector/map_consistency_depth` | `0.40` m | Depth consistency margin against the map memory. |
| `dynamic_filter/m_detector/min_cluster_points` | `50` | Minimum points for a dynamic candidate cluster. |
| `dynamic_filter/m_detector/min_track_cluster_points` | `100` | Minimum points for a cluster to become or update a track. |
| `dynamic_filter/m_detector/max_cluster_extent` | `2.4` m | Maximum cluster extent accepted as an object. Smaller preserves large static structure. |
| `dynamic_filter/m_detector/max_assoc_distance` | `0.9` m | Track-to-cluster association distance. |
| `dynamic_filter/m_detector/track_confirm_hits` | `2` | Hits needed before a tentative track becomes confirmed. |
| `dynamic_filter/m_detector/track_ttl_scans` | `12` | Missed scans before a track expires. |
| `dynamic_filter/m_detector/static_veto_ratio` | `0.12` | Static-support veto ratio. Lower is more static-preserving. |
| `dynamic_filter/m_detector/body_static_bypass/*` | enabled with size/count gates | Rescue path for slow or stopped human-sized clusters that acquired static support. |

### IMU And Run-State Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `odom/gravity` | `9.80665` | Gravity magnitude used for IMU handling. |
| `odom/computeTimeOffset` | `false` | Enables LiDAR/IMU time-offset estimation logic. Leave off unless explicitly tuning timing. |
| `odom/imu/approximateGravity` | `true` | Uses approximate gravity alignment during initialization. |
| `odom/imu/calibration/gyro`, `odom/imu/calibration/accel` | `true`, `true` | Enables startup gyro and accelerometer bias calibration. |
| `odom/imu/calibration/time` | `3.0` s | Stationary calibration duration. Keep the robot still during this window. |
| `odom/imu/bufferSize` | `5000` | IMU sample buffer size. |
| `odom/imu/unit_check/enabled` | `false` | Enables raw IMU unit detection before calibration. |
| `odom/imu/unit_check/auto_scale` | `false` | When enabled, scales suspected `g` and `deg/s` data into SI units. |
| `odom/imu/unit_check/min_samples` | `50` | Samples needed before unit classification. |
| `odom/imu/unit_check/max_wait_sec` | `0.5` s | Maximum time to wait for unit-classification samples. |
| `odom/imu/unit_check/warn_period_sec` | `2.0` s | Warning print period when non-identity scaling is active. |
| `odom/imu/unit_check/assume_deg_per_sec_when_accel_g` | `true` | If acceleration looks like `g`, also treat gyro as `deg/s`. |
| `odom/imu/unit_check/accel_scale_override`, `odom/imu/unit_check/gyro_scale_override` | `0.0`, `0.0` | Positive values force manual scaling before calibration. |
| `imu/calibration` | `true` | If `false`, uses prior IMU biases from `dlio.yaml` instead of estimating them. |
| `imu/intrinsics/accel/bias`, `imu/intrinsics/gyro/bias` | zero vectors | Prior IMU biases used when `imu/calibration` is disabled. |
| `imu/intrinsics/accel/sm` | identity matrix | Accelerometer scale/misalignment matrix used when `imu/calibration` is disabled. |
| `run_stats/enabled` | `false` | Writes pose, twist, and bias rows to `run_stats.csv`. |
| `run_stats/output_dir` | `/tmp/dlio_run_stats` | Directory for CSV, plots, and summary. |
| `run_stats/overwrite` | `false` | If `true`, clears old run-state artifacts on startup. |
| `run_stats/plot_on_shutdown` | `false` | If `true`, generates plots during normal shutdown. |
| `run_stats/plot_dpi` | `600` | Plot image DPI. Values below `72` are clamped. |
| `run_stats/plot_script` | empty | Empty resolves to the installed `scripts/plot_run_stats.py`. |

### Visualization Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `odom/debug/enabled` | `true` | Enables extra odometry debug output. |
| `viz/vel_marker/enabled` | `true` | Publishes linear and angular velocity markers. |
| `viz/vel_marker/scale_lin` | `0.5` | Linear-velocity arrow length scale. |
| `viz/vel_marker/ang/radius_gain` | `0.20` | Angular-velocity marker radius gain. |
| `viz/vel_marker/ang/r_min`, `viz/vel_marker/ang/r_max` | `0.10`, `0.50` | Angular marker radius limits. |
| `viz/vel_marker/thickness` | `0.03` | Velocity marker line/disc thickness. |
| `viz/vel_marker/lifetime` | `0.10` s | Velocity marker lifetime. |
| `viz/corr_marker/enabled` | `true` | Publishes scan correction markers. |
| `viz/corr_marker/scale` | `1.0` | Correction marker length scale. |
| `viz/corr_marker/line_width` | `0.03` | Correction marker line width. |
| `viz/corr_marker/max_segments` | `2000` | Maximum stored correction-marker line segments. |
| `viz/corr_marker/lifetime` | `0.0` s | Correction marker lifetime. `0.0` means persistent until updated/deleted. |

## Build

Use a ROS 2 Jazzy environment. The validation container used for this repository is:

```bash
rslethz/ros2jazzy.perception:latest
```

Build from the colcon workspace that contains this package:

```bash
cd <workspace>
source /opt/ros/jazzy/setup.bash
colcon build --packages-select direct_lidar_inertial_odometry --symlink-install
source install/setup.bash
```

The package's `CMakeLists.txt` already builds in Release (`-O3`), so no extra
`--cmake-args` are needed. Do not inject `-fsanitize=...` flags — they make the
node much slower and can abort it on benign overflows. `--symlink-install` lets
you edit YAML/launch files without rebuilding (rebuild only after C++ changes).

Run tests:

```bash
cd <workspace>
source /opt/ros/jazzy/setup.bash
colcon test --packages-select direct_lidar_inertial_odometry --event-handlers console_direct+
```

## Run Generic DLIO

Terminal 1:

```bash
cd <workspace>
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch direct_lidar_inertial_odometry dlio.launch.py \
  rviz:=true \
  use_sim_time:=true \
  pointcloud_topic:=/lidar_points \
  imu_topic:=/lidar_imu
```

Terminal 2 (remember to source ROS 2 here too — it is a new shell):

```bash
source /opt/ros/jazzy/setup.bash
ros2 bag play <bag_or_mcap_path> \
  -r 1.0 \
  --clock \
  --read-ahead-queue-size 2000 \
  --remap /tf:=/tf_bag
```

`--clock` publishes `/clock` so the nodes can run on sim time; `--remap /tf:=/tf_bag`
keeps the bag's TF from fighting the live one.

Set `rviz:=false` if you do not want RViz:

```bash
ros2 launch direct_lidar_inertial_odometry dlio.launch.py rviz:=false use_sim_time:=true
```

## Run The A2 Front-Lidar Setup Live

This launch is for the live A2 front sensor pair on `/front_lidar/points` and
`/front_lidar/imu`.

```bash
cd <workspace>
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch direct_lidar_inertial_odometry a2_front_live.launch.py
```

The live A2 launch enables:

- `dynamic_filter/max_range:=10.0`
- live robot output topics `/state_estimation` and `/registered_scan`
- map cropping for live memory control

For a full-mission saved map during a live run, disable live map cropping:

```bash
ros2 launch direct_lidar_inertial_odometry a2_front_live.launch.py map_crop_enabled:=false
```

Set `rviz:=true` if you want the A2 RViz display during live operation:

```bash
ros2 launch direct_lidar_inertial_odometry a2_front_live.launch.py rviz:=true
```

## Replay An MCAP End-To-End

`a2_front_replay.launch.py` starts the A2 front DLIO odom + map nodes, RViz2,
and an xterm running `ros2 bag play --clock`. It does not save maps
automatically.

```bash
cd <workspace>
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch direct_lidar_inertial_odometry a2_front_replay.launch.py \
  bag:=/home/ttuna/colcon_ws/src/summerschool_data/arche_loop_0.mcap
```

ROS 2 launch arguments must use `name:=value`. If the path contains spaces,
quote the whole `bag:=...` value:

```bash
ros2 launch direct_lidar_inertial_odometry a2_front_replay.launch.py \
  bag:="/media/ttuna/RSS2026/A2 bags/challenge_1_0.mcap"
```

Focus the xterm and press SPACE to pause/resume `ros2 bag play`.

## Save Maps

The map node creates the `save_pcd` service. With the provided launch files
running at the root namespace, `ros2 service list` should show:

```bash
/save_pcd
```

Save the current map with defaults:

```bash
ros2 service call /save_pcd direct_lidar_inertial_odometry/srv/SavePCD "{}"
```

If you launch DLIO under a namespace or remap the service, use the exact name
shown by:

```bash
ros2 service list | grep save_pcd
```

The `{}` request uses the service defaults: an empty `save_path` writes to
`/tmp/dlio_maps`, and `leaf_size <= 0` uses `map/sparse/leafSize` from the map
node parameters. Those request defaults are documented in
[srv/SavePCD.srv](./srv/SavePCD.srv), the hard-coded fallback save directory is
defined in [src/dlio/map.cc](./src/dlio/map.cc), and the default parameter value
loaded by the provided launches is in [cfg/params.yaml](./cfg/params.yaml).

Call this while the DLIO launch is still running and after enough keyframes have been published.

With the default save path, the service always writes:

- `/tmp/dlio_maps/dlio_map.pcd`
- `/tmp/dlio_maps/clean_map.pcd`
- `/tmp/dlio_maps/save_summary.txt`

If `map/save_dynamic_removed/enabled:=true`, it also writes:

- `/tmp/dlio_maps/dlio_dynamic_removed_map.pcd`
- `/tmp/dlio_maps/dynamic_points.pcd`

`clean_map.pcd` is the persistent map built from cleaned keyframes. `dynamic_points.pcd` contains points actually suppressed from keyframes/maps by the online dynamic filter. Registration-only candidates and intermediate debug likelihood points are not supposed to be accumulated into `dynamic_points.pcd`.

Override the defaults when needed:

```bash
ros2 service call /save_pcd direct_lidar_inertial_odometry/srv/SavePCD \
  "{leaf_size: 0.15, save_path: '/tmp/my_dlio_maps'}"
```

For full-mission maps, disable map cropping before the run:

```bash
ros2 launch direct_lidar_inertial_odometry dlio.launch.py \
  use_sim_time:=true \
  pointcloud_topic:=/lidar_points \
  imu_topic:=/lidar_imu
```

and set in [cfg/params.yaml](./cfg/params.yaml):

```yaml
map/crop/enabled: false
```

`a2_front_replay.launch.py` uses the YAML default, which is crop off.
`a2_front_live.launch.py` defaults crop on for memory control; pass
`map_crop_enabled:=false` when you want a full live-run map.

## Save Run-State Plots

Run-state export is controlled by these parameters in [cfg/params.yaml](./cfg/params.yaml):

```yaml
run_stats/enabled: true
run_stats/output_dir: "/tmp/dlio_run_stats"
run_stats/overwrite: true
run_stats/plot_on_shutdown: true
run_stats/plot_dpi: 600
run_stats/plot_script: ""
```

When `run_stats/enabled` is true, the odom node writes:

- `run_stats.csv`

When `run_stats/plot_on_shutdown` is true, Ctrl+C or normal node shutdown also generates:

- `pose_position.pdf`
- `pose_position.png`
- `pose_orientation_rpy.pdf`
- `pose_orientation_rpy.png`
- `twist_linear_body.pdf`
- `twist_linear_body.png`
- `twist_angular_body.pdf`
- `twist_angular_body.png`
- `bias_accel.pdf`
- `bias_accel.png`
- `bias_gyro.pdf`
- `bias_gyro.png`
- `run_stats_summary.txt`

The x-axis is time in seconds. The y-axes use physical units: meters, radians, meters per second, radians per second, `m/s^2`, and `rad/s`.

The default output directory is:

```bash
/tmp/dlio_run_stats
```

For a normal bag workflow, let the bag finish, then press Ctrl+C in the DLIO launch terminal. The odom node closes the CSV and runs the plotter during shutdown.

If the process is killed with `SIGKILL`, plots may not be generated, but rows already flushed to `run_stats.csv` remain.

## Dynamic Object Removal

Dynamic filtering is configured under `dynamic_filter/*` in [cfg/params.yaml](./cfg/params.yaml).

Common controls:

```yaml
dynamic_filter/enabled: true
dynamic_filter/min_range: 1.0
dynamic_filter/max_range: 8.0
dynamic_filter/local_radius: 30.0
dynamic_filter/force_removed_cloud_output: false
```

The live A2 launch overrides `dynamic_filter/max_range` to `10.0`.

Important range semantics:

- `dynamic_filter/min_range` and `dynamic_filter/max_range` gate dynamic detection/removal only.
- Finite points outside this range still pass into the clean map.
- Out-of-range points should not appear in `dynamic_points.pcd`.
- The active backend is M-detector-style ego-motion-compensated temporal depth comparison, cluster filtering, and object tracking.

For deterministic dynamic-point PCD generation, use:

```yaml
map/save_dynamic_removed/enabled: true
dynamic_filter/force_removed_cloud_output: true
```

The checked-in A2 live and replay launch defaults leave dynamic-point PCD
artifacts off. Enable the two parameters above before the run if you need
`dynamic_points.pcd`; otherwise the save service still writes the clean map.

## IMU Unit Auto-Scaling

The unit checker runs at the start of `OdomNode::callbackImu()` and scales the raw IMU message before:

- IMU extrinsic transform
- calibration accumulation
- gravity alignment
- bias estimation
- IMU buffering
- deskew integration
- propagation

Parameters:

```yaml
odom/imu/unit_check/enabled: true
odom/imu/unit_check/auto_scale: true
odom/imu/unit_check/min_samples: 50
odom/imu/unit_check/max_wait_sec: 0.5
odom/imu/unit_check/warn_period_sec: 2.0
odom/imu/unit_check/assume_deg_per_sec_when_accel_g: true
odom/imu/unit_check/accel_scale_override: 0.0
odom/imu/unit_check/gyro_scale_override: 0.0
```

Detection behavior:

- Raw accel norm near `9.81`: treated as ROS-standard `m/s^2`; scale remains identity.
- Raw accel norm near `1.0`: treated as `g`; accel is multiplied by gravity.
- If accel is detected as `g` and `assume_deg_per_sec_when_accel_g` is true, gyro is multiplied by `pi / 180`.
- Positive override values force the scale and still happen before calibration.

When non-identity scaling is active, the odom node prints a large orange warning periodically with the raw medians, scales, and classification.

## RViz

The A2 and generic RViz launch paths include environment fixes for common
container/X11 issues:

```bash
DBUS_FATAL_WARNINGS=0
NO_AT_BRIDGE=1
QT_ACCESSIBILITY=0
QT_QPA_PLATFORM=xcb
QT_X11_NO_MITSHM=1
```

If RViz still fails in your environment, run DLIO without RViz:

```bash
ros2 launch direct_lidar_inertial_odometry a2_front_replay.launch.py rviz:=false
```

and start RViz separately after fixing host/container display access.

## Citation
If you found this work useful, please cite our manuscript:

```bibtex
@article{chen2022dlio,
  title={Direct LiDAR-Inertial Odometry: Lightweight LIO with Continuous-Time Motion Correction},
  author={Chen, Kenny and Nemiroff, Ryan and Lopez, Brett T},
  journal={2023 IEEE International Conference on Robotics and Automation (ICRA)},
  year={2023},
  pages={3983-3989},
  doi={10.1109/ICRA48891.2023.10160508}
}
```

## Acknowledgements

We thank the authors of the [FastGICP](https://github.com/SMRT-AIST/fast_gicp) and [NanoFLANN](https://github.com/jlblancoc/nanoflann) open-source packages:

- Kenji Koide, Masashi Yokozuka, Shuji Oishi, and Atsuhiko Banno, “Voxelized GICP for Fast and Accurate 3D Point Cloud Registration,” in _IEEE International Conference on Robotics and Automation (ICRA)_, IEEE, 2021, pp. 11 054–11 059.
- Jose Luis Blanco and Pranjal Kumar Rai, “NanoFLANN: a C++ Header-Only Fork of FLANN, A Library for Nearest Neighbor (NN) with KD-Trees,” https://github.com/jlblancoc/nanoflann, 2014.

We would also like to thank Helene Levy and David Thorne for their help with data collection.

## License
This work is licensed under the terms of the MIT license.

<br>
<p align='center'>
    <img src="./doc/img/ucla.png" alt="drawing" width="720"/>
</p>
<p align='center'>
    <img src="./doc/img/trees.png" alt="drawing" width="720"/>
</p>
