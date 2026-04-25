# tests/conftest.py

import pytest
import tempfile
from pathlib import Path
import json


@pytest.fixture
def temp_csv():
    """Fixture providing a temporary CSV file with sample data"""
    csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,yaw_deg,pitch_deg,roll_deg
0,0,0,0,0,0,0,0
150,45,45,45,45,0,0,0
300,90,90,90,90,2,0,0
450,135,135,135,135,4,0,0
600,0,180,0,180,0,0,0"""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(csv_content)
        f.flush()
        yield f.name
    
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_empty_csv():
    """Fixture providing an empty CSV file"""
    csv_content = "time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,yaw_deg,pitch_deg,roll_deg\n"
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(csv_content)
        f.flush()
        yield f.name
    
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_output_py():
    """Fixture providing a temporary output file path"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
        yield f.name
    
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def sample_config():
    """Fixture providing sample robot config"""
    return {
        "com_port": "COM3",
        "motors": {
            "A": True,
            "B": True,
            "C": False
        },
        "sensors": {
            "distance": "D",
            "force": "F"
        }
    }


@pytest.fixture
def temp_config_file(sample_config):
    """Fixture providing a temporary config JSON file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(sample_config, f)
        f.flush()
        yield f.name
    
    Path(f.name).unlink(missing_ok=True)


# ============================================================
# MARKERS
# ============================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests as unit tests"
    )


# ============================================================
# SAMPLE DATA GENERATORS
# ============================================================

def generate_stationary_csv(duration_ms=1000, sample_interval=150):
    """Generate CSV for stationary robot"""
    lines = ["time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,yaw_deg,pitch_deg,roll_deg"]
    for t in range(0, duration_ms, sample_interval):
        lines.append(f"{t},0,0,0,0,0,0,0")
    return "\n".join(lines)


def generate_driving_csv(duration_ms=1500, sample_interval=150, speed_deg_per_step=45):
    """Generate CSV for driving forward"""
    lines = ["time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,yaw_deg,pitch_deg,roll_deg"]
    motor_pos = 0
    for t in range(0, duration_ms, sample_interval):
        lines.append(f"{t},{motor_pos},{motor_pos},{motor_pos},{motor_pos},0,0,0")
        motor_pos += speed_deg_per_step
    return "\n".join(lines)


def generate_turning_csv(duration_ms=1500, sample_interval=150, yaw_per_step=30):
    """Generate CSV for turning"""
    lines = ["time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,yaw_deg,pitch_deg,roll_deg"]
    yaw = 0
    for t in range(0, duration_ms, sample_interval):
        lines.append(f"{t},0,0,0,0,{yaw},0,0")
        yaw += yaw_per_step
    return "\n".join(lines)


@pytest.fixture
def stationary_csv():
    """Fixture for stationary robot data"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(generate_stationary_csv())
        f.flush()
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def driving_csv():
    """Fixture for driving robot data"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(generate_driving_csv())
        f.flush()
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def turning_csv():
    """Fixture for turning robot data"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write(generate_turning_csv())
        f.flush()
        yield f.name
    Path(f.name).unlink(missing_ok=True)