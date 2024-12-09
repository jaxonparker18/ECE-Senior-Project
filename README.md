# ECE Senior Project: Robotic Fire Extinguishment System (RFES)

## Authors
- Austin LaMontagne
- Hank Thompson
- Jaxon Parker
- Nathaniel Ray Raharjo

## Summary 
This repository contains the complete codebase for the **Robotic Fire Extinguishment System (RFES)**, an autonomous system designed to detect and extinguish fires using a Raspberry Pi. The project combines advanced computer vision, real-time control systems, and efficient hardware interfacing to deliver a responsive and effective firefighting solution.

## Features Overview

### Auto-Tracking
- Utilizes Roboflow's Image Recognition API with a model trained specifically for real-time fire detection.  
- Employs Python's CV2 library for lightweight and efficient fire tracking.  
- A custom Proportional-Integral (PI) controller drives the system accurately towards the fire.  
- Includes a patrol mode and auto-scanning functionality to monitor the environment for fires.  

### Motors & Motor Driver
- Software PWM controls ensure precise speed and direction management.  
- Integrated dual-channel H-bridge motor driver facilitates motor control via Raspberry Pi GPIO.  

### Power System
- **Dual-battery configuration**:  
- 3 Lithium-ion batteries (5V) power the Raspberry Pi and sensors.  
- 12V lithium-ion battery pack powers the pump, motors, and servos.  
- Includes a 12V-to-5V power converter for the relay and motor driver.  

### Raspberry Pi 4 & Camera
- The Raspberry Pi acts as the central controller for the system.  
- Implements client-server communication using TCP protocol for seamless information transfer.  
- Captures and streams video for fire detection and monitoring.  
- Manages all hardware components via GPIO pins.  

### Pump, Servos, and Sensors
- Water pump operation is controlled by a relay serving as an electronic switch.  
- Servo motors are controlled using hardware PWM for precise adjustments.  
- Water sensors monitor reservoir levels and provide real-time feedback.  

---

This repository showcases the integration of hardware and software to create a functional, real-world fire extinguishing system. 

---

For all the 3D design models used in this project, please visit **ECE-Senior-Project-CAD**: [Link to CAD Repository](https://github.com/jaxonparker18/ECE-Senior-Project-CAD)


