# Copyright (c) 2026 Collin Tower and Amots Avigad
# Distributed under the terms of the MIT License.
# See LICENSE file in the project root for full terms.

__author__ = "Collin Tower, Amots Avigad"
__license__ = 'GNU GPL V3.0'
__version__ = "1.0.0"

#gui imports
import tkinter as tk
from tkinter import ttk 
from tkinter import filedialog
from tkinter import messagebox

# import custom classes
import classes

#serial communication
import pyvisa

#threading
import threading
import time


def main(): #function to start program, called at end of the file
	raman_program = Application()
	raman_program.mainloop()

class Application(tk.Tk):

	def __init__(self):
		super().__init__()
		################
		# Window setup #
		################
		self.title("Triax 320 controller")

		self.protocol("WM_DELETE_WINDOW", self.close)
			
		######################
		# "global" variables #
		######################
		self.rm = pyvisa.ResourceManager() # starts serial communication
		print(self.rm) #prints location of GPIB dll file
		self.triax_com = None #stores triax communication

		self.button_list = None
		################
		#Gui File Menu #
		################
		menubar = tk.Menu(self)
		#about menu
		about_menu = tk.Menu(menubar, tearoff=0)
		about_menu.add_command(label="About", command=self.show_about)
		menubar.add_cascade(label="About", menu=about_menu)

		self.config(menu=menubar)

		##########
		# Frames #
		##########

		self.main_frame = ttk.Frame(self)
		self.main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

		self.triax_select_frame = classes.TriaxSelect(self.main_frame,self,"Select Port")
		#self.triax_select_frame.grid(row=0, column=0, sticky="nsew") #, padx=5, pady=5
		self.triax_select_frame.pack(fill="both")

		self.init_frame = classes.Initialize(self.main_frame,self,"Initialize")
		self.init_frame.pack(fill="both")

		self.grating_frame = classes.Grating(self.main_frame,self,"Grating")
		self.grating_frame.pack(fill="both")

		self.slit_frame = classes.Slit(self.main_frame,self,"Slit")
		self.slit_frame.pack(fill="both")

		self.progress_frame = classes.Progress(self.main_frame,self,"Progress")
		self.progress_frame.pack(fill="both")


		#get all the buttons for disabling
		self.button_list = self.all_buttons(self)

	#3################3
	# Get all buttons #
	###################

	def all_buttons(self,parent):
		button_list = []
		
		for child in parent.winfo_children():
			widget_class = child.winfo_class()

			if widget_class in ("Button","TButton"):
				button_list.append(child)
			if child.winfo_children():
				button_list.extend(self.all_buttons(child))

		return button_list

	def button_state(self,action):
		for button in self.button_list:
			if action == "enable":
				button.configure(state=tk.NORMAL)
			elif action == "disable":
				button.configure(state=tk.DISABLED)

	#3#######
	# About #
	#########

	def show_about(self):
	    title = "About Triax 320 Controller"
	    message = (
	        f"Triax 320 Spectrometer Control v1.0.0\n\n"
              "Developed by: Collin Tower and Amots Avigad\n"
              "License: MIT License\n\n"
	    )
	    messagebox.showinfo(title, message)

	#################
	# close program #
	#################

	def close(self): #function used for closing the ports when closing the window
		try:
			self.triax_com.close() #closes Triax com port
		except:
			pass

		self.quit()    #closes the window
		self.destroy()

	##############################
	# Closing and ending threads #
	##############################

		
if __name__ == "__main__":
	main()
