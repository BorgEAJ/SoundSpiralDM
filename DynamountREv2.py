import numpy as np
import DynamountREv2_helper as h
from TMC_2209.TMC_2209_StepperDriver import *
from sshkeyboard import listen_keyboard, stop_listening
import time
import json
import os
import threading

#Initial settings
mic_dim = 121
#mic_dim = 500
lin_X = 0
lin_Y = 0
mic_dim = mic_dim + 20
loop = True
rot_steps = 1
lin_steps = 5
loaded = False
loaded_name = ""

#Create objects
Base = h.Joint()
T1 = h.Joint(Theeta=90, alfa=90, d=60)
T2 = h.Joint(Theeta=90, alfa=90, r=45)
T3 = h.Joint(Theeta=90, alfa=90, r=58)
TCP = h.Joint(r=mic_dim, d=120)

#Try to load saved poses
if os.path.exists("poses.json"):
    with open("poses.json", "r") as f:
        data = json.load(f)
else:
    data = {}

#Function for matrix calculations
def TCP_pos():
    return np.round(Base.matrix() @ T1.matrix() @ T2.matrix() @ T3.matrix() @ TCP.matrix(),2)

print(TCP_pos()[0,3])
print(TCP_pos())

print(np.rint(TCP_pos()[0,3]).astype(int))
print(TCP_pos())

print("------------------------")
print("SoundSpiral R.E.D V0.9.2 TEST")
print("------------------------")

#Stepper settings
tmc = TMC_2209(5, 19, 26, loglevel=Loglevel.INFO, driver_address=0)
time.sleep(0.5)
tmcX = TMC_2209(24, 17, 27, loglevel=Loglevel.INFO, driver_address=1)
time.sleep(0.5)
tmcY = TMC_2209(22, 11, 7, loglevel=Loglevel.INFO, driver_address=2)
time.sleep(0.5)




tmc.set_direction_reg(False)
tmc.set_current(700)
tmc.set_interpolation(False)
tmc.set_spreadcycle(False)
tmc.set_microstepping_resolution(2)
tmc.set_internal_rsense(False)
#tmc.set_motor_enabled(True)
tmc.set_acceleration_fullstep(20)
tmc.set_max_speed_fullstep(20)
time.sleep(0.5)

tmcY.set_direction_reg(False)
tmcY.set_current(300)
tmcY.set_interpolation(False)
tmcY.set_spreadcycle(False)
tmcY.set_microstepping_resolution(2)
tmcY.set_internal_rsense(False)
#tmcY.set_motor_enabled(True)
tmcY.set_acceleration_fullstep(100)
tmcY.set_max_speed_fullstep(100)
time.sleep(0.5)

tmcX.set_direction_reg(False)
tmcX.set_current(300)
tmcX.set_interpolation(False)
tmcX.set_spreadcycle(False)
tmcX.set_microstepping_resolution(2)
tmcX.set_internal_rsense(False)
#tmcX.set_motor_enabled(True)
tmcX.set_acceleration_fullstep(100)
tmcX.set_max_speed_fullstep(100)
#time.sleep(5)
tmc.set_motor_enabled(True)
tmcY.set_motor_enabled(True)
tmcX.set_motor_enabled(True)

def move(X,Y,r):
    TCP_matrix = TCP_pos() #calculate matrix

    prevX = np.rint(TCP_matrix[0,3]).astype(int) #TCP X-coordinate int
    prevY = np.rint(TCP_matrix[1,3]).astype(int) #TCP Y-coordinate int

    prevXf = TCP_matrix[0,3] #TCP X-coordinate float
    prevYf = TCP_matrix[1,3] #TCP X-coordinate float

    TCP.Theeta = TCP.Theeta + r/-4 #calculate degrees of rotation and set value to TCP DH

    TCP_matrix = TCP_pos() #calculate matrix(update)
    
    if r != 0: #If rotation, linear compensation
        X = np.rint((prevX - (TCP_matrix[0,3]))*10).astype(int)
        Y = np.rint((prevY - (TCP_matrix[1,3]))*10).astype(int)
    else:
        T2.d += X/10
        T3.d += Y/10

    #Update matrices
    T2.d += prevXf - TCP_matrix[0,3]
    T3.d += prevYf - TCP_matrix[1,3]
    tmc.run_to_position_steps_threaded(r, MovementAbsRel.RELATIVE)
    tmcX.run_to_position_steps_threaded(X, MovementAbsRel.RELATIVE)
    tmcY.run_to_position_steps_threaded(Y, MovementAbsRel.RELATIVE)

def press(key):
    X=0
    Y=0
    r=0
    global rot_steps
    global lin_steps
    global data
    global mic_dim
    global loop
    global loaded
    global loaded_name

    
    if key.isdigit():              # "0".."9"
        if int(key) == 0:
            rot_steps = 1 * 10
            lin_steps = 5 * 10
        else:
            rot_steps = 1 * int(key)
            lin_steps = 5 * int(key)

    #Linear 1 step = 1/10 mm
    elif key == "w":
        print("Forward")
        X = lin_steps
        move(X,Y,r)
        loaded = False
    elif key == "s":
        print("Backward")
        X = -lin_steps
        move(X,Y,r)
        loaded = False
    elif key == "a":
        print("Left")
        Y = lin_steps
        move(X,Y,r)
        loaded = False
    elif key == "d":
        print("Right")
        Y = -lin_steps
        move(X,Y,r)
        loaded = False

    #Rotation 1 step = 1/4 deg
    elif key == "q":
        print("CW")
        r = -rot_steps
        move(X,Y,r)
        loaded = False
    elif key == "e":
        print("CCW")
        r = rot_steps
        move(X,Y,r)
        loaded = False

    #Reset position to original
    elif key == "r":
        print("Reset position")
        tmc.run_to_position_steps_threaded(0, MovementAbsRel.ABSOLUTE)
        tmcX.run_to_position_steps_threaded(0, MovementAbsRel.ABSOLUTE)
        tmcY.run_to_position_steps_threaded(0, MovementAbsRel.ABSOLUTE)
        TCP.Theeta = 0
        T2.d = 0
        T3.d = 0
        loaded = False

    #Save position
    elif key == "c":
        print(f"\nExisting entries\n")
        for key in data.keys():
            print(key,data[key])
        stop_listening()
        time.sleep(0.1)
        name = input(f"\nEnter name to save\n")
        if len(name) < 1:
            print("Entry not valid, returning to main")
            time.sleep(1)
        else:
            r = tmc.get_current_position()
            X = tmcX.get_current_position()
            Y = tmcY.get_current_position()
            data[name] = [r,X,Y,mic_dim]
            with open("poses.json", "w") as f:
                json.dump(data, f, indent=2)
            #for key in data.keys():
                #print(key,data[key])
            loaded = True
            loaded_name = name
            
    #Load position
    elif key == "v":
        entries = list(data.items())
        print(f"\nExisting entries\n")
        for i, (name, values) in enumerate(entries, start=1):
            print(f"{i}) {name} {values}")
        stop_listening()
        time.sleep(0.1)

        try:
            choice = int(input("\nSelect number: ")) - 1
            name, values = entries[choice]
        except:
            print("No valid selection, returning to main")
            time.sleep(1)
            update_display()
            return

        try:
            tmc.run_to_position_steps_threaded(values[0], MovementAbsRel.ABSOLUTE)
            tmcX.run_to_position_steps_threaded(values[1], MovementAbsRel.ABSOLUTE)
            tmcY.run_to_position_steps_threaded(values[2], MovementAbsRel.ABSOLUTE)
            TCP.Theeta=values[0]/-4
            T2.d=values[1]/10
            T3.d=values[2]/10
            mic_dim=values[3]
            TCP.r=mic_dim
            loaded = True
            loaded_name = name
        except:
            print("No valid selection, returning to main")
            time.sleep(1)


    #Delete entries
    elif key == "x":
        entries = list(data.items())
        print(f"\nExisting entries\n")
        for i, (name, values) in enumerate(entries, start=1):
            print(f"{i}) {name} {values}")
        stop_listening()
        time.sleep(0.1)
        loaded = False

        try:
            choice = int(input("\nSelect number for deletion: ")) - 1
            name, values = entries[choice]
            confirmation = input(f"Are you sure you want to delete: {name} Y/N\n").lower()
            if name in data and confirmation == "y":
                data.pop(name)
                with open("poses.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(f"Deleted: {name}")
                time.sleep(1)
            else:
                print("No action, returning to main")
                time.sleep(1)
        except:
            print("No valid selection, returning to main")
            time.sleep(1)
            update_display()
            return

    #Exit program
    elif key == "z":
        stop_listening()
        time.sleep(0.1)
        os.system("clear")
        quit = input(f"Are you sure you want to exit program? Y/N\n").lower()
        if quit == "y":
            loop = False
            stop_listening()
        else:
            update_display()

    elif key == "m":
        stop_listening()
        time.sleep(0.1)
        try:
            mic_dim = int(input(f"Enter mic dim in mm\nDefault 121mm\n")) + 20
            TCP.r = mic_dim
        except:
            print("mic dim set to default")
            mic_dim = 141
            TCP.r = mic_dim
            time.sleep(1)
    
    update_display()

def update_display():
    global rot_steps
    global lin_steps
    global data
    global mic_dim
    TCP_matrix = TCP_pos()
    os.system("clear")

    if loaded:
        print(f"Saved position: {loaded_name}")

    print(f"""Rotation:{TCP.Theeta}deg
X:{round((TCP_matrix[0,3] - (199 + mic_dim - 141))/0.5,0)*0.5}mm
Y:{round((TCP_matrix[1,3]/0.5),0)*0.5}mm""")
    
    print(f"""Mic dimension: {mic_dim-20}mm
Rotational steps: {round(rot_steps/4,3)}deg
Linear steps {round(lin_steps/10,3)}mm""")
    
    print(f"""WASD = linear movement
QE = rotation
0-9 = step size selection
R = reset position
C = save position and corresponding mic dimension
V = load position and corresponding mic dimension
X = Select a saved position for deletion
M = adjust mic dimension
Z = exit program""")

update_display()
while(loop == True):
    listen_keyboard(on_press=press)