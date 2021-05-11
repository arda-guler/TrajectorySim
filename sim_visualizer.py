#   TRAJECTORY SIMULATION VISUALIZER

version = "0.4.2"

from dearpygui.core import *
from dearpygui.simple import *
import math
import pandas as pd
import time as t

#set initial window configuration (purely cosmetic)
set_main_window_size(1300, 700)
set_main_window_title("Trajectory Real-time Visualizer | MRS")
set_theme("Dark")

calc_run_number = 0

last_results = []

# graph display toggles
is_ground_displayed = False
is_karman_displayed = False

set_value(name="progress", value=0)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#                   FILE IMPORT
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def importFile():

    try:
        import_filepath = get_value("filepath_field")
        
        if not import_filepath[-4:] == ".txt":
            if import_filepath[-5:] == ".xlsx":
                log_warning("Exported .xlsx files don't contain input info. Trying " + import_filepath[:-5] + ".txt instead...", logger="Logs")
                import_filepath = import_filepath[:-5] + ".txt"
            else:
                import_filepath = import_filepath + ".txt"
            
        log_info("Importing inputs from " + import_filepath, logger="Logs")
        import_file = open(import_filepath, "r")
    except:
        log_error("Import failed. Check filepath.", logger="Logs")
        return

    try:
        import_lines = import_file.readlines()
        if not import_lines[0][18:-1] == version:
            log_warning("Save file version does not match software version. Import might fail.", logger="Logs")

        set_value(name="eev_field", value=import_lines[4][28:-5])
        set_value(name="mdot_field", value=import_lines[5][11:-6])
        set_value(name="mass_init_field", value=import_lines[6][14:-4])
        set_value(name="mass_final_field", value=import_lines[7][12:-4])
        set_value(name="alt_init_field", value=import_lines[8][18:-3])
        set_value(name="exit_pressure_field", value=import_lines[9][22:-4])
        set_value(name="exit_area_field", value=import_lines[10][18:-5])
        set_value(name="time_increment_field", value=import_lines[11][16:-3])

        if import_lines[14] == "Drag model ENABLED.\n":
            set_value(name="drag_model_checkbox", value=True)
            set_value(name="cross_sec_field", value=import_lines[12][39:-5])
            set_value(name="drag_coeff_field", value=import_lines[13][41:-1])
        else:
            set_value(name="drag_model_checkbox", value=False)
            set_value(name="cross_sec_field", value="Drag model disabled.")
            set_value(name="drag_coeff_field", value="Drag model disabled.")
            
    except:
        log_error("Import failed. Check file formatting.", logger="Logs")
        return

    log_info("Import successful.", logger="Logs")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#                SIMULATION SETUP
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def simulateTraj():
    
    global calc_run_number
    calc_run_number += 1
    log_info(message = "Run [" + str(calc_run_number) + "]: Simulating trajectory...", logger = "Logs")

    # get input values from entry fields

    drag_enabled = get_value("drag_model_checkbox")
    
    try:
        eev = float(get_value("eev_field"))
        mdot = float(get_value("mdot_field"))
        mass_init = float(get_value("mass_init_field"))
        mass_final = float(get_value("mass_final_field"))
        alt_init = float(get_value("alt_init_field"))
        exit_pressure = float(get_value("exit_pressure_field"))
        exit_area = float(get_value("exit_area_field"))
        time_increment = float(get_value("time_increment_field"))
        vis_scale = float(get_value("vis_scale_field"))

        if drag_enabled:
            cross_sec = float(get_value("cross_sec_field"))
            drag_coeff = float(get_value("drag_coeff_field"))
        else:
            cross_sec = -1.0
            drag_coeff = -1.0
            
    except:
        log_error("Input error. Make sure all design parameters are float values.", logger = "Logs")
        return

    if mass_final >= mass_init:
        log_error("Final mass can not be larger than initial mass!", logger = "Logs")
        return

    log_info("Inputs:\n" +
             "Eff. Ex. Vel: " + str(eev) + " m/s\n"
             "Mass Flow: " + str(mdot) + " kg/s\n"
             "Initial Mass: " + str(mass_init) + " kg\n"
             "Final Mass: " + str(mass_final) + " kg\n"
             "Initial Alt.: " + str(alt_init) + " m\n"
             "Exit Press.: " + str(exit_pressure) + " Pa\n"
             "Exit Area: " + str(exit_area) + " m^2\n"
             "Time Increment: " + str(time_increment) + " s\n"
             "Cross Section: " + str(cross_sec) + " m^2", logger = "Logs")


    # Calculation sub-functions

    def clamp(num, min_value, max_value):
        return max(min(num, max_value), min_value)

    def sign(x): return 1 if x >= 0 else -1

    def alt2dens(altitude):

        if altitude > 85000:
            return 0.0
        else:
            # atmospheric density lookup file has values in kg/m^3, with steps of 100 meters
            # retrieved from https://www.digitaldutch.com/atmoscalc/table.htm
            model_filename = "atm_density_model.txt"
            model_file = open(model_filename, "r")
            model_lines = model_file.readlines()

            alt_low = int(altitude/100)
            alt_high = alt_low + 1

            lookup_line_low = float(model_lines[alt_low])
            lookup_line_high = float(model_lines[alt_high])

            # do linear interpolation so you don't get "staircase" values
            interpolated_density = lookup_line_low + ((lookup_line_high - lookup_line_low)/100) * ((altitude - (alt_low * 100)))

            return float(interpolated_density)

    # https://www.grc.nasa.gov/www/k-12/airplane/atmosmet.html
    def alt2press(altitude):

        # takes altitude in meters
        # returns typical pressure, density or temperature on demand
        # altitude: m
        # pressure: Pa
        # temp: degrees C

        if altitude < 11000:
            temp = -131.21 + 0.00299 * altitude
            press = 101330 * (1-((0.0065 * altitude)/(288.15)))**((9.807)/(286.9 * 0.0065))

        if 25000 > altitude >= 11000:
            temp = -56.46
            press = (22.65 * math.e ** (1.73 - 0.000157 * altitude)) * 1000

        if altitude >= 25000:
            temp = -131.21 + 0.00299 * altitude
            press = (2.488 * ((temp + 273.1)/(216.6))**(-11.388)) * 1000
        
        return press

    # VERY TERRIBLE approximation of drag force on the vessel
    def calc_drag(velocity, altitude):

        if get_value("drag_model_checkbox"):
            # drag_coeff = 0.1
            drag = (0.5 * alt2dens(altitude) * velocity**2 * drag_coeff * cross_sec) * -sign(velocity)
            dynamic_press = 0.5 * alt2dens(altitude) * velocity**2

            return drag, dynamic_press
        
        else:
            return 0.0, 0.0

    def calc_grav(altitude):
        gravity = 9.80665 * (6369000/(6369000+altitude))**2
        return gravity

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                   RUN SIMULATION
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    #set initial values
    
    alt = alt_init
    alt_g = 0
    thrust = mdot * eev + exit_area * (exit_pressure - alt2press(alt_init))
    mass = mass_init
    vel = 0
    accel = 0
    external_pressure = alt2press(alt_init)
    isp = (thrust)/(mdot * 9.80665)
    set_value(name="isp_min", value=isp)
    drag = 0
    dyn_press = 0
    density = alt2dens(alt_init)
    gravity = -calc_grav(alt_init)
    time = 0
    
    time_list = []
    alt_list = []
    vel_list = []
    accel_list = []
    ground_level_list = []
    karman_line_list = []
    thrust_list = []
    external_pressure_list = []
    gravity_list = []
    isp_list = []
    drag_list = []
    dyn_press_list = []
    density_list = []

    is_going_up = True
    is_accelerating_up = True
    is_launching = True

    show_item("progress_bar")
    progress_loop = 0

    # BEGIN TIMESTEPS
    
    while (True):

        # update visualizer ---

        vis_scale = float(get_value("vis_scale_field"))
        clear_drawing("vis_canvas")

        if not get_value("lock_on_rocket"):
            # sea
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,1,680,380), pmax=space2screen(340,1,680,380), color=[0,100,255,255])
            draw_text(drawing="vis_canvas", pos=[space2screen(-340,1,680,380)[0], space2screen(340,1,680,380)[1] - 14], text="Sea Level", size=14, color=[0,100,255,255])
            
            # ground
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,int(alt_init/vis_scale)+1,680,380), pmax=space2screen(340,int(alt_init/vis_scale)+1,680,380), color=[0,255,0,255])
            draw_text(drawing="vis_canvas", pos=[space2screen(-340,int(alt_init/vis_scale)+1,680,380)[0], space2screen(-340,int(alt_init/vis_scale),680,380)[1] - 14], text="Ground", size=14, color=[0,255,0,255])

            # rocket
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,int(alt/vis_scale)+1,680,380), pmax=space2screen(0,int(alt/vis_scale)+5,680,380), color=[200,0,0,255])

            # plume
            if is_accelerating_up:
                draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,int(alt/vis_scale)-2,680,380), pmax=space2screen(0,int(alt/vis_scale)+1,680,380), color=[200,150,10,255])

            # Karman line
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,int(100000/vis_scale),680,380), pmax=space2screen(340,int(100000/vis_scale),680,380), color=[255,100,255,128])
            draw_text(drawing="vis_canvas", pos=[space2screen(-340,int(100000/vis_scale),680,380)[0], space2screen(-340,int(100000/vis_scale),680,380)[1] - 14], text="Karman Line", size=14, color=[255,100,255,128])

        else:
            -int((alt/vis_scale))
            
            # sea
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340, 170-int(alt/vis_scale), 680, 380), pmax=space2screen(340, 170-int(alt/vis_scale), 680, 380), color=[0,100,255,255])
            draw_text(drawing="vis_canvas", pos=space2screen(-340, 170-int(alt/vis_scale)+14, 680, 380), text="Sea Level", size=14, color=[0,100,255,255])
            
            # ground
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340, 170-int((alt-alt_init)/vis_scale), 680, 380), pmax=space2screen(340, 170-int((alt-alt_init)/vis_scale), 680, 380), color=[0,255,0,255])
            draw_text(drawing="vis_canvas", pos=space2screen(-340, 170-int((alt-alt_init)/vis_scale)+14, 680, 380), text="Ground", size=14, color=[0,255,0,255])

            # rocket
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,170,680,380), pmax=space2screen(0,175,680,380), color=[200,0,0,255])

            # plume
            if is_accelerating_up:
                draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,165,680,380), pmax=space2screen(0,170,680,380), color=[200,150,10,255])

            # Karman line
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340, 170+int((100000-alt)/vis_scale), 680, 380), pmax=space2screen(340, 170+int((100000-alt)/vis_scale), 680, 380), color=[255,100,255,128])
            draw_text(drawing="vis_canvas", pos=space2screen(-340, 170+int((100000-alt)/vis_scale)+14, 680, 380), text="Karman Line", size=14, color=[255,100,255,128])
        # --- --- --- --- --- ---

        if progress_loop < 1.0:
            progress_loop = progress_loop + 0.01
        else:
            progress_loop = 0.0

        set_value(name="progress", value=progress_loop)
        setProgressBarOverlay("Simulation running...")

        if is_launching:

            # not enough thrust at lift-off!
            if thrust < (-gravity * mass_init):
                log_error("Not enough thrust - vehicle won't lift off.", logger = "Logs")
                delete_series(series="Altitude", plot="alt_plot")
                set_value(name="alt_max", value="Not enough thrust at launch. Simulation terminated.")
                set_value(name="vel_max", value="")
                set_value(name="flight_time", value="")
                return
            
            is_launching = False

        thrust_list.append(thrust)
        time_list.append(time)
        alt_list.append(alt)
        vel_list.append(vel)
        ground_level_list.append(alt_init)
        karman_line_list.append(100000)
        external_pressure_list.append(external_pressure)
        gravity_list.append(-gravity)
        accel_list.append(accel)
        isp_list.append(isp)
        drag_list.append(drag)
        dyn_press_list.append(dyn_press)
        density_list.append(density)

        density = alt2dens(alt)
        
        time = time + time_increment

        if mass > mass_final:
            thrust = mdot * eev + exit_area * (exit_pressure - external_pressure)
        else:
            thrust = 0

        gravity = -calc_grav(alt)
        
        external_pressure = alt2press(alt)

        # don't provide thrust if propellants are depleted!
        if mass > mass_final:      
            vel = vel + ((thrust/mass) * time_increment) + (gravity * time_increment) + (drag/mass * time_increment)
            mass = mass - mdot * time_increment
        else:
            vel = vel + gravity * time_increment + drag/mass * time_increment

        alt = alt + vel * time_increment
        alt_g = alt - alt_init
        accel = thrust/mass + gravity + drag/mass
        isp = (thrust)/(mdot * 9.80665)
        drag, dyn_press = calc_drag(vel, alt)

        if is_going_up and vel < 0:
            is_going_up = False
            alt_max = alt
            set_value(name="tt_apoapsis", value=time)
            set_value(name="alt_max", value=alt_max)
            set_value(name="max_Q", value=max(dyn_press_list))

        if is_accelerating_up and not mass > mass_final:
            is_accelerating_up = False
            vel_max = vel
            set_value(name="tt_max_vel", value=time)
            set_value(name="vel_max", value=vel_max)
            set_value(name="accel_max", value=accel)
            set_value(name="isp_max", value=isp)
            set_value(name="cutoff_time", value=time)

        # vehicle reached ground!
        if alt < alt_init:
            flight_time = time
            set_value(name="flight_time", value=flight_time)
            log_info("Simulation completed.", logger="Logs")
            if time_increment > 0.1:
                log_warning("Time increment too large. Last simulation may be inaccurate.", logger = "Logs")
                
            set_value(name="progress", value=0)
            hide_item("progress_bar")
            setProgressBarOverlay("")

            set_value(name="alt", value=alt_init)
            set_value(name="alt_g", value="IMPACT!")
            set_value(name="vel", value=vel)
            set_value(name="time", value=time)
            break

        t.sleep(time_increment)
        set_value(name="alt", value=alt)
        set_value(name="alt_g", value=alt_g)
        set_value(name="vel", value=vel)
        set_value(name="time", value=time)

        if get_value("realtime_graph"):
            add_line_series(name="Altitude", plot="alt_plot",x=time_list, y=alt_list)
            add_line_series(name="Velocity", plot="vel_plot",x=time_list, y=vel_list)
            add_line_series(name="Acceleration", plot="accel_plot",x=time_list, y=accel_list)
            add_line_series(name="Thrust", plot="thrust_plot",x=time_list, y=thrust_list)
            add_line_series(name="External Pressure", plot="ext_press_plot",x=time_list, y=external_pressure_list)
            add_line_series(name="Gravity", plot="grav_plot",x=time_list, y=gravity_list)
            add_line_series(name="Isp", plot="isp_plot", x=time_list, y=isp_list)
            add_line_series(name="Drag", plot="drag_plot", x=time_list, y=drag_list)
            add_line_series(name="Dynamic Pressure", plot="dyn_press_plot", x=time_list, y=dyn_press_list) 

    setProgressBarOverlay("Updating graphs...")
    add_line_series(name="Altitude", plot="alt_plot",x=time_list, y=alt_list)
    add_line_series(name="Velocity", plot="vel_plot",x=time_list, y=vel_list)
    add_line_series(name="Acceleration", plot="accel_plot",x=time_list, y=accel_list)
    add_line_series(name="Thrust", plot="thrust_plot",x=time_list, y=thrust_list)
    add_line_series(name="External Pressure", plot="ext_press_plot",x=time_list, y=external_pressure_list)
    add_line_series(name="Gravity", plot="grav_plot",x=time_list, y=gravity_list)
    add_line_series(name="Isp", plot="isp_plot", x=time_list, y=isp_list)
    add_line_series(name="Drag", plot="drag_plot", x=time_list, y=drag_list)
    add_line_series(name="Dynamic Pressure", plot="dyn_press_plot", x=time_list, y=dyn_press_list)
    #add_line_series(name="Density", plot="density_plot", x=time_list, y=density_list)

    global last_results
    last_results = [thrust_list, time_list, alt_list, vel_list, ground_level_list, karman_line_list, external_pressure_list, gravity_list, accel_list, isp_list, drag_list, dyn_press_list]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#                    USER INTERFACE
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def space2screen(space_x, space_y, screen_width, screen_height):
    
    screen_x = space_x + screen_width/2
    screen_y = -space_y + screen_height

    return [screen_x, screen_y]

# hacky function to update progress bar overlay text
# because dearpygui.simple doesn't have such a solution
def setProgressBarOverlay(overlay_str):
    internal_dpg.configure_item("progress_bar", overlay=overlay_str)

# toggle graph guidelines to aid the naked eye
def toggleGround():
    global is_ground_displayed
    if calc_run_number > 0:
        if is_ground_displayed:
            delete_series(series="Ground", plot="alt_plot")
            is_ground_displayed = False
        else:
            add_line_series(name="Ground", plot="alt_plot",x=last_results[1], y=last_results[4], color=[0, 255, 0, 255])
            is_ground_displayed = True
    else:
        log_warning("Run a calculation first!", logger = "Logs")

def toggleKarman():
    global is_karman_displayed
    if calc_run_number > 0:
        if is_karman_displayed:
            delete_series(series="Karman Line", plot="alt_plot")
            is_karman_displayed = False
        else:
            add_line_series(name="Karman Line", plot="alt_plot", x=last_results[1], y=last_results[5], color=[255, 0, 0, 255])
            is_karman_displayed = True
    else:
        log_warning("Run a calculation first!", logger = "Logs")

#FILE OPERATIONS BAR
with window("File I/O", width=1260, height=60, no_close=True, no_move=True):
    set_window_pos("File I/O", 10, 10)
    add_input_text(name="filepath_field", label="Filepath", tip = "If the file is in the same directory with the script, you don't need\nto write the full path.")
    add_same_line()
    add_button("Import", callback = importFile)
    add_same_line()
    add_progress_bar(name="progress_bar", source="progress", width=200, overlay="progress_overlay")
    hide_item("progress_bar")

#INPUTS WINDOW
with window("Input", width=550, height=360, no_close=True):   
    set_window_pos("Input", 10, 80)
    add_text("Enter parameters in float values.")
    add_spacing(count=6)
    add_input_text(name = "eev_field", label = "Effective Exhaust Vel. (m/s)")
    add_input_text(name = "mdot_field", label = "Mass Flow (kg/s)")
    add_input_text(name = "mass_init_field", label = "Initial Mass (kg)", tip="WET mass, not dry mass")
    add_input_text(name = "mass_final_field", label = "Final Mass (kg)", tip="Enter vehicle dry mass if all propellant will be used.")
    add_input_text(name = "alt_init_field", label = "Initial Altitude (m)")
    add_input_text(name = "exit_pressure_field", label = "Exhaust Exit Press. (Pa)")
    add_input_text(name = "exit_area_field", label = "Nozzle Exit Area (m^2)")
    add_input_text(name = "time_increment_field", label = "Time Increments (s)", tip="Enter lower values for higher precision.", default_value="0.01")
    add_spacing(count=6)
    add_button("Simulate Trajectory", callback = simulateTraj)
    add_same_line()
    add_checkbox(name = "realtime_graph", label = "Update graphs in real-time", tip="Looks really cool but reduces performance.")
    add_spacing(count=6)
    add_checkbox(name = "drag_model_checkbox", label = "Enable the terrible drag model", tip="DON'T TRUST THIS!")
    add_input_text(name = "cross_sec_field", label = "Vessel Cross Section (m^2)", tip="Cross-sec facing the airflow.")
    add_input_text(name = "drag_coeff_field", label = "Drag Coefficient")

#OUTPUTS WINDOW
with window("Output", width=700, height=560, no_close=True):
    set_window_pos("Output", 570, 80)

    add_input_text(name="alt_output", label="Altitude ASL (m)", source="alt", readonly=True, enabled=False)
    add_input_text(name="alt_g_output", label="Altitude AGL (m)", source="alt_g", readonly=True, enabled=False)
    add_input_text(name="vel_output", label="Velocity (m/s)", source="vel", readonly=True, enabled=False)
    add_input_text(name="time_output", label="Mission Elapsed Time (s)", source="time", readonly=True, enabled=False)

    add_tab_bar(name="graph_switch")
    end("graph_switch")
    add_tab(name="graphs_tab", label="Graphs", parent="graph_switch")
    end("graphs_tab")
    add_tab(name="vis_tab", label="Visualization", parent="graph_switch")
    end("vis_tab")
    
    add_tab_bar(name="output_tabs", parent="graphs_tab")
    end("output_tabs")
    add_tab(name="alt_tab", label="Altitude", parent="output_tabs")
    end("alt_tab")
    add_tab(name="vel_tab", label="Velocity", parent="output_tabs")
    end("vel_tab")
    add_tab(name="accel_tab", label="Acceleration", parent="output_tabs")
    end("accel_tab")
    add_tab(name="thrust_tab", label="Thrust", parent="output_tabs")
    end("thrust_tab")
    add_tab(name="ext_press_tab", label="Ext. Press", parent="output_tabs")
    end("ext_press_tab")
    add_tab(name="grav_tab", label="Gravity", parent="output_tabs")
    end("grav_tab")
    add_tab(name="isp_tab", label="Isp", parent="output_tabs")
    end("isp_tab")
    add_tab(name="drag_tab", label="Drag", parent="output_tabs")
    end("drag_tab")
    add_tab(name="dyn_press_tab", label="Dyn. Press.", parent="output_tabs")
    end("dyn_press_tab")
    #add_tab(name="density_tab", label="Density", parent="output_tabs")
    #end("density_tab")
    
    add_input_text(name = "tt_apoapsis_output_field", label = "Time to Apoapsis (s)",
                   source="tt_apoapsis", readonly=True, enabled=False, parent ="alt_tab")
    add_plot(name="alt_plot", label="Altitude vs Time",
             x_axis_name="Time (s)", y_axis_name = "Altitude (m)", anti_aliased=True, parent="alt_tab")
    add_button(name="karman_line_toggle", label="Toggle Karman Line", parent="alt_tab", callback=toggleKarman)
    add_button(name="ground_toggle", label="Toggle Ground", parent="alt_tab", callback=toggleGround)

    add_input_text(name = "tt_max_vel_output_field", label = "Time to Max. Velocity (s)",
                   source="tt_max_vel", readonly=True, enabled=False, parent ="vel_tab")
    add_plot(name="vel_plot", label="Velocity vs Time",
             x_axis_name="Time (s)", y_axis_name = "Velocity (m/s)", anti_aliased=True, parent="vel_tab")

    add_input_text(name = "max_accel_output_field", label = "Max. Acceleration (m/s^2)",
                   source="accel_max", readonly=True, enabled=False, parent ="accel_tab")
    add_plot(name="accel_plot", label="Acceleration vs Time",
             x_axis_name="Time (s)", y_axis_name = "Acceleration (m/s^2)", anti_aliased=True, parent="accel_tab")

    add_input_text(name = "cutoff_time_output_field", label = "Engine Cutoff Time (s)",
                   source="cutoff_time", readonly=True, enabled=False, parent ="thrust_tab")
    add_plot(name="thrust_plot", label="Thrust vs Time",
             x_axis_name="Time (s)", y_axis_name = "Thrust (N)", anti_aliased=True, parent="thrust_tab")

    add_plot(name="ext_press_plot", label="External Pressure vs Time",
             x_axis_name="Time (s)", y_axis_name = "Pressure (Pa)", anti_aliased=True, parent="ext_press_tab")

    add_plot(name="grav_plot", label="Gravity vs Time",
             x_axis_name="Time (s)", y_axis_name = "Gravity (m/s^2)", anti_aliased=True, parent="grav_tab")

    add_input_text(name = "min_isp_output_field", label = "Min. Isp (s)",
                   source="isp_min", readonly=True, enabled=False, parent ="isp_tab")
    add_input_text(name = "max_isp_output_field", label = "Max. Isp (s)",
                   source="isp_max", readonly=True, enabled=False, parent ="isp_tab")
    add_plot(name="isp_plot", label="Specific Impulse (Isp) vs Time",
             x_axis_name="Time (s)", y_axis_name = "Specific Impulse (s)", anti_aliased=True, parent="isp_tab")

    add_plot(name="drag_plot", label="Drag vs Time",
             x_axis_name="Time (s)", y_axis_name = "Drag (N)", anti_aliased=True, parent="drag_tab")

    add_input_text(name = "max_Q_field", label = "Max. Q at Launch (Pa)",
                   source="max_Q", readonly=True, enabled=False, parent ="dyn_press_tab", tip="Max Q on the way up.")
    add_plot(name="dyn_press_plot", label="Dynamic Pressure vs Time",
             x_axis_name="Time (s)", y_axis_name = "Dynamic Pressure (Pa)", anti_aliased=True, parent="dyn_press_tab")

    #add_plot(name="density_plot", label="Density vs Time",
    #         x_axis_name="Time (s)", y_axis_name = "Density (kg/m^3)", anti_aliased=True, parent="density_tab")


    #VISUALIZATION

    add_slider_float(name="vis_scale_field", label="Scale (m/pixel)",
                     min_value=1.0, max_value=750.0, default_value=15.0,
                     clamped=True, parent="vis_tab", width=300)

    add_same_line(parent="vis_tab")
    add_checkbox(name="lock_on_rocket", label="Lock View on Rocket", parent="vis_tab")

    add_drawing("vis_canvas", parent="vis_tab", width=680, height=380)
    clear_drawing("vis_canvas")
    draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,1,680,380), pmax=space2screen(340,1,680,380), color=[0,100,255,255])
    draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,1,680,380), pmax=space2screen(0,5,680,380), color=[200,0,0,255])

#LOG WINDOW
with window("Log", width=550, height=190, no_close=True):
    set_window_pos("Log", 10, 450)
    add_logger("Logs", log_level=0, autosize_x = True, autosize_y = True)

start_dearpygui()
