############################################################################################################
#NAME: run_assembly.py
#AUTHOR: Christophe Van den Eynde
#FUNCTION: creates some texts files containing location variables that are used by the snakefile as input
#USAGE: pyhton3 get_enviroment.py
############################################################################################################

#TIMER START================================================================================================
import datetime
start = datetime.datetime.now()
#===========================================================================================================

#IMPORT PACKAGES============================================================================================
import os
import platform
import subprocess
import string
from datetime import date
from pathlib import Path
import shutil
import sys
#===========================================================================================================

#GENERAL====================================================================================================
print("Please wait while the Script fetches some system info:")
#FETCH OS-TYPE----------------------------------------------------------------------------------------------
system=platform.system()
if "Windows" in system:
    system = "Windows"
    print("  - Windows based system detected ({})".format(system))
    # check if HyperV is enabled (indication of docker Version, used to give specific tips on preformance increase)
    HV = subprocess.Popen('powershell.exe get-service | findstr vmcompute', shell=True, stdout=subprocess.PIPE) 
    for line in HV.stdout:  
        if "Running" in line.decode("utf-8"):
            HyperV="True" 
        else: 
            HyperV="False"
elif "Darwin" in system:
    system = "MacOS"
    print("  - MacOS based system detected ({})".format(system))
else:
    system = "UNIX"
    print("  - UNIX based system detected ({})".format(system))
#LINUX OS: GET USER ID AND GROUP ID-------------------------------------------------------------------------
# if system == "UNIX":
#     UID = subprocess.Popen('id -u', shell=True, stdout=subprocess.PIPE)
#     for line in UID.stdout:
#         UID = line.decode("utf-8")
#     GID = subprocess.Popen('id -g', shell=True, stdout=subprocess.PIPE) 
#     for line in GID.stdout:
#         GID = line.decode("utf-8")
#     options["Group"] = UID+":"+GID
#===========================================================================================================

# GET MAX THREADS===========================================================================================
    # For windows, the threads avaible to docker are already limited by the virtualisation program. 
    # This means that the total ammount of threads avaiable on docker is only a portion of the threads avaiable to the host
    # --> no extra limitation needed
    # Linux/Mac doesn't use a virutalisation program.
    # The number of threads available to docker should be the same as the total number of threads available on the HOST
    # --> extra limitation is needed in order to not slow down the PC to much (reserve CPU for host)
# TOTAL THREADS OF HOST-------------------------------------------------------------------------------------
print("  - Fetching amount of threads on system")
if system == "Windows":
    host = subprocess.Popen('WMIC CPU Get NumberOfLogicalProcessors', shell=True, stdout=subprocess.PIPE)
elif system == "MacOS":
    host = subprocess.Popen('sysctl -n hw.ncpu', shell=True, stdout=subprocess.PIPE)
else:
    host = subprocess.Popen('nproc --all', shell=True, stdout=subprocess.PIPE)

for line in host.stdout:
    # linux only gives a number, Windows gives a text line + a number line
    if any(i in line.decode("UTF-8") for i in ("0","1","2","3","4","5","6","7","8","9")):
        h_threads = int(line.decode("UTF-8"))
# MAX THREADS AVAILABLE IN DOCKER----------------------------------------------------------------------------
docker = subprocess.Popen('docker run -it --rm --name ubuntu_bash christophevde/ubuntu_bash:v2.0_stable nproc --all', shell=True, stdout=subprocess.PIPE)
for line in docker.stdout:
    d_threads = int(line.decode("UTF-8"))
# SUGESTED THREADS FOR ANALYSIS CALCULATION-----------------------------------------------------------------
if system=="UNIX":
    if h_threads < 5:
        s_threads = h_threads//2
    else:
        s_threads = h_threads//4*3
else:
    s_threads = d_threads
print("Done\n")
#===========================================================================================================

#FUNCTIONS==================================================================================================
#SETTINGS FILE PARSING--------------------------------------------------------------------------------------
def settings_parse(settings):
    file = open(settings,'r')
    global options
    options = {}
    for line in file:
        if  "Illumina=" in line:
            options["Illumina"] = line.replace('Illumina=','').replace('\n','')
        elif "MinIon=" in line:
            options["MinIon"] = line.replace('MinIon=','').replace('\n','')
        elif "Results=" in line:
            options["Results"] = line.replace('Results=','').replace('\n','')
        elif "Adaptors=" in line:
            options["Adaptors"] = line.replace('Adaptors=','').replace('\n','')
        elif "Barcode_kit=" in line:
            options["Barcode_kit"] = line.replace('Barcode_kit=','').replace('\n','')
        elif "Threads=" in line:
            options["Threads"] = line.replace('Threads=','').replace('\n','')
        elif "Start_genes" in line:
            options["Start_genes"] = line.replace('Start_genes=','').replace('\n','')
    options["Run"] = date.today().strftime("%Y%m%d")
    options["Scripts"] = os.path.dirname(os.path.realpath(__file__))
    file.close()
    return options
#PATH CORRECTION--------------------------------------------------------------------------------------------
def correct_path(dictionairy):
    global options
    options_copy = dictionairy
    options = {}
    not_convert = ["Threads", "Run", "Analysis", "Group", "Barcode_kit", "Genus", "Species", "Kingdom"]
    if system == "Windows":
        print("\nConverting Windows paths for use in Docker:")
        for key, value in options_copy.items():
            options[key] = value
            for i in list(string.ascii_lowercase+string.ascii_uppercase):
                options[key] = value
                if value.startswith(i+":/"):
                    options[key+"_m"] = value.replace(i+":/","/"+i.lower()+"//").replace('\\','/')
                elif value.startswith(i+":\\"):
                    options[key+"_m"] = value.replace(i+":\\","/"+i.lower()+"//").replace('\\','/')
            print(" - "+ key +" location ({}) changed to: {}".format(str(options[key]),str(options[key+"_m"])))
    else:
        print("\nUNIX paths shouldn't require a conversion for use in Docker:")
        for key, value in options_copy.items():
            options[key] = value
            if not key in not_convert:
                options[key+"_m"] = value
                print(" - "+ key +" location ({}) changed to: {}".format(str(options[key]),str(options[key+"_m"])))
        return options
#SAVING INPUT TO FILE---------------------------------------------------------------------------------------
#SHORT READ SAMPLE LIST CREATION----------------------------------------------------------------------------
def sample_list(Illumina):
    global ids
    ids =[]
    for sample in os.listdir(Illumina):
        if ".fastq.gz" in sample:
            ids.append(sample.replace('_L001_R1_001.fastq.gz','').replace('_L001_R2_001.fastq.gz',''))
    ids = sorted(set(ids))
    return ids
#===========================================================================================================

#LONG READ ONLY ASSEMBLY====================================================================================
options = {}
#ERROR COLLECTION-------------------------------------------------------------------------------------------
errors = []
error_count = 0
while error_count == 0:
#GET INPUT--------------------------------------------------------------------------------------------------
    print("\n[LONG READ ASSEMBLY] SETTINGS"+"="*71)
    try:
        settings = sys.argv[2]
    except:
#ASK FOR SETTINGS FILE----------------------------------------------------------------------------------
        question = input("Do you have a premade settings-file that you want to use? (y/n) \
            \nPress 'n' to automatically create your own settings-file using the questions asked by this script: ").lower()
        if question == "y":
            settings = input("\nInput location of settings-file here: \n")
    #PARSE FILE
            print("\nParsing settings file")
            settings_parse(settings)
            #convert paths if needed --> function
            #append converted paths to settings-file --> function
            print("Done")
        elif question == "n":
#REQUIRED INPUT----------------------------------------------------------------------------------------
            settings = ''
            print("\nLONG READS"+'-'*90)
            options["MinIon"] = input("Input location of MinIon sample files here: \n")   
            print("\nRESULTS"+'-'*93)
            options["Results"] = input("Input location to store the results here \n")
            options["Scripts"] = os.path.dirname(os.path.realpath(__file__))
            options["Run"] = date.today().strftime("%Y%m%d")
#OPTIONAL INPUT----------------------------------------------------------------------------------------
            print("\n[LONG READS ASSEMBLY] OPTIONAL SETTINGS"+"="*61)
            advanced = input("Show optional settings? (y/n): ").lower()
            if advanced == "y" or advanced =="yes":
                options["Start_genes"] = input("\nInput location of multifasta containing start genes to search for: \n")
                options["Barcode_kit"] = input("Input the ID of the used barcoding kit: \n")
    #THREADS------------------------------------------------------------------------------------------
                print("\nTotal threads on host: {}".format(h_threads))
                print("Max threads in Docker: {}".format(d_threads))
                print("Suggest ammount of threads to use in the analysis: {}".format(s_threads))
                options["Threads"] = input("\nInput the ammount of threads to use for the analysis below.\
                \nIf you want to use the suggested ammount, just press ENTER (or type in the suggested number)\n")
                if options["Threads"] =='':
                    options["Threads"] = str(s_threads)
                    print("\nChosen to use the suggested ammount of threads. Reserved {} threads for Docker".format(options["Threads"]))
                else:
                    print("\nManually specified the ammount of threads. Reserved {} threads for Docker".format(options["Threads"]))
#CREATE REQUIRED FOLDERS IF NOT EXIST-----------------------------------------------------------------------
    folders = [options["Results"]+"/Long_reads/"+options["Run"],]
    for i in folders:
        os.makedirs(i, exist_ok=True)
#CONVERT MOUNT_PATHS (INPUT) IF REQUIRED--------------------------------------------------------------------
    correct_path(options)
#SAVE INPUT TO FILE-----------------------------------------------------------------------------------------
#If SETTINGS FILE PROVIDED: APPEND CONVERTED PATHS------------------------------------------------------
    if not settings == '':
    #read content of file (apparently read&write can't happen at the same time)
        loc = open(settings, 'r')
        content = loc.read()
    #print(content)
        loc.close()
    #append converted paths to file
        loc = open(settings, 'a')
        if not "#CONVERTED PATHS" in content:
            loc.write("\n\n#CONVERTED PATHS"+'='*92)
            for key, value in options.items():
                if not key in content:
                    if key == "Illumina_m" or key == "MinIon_m" or key == "Results_m" or key == "Start_genes_m":
                        loc.write('\n'+key+'='+value)
            loc.write("\n"+'='*108)          
        loc.close()
#IF NO SETTINGS FILE PROVIDED: WRITE ALL TO FILE---------------------------------------------------------
    else:
        loc = open(options["Results"]+"/Long_reads/"+options["Run"]+"/environment.txt", "w")
        for key, value in options.items():
            if not key == "Threads":
                loc.write(key+"="+value+"\n")
            else:
                loc.write(key+"="+value)  
        loc.close()
#MOVE (AND RENAME) ... TO ... FOLDER------------------------------------------------------------------------
    shutil.copy(options["Start_genes"], options["Results"]+"/Long_reads/"+options["Run"]+"/start_genes.fasta")
    #settings-file to results-folder
#LONG READS: DEMULTIPLEXING (GUPPY)-------------------------------------------------------------------------
    print("\n[STARTING] Long read assembly: preparation")
    print("\nDemultiplexing Long reads")
    my_file = Path(options["Results"]+"/Long_reads/"+options["Run"]+"/01_Demultiplex/barcoding_summary.txt")
    if not my_file.is_file():
        #file doesn't exist -> guppy demultiplex hasn't been run
        if system == "UNIX":
            os.system("dos2unix -q "+options["Scripts"]+"/01_demultiplex.sh")
        os.system('sh ./Scripts/01_demultiplex.sh '\
            +options["MinIon"]+'/fastq/pass '\
            +options["Results"]+' '\
            +options["Run"]+' '\
            +options["Threads"])
        print("Done")
        if not my_file.is_file():
            errors.append("[ERROR] STEP 1: Guppy demultiplexing failed")
            error_count +=1
    else:
        print("Results already exist, nothing to be done")
#LONG READS: QC (PYCOQC)------------------------------------------------------------------------------------
    print("\nPerforming QC on Long reads")
    if not os.path.exists(options["Results"]+"/Long_reads/"+options["Run"]+"/02_QC/"):
        os.makedirs(options["Results"]+"/Long_reads/"+options["Run"]+"/02_QC/")
    my_file = Path(options["Results"]+"/Long_reads/"+options["Run"]+"/02_QC/QC_Long_reads.html")
    if not my_file.is_file():
        #file doesn't exist -> pycoqc hasn't been run
        if system == "UNIX":
            os.system("dos2unix -q "+options["Scripts"]+"/02_pycoQC.sh") 
        os.system('sh ./Scripts/02_pycoQC.sh '\
            +options["MinIon"]+'/fast5/pass '\
            +options["Results"]+'/Long_reads/'+options["Run"]+' '\
            +options["Threads"])
        print("Done")
        if not my_file.is_file():
            errors.append("[ERROR] STEP 2: PycoQC quality control failed")
            error_count +=1
    else:
        print("Results already exist, nothing to be done")
#LONG READS: DEMULTIPLEXING + TRIMMING (PORECHOP)-----------------------------------------------------------
    print("\nTrimming Long reads")
    my_file = Path(options["Results"]+"/Long_reads/"+options["Run"]+"/02_QC/demultiplex_summary.txt")
    if not my_file.is_file():
        #file doesn't exist -> porechop trimming hasn't been run
        if system == "UNIX":
            os.system("dos2unix -q "+options["Scripts"]+"/03_Trimming.sh")
        #demultiplex correct + trimming 
        os.system('sh '+options["Scripts"]+'/03_Trimming.sh '\
            +options["Results"]+'/Long_reads/'+options["Run"]+'/01_Demultiplex '\
            +options["Results"]+' '\
            +options["Run"]+' '\
            +options["Threads"])
        #creation of summary table of demultiplexig results (guppy and porechop)
        os.system("python3 "+options["Scripts"]+"/04_demultiplex_compare.py "\
            +options["Results"]+"/Long_reads/"+options["Run"]+"/01_Demultiplex/ "\
            +options["Results"]+"/Long_reads/"+options["Run"]+"/03_Trimming/ "\
            +options["Results"]+"/Long_reads/"+options["Run"]+"/02_QC/")
        if not my_file.is_file():
            errors.append("[ERROR] STEP 3: Porechop demuliplex correction and trimming failed")
            error_count +=1
    else:
        print("Results already exist, nothing to be done")
    print("[COMPLETED] Hybrid assembly preparation: Long reads")
#LONG READ ASSEMBLY--------------------------------------------------------------------------------------------
    if system == "UNIX":
        os.system("dos2unix -q "+options["Scripts"]+"/05_Unicycler.sh")
    print("\n[STARTING] Unicycler: Long read assembly")
    for bc in os.listdir(options["Results"]+"/Long_reads/"+options["Run"]+"/03_Trimming/"):
        bc = bc.replace('.fastq.gz','')
        if "BC" in bc:
            print("Starting assembly for barcode: "+bc)
            my_file = Path(options["Results"]+"/Long_reads/"+options["Run"]+"/04_Assembly/"+bc+"/assembly.fasta")
            if not my_file.is_file():
                #file doesn't exist -> unicycle hasn't been run
                os.system('sh ./Scripts/05_Unicycler.sh '\
                    +options["Results"]+'/Long_reads/'+options["Run"]+' '\
                    +bc+' '\
                    +options["Threads"])
                if not my_file.is_file():
                    errors.append("[ERROR] STEP 4: Unicycler assembly failed")
                    error_count +=1
            else:
                print("Results already exist for barcode: "+bc+", nothing to be done")
#BANDAGE----------------------------------------------------------------------------------------------------
    print("Bandage is an optional step used to visualise and correct the created assemblys, and is completely manual")
    Bandage = input("Do you wan't to do a Bandage visualisalisation? (y/n)").lower()
    if Bandage == "y":
        Bandage_done = input("[WAITING] If you're done with Bandage input 'y' to continue: ").lower()
        while Bandage_done != 'y':
            Bandage_done = input("[WAITING] If you're done with Bandage input 'y' to continue: ").lower()
    elif Bandage == "n":
        print("skipping Bandage step")
#PROKKA-----------------------------------------------------------------------------------------------------
    if system == "UNIX":
        os.system("dos2unix -q "+options["Scripts"]+"/06_Prokka.sh")
    print("\n[STARTING] Prokka: Long read assembly annotation")
    for sample in os.listdir(options["Results"]+"/Long_reads/03_Assembly/"):
        my_file = Path(options["Results"]+"/Long_reads/04_Prokka/"+sample+"/*.gff")
        if not my_file.is_file():
            os.system('sh '+options["Scripts"]+'/06_Prokka.sh '\
                +options["Results"]+'/Long_reads/04_Prokka/'+sample+' '\
                +options["Genus"]+' '\
                +options["Species"]+' '\
                +options["Kingdom"]+' '\
                +options["Results"]+'/Long_reads/03_Assembly/'+sample+'/assembly.fasta '\
                +options["Threads"])
            if not my_file.is_file():
                errors.append("[ERROR] STEP 6: Prokka annotation failed")
                error_count +=1
        else:
            print("Results already exist for "+sample+", nothing to be done")
#ERROR DISPLAY----------------------------------------------------------------------------------------------
if error_count > 0:
    print("[ERROR] Assembly failed, see message(s) below to find out where:")
    for error in errors:
        print(error)
#===========================================================================================================

#TIMER END==================================================================================================
end = datetime.datetime.now()
timer = end - start
#CONVERT TO HUMAN READABLE----------------------------------------------------------------------------------
print("Analysis took: {} (H:MM:SS) \n".format(timer))
#===========================================================================================================