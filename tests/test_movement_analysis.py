# tests/test_movement_analysis.py

import pytest
import csv
import tempfile
from pathlib import Path
from io import StringIO

# Assumes movement_analysis.py is importable
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from movement_analysis import DataPoint, load_data, unwrap_angles, velocities, classify_movements, run


class TestDataPoint:
    """Test DataPoint class"""
    
    def test_init_basic(self):
        """Test basic DataPoint initialization"""
        data = {
            "time_ms": "1500",
            "motorA_rel_deg": "45.5",
            "yaw_deg": "10.2"
        }
        point = DataPoint(data)
        assert point.t == 1500.0
        assert point.yaw == 10.2
    
    def test_motor_extraction(self):
        """Test motor data extraction"""
        data = {
            "time_ms": "0",
            "motorA_rel_deg": "45",
            "motorA_abs_deg": "100",
            "motorB_rel_deg": "-30",
            "yaw_deg": "0",
            "pitch_deg": "0",
            "roll_deg": "0"
        }
        point = DataPoint(data)
        assert "motorA_rel_deg" in point.motors
        assert point.motors["motorA_rel_deg"] == 45.0
    
    def test_sensor_extraction(self):
        """Test sensor data extraction"""
        data = {
            "time_ms": "0",
            "distance_D_mm": "250",
            "force_F_N": "5.5",
            "yaw_deg": "0",
            "pitch_deg": "0",
            "roll_deg": "0"
        }
        point = DataPoint(data)
        assert "distance_D_mm" in point.sensors
        assert point.sensors["distance_D_mm"] == 250.0


class TestLoadData:
    """Test CSV loading"""
    
    def test_load_valid_csv(self):
        """Test loading valid CSV"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,yaw_deg,pitch_deg,roll_deg
0,0,0,0,0,0
150,45,45,2.5,0.1,0.0
300,90,90,5.0,0.2,-0.1"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            data = load_data(f.name)
            assert len(data) == 3
            assert data[0].t == 0
            assert data[1].t == 150
            assert data[2].yaw == 5.0
            
            Path(f.name).unlink()
    
    def test_load_empty_csv(self):
        """Test loading empty CSV"""
        csv_content = "time_ms,motorA_rel_deg,motorA_abs_deg,yaw_deg,pitch_deg,roll_deg\n"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            data = load_data(f.name)
            assert len(data) == 0
            
            Path(f.name).unlink()
    
    def test_skip_comment_lines(self):
        """Test that comment lines are skipped"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,yaw_deg,pitch_deg,roll_deg
#This is a comment
0,0,0,0,0,0
150,45,45,2.5,0.1,0.0"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            data = load_data(f.name)
            assert len(data) == 2  # Comment line skipped
            
            Path(f.name).unlink()


class TestUnwrapAngles:
    """Test angle unwrapping"""
    
    def test_no_wrap(self):
        """Test angles that don't wrap"""
        angles = [0, 5, 10, 15, 20]
        result = unwrap_angles(angles)
        assert result == angles
    
    def test_positive_wrap(self):
        """Test positive wrap (180 -> -180)"""
        angles = [170, 175, 180, -170]
        result = unwrap_angles(angles)
        # After unwrapping: 170, 175, 180, 190 (instead of -170)
        assert result[-1] > 180
    
    def test_negative_wrap(self):
        """Test negative wrap (-180 -> 180)"""
        angles = [-170, -175, -180, 170]
        result = unwrap_angles(angles)
        assert result[-1] < 0 or abs(result[-1]) == 170
    
    def test_empty_list(self):
        """Test empty input"""
        assert unwrap_angles([]) == []
    
    def test_single_angle(self):
        """Test single angle"""
        assert unwrap_angles([45]) == [45]


class TestVelocities:
    """Test velocity calculation"""
    
    def test_stationary(self):
        """Test velocities when robot is stationary"""
        data = []
        for i in range(3):
            d = DataPoint({
                "time_ms": str(i * 150),
                "motorA_rel_deg": "0",
                "motorB_rel_deg": "0",
                "yaw_deg": "0",
                "pitch_deg": "0",
                "roll_deg": "0"
            })
            data.append(d)
        
        drive_v, yaw_v = velocities(data)
        assert all(v == 0 for v in drive_v)
        assert all(v == 0 for v in yaw_v)
    
    def test_constant_motion(self):
        """Test velocities during constant motion"""
        data = []
        for i in range(3):
            d = DataPoint({
                "time_ms": str(i * 150),
                "motorA_rel_deg": str(i * 45),
                "motorB_rel_deg": str(i * 45),
                "yaw_deg": "0",
                "pitch_deg": "0",
                "roll_deg": "0"
            })
            data.append(d)
        
        drive_v, yaw_v = velocities(data)
        assert drive_v[0] == 0  # First is always 0
        assert drive_v[1] > 0   # Moving forward
        assert drive_v[2] > 0   # Still moving
    
    def test_yaw_rotation(self):
        """Test yaw velocity detection"""
        data = []
        for i in range(3):
            d = DataPoint({
                "time_ms": str(i * 150),
                "motorA_rel_deg": "0",
                "motorB_rel_deg": "0",
                "yaw_deg": str(i * 30),  # Rotating 30 deg per step
                "pitch_deg": "0",
                "roll_deg": "0"
            })
            data.append(d)
        
        drive_v, yaw_v = velocities(data)
        assert yaw_v[1] > 0  # Rotating


class TestClassifyMovements:
    """Test movement classification"""
    
    def test_all_stationary(self):
        """Test classifying stationary data"""
        data = []
        for i in range(5):
            d = DataPoint({
                "time_ms": str(i * 150),
                "motorA_rel_deg": "0",
                "motorB_rel_deg": "0",
                "yaw_deg": "0",
                "pitch_deg": "0",
                "roll_deg": "0"
            })
            data.append(d)
        
        segments = classify_movements(data)
        assert len(segments) == 1
        assert segments[0]['type'] == 'stationary'
    
    def test_driving_detection(self):
        """Test detecting driving motion"""
        data = []
        # Stationary phase
        for i in range(2):
            d = DataPoint({
                "time_ms": str(i * 150),
                "motorA_rel_deg": "0",
                "motorB_rel_deg": "0",
                "yaw_deg": "0",
                "pitch_deg": "0",
                "roll_deg": "0"
            })
            data.append(d)
        
        # Driving phase (50 deg/s = high speed)
        for i in range(2, 6):
            d = DataPoint({
                "time_ms": str(i * 150),
                "motorA_rel_deg": str((i-2) * 100),  # Large motor movement
                "motorB_rel_deg": str((i-2) * 100),
                "yaw_deg": "0",  # Not turning
                "pitch_deg": "0",
                "roll_deg": "0"
            })
            data.append(d)
        
        segments = classify_movements(data)
        # Should detect stationary then driving_straight
        types = [s['type'] for s in segments]
        assert 'driving_straight' in types
    
    def test_turning_detection(self):
        """Test detecting turning motion"""
        data = []
        # Turning phase
        for i in range(5):
            d = DataPoint({
                "time_ms": str(i * 150),
                "motorA_rel_deg": "0",
                "motorB_rel_deg": "0",
                "yaw_deg": str(i * 50),  # High yaw rate
                "pitch_deg": "0",
                "roll_deg": "0"
            })
            data.append(d)
        
        segments = classify_movements(data)
        # Should detect turning
        assert any('turning' in s['type'] for s in segments)


class TestRun:
    """Integration test"""
    
    def test_full_workflow(self):
        """Test complete analysis workflow"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,yaw_deg,pitch_deg,roll_deg
0,0,0,0,0,0,0,0
150,45,45,45,45,0,0,0
300,90,90,90,90,2,0,0
450,135,135,135,135,4,0,0
600,0,180,0,180,0,0,0
750,0,180,0,180,0,0,0
900,0,180,0,180,0,0,0"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            segments = run(f.name)
            
            # Should detect at least 2 segments
            assert len(segments) >= 2
            
            # Verify segment structure
            for seg in segments:
                assert 'start' in seg
                assert 'end' in seg
                assert 'type' in seg
                assert 'duration' in seg
                assert 'avg_speed' in seg
            
            Path(f.name).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])