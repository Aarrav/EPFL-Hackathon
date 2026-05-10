# Hardware Assets

- `cad/` contains the SolidWorks, STEP, and STL files for the fruit gripper, blade, basket extension, camera holder, servo holder, and SO101 assembly references.
- `calibration/` contains LeRobot leader/follower motor calibration JSON files.
- `urdf/` is reserved for the SO101 URDF required by the inverse-kinematics pipeline.

`cad/imported_duplicates/` contains imported duplicate CAD drops retained for traceability when a delete could not be performed in the current sandbox.

The runtime scripts default to `hardware/urdf/SO101/so101_new_calib.urdf`. Add that file from the SO-ARM100 simulation assets or set `SO101_URDF_PATH` in `.env`.
