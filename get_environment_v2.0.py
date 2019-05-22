############################################################################################################
#NAME:  get_enviroment.py
#AUTHOR: Christophe Van den Eynde
#FUNCTION: creates some texts files containing location variables that are used by the snakefile as input
#USAGE: pyhton3 get_enviroment.py
############################################################################################################

#TIMER START================================================================================================
import datetime
start = datetime.datetime.now()
#===========================================================================================================

# GET LOCATIONS=============================================================================================
# input directory (rawdata)----------------------------------------------------------------------------------
import os
print("LOCATION INFO"+"-"*50)
print("Before submitting the rawdata location, please check wheter upper and lower case letters are correct")
print("Please also check if there are spaces in your path, this will give an error at the moment (I'm trying to get this fixed)")
print("Windows users using 'Docker-toolbox': \nIt's advised to have the rawdata on the C-drive before the analysis, otherwise there might be problems finding the location")
rawdata = input("\nInput the full path/location of the folder with the raw-data to be analysed:\n")

# get current directory-------------------------------------------------------------------------------------
location = os.getcwd()
#===========================================================================================================

# PATH CORRECTION===========================================================================================
#check for spaces in the paths------------------------------------------------------------------------------
if ' ' in rawdata:
    print("\nERROR: spaces found in the path to the rawdata\n")
elif ' ' in location:
    print("\nERROR: spaces found in the path to the current location\n")
else: 
#-----------------------------------------------------------------------------------------------------------

#find system-type-------------------------------------------------------------------------------------------
    import platform
    system=platform.platform()
#-----------------------------------------------------------------------------------------------------------

# fix the path if system is Windows-------------------------------------------------------------------------
    import string
    if "Windows" in system:
        print("\nWindows based system detected ({}), converting paths for use in Docker:".format(system))
        sys="Windows"
        for i in list(string.ascii_lowercase+string.ascii_uppercase):
            if rawdata.startswith(i+":/"):
                rawdata_m = rawdata.replace(i+":/","/"+i.lower()+"//").replace('\\','/')
            elif rawdata.startswith(i+":\\"):
                rawdata_m = rawdata.replace(i+":\\","/"+i.lower()+"//").replace('\\','/')
            if location.startswith(i+":/"):
                location_m = location.replace(i+":/","/"+i.lower()+"//").replace('\\','/')
            elif location.startswith(i+":\\"):
                location_m = location.replace(i+":\\","/"+i.lower()+"//").replace('\\','/')
        print(" - Raw-data location ({}) changed to: {}".format(rawdata,rawdata_m))
        print(" - Current location ({}) changed to: {}".format(location,location_m))
# ----------------------------------------------------------------------------------------------------------

# keeping paths as they are if system isn't Windows---------------------------------------------------------
    else:
        sys="UNIX"
        rawdata_m = rawdata
        location_m = location
        print("\nUNIX based system detected ({}), paths shouldn't require a conversion for use in Docker:".format(system))
        print(" - rawdata={}".format(rawdata))
        print(" - Current location={}".format(location))
    print("-"*63)
#-----------------------------------------------------------------------------------------------------------

# create location/data--------------------------------------------------------------------------------------
    if not os.path.exists(location+"/data"):
        os.mkdir(location+"/data/")
#-----------------------------------------------------------------------------------------------------------

# CREATE SAMPLE LIST========================================================================================
# read directory content------------------------------------------------------------------------------------
    ids =[]
    for sample in os.listdir(rawdata):
        ids.append(sample.replace('_L001_R1_001.fastq.gz','').replace('_L001_R2_001.fastq.gz',''))
    ids = sorted(set(ids))
#-----------------------------------------------------------------------------------------------------------

# writhing samplelist.txt-----------------------------------------------------------------------------------
    file = open(location+"/data/sampleList.txt",mode="w")
    for i in ids:
        file.write(i+"\n")
    file.close()
#===========================================================================================================

# GET MAX THREADS===========================================================================================
# For windows, the threads avaible to docker are already limited by the virtualisation program. 
# This means that the total ammount of threads avaiable on docker is only a portion of the threads avaiable to the host
    # --> no extra limitation needed
# Linux/Mac doesn't use a virutalisation program.
# The number of threads available to docker should be the same as the total number of threads available on the HOST
    # --> extra limitation is needed in order to not slow down the PC to much (reserve CPU for host)
    print("\nFetching system info (number of threads) please wait for the next input screen, this shouldn't take long\n")

# MAX THREADS AVAILABLE IN DOCKER----------------------------------------------------------------------------
    import subprocess
    docker = subprocess.Popen('docker run -it --rm --name ubuntu_bash christophevde/ubuntu_bash:v2.0_stable nproc --all', shell=True, stdout=subprocess.PIPE)
    for line in docker.stdout:
        d_threads = int(line.decode("UTF-8"))
#-----------------------------------------------------------------------------------------------------------

# TOTAL THREADS OF HOST-------------------------------------------------------------------------------------
    if sys == "Windows":
        host = subprocess.Popen('WMIC CPU Get NumberOfLogicalProcessors', shell=True, stdout=subprocess.PIPE)
        # check if HyperV is enabled (indication of docker Version, used to give specific tips on preformance increase)
        HV = subprocess.Popen('powershell.exe get-service | findstr vmcompute', shell=True, stdout=subprocess.PIPE) 
        for line in HV.stdout:  
            if "Running" in line.decode("utf-8"):
                HyperV="True" 
            else: 
                HyperV="False" 
    else:
        host = subprocess.Popen('nproc --all', shell=True, stdout=subprocess.PIPE)

    for line in host.stdout:
        # linux only gives a number, Windows gives a text line + a number line
        if any(i in line.decode("UTF-8") for i in ("0","1","2","3","4","5","6","7","8","9")):
            h_threads = int(line.decode("UTF-8"))
            #print(h_threads)
        #print("line="+line.decode("UTF-8"))
#-----------------------------------------------------------------------------------------------------------

# SUGESTED THREADS FOR ANALYSIS CALCULATION----------------------------------------------------------------------
    if sys=="UNIX":
        if h_threads < 5:
            s_threads = h_threads//2
        else:
            s_threads = h_threads//4*3
    else:
        s_threads = d_threads
#-----------------------------------------------------------------------------------------------------------

# ASK USER FOR THREADS TO USE-------------------------------------------------------------------------------
# give advanced users the option to overrule the automatic thread detection and specify the ammount themself
# basic users can just press ENTER to accept the automatically sugested ammount of threads

    print("ANALYSIS OPTIONS"+"-"*47)
    print("Total threads on host: {}".format(h_threads))
    print("Max threads in Docker: {}".format(d_threads))
    print("Suggest ammount of threads to use in the analysis: {}".format(s_threads))
    if sys=="Windows":
        print("\nTIP to increase performance (make more threads available to docker)")
        if HyperV=="True":
            print("  1) Open the settings menu of 'Docker Desktop'")
            print("  2) Go to the advanced tab")
            print("  3) Increase the CPU and RAM (memory) available to Docker by moving the corresponding sliders.")
            print("     It's advised to keep some CPU and RAM reserved for the host system") 
        else:
            print("  1) Open Oracle Virtual Box")
            print("  2) Select the Docker virtual image")
            print("  3) Click on the cogwheel (settings)")
            print("  4) Open the system menu")
            print("  5) Increase basic memory by moving the slider (keep the slider in the green part)")
            print("  6) Go to the processor tab in the system menu ")
            print("  7) Increase available CPu by moving the slider (keep the slider in the green part)")
    threads = input("\nInput the ammount of threads to use for the analysis below.\
    \nIf you want to use the suggested ammount, just press ENTER (or type in the suggested number)\n")
    if threads =='':
        threads = s_threads
        print("\nChosen to use the suggested ammount of threads. Reserved {} threads for Docker".format(threads))
    else:
        print("\nManually specified the ammount of threads. Reserved {} threads for Docker".format(threads))
    print("-"*63+"\n")
#===========================================================================================================

# WRITE ALL HOST INFO TO FILE===============================================================================
    loc = open(location+"/environment.txt", mode="w")
    loc.write("rawdata="+rawdata+"\n")
    loc.write("rawdata_m="+rawdata_m+"\n")
    loc.write("location="+location+"\n")
    loc.write("location_m="+location_m+"\n")
    loc.write("threads="+str(threads))
    loc.close()
#===========================================================================================================

# EXECUTE SNAKEMAKE DOCKER==================================================================================
    cmd = 'docker run -it --rm \
        --name snakemake \
        --cpuset-cpus="0" \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v '+rawdata_m+':/home/rawdata/ \
        -v '+location_m+':/home/Pipeline/ \
        christophevde/snakemake:v2.0_stable \
        /bin/bash -c "cd /home/Snakemake/ && snakemake; /home/Scripts/copy_log.sh"'
    os.system(cmd)
#===========================================================================================================

#TIMER END==================================================================================================
end = datetime.datetime.now()
timer = end - start
#conver to human readable

print("Analysis took: {} (H:MM:SS) \n".format(timer))
#===========================================================================================================