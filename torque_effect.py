import sys
sys.path.insert(0, 'C:/users/mathimyh/documents/boris data/borispythonscripts/')

from NetSocks import NSClient   # type: ignore
import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt



font = {'size' : 20}
mpl.rc('font', **font)

# Initializes an AFM mesh with its parameters and a relax stage. Saves the ground state after the simuation is over
def Init(t0):

    ns = NSClient(); ns.configure(True, False)
    ns.reset()
    
    # Initialize the mesh
    Lx = 600
    Ly = 20
    Lz = 8
    
    # Add the base layer
    Base = np.array([0, 0, 0, Lx, Ly, Lz]) * 1e-9
    ns.setafmesh("base", Base)
    ns.cellsize("base", np.array([4, 4, 4]) * 1e-9)

    # Add the modules
    ns.addmodule("base", "aniuni")

    # Set temperature
    ns.temperature("0.3K")

    # Set parameters
    ns.setparam("base", "grel_AFM", (1, 1))
    ns.setparam("base", "damping_AFM", (0.002, 0.002))
    ns.setparam("base", "Ms_AFM", 2.1e3)
    ns.setparam("base", "Nxy", (0, 0))
    ns.setparam("base", "A_AFM", 1e-12)
    ns.setparam("base", "Ah", -200e3)
    ns.setparam("base", "Anh", (0.0, 0.0))
    ns.setparam("base", "J1", 0)
    ns.setparam("base", "J2", 0)
    ns.setparam("base", "K1_AFM", (10e3, 10e3))
    ns.setparam("base", "K2_AFM", 0)
    ns.setparam("base", "K3_AFM", 0)
    ns.setparam("base", "cHa", 1)
    ns.setparam("base", "D_AFM", (0, 250e-6))
    ns.setparam("base", "ea1", (1,0,0))

    # Set the first relax stage, this finds the ground state
    ns.setstage('Relax')
    ns.editstagestop(0, 'time', t0 * 1e-12)

    ns.setode('sLLG', 'RK4')
    ns.setdt(1e-15)
    ns.random()

    ns.Run()

    ns.savesim('ground_state.bsm')

# Sets up a simulation with a virtual current
def virtual_current(t, V, sim_name):

    ns = NSClient(); ns.configure(True, False)
    ns.reset()
    
    ns.loadsim(sim_name)
    ns.reset()

    # Voltage stage
    ns.setstage('V')

    ns.editstagevalue('0', str(0.001*V))
    
    ns.editstagestop(0, 'time', t * 1e-12)


    # Set spesific params and modules here for torque
    ns.addmodule("base", "SOTfield")
    ns.addmodule("base", "transport")
    ns.setparam("base", "SHA", '1')
    ns.setparam("base", "flST", '1')
    
    # Add the electrodes
    ns.addelectrode('0,0,0,600e-9,0,8e-9')
    ns.addelectrode('0,20e-9,0,600e-9,20e-9,8e-9')
    ns.designateground('1')
    
    # Add step function so that torque only acts on region in the injector
    ns.setparamvar('SHA','equation','step(x-100e-9)-step(x-120e-9)')
    ns.setparamvar('flST','equation','step(x-100e-9)-step(x-120e-9)')

    # Add damping function so it increases at the edges
    ns.setparamvar('damping_AFM', 'equation', '1 + 100000 * (exp(-(x)^2 / 500e-18) + exp(-(x-600e-9)^2 / 500e-18))')

    return ns

# Runs the simulation and saves the spin accumulation. NOT time averaged
def runSimulation(t, V, data, x_start, x_stop):

    ns = virtual_current(t, V)
    ns.editdatasave(0, 'time', t * 1e-12)

    ns.cuda(1)

    first = np.array([x_start, 0, 0, x_start+1, 20, 8]) * 1e-9
    ns.setdata(data, "base", first)
    for i in range(x_stop - x_start -1):
        temp = np.array([x_start + 1 + 1*i, 0, 0, x_start + 2 + 1*i, 20, 8]) * 1e-9
        ns.adddata(data, "base", temp)

    # Saving 
    if data == '<mxdmdt>':
            savedata = 'mxdmdt'
    elif data == 'mxdmdt2':
        savedata = 'mxdmdt2'

    savename = 'C:/Users/mathimyh/Documents/Boris Data/Simulations/boris_fordypningsoppgave/cache/V' + str(V) + '_' + savedata + '_' + str(x_start) + '_' + str(x_stop) + '.txt'
    ns.savedatafile(savename)

    ns.Run()

# A function that runs the virtual current from a simulation for a given time and saves the simulation after
def run_and_save(t, V, loadname, savename):
    
    ns = virtual_current(t, V, loadname)

    ns.cuda(1)

    ns.Run()

    ns.savesim(savename)


# Function for finding the plateau. Saves data from one point along the x-axis.
def find_plateau(t, V, data, damping, x_val=False):

    ns = virtual_current(t, V, 'C:/Users/mathimyh/Documents/Boris Data/Simulations/boris_fordypningsoppgave/sims/ground_state.bsm')

    ns.setparam("base", "damping_AFM", (damping, damping))

    ns.cuda(1)

    # Save a profile to find the plateau
    if x_val != False:

        if data == '<mxdmdt>':
            savedata = 'mxdmdt'
        elif data == 'mxdmdt2':
            savedata = 'mxdmdt2'
        
        ns.editdatasave(0, 'time', 5e-12)
        
        temp = np.array([x_val, 0, 0, x_val + 10, 20, 8]) * 1e-9
        savename = 'C:/Users/mathimyh/Documents/Boris Data/Simulations/boris_fordypningsoppgave/cache/plateau_V' + str(V) + '_damping' + str(damping) + '_' + savedata + '_' + str(x_val) + 'nm.txt'
        
        ns.savedatafile(savename)

        ns.setdata('time')

        ns.adddata(data, "base", temp)

    ns.Run()

# Load a simulation in steady state, run the simulation and save the SA along with the time
def time_avg_SA(t, V, data, x_start, x_stop, damping):

    if data == '<mxdmdt>':
        savedata = 'mxdmdt'
    elif data == '<mxdmdt2>':
        savedata = 'mxdmdt2'

    sim_name = 'sims/' + str(V) + '_steady_state.bsm'
    
    ns = virtual_current(t, V, sim_name)
    ns.reset()

    ns.setparam("base", "damping_AFM", (damping, damping))

    ns.editdatasave(0, 'time', 5e-12)

    ns.setdata('time')
    for i in range(x_stop - x_start):
        temp = np.array([x_start + 1*i, 0, 0, x_start + 1 + 1*i, 20, 8]) * 1e-9
        ns.adddata(data, "base", temp)

    dampname = str(damping)
    Vname = str(V)

    savename = 'C:/Users/mathimyh/documents/boris data/simulations/cache/tAvg_damping' + dampname + '_V' + Vname + '_' + savedata  + '.txt'

    ns.savedatafile(savename)

    ns.cuda(1)

    ns.Run()

def main():
    
    t0 = 20
    t = 300
    
    # What gives a good signal without flipping the magnetization
    V = 0.08
    data = '<mxdmdt>'

    # runSimulation(t, V, data, negative=True)
    find_plateau(t, V, data, damping=0.0001, x_val=350)
    # Init(t0)
    # run_and_save(t, V, negative=True, loadname="sims/ground_state.bsm", savename="sims/negV_steady_state.bsm")
    # time_avg_SA(t, V, data, negative=True)


if __name__ == '__main__':
    main()