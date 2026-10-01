# Copyright (c) 2026 Collin Tower and Amots Avigad
# Distributed under the terms of the MIT License.
# See LICENSE file in the project root for full terms.


#gui
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

#threading
import threading
import time

#communication
import pyvisa


####################
# Thread decorator #
####################
def threaded(fn):
	def wrapper(*args, **kwargs):
		thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
		thread.start()
		return thread
	return wrapper

class TriaxSelect(ttk.LabelFrame):
	def __init__(self,parent,controller,text):
		super().__init__(parent,text=text)

		self.controller = controller
		self.port_list = ["Select Triax Port"]

		#dropdown
		self.select_frame = ttk.Frame(self)
		self.select_frame.grid(row=0,column=0,sticky="news")

		select_label = ttk.Label(self.select_frame,text="Port: ")
		select_label.grid(row=0,column=0,sticky="ew")

		self.dropdown_var = tk.StringVar(value=self.port_list[0])
		self.dropdown = ttk.OptionMenu(self.select_frame, self.dropdown_var, *self.port_list,
										 command=lambda port_name: self.port_select(port_name) )
		self.dropdown.grid(row=0,column=1,sticky="ew")
		self.dropdown.config(width=15)

		refresh_button = ttk.Button(self.select_frame, text="refresh",command = self.refresh_list)
		refresh_button.grid(row=0,column=2,sticky="ew")

		#status
		status_frame = ttk.Frame(self)
		status_frame.grid(row=1,column=0,sticky="news")

		status_label_static = ttk.Label(status_frame,text="Status: ")
		status_label_static.grid(row=0,column=0, sticky = 'w')
		self.status_label = ttk.Label(status_frame,text="disconnected",foreground="red")
		self.status_label.grid(row=0,column=1, sticky = 'w')

		self.refresh_list()

	def port_select(self,port_name):
		if port_name in self.controller.rm.list_resources():
			#do not reconnect to connected device
			if (self.controller.triax_com is not None) :
				print("Triax already connected")
				return
			else:
				try:
					self.controller.triax_com = self.controller.rm.open_resource(port_name,timeout=1000)
					self.controller.triax_com.read_termination = '' #Triax does not use default termination characters, this negates the defaul pyvisa return character
					self.controller.triax_com.write_termination = ''
					self.status_label.configure(text="connected",foreground="green")
				except:
					messagebox.showwarning("Connection error!", "Count not connect.")

			
	def refresh_list(self):
		self.controller.triax_com = None
		self.status_label.configure(text="disconnected",foreground="red")
		try:
			self.controller.progress_frame.status_label.configure(text="Status: Uninitialized",background="red")
		except:
			pass
		number_of_ports = len(self.controller.rm.list_resources())

		if number_of_ports == 0:
			self.port_list = ["Select Triax Port","no ports found"]
		else:
			self.port_list = ["Select a port"]
			self.port_list.extend(self.controller.rm.list_resources())

		#have to recreate dropdown or it does not update

		self.dropdown_var = tk.StringVar(value=self.port_list[0])
		self.dropdown = ttk.OptionMenu(self.select_frame, self.dropdown_var, *self.port_list,
										 command=lambda port_name: self.port_select(port_name) )
		self.dropdown.grid(row=0,column=1,sticky="ew")
		self.dropdown.config(width=15) 

class Initialize(ttk.LabelFrame):
	def __init__(self,parent,controller,text):
		super().__init__(parent,text=text)

		self.controller = controller

		init_button = ttk.Button(self, text="Initialize",command = self.initialize)
		init_button.pack(side="left")

		reset_button = ttk.Button(self, text="reset",command = self.stepper_reset)
		reset_button.pack(side="left")
	@threaded
	def initialize(self): #Unstucks Triax program, checks for connection with Triax 320, checks for grating stepper and slit position and updates labels
		if self.controller.triax_com is None:
			messagebox.showinfo("", "Triax not connected.")
			return
		self.controller.progress_frame.cycle_progress(0) #start progress bar

		try:

			self.controller.button_state("disable") # disable all buttons
			self.controller.triax_com.write("222") #used to see if Triax is stuck (222 reboot if 'hung')
			time.sleep(200e-3)
			self.controller.triax_com.write(" ") #Checks/Displays Boot (B) or Main (F).
			time.sleep(200e-3)
			state = self.controller.triax_com.read()
			if state == "F":
				self.controller.progress_frame.status_label.configure(text="Status: Connected",background="green")
			elif state == "B":
				self.controller.progress_frame.status_label.configure(text="Status: intitializing",background="red")
				self.controller.triax_com.write("O2000\0") #02000\0 start main program
				time.sleep(200e-3)

				self.controller.triax_com.write(" ") #Checks/Displays Boot (B) or Main (F).
				time.sleep(200e-3)
				state = self.controller.triax_com.read()
				if state=="B":
					self.initialize()
				elif state == "F":
					self.controller.progress_frame.status_label.configure(text="Status: stepper should be reset",background="green")

			self.controller.grating_frame.update_grating()
			self.controller.grating_frame.update_motor_position()
			self.controller.slit_frame.update_slit_position()

		except:
			messagebox.showerror("Time out", "Could not communicate with Triax.")

		self.controller.progress_frame.cycle_progress(1) # end progress
		self.controller.button_state("enable") #enable all buttons

	
	@threaded
	def stepper_reset(self): # To be used when grating is hung or was interupted from completing a grating change. Runs a command to unstuck and puts grating 1800 in position
		try:
			self.controller.button_state("disable") # disable all buttons
			self.controller.progress_frame.status_label.configure(text="Status: resetting stepper",background="red")

			self.controller.triax_com.write("A") #"A" initalizes stepper motor, manual recommends waits 100 seconds seems to quick in certain scenarios
			self.controller.progress_frame.progress_update(200) #update progress bar for 200s
			time.sleep(200)
			state = self.controller.triax_com.read()
			if state.strip() == "o":
				self.controller.grating_frame.radio_var.set(0) #set grating buttons to deafault grating 
			else:
				messagebox.showerror("Grating error", "Could not reset.")
				return

			self.controller.triax_com.write("G0,0\r") # sets absolute stepper position to 0 with 1800 g/mm
			time.sleep(200e-3)
			state = self.controller.triax_com.read()

			self.controller.triax_com.write("i0,0,0\r") # sets slit position calibration to 0
			time.sleep(200e-3)
			state = self.controller.triax_com.read()
			
			self.controller.grating_frame.update_grating()
			self.controller.grating_frame.update_motor_position()
			self.controller.slit_frame.update_slit_position()
		except:
			messagebox.showerror("Time out", "Could not communicate with Triax.")
		
		self.controller.button_state("enable")
		self.controller.progress_frame.status_label.configure(text="Status: stepper reset",background="green")

class Grating(ttk.LabelFrame):
	def __init__(self,parent,controller,text):
		super().__init__(parent,text=text)

		self.controller = controller

		#radio buttons for grating
		self.grating_frame = ttk.Frame(self)
		self.grating_frame.grid(row=0,column=1,sticky="news",padx=5)

		self.radio_var = tk.IntVar()
		self.radio_var.set(-1)

		grating_0 = tk.Radiobutton(self.grating_frame,text="1800 g/mm",variable=self.radio_var,value=0)
		grating_0.grid(row=0,column=0,sticky="ew")

		grating_1 = tk.Radiobutton(self.grating_frame,text="600 g/mm",variable=self.radio_var,value=1)
		grating_1.grid(row=1,column=0,sticky="ew")

		grating_2 = tk.Radiobutton(self.grating_frame,text="300 g/mm",variable=self.radio_var,value=2)
		grating_2.grid(row=2,column=0,sticky="ew")

		grating_button = ttk.Button(self.grating_frame, text="change grating",command=self.change_grating)
		grating_button.grid(row=3,column=0,sticky="ew")

		#steps
		self.steps_frame = ttk.Frame(self)
		self.steps_frame.grid(row=0,column=0,sticky="news",padx=5)

		self.grating_pos_label = ttk.Label(self.steps_frame,text="Grating position: Unknown")
		self.grating_pos_label.grid(row=0,column=0,sticky="ew",pady=5)

		self.steps_entry_frame = ttk.Frame(self.steps_frame)
		self.steps_entry_frame.grid(row=1,column=0,sticky="news")

		grating_entry_label = ttk.Label(self.steps_entry_frame,text = "steps (+/-): ")
		grating_entry_label.grid(row=0,column=0,sticky="w")

		self.grating_entry_var = tk.StringVar(value="0")
		grating_entry = ttk.Entry(self.steps_entry_frame,width=10,textvariable=self.grating_entry_var)
		grating_entry.grid(row=0,column=1,sticky="w")

		steps_button_frame = ttk.Frame(self.steps_frame)
		steps_button_frame.grid(row=2,column=0,sticky="news")

		step_button = ttk.Button(steps_button_frame, text="step by",command= lambda: self.move_stepper(self.grating_entry_var.get()))
		step_button.grid(row=0,column=0,sticky="ew")

		goto_button = ttk.Button(steps_button_frame, text="go to",command = self.move_stepper_to)
		goto_button.grid(row=0,column=1,sticky="ew")

	def update_grating(self): # checks for grating position and the if statement block below sets label to current position. returns Triax message
		try:
			self.controller.triax_com.write("Z452,0,0,0\r") #Checks/Displays grating position
			time.sleep(200e-3)
			state = self.controller.triax_com.read()

			if(state.strip()=="o0"):
				self.radio_var.set(0)

			elif(state.strip()=="o1"):
				self.radio_var.set(1)

			elif(state.strip()=="o2"):
				self.radio_var.set(2)
		except:
			messagebox.showerror("Time out", "Could not communicate with Triax.")

	def update_motor_position(self): # checks position of gratign stepper and sets the corresponding label to display trimmed device response
		try:
			self.controller.triax_com.write("H0\r") #Checks/Displays Boot (B) or Main (F).
			time.sleep(200e-3)
			motor_position = self.controller.triax_com.read()
			#print(motor_position)

			self.grating_pos_label.configure(text=f"Grating position: {motor_position[1:]}")
		except:
			messagebox.showwarning("Connection error!", "Count not get motor position.")

	@threaded
	def change_grating(self):
		try:
			self.controller.progress_frame.cycle_progress(0) #start progress bar
			self.controller.button_state("disable") # disable all buttons

			grating_number = self.radio_var.get()
			#check for valid grating selection
			if(grating_number!=0 and grating_number!=1 and grating_number!=2):
				messagebox.showinfo("", "No grating selected.")
				self.controller.progress_frame.cycle_progress(1) #end progress bar
				self.controller.button_state("enable") # enable all buttons
				return

			#check if on current grating
			self.controller.triax_com.write("Z452,0,0,0\r")  #Checks/Displays grating position
			time.sleep(200e-3)
			state = self.controller.triax_com.read()
			if(int(state.strip()[1:]) == grating_number):
				messagebox.showinfo("", "Grating is already at the target position.")
				self.controller.progress_frame.cycle_progress(1) #end progress bar
				self.controller.button_state("enable") # enable all buttons
				return

			command = ""
			if (grating_number == 0): # corresponding commands for changing the grating to 0,1,2
				command = "Z451,0,0,0,0\r" 
			elif(grating_number == 1):
				command = "Z451,0,0,0,1\r"
			elif(grating_number == 2):
				command = "Z451,0,0,0,2\r"

			self.controller.progress_frame.status_label.configure(text="Status: changing grating",background="red")

			self.controller.triax_com.write(command)  #Checks/Displays grating position
			time.sleep(200e-3)
			state = self.controller.triax_com.read()

			state="q"
			while(state.strip() != "oz"): #triax give back oz while moveing the grating
				self.controller.triax_com.write("l")  #Checks moving status
				time.sleep(1)
				state = self.controller.triax_com.read()

			self.controller.progress_frame.status_label.configure(text="Status: grating changed",background="green")

		except:
			messagebox.showerror("Time out", "Could not communicate with Triax.")

		self.update_grating()
		self.update_motor_position()
		self.controller.progress_frame.cycle_progress(1) #end progress bar
		self.controller.button_state("enable") # enable all buttons

	@threaded
	def move_stepper(self,steps): # moves grating stepper by a given step amount
		try:

			try:
				steps = int(steps)
			except:
				messagebox.showinfo("", "Invalid entry.")
				return

			if steps == 0:
				return

			self.controller.progress_frame.cycle_progress(0) #start progress bar
			self.controller.button_state("disable") # disable all buttons
			
			command = "F0,"

			if steps > 0:
				command+= str(steps)+"\r"

				self.controller.triax_com.write(command)  #move stepper
				time.sleep(200e-3)
				state = self.controller.triax_com.read()

				state="q"
				while(state!="oz"):
					self.controller.triax_com.write("E")  #check moving status
					time.sleep(20e-3)
					state = self.controller.triax_com.read()
					self.update_motor_position()

			elif steps < 0:
				command+= str(steps-2500)+"\r"      # overshoot position by 2500 steps (backlash correction)
				
				self.controller.triax_com.write(command)  #move stepper
				time.sleep(200e-3)
				state = self.controller.triax_com.read()

				state="q"
				while(state!="oz"):
					self.controller.triax_com.write("E")  #check moving status
					time.sleep(20e-3)
					state = self.controller.triax_com.read()
					self.update_motor_position()

				command= "F0,"+str(2500)+"\r"
				self.controller.triax_com.write(command)  #move stepper
				time.sleep(200e-3)
				state = self.controller.triax_com.read()
				
				state="q"
				while(state!="oz"):
					self.controller.triax_com.write("E")  #check moving status
					time.sleep(20e-3)
					state = self.controller.triax_com.read()
					self.update_motor_position()

		except:
			messagebox.showerror("Time out", "Could not communicate with Triax.")

		self.controller.progress_frame.cycle_progress(1) #end progress bar
		self.controller.button_state("enable") # enable all buttons

	def move_stepper_to(self): # moves the stepper to given positions (finding needed steps from current to given positions and inputting to 'MoveStepper' function)

		position = self.grating_entry_var.get()
		try:
			position = int(position)
		except:
			messagebox.showinfo("", "Invalid entry.")
			return
		self.controller.triax_com.write("H0\r")  #check moving status
		time.sleep(200e-3)
		motor_position = int(self.controller.triax_com.read()[1:])

		steps = position-motor_position
		self.move_stepper(steps)

class Slit(ttk.LabelFrame):
	def __init__(self,parent,controller,text):
		super().__init__(parent,text=text)

		self.controller = controller

		#steps
		self.steps_frame = ttk.Frame(self)
		self.steps_frame.grid(row=0,column=0,sticky="news",padx=5)

		self.slit_pos_label = ttk.Label(self.steps_frame,text="Slit position: Unknown")
		self.slit_pos_label.grid(row=0,column=0,sticky="ew",pady=5)

		self.steps_entry_frame = ttk.Frame(self.steps_frame)
		self.steps_entry_frame.grid(row=1,column=0,sticky="news")

		slit_entry_label = ttk.Label(self.steps_entry_frame,text = "steps (+/-): ")
		slit_entry_label.grid(row=0,column=0,sticky="w")

		self.slit_entry_var = tk.StringVar(value="0")
		slit_entry = ttk.Entry(self.steps_entry_frame,width=10,textvariable=self.slit_entry_var)
		slit_entry.grid(row=0,column=1,sticky="w")

		steps_button_frame = ttk.Frame(self.steps_frame)
		steps_button_frame.grid(row=2,column=0,sticky="news")

		step_button = ttk.Button(steps_button_frame, text="step by",command = lambda: self.move_slit(self.slit_entry_var.get()))
		step_button.grid(row=0,column=0,sticky="ew")

		goto_button = ttk.Button(steps_button_frame, text="go to",command = self.move_slit_to)
		goto_button.grid(row=0,column=1,sticky="ew")

	def update_slit_position(self): # checks the position the outer slits and sets the corresponding label to display trimmed device response, converted from steps to microns

		self.controller.triax_com.write("j0,0\r") # Using 1 step = 2 um, the device's step position is converted to micrometres
		time.sleep(200e-3)
		slit_position = int(self.controller.triax_com.read()[1:]) * 2

		self.slit_pos_label.configure(text = f"Slit position: {slit_position} \u03bcm")

	@threaded
	def move_slit(self,slit_width): # moves slits by a given micron scale input
		try:
			slit_width = int(slit_width)
		except:
			messagebox.showinfo("", "Invalid entry.")

		self.controller.progress_frame.cycle_progress(0) #start progress bar
		self.controller.button_state("disable") # disable all buttons
		
		
		steps = int(slit_width/2) # each step is 2 um
		max_steps = 1200 #slit has issues going past 2.5 mm

		self.controller.triax_com.write("j0,0\r") # Using 1 step = 2 um, the device's step position is converted to micrometres
		time.sleep(200e-3)
		slit_position = int(self.controller.triax_com.read()[1:])

		#check for valid steps
		if (slit_position + steps > max_steps) or (slit_position + steps < 0):
			messagebox.showinfo("", "Slit position out of range (0-2400 \u03bcm).")
			self.controller.progress_frame.cycle_progress(1) #end progress bar
			self.controller.button_state("enable") # enable all buttons
			return

		elif(steps==0):
			self.controller.progress_frame.cycle_progress(1) #end progress bar
			self.controller.button_state("enable") # enable all buttons
			return
		
		command="k0,0,"+str(steps)+"\r" # command to increment slits by steps
		self.controller.triax_com.write(command)  #move stepper
		time.sleep(200e-3)
		state = self.controller.triax_com.read()
		state="q"
		while(state!="oz"):
			self.controller.triax_com.write("E")  #move stepper
			time.sleep(20e-3)
			state = self.controller.triax_com.read()
			self.update_slit_position()

		self.update_slit_position()
		self.controller.progress_frame.cycle_progress(1) #end progress bar
		self.controller.button_state("enable") # enable all buttons

	def MoveSlitTo(self): # moves slits to a given micron scale positions (finds needed increment from current and given postion and passes it to 'Slit' function)
		DisableButtons()
		CycProgress(0)
		slit_pos = float(WriteRead(Triax_com,"j0,0\r",0.3).strip()[1:])*2
		move=position-slit_pos
		slit(move)

	def move_slit_to(self): # moves the stepper to given positions (finding needed steps from current to given positions and inputting to 'MoveStepper' function)

		slit_width = self.slit_entry_var.get()
		try:
			slit_width = int(slit_width)
		except:
			messagebox.showinfo("", "Invalid entry.")
			return
		self.controller.triax_com.write("j0,0\r")  #check moving status
		time.sleep(200e-3)
		slit_position = int(self.controller.triax_com.read()[1:])

		steps = (slit_width/2.0) - slit_position
		slit_width = int(2 * steps)
		self.move_slit(slit_width)

class Progress(ttk.LabelFrame):
	def __init__(self,parent,controller,text):
		super().__init__(parent,text=text)

		self.controller = controller

		self.status_label = ttk.Label(self,text="Status: Uninitialized")
		self.status_label.configure(background="red")
		self.status_label.pack(padx=4,side="left")


		#progress bar
		self.progress_var = tk.IntVar()
		self.progressbar = ttk.Progressbar(self,variable=self.progress_var,orient="horizontal",length=200,maximum=100)
		self.progressbar.pack()

	def cycle_progress(self,mode_): # CycProgress(0) starts a cyclical progress bar animation and CycProgress(1) ends the cyclical animation
		if(mode_==0):
			self.progressbar.configure(mode="indeterminate")
			self.progressbar.start()
		else:
			self.progressbar.stop()
			self.progressbar.configure(mode="determinate")
			self.progress_var.set(0)

	@threaded
	def progress_update(self,time_amount): # When a wait has a known time this method can be called to create a progress bar filling up with static time
		self.progressbar.configure(mode="determinate")
		for half_sec in range(2*time_amount):
			time.sleep(0.5)
			self.progress_var.set(0.5*half_sec*(100/time_amount))

		self.progress_var.set(0)

