# FLL Robot Tracker

**A web-based system for LEGO FIRST Robotics League teams to record, analyze, and replay robot movements.**

**Website:** https://aksh19.pythonanywhere.com/   (USERS can access this directly instead of needign to download the repository)
**Demo:** 
**GitHub:** https://github.com/9Akshit1/FLL-Robot-Tracker

---

## Features

- **Motion Recording** - Connect a LEGO SPIKE Prime and record motor/sensor data while moving the robot manually
- **Movement Classification** - Automatically detect and classify movements (driving straight, turning left/right, stationary)
- **Code Generation** - Convert recorded movements into executable Python scripts with accurate timing and speed compensation
- **Robot Replay** - Upload the generated code and replay the exact motion on your robot
- **Dynamic Configuration** - Adapts to different motor configurations (1, 2, or 3 motors) and sensor setups
- **Cross-Platform** - Works on Windows, macOS, and Linux with both local and cloud deployment

---

## Installation (for developers)

### Requirements

Before installing, make sure you have:
- **Python 3.8+** - [Download here](https://www.python.org/downloads/)
- **LEGO SPIKE Prime** - With motors connected and firmware updated
- **USB cable** - For robot connection
- **Git** (optional) - For cloning the repository

### Dependencies

The project requires these Python libraries:

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 2.3+ | Web server for dashboard and API |
| Pybricks | 3.4+ | Robot motor/sensor communication |
| pyserial | 3.5+ | USB serial port detection |
| mpremote | Latest | Upload/execute code on SPIKE Prime |
| pandas | 2.0+ | CSV data manipulation |
| numpy | 1.24+ | Numerical computation |
| pytest | 9.0+ | Automated testing |

For simple installation, we will run pip install -r requirements.txt.

### Setup Instructions

**1. Clone the repository:**
```bash
git clone https://github.com/9Akshit1/FLL-Robot-Tracker.git
cd FLL-Robot-Tracker
```

**2. Create a virtual environment:**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Run the application:**
```bash
python app.py
```

The web dashboard will be available at `http://localhost:5000`

### First-Time Setup Checklist

1. **Connect your robot** - Plug SPIKE Prime in via USB
2. **Run the local agent** - On first use, download and run `local_agent.py` on your computer (enables USB communication)
3. **Configure motors** - Select which motor ports are active (A, B, C)
4. **Test connection** - Click "Detect Ports" to verify robot is recognized

---

## Quick Start

### Basic Workflow

1. **Click "Connect & Record"** - A window appears on your robot
2. **Press the LEFT button on the robot** - Recording starts (display shows "REC")
3. **Move your robot manually** - Perform the motion you want to record
4. **Press the RIGHT button** - Recording stops (display shows "STP")
5. **Click "Pull Data"** - Retrieves the recording from the robot
6. **Click "Analyze"** - Detects movement segments (drive, turn, etc.)
7. **Click "Generate"** - Creates Python code based on the motion
8. **Click "Upload" then "Run"** - Robot replays the motion automatically

---

## Known Bugs & Limitations

### Known Issues

1. **Motor Replay Accuracy** - Robot replay motion is within ±8% for normal speeds (<60 deg/s) and ±12% for high speeds. This is due to motor acceleration/deceleration lag not modeled in the original recording. This is acceptable for FLL missions but not suitable for high-precision tasks.

2. **Gyroscope Drift** - Long recordings (>30 seconds) may accumulate slight yaw drift from IMU sensor integration error. Doesn't affect recorded motion replay significantly.

3. **Connectivity** - Depending on user setup and device, the application may not be able to connect to the robot. Next versions of the project will throughly investigate compatibiltiy with different devices. Current working devices: Windows laptops

### Limitations

- **Single Robot at a Time** - Cannot control multiple robots simultaneously (would require session management)
- **Cloud-Only Deployment** - PythonAnywhere requires local_agent.py to be downloaded and run on the user's machine
- **Sensor Support** - Currently supports force and distance sensors. Camera/color sensors not yet implemented.

---

## Support

### Getting Help

- **Setup Issues?** See the Troubleshooting section above
- **Code Questions?** Check `API_DOCS.md` for endpoint documentation
- **Testing?** See `TESTING_GUIDE.md` for detailed testing procedures

### Reporting Issues

Found a bug? Create an issue on GitHub: https://github.com/9Akshit1/FLL-Robot-Tracker/issues

Include:
- What you were trying to do
- What happened
- Expected behavior
- Your system info (Windows/Mac/Linux, Python version, robot model)
- Error messages (if any)

### Contact

**Project Authors:**
- Akshit Erukulla (9Akshit1)
- Rick He (wustigo)

---

## Sources & References

The following resources were consulted during development:

### Hardware & Robot APIs

[1] LEGO Education. (2025). *SPIKE Prime Python Help - Motor Control*.  
https://spike.legoeducation.com/essential/help/lls-help-python  
Used for: Motor encoder API (`motor.relative_position()`, `motor.absolute_position()`), motor control commands, and timing requirements.

[2] LEGO Education. (2025). *SPIKE Prime Motion Sensor (Gyroscope) Documentation*.  
https://spike.legoeducation.com/essential/help/motion-sensor  
Used for: IMU yaw/pitch/roll angle extraction via `motion_sensor.tilt_angles()`, understanding angle ranges (-180 to 180 degrees), and sensor accuracy specifications.

[3] Pybricks Development Team. (2025). *Pybricks - Python 3 for LEGO Robots*.  
https://pybricks.com/  
Used for: Pybricks library documentation, async/await patterns with `runloop`, file I/O operations (`open()`, `os.sync()`), and button input handling.

### Backend & Framework

[4] Pallets. (2025). *Flask - The Python Micro Framework for Building Web Applications*.  
https://flask.palletsprojects.com/  
Used for: Creating Flask app instances, route decorators (`@app.route`), JSON responses (`jsonify()`), and request handling (`request.get_json()`).

[5] The pandas development team. (2025). *pandas: Powerful Python Data Analysis Toolkit*.  
https://pandas.pydata.org/  
Used for: CSV parsing with error handling, DataFrame operations, and data manipulation for movement analysis.

[6] Harris, C. R., et al. (2020). Array programming with NumPy. *Nature*, 585(7825), 357-362.  
https://numpy.org/  
Used for: Numerical array operations, list comprehensions, and mathematical computations for velocity calculations.

### Hardware Communication

[7] Radomski, D. (2025). *mpremote - MicroPython Remote Command Line Tool*.  
https://github.com/micropython/micropython/blob/master/tools/mpremote/  
Used for: Uploading Python files to SPIKE Prime, executing remote code, downloading files via USB serial port, and subprocess management.

[8] pySerial Team. (2025). *pySerial - Python Serial Port Access*.  
https://pyserial.readthedocs.io/  
Used for: Detecting available COM ports with `serial.tools.list_ports.comports()`, enumerating USB devices, and providing fallback port detection.

### Testing & Development

[9] Pytest Team. (2025). *pytest - The Python Testing Framework*.  
https://pytest.org/  
Used for: Writing unit tests with fixtures, parameterized testing, test discovery, and coverage reporting (`pytest --cov`).

[10] Stack Overflow. (2025). *Stack Overflow - Collaborative Q&A Platform*.  
https://stackoverflow.com/  
Referenced for: Python async/await patterns in robotics, mpremote subprocess management, handling file system synchronization on embedded systems, and cross-platform USB communication best practices.

### Software Engineering & Architecture

[11] Microsoft. (2025). *Design Patterns - Bridge Pattern*.  
https://microsoft.github.io/AppModelv2-WebApp-OpenIDConnect-DotNet/  
Consulted for: Bridge pattern design for cloud-to-hardware communication, separating abstraction (web UI) from implementation (local USB access).

[12] van Rossum, G., Warsaw, B., & Coghlan, N. (2001). *PEP 8 - Style Guide for Python Code*.  
https://pep8.org/  
Used for: Code style consistency, naming conventions, and professional Python formatting throughout the project.

### References Used in Context

Each source was selected based on specific implementation needs:
- Hardware APIs provide the foundation for robot communication
- Flask enables the web server architecture
- pandas/NumPy provide mathematical operations for movement analysis
- mpremote is the critical tool for bridging cloud-to-hardware gap
- Testing frameworks ensure code reliability
- Design pattern references informed architectural decisions

---

## License

This project is licensed under the **MIT License**. You are free to use, modify, and distribute this software for educational and personal projects.

---

**Version:** 2.1  
**Last Updated:** May 2026  
**Status:** Production Ready