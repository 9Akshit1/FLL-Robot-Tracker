# TESTING_GUIDE.md

## Overview

This guide covers how to test the FLL Robot Tracker for bugs, crashes, and edge cases. Testing happens at three levels:

1. **Unit Tests** - Individual functions (automated)
2. **Integration Tests** - Full workflows (automated)
3. **Manual Testing** - Real scenarios (done by you)

---

## Running Automated Tests

### Setup

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
# View: htmlcov/index.html
```

### Test Categories

```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run slow tests (takes longer)
pytest tests/ -m slow

# Skip slow tests
pytest tests/ -m "not slow"

# Run a specific test
pytest tests/test_movement_analysis.py::TestDataPoint::test_init_basic -v
```

---

## Debugging Tools

### Flask Debug Mode
```python
# app.py
app.run(debug=True)  # Enables interactive debugger
```

### Browser DevTools
- F12 to open
- Network tab: See API calls and responses
- Console: Check for JavaScript errors
- Storage: View localStorage (saved config)

### mpremote Debug
```bash
mpremote --help
mpremote connect COM3 ls /flash  # List files on robot
mpremote connect COM3 cat /flash/data_log.csv | head -20  # View CSV
```


# Current State
```
tests/test_convert_to_code.py::TestLoadRows::test_load_valid_csv PASSED                                                                                  [  3%]
tests/test_convert_to_code.py::TestLoadRows::test_motor_extraction PASSED                                                                                [  6%]
tests/test_convert_to_code.py::TestLoadRows::test_skip_malformed_rows PASSED                                                                             [ 10%]
tests/test_convert_to_code.py::TestLoadRows::test_empty_csv PASSED                                                                                       [ 13%]
tests/test_convert_to_code.py::TestGenerateSpikeScript::test_basic_script_generation PASSED                                                              [ 17%]
tests/test_convert_to_code.py::TestGenerateSpikeScript::test_timeline_structure PASSED                                                                   [ 20%]
tests/test_convert_to_code.py::TestGenerateSpikeScript::test_motor_delta_calculation PASSED                                                              [ 24%]
tests/test_convert_to_code.py::TestGenerateSpikeScript::test_config_aware_motors PASSED                                                                  [ 27%]
tests/test_convert_to_code.py::TestGenerateSpikeScript::test_error_empty_csv PASSED                                                                      [ 31%]
tests/test_convert_to_code.py::TestGenerateSpikeScript::test_speed_computation PASSED                                                                    [ 34%]
tests/test_convert_to_code.py::TestScriptExecutability::test_syntax_valid PASSED                                                                         [ 37%]
tests/test_movement_analysis.py::TestDataPoint::test_init_basic PASSED                                                                                   [ 41%]
tests/test_movement_analysis.py::TestDataPoint::test_motor_extraction PASSED                                                                             [ 44%]
tests/test_movement_analysis.py::TestDataPoint::test_sensor_extraction PASSED                                                                            [ 48%]
tests/test_movement_analysis.py::TestLoadData::test_load_valid_csv PASSED                                                                                [ 51%]
tests/test_movement_analysis.py::TestLoadData::test_load_empty_csv PASSED                                                                                [ 55%]
tests/test_movement_analysis.py::TestLoadData::test_skip_comment_lines PASSED                                                                            [ 58%]
tests/test_movement_analysis.py::TestUnwrapAngles::test_no_wrap PASSED                                                                                   [ 62%]
tests/test_movement_analysis.py::TestUnwrapAngles::test_positive_wrap PASSED                                                                             [ 65%]
tests/test_movement_analysis.py::TestUnwrapAngles::test_negative_wrap PASSED                                                                             [ 68%]
tests/test_movement_analysis.py::TestUnwrapAngles::test_empty_list PASSED                                                                                [ 72%]
tests/test_movement_analysis.py::TestUnwrapAngles::test_single_angle PASSED                                                                              [ 75%]
tests/test_movement_analysis.py::TestVelocities::test_stationary PASSED                                                                                  [ 79%]
tests/test_movement_analysis.py::TestVelocities::test_constant_motion PASSED                                                                             [ 82%]
tests/test_movement_analysis.py::TestVelocities::test_yaw_rotation PASSED                                                                                [ 86%]
tests/test_movement_analysis.py::TestClassifyMovements::test_all_stationary PASSED                                                                       [ 89%]
tests/test_movement_analysis.py::TestClassifyMovements::test_driving_detection PASSED                                                                    [ 93%]
tests/test_movement_analysis.py::TestClassifyMovements::test_turning_detection PASSED                                                                    [ 96%]
tests/test_movement_analysis.py::TestRun::test_full_workflow PASSED                                                                                      [100%]
```

---
