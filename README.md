# Prende Tu Mente
A workshop by Ideo-Maker and Helment

All setup files are found in the Setup directory
## PROGRAM SETUP

On a Windows computer, install:
1. Python 3.12.0
2.  Add Python to **system path** (Python generally located in C:\Users\[USERNAME]\AppData\Local\Programs\Python\Python312\ after standard installation)
3. Install required libraries for the workshop programs to run:
- Micrsoft Visual Studio **C++ build tools 14.1 or greater**: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Microsoft Visual Studio redistributable 
- **Python libraries** by typing in command line window: python -m pip install -r [PATH TO FILE]\requirements
4. Install the Neuri GUI via command line: python -m pip install [PATH TO FILE]\neurigui-2.70-py3-none-any.whl
5. Install the **CP201x** driver: After connecting the Neuri board, open the Hardware Manager and update the driver by pointing the installer to the CP201x folder
6. A **system restart** might be required

## EXPERIMENTAL SETUP

1. Place electrode paste (Ten20) on each electrode (the more the better).
2. Connect electrodes to your body and board:
- Blue: 	Chest above heart 			            Input electrode
- Red: 		Front of head (between hair and eyes) 	Reference electrode SRB2
- Yellow 	Lower leg				                Eletrical ground BIAS

## RUN PROGRAMS

Two programs are required to run at the same time:
1. The Neuri GUI responsable for extracting signals from the Neuri board
2. The PRENDE_TU_MENTE program that allows for controlling the Arduino

Both programs need to be **run sequentially** (Neuri GUI first):
1. Start the program by typing "python" in the command line. This will open a Python instance. Here, run:
```
import neurigui.neuri_gui as ng 
ng.Run()
```	
2. Chose the connection port (first parameter). You can leave all other parameters as they are

Secondly, start the PRENDE_TU_MENTE program:
1. Double-click on the PRENDE_TU_MENTE.py file
2. After startup, it will ask you for the connection port. Chose the connection port of the Arduino, NOT the Neuri board.
3. Set the threshold on the right axis to turn on the Arduino LED specifically during heart beats

## TROUBLESHOOTING

1. If the signal quality is not allowing to distinguish between background signal and heart beats, place the lead electrode on the SIDE of the chest
2. If the programs seem to be stuck, most probably the wrong ports have been selected Check the port names (ie COM12 vs COM13)
3. If you are sure about hving set the correct port but the program throws an errorthat the port could not be opened ("Access denied"), check if the PC is plugged in. Laptops running low on battery tend to shut down ports.
