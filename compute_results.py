#!/usr/bin/python3

# this program reads a Oscar 2013 file (either from the SMASH or BHAC-QGP output) and writes in an output pickle file:
# a short information string about the other contents of the file
# the python dictionary with the considered hadrons (called hadrons, see later in this source file)
# number of sampling events (please, note that a freeze-out hypersurface can be sampled many times)
# the minimum transverse momentum pT allowed in dN/dy(y), v1(y) and v2(y) plots
# the maximum transverse momentum pT allowed in dN/dy(y), v1(y) and v2(y) plots
# the maximum absolute value of the rapidity in dN/dpT(pT), v1(pT) and v2(pT) plots
# the y rapidity bin array (central points)
# the pT transverse momentum bin array (central points)
# dy (the y bin width)
# dpT (the pT bin width)
# a 3D array with: hadron index, y, third index: average dN/dy(y) spectra, average v1(y), average v2(y)
# a 3D array with: hadron index, pT, third index: average dN/dpT(pT) spectra, average v1(pT), average v2(pT)
# The indexes of the hadrons are specified in the hadron dictionary, see the source file below.

import argparse
from datetime import date, datetime
import math
import numpy as np
import os
import sys
import pickle

# rapidity cut for dN/dpT
rap_cut = 1000

# minimum transverse momentum cut for dN/dy
pT_min_cut = 0.
# maximum transverse momentum cut for dN/dy
pT_max_cut = 1000

# rapidity resolution (dy)
rap_resolution = 0.2
# max rapidity (absolute value), referred to the border of the bin
# please, notice the the actual used value will be rounded so to have an integer number of cells,
# with  0 as the midpoint of the central cell
max_rapidity = 5.1

# pT resolution (dpT)
pT_resolution = 0.1
# max pT, referred to the border of the bin
# please, notice the the actual used value will be rounded so to have an integer number of cells
max_pT = 4

#################

hadrons = {"211":(0,"pion_plus"),\
           "-211":(1,"pion_minus"),\
           "111":(2,"pion_0"),\
           "321":(3,"kaon_plus"),\
           "-321":(4,"kaon_minus"),\
           "2212":(5,"proton"),\
           "-2212":(6,"anti-proton"),\
           "2112":(7,"neutron"),\
           "-2112":(8,"anti-neutron"),\
          }

parser = argparse.ArgumentParser(description='A scripts that computes dN/dy and dN/dpT of selected hadrons from Oscar 2013 output files')

parser.add_argument('--output', '-o', help='Path to the output file (pickle format). Default is "./output.pickle".', default="./output.pickle")
parser.add_argument('--type', '-t', help='Oscar format type: "SMASH" or "BHAC-QGP". Default is "SMASH",', default="SMASH")
parser.add_argument('inputs', nargs='+', help='Oscar 2013 input files')
parser.add_argument("--verbose", '-v', help="increase output verbosity", action="store_true")

args = parser.parse_args()

if args.verbose:
    verbose = True
else:
    verbose = False

if (args.type == "SMASH"):
    pdg_idx = 9
    mom_start = 5
    mom_end =  mom_start + 4
    event_name_identifier = "event"
    event_start_identifier = "out"
    event_end_identifier = "end"
elif (args.type == "BHAC-QGP"):
    pdg_idx = 8
    mom_start = 4
    mom_end = mom_start + 4
    event_name_identifier = "Event"
    event_start_identifier = "start"
    event_end_identifier = "end"
else:
    print("Oscar format type unknown. It can be either SMASH or BHAC-QGP.")
    sys.exit(1)

outputfile = args.output

nh = len(hadrons)

dy = rap_resolution

dpT = pT_resolution

ny = int(2*max_rapidity/dy) + 1

npT = int(max_pT/pT_resolution)

y_arr = np.linspace(-ny*dy/2 + dy/2, ny*dy/2 - dy/2, num = ny)

pT_arr = np.linspace(0+dpT/2, npT*dpT-dpT/2, num = npT)

y_spectra = np.zeros((nh,ny,3),dtype=np.float64)

pT_spectra = np.zeros((nh,npT,3),dtype=np.float64)

total_events = 0

# format for quantities in output file
cf='{:7.3f}'
ff='{:16.12e}'
sp="    "

# third indexes of multidimensional arrays with results
dN_idx = 0
v1_idx = 1
v2_idx = 2

def extract_data_oscar(infile, y_arr, pT_arr, dy, dpT):
    unfinished_event = False
    y_start = y_arr[0] - dy/2
    pT_start = pT_arr[0] - dpT/2
    with open(infile,"r") as ifile:

        # we count the hadrons event by event and we add them only if the event is complete
        events_in_file = np.int64(0) 
        y_spectra_event = np.zeros((nh,ny,3),dtype=np.float64)
        pT_spectra_event = np.zeros((nh,npT,3),dtype=np.float64)
        y_spectra_file = np.zeros((nh,ny,3),dtype=np.float64)
        pT_spectra_file = np.zeros((nh,npT,3),dtype=np.float64)

        for iline in ifile:
 
            line = iline.split()
            if (line[0][0] == "#"):
                if (line[1] == event_name_identifier):
                    if (line[3] == event_start_identifier):
                        unfinished_event = True
                    elif (line[3] == event_end_identifier):
                        if unfinished_event:
                            unfinished_event = False
                            events_in_file += 1
                            y_spectra_file += y_spectra_event
                            y_spectra_event.fill(0)
                            pT_spectra_file += pT_spectra_event
                            pT_spectra_event.fill(0)                 
                            if verbose:
                                print("Read event in file number: " + str(events_in_file))
                        else:
                            print("Error, detected end of event without detecting its beginning")
                            sys.exit(1)
                    else:
                        print("Error, unkown event label: " + line[3])
                        sys.exit(1)
                continue
        
            pdg_ID = line[pdg_idx]
            if (pdg_ID in hadrons):
                hadron_index = hadrons[pdg_ID][0]                
            else:
                continue
            t, x, y, z = np.float64(line[0:4])
            p0, px, py, pz = np.float64(line[mom_start:mom_end])

            if (((p0 - pz)*(p0 + pz)) <= 0):
                continue
            rapidity = 0.5 * math.log((p0+pz)/(p0-pz))
            pT2 = px**2 + py**2
            if (pT2 == 0):
                continue
            pT = math.sqrt(pT2)
            v1 = px / pT
            v2 = (px**2 - py**2) / pT2
            
            rapidity_index = int(math.floor((rapidity - y_start)/dy))
            
            if ((rapidity_index >= 0) and (rapidity_index < ny) and (pT >= pT_min_cut) and (pT < pT_max_cut)):
                y_spectra_event[hadron_index, rapidity_index, dN_idx] += 1
                y_spectra_event[hadron_index, rapidity_index, v1_idx] += v1
                y_spectra_event[hadron_index, rapidity_index, v2_idx] += v2
 
            pT_index = int(math.floor((pT - pT_start)/dpT))

            if ((pT_index >= 0) and (pT_index < npT) and (abs(rapidity) < rap_cut)):
                pT_spectra_event[hadron_index, pT_index, dN_idx] += 1
                pT_spectra_event[hadron_index, pT_index, v1_idx] += v1
                pT_spectra_event[hadron_index, pT_index, v2_idx] += v2
              
    return events_in_file, y_spectra_file, pT_spectra_file

if os.path.exists(outputfile):
    current_date = datetime.now()
    date_string = current_date.strftime("%Y-%m-%d-%H-%M-%S")
    new_name_for_old_outputfile = outputfile + "_backup_copy_" + date_string
    os.rename(outputfile, new_name_for_old_outputfile)
    
for infile in args.inputs:
    new_events, new_y_spectra, new_pT_spectra = extract_data_oscar(infile, y_arr, pT_arr, dy, dpT)
    if new_events == None:
        print("Warning, error detected when reading " + infile + ", file discarded.")
        continue
    if new_events == 0:
        print("Warning, 0 events found in " + infile + ", file unused.")
        continue
    total_events += new_events
    y_spectra += new_y_spectra
    pT_spectra += new_pT_spectra

if total_events == 0:
    print("Sorry, something went wrong, I collected 0 events...")
    sys.exit(2)
    
# now we print the results

with open(outputfile,"wb") as outf:
    info_results = "The pickled file contains a tuple with:\n"
    info_results += "0 this information string\n"
    info_results += "1 the dictionary of the considered hadrons"
    info_results += "2 the total number of sampling events (numpy int64)\n"
    info_results += "3 the minimum transverse momentum pT allowed in dN/dy plots\n"
    info_results += "4 the maximum transverse momentum pT allowed in dN/dy plots\n"
    info_results += "5 the maximum absolute value of the rapidity in dN/dpT plots\n"
    info_results += "6 the y rapidity bin array (central points)\n"
    info_results += "7 the pT transverse momentum bin array (central points)\n"
    info_results += "8 the y bin width dy\n" 
    info_results += "9 the pT bin width dpT\n" 
    info_results += "10 the total dN vs dy yields (not averaged by events, not divided by dy), v1 and v2 total sum (float 64 array)\n"
    info_results += "11 the total dN vs dpT yields (not averaged by events, not divided by dpT), v1 and v2 total sum (float 64 array)\n"
    info_results += "The 3D arrays have dimensions: number of hadrons, length of rapidity or pT array, 3 (dN, v1, v2)\n\n"

    pickle.dump((info_results, hadrons, total_events, pT_min_cut, pT_max_cut, rap_cut, y_arr, pT_arr, dy, dpT, y_spectra, pT_spectra),outf)
