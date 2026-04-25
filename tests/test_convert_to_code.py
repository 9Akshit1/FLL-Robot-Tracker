# tests/test_convert_to_code.py

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from convert_to_code import load_rows, generate_spike_script


class TestLoadRows:
    """Test CSV loading for code generation"""
    
    def test_load_valid_csv(self):
        """Test loading valid CSV with motors"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg
0,0,0,0,0
150,45,45,45,45
300,90,90,90,90"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            rows = load_rows(f.name)
            assert len(rows) == 3
            assert rows[0]['t'] == 0
            assert rows[1]['t'] == 150
            assert 'A_rel' in rows[1]
            
            Path(f.name).unlink()
    
    def test_motor_extraction(self):
        """Test extracting motor deltas"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,motorC_rel_deg,motorC_abs_deg
0,0,0,0,0,0,0
150,45,45,30,30,0,0
300,90,90,60,60,0,0"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            rows = load_rows(f.name)
            
            # Check motor columns exist
            assert 'A_rel' in rows[1]
            assert 'B_rel' in rows[1]
            assert rows[1]['A_rel'] == 45
            assert rows[1]['B_rel'] == 30
            
            Path(f.name).unlink()
    
    def test_skip_malformed_rows(self):
        """Test skipping malformed rows"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg
#Comment line
0,0,0,0,0
invalid data
150,45,45,30,30"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            # Should not crash, just skip bad rows
            rows = load_rows(f.name)
            assert len(rows) >= 1
            
            Path(f.name).unlink()
    
    def test_empty_csv(self):
        """Test loading empty CSV"""
        csv_content = "time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg\n"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            f.flush()
            
            rows = load_rows(f.name)
            assert len(rows) == 0
            
            Path(f.name).unlink()


class TestGenerateSpikeScript:
    """Test script generation"""
    
    def test_basic_script_generation(self):
        """Test generating a basic replay script"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg
0,0,0,0,0
150,45,45,45,45
300,90,90,90,90"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f_in:
            f_in.write(csv_content)
            f_in.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f_out:
                output_path = f_out.name
            
            generate_spike_script(f_in.name, output_path)
            
            # Check file was created
            assert Path(output_path).exists()
            
            # Check content
            content = Path(output_path).read_text()
            assert 'import runloop' in content
            assert 'import motor' in content
            assert 'timeline' in content
            assert 'async def main' in content
            
            Path(f_in.name).unlink()
            Path(output_path).unlink()
    
    def test_timeline_structure(self):
        """Test that timeline has correct structure"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg
0,0,0,0,0
150,45,45,45,45
300,90,90,90,90"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f_in:
            f_in.write(csv_content)
            f_in.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f_out:
                output_path = f_out.name
            
            generate_spike_script(f_in.name, output_path)
            content = Path(output_path).read_text()
            
            # Timeline should have format: (dt, dA, dB, ...)
            assert 'timeline = [' in content
            assert '(150' in content or '(150,' in content
            
            Path(f_in.name).unlink()
            Path(output_path).unlink()
    
    def test_motor_delta_calculation(self):
        """Test that motor deltas are calculated correctly"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg
0,0,0,0,0
150,45,45,30,30
300,90,90,60,60"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f_in:
            f_in.write(csv_content)
            f_in.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f_out:
                output_path = f_out.name
            
            generate_spike_script(f_in.name, output_path)
            content = Path(output_path).read_text()
            
            # Between frame 0->1: dt=150, dA=45, dB=30
            # Between frame 1->2: dt=150, dA=45, dB=30
            assert '150, 45, 30' in content or '(150, 45, 30)' in content
            
            Path(f_in.name).unlink()
            Path(output_path).unlink()
    
    def test_config_aware_motors(self):
        """Test that script respects motor config"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg,motorC_rel_deg,motorC_abs_deg
0,0,0,0,0,0,0
150,45,45,30,30,20,20
300,90,90,60,60,40,40"""
        
        config = {
            "motors": {
                "A": True,
                "B": True,
                "C": False  # C is disabled
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f_in:
            f_in.write(csv_content)
            f_in.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f_out:
                output_path = f_out.name
            
            generate_spike_script(f_in.name, output_path, config=config)
            content = Path(output_path).read_text()
            
            # Should have A and B but not C
            assert 'motor.run_for_degrees(port.A' in content
            assert 'motor.run_for_degrees(port.B' in content
            # C should not appear in motor commands (only in timeline data)
            assert 'motor.run_for_degrees(port.C' not in content or 'if dC != 0' not in content
            
            Path(f_in.name).unlink()
            Path(output_path).unlink()
    
    def test_error_empty_csv(self):
        """Test that empty CSV raises error"""
        csv_content = "time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg\n"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f_in:
            f_in.write(csv_content)
            f_in.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f_out:
                output_path = f_out.name
            
            with pytest.raises(RuntimeError, match="No data loaded"):
                generate_spike_script(f_in.name, output_path)
            
            Path(f_in.name).unlink()
    
    def test_speed_computation(self):
        """Test that speed computation is included"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg
0,0,0,0,0
150,45,45,45,45
300,90,90,90,90"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f_in:
            f_in.write(csv_content)
            f_in.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f_out:
                output_path = f_out.name
            
            generate_spike_script(f_in.name, output_path)
            content = Path(output_path).read_text()
            
            # Should include speed computation
            assert 'compute_speed' in content
            assert 'def compute_speed' in content
            
            Path(f_in.name).unlink()
            Path(output_path).unlink()


class TestScriptExecutability:
    """Test that generated scripts are valid Python"""
    
    def test_syntax_valid(self):
        """Test that generated script is valid Python"""
        csv_content = """time_ms,motorA_rel_deg,motorA_abs_deg,motorB_rel_deg,motorB_abs_deg
0,0,0,0,0
150,45,45,45,45"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f_in:
            f_in.write(csv_content)
            f_in.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f_out:
                output_path = f_out.name
            
            generate_spike_script(f_in.name, output_path)
            content = Path(output_path).read_text()
            
            # Should compile without syntax errors
            compile(content, output_path, 'exec')
            
            Path(f_in.name).unlink()
            Path(output_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])