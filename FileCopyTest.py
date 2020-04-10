#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  FileCopyTest.py
#  ======
#  Copyright (C) 2019 n.fujita
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from __future__ import print_function

import sys
import argparse
import csv
import logging
import traceback
import shutil
import time, datetime
import math
import glob
import subprocess
import re
import os

SummaryResultCSVFile  = 'ResultsSummary.csv'
DetailResultsFileHead = 'ResultsDetail'
ExecCommand           = './_do_FileCopy.py'

# ---------------------------
# Initialize Section
# ---------------------------
def get_args():
    parser = argparse.ArgumentParser(
        description='Execute tool')
        
    parser.add_argument('CSV_FilePath',
        action='store',
        help='Specify CSV file path with a list of files to be copied')

    parser.add_argument('-d','--debug',
        action='store_true',
        default=False,
        required=False,
        help='Enable dry-run')

    return( parser.parse_args() )


# ---------------------------
# Main function
# ---------------------------
def main():

    # Initialize
    args = get_args()

    # Read the Copy File List
    copylist = []
    with open( args.CSV_FilePath, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            copylist.append(row)
    NumOfFile = len(copylist)
 
    # Run by background
    print( "Run CopyFile programs." )
    StartTime = time.time()
    BaseTime = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    
    idx = 0
    for row in copylist:
        if args.debug:
            print("source1={}\nsource2={}\ndest={}".format(row[0],row[1],row[2]))

        cmd = [ ExecCommand, '--basetime', str(BaseTime), '--output', "temp_result_{0:04d}.csv".format(idx), row[0], row[1], row[2] ]
        process = subprocess.Popen(cmd)
        process.wait()
        idx += 1
        
    # Finish
    EndTime = time.time()
    print( "Done all test programs." )

    # Calculate the result
    time_delta = EndTime - StartTime
    StartDate = datetime.datetime.fromtimestamp( StartTime ).strftime("%Y/%m/%d %H:%M:%S")
    EndDate   = datetime.datetime.fromtimestamp( EndTime ).strftime("%Y/%m/%d %H:%M:%S")

    # Check results and Marge result file
    total = 0
    success = 0
    failed = 0
    unknown = 0
    repatter_success = re.compile(r"Success")
    repatter_failed  = re.compile(r"Failed")
    with open( "{0}_{1:04d}_{2}.csv".format(DetailResultsFileHead, NumOfFile, datetime.datetime.fromtimestamp( StartTime ).strftime("%Y%m%d_%H%M%S")), "w" ) as MargedFiled:
        for i in range(0,NumOfFile):
            try:
                fp = open( "temp_result_{0:04d}.csv".format(i), 'r')
                for line in fp:
                    if repatter_success.search(line):
                        success += 1
                    elif repatter_failed.search(line):
                        failed += 1
                    else:
                        unknown += 1
                    total += 1
                    MargedFiled.write(line)
                MargedFiled.flush()
                fp.close()
            except:
                e = sys.exc_info()
                logging.error("{}".format(e))
            
        MargedFiled.close()

    # Write to the summary file  
    with open(SummaryResultCSVFile, "a") as FpSummary:
        writer = csv.writer(FpSummary, lineterminator='\n')

        print( "NumOfFiles, NumOfParallels, ExeTime(sec), StartTime, EndTime, SuccessedFiles, FailedFiles, UnknownFIles, TotalFiles" )
        row = [ NumOfFile, NumOfFile, time_delta, StartDate, EndDate, success, failed, unknown, total ]
        print (row)
        writer.writerow( row )


    # Delete temporary files
    for fn in glob.glob( "temp_result_*.csv" ):
            os.remove(fn)

    # Finish
    return

if __name__ == "__main__":
    sys.exit(main())
