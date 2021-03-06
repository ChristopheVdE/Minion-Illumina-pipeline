#!bin/bash

############################################################################################################
#NAME SCRIPT: MultiQC.sh
#AUTHOR: Christophe van den Eynde
#RUNNING MultiQC
#USAGE: ./runMultiQC.sh
############################################################################################################

#FUNCTION--------------------------------------------------------------------------------------------------
usage() {
	errorcode=" \nERROR -> This script can have only 1 parameter:\n
          1: Sample ID
          2: [OPTIONAL] Run date\n";
	echo ${errorcode};
	exit 1;
}
if [ "$#" -gt 2 ]; then
	usage
fi
echo
#-----------------------------------------------------------------------------------------------------------

#VARIABLES--------------------------------------------------------------------------------------------------
Sample="$1"
Run="$2"
#-----------------------------------------------------------------------------------------------------------

#===========================================================================================================
# 2) MULTIQC ON EACH SAMPLE (SEPARATELY)
#===========================================================================================================

#CREATE OUTPUTFOLDER IF NOT EXISTS--------------------------------------------------------------------------
mkdir -p /home/Pipeline/Hybrid/${Run}/01_Short_reads/${Sample}/03_QC-Trimmomatic_Paired/QC_MultiQC
#-----------------------------------------------------------------------------------------------------------

#EXECUTE MultiQC--------------------------------------------------------------------------------------------
#RUN MultiQC
echo -e "\nStarting MultiQC on sample: ${Sample}\n"
echo "----------"
multiqc /home/Pipeline/Hybrid/${Run}/01_Short_reads/${Sample}/03_QC-Trimmomatic_Paired/QC_FastQC/ \
-o /home/Pipeline/Hybrid/${Run}/01_Short_reads/${Sample}/03_QC-Trimmomatic_Paired/QC_MultiQC \
2>&1 | tee -a /home/Pipeline/Hybrid/${Run}/01_Short_reads/${Sample}/03_QC-Trimmomatic_Paired/QC_MultiQC/stdout_err.txt;
echo "----------"
echo -e "\nDone"
#-----------------------------------------------------------------------------------------------------------