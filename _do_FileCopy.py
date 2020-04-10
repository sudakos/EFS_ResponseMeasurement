#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  _do_FileCopy.py
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
#from __future__ import print_function

import sys
import argparse
import shutil
import logging
import csv
import time


# ---------------------------
# Initialize Section
# ---------------------------
def get_args():
    parser = argparse.ArgumentParser(
        description='Copy a file.')

    parser.add_argument('src1',
        action='store',
        help='Specify the 1st source file path.')

    parser.add_argument('src2',
        action='store',
        help='Specify the 2nd source file path.')

    parser.add_argument('dst',
        action='store',
        help='Specify the destination file path.')
    
    parser.add_argument('-o','--output',
        action='store',
        default="output_do_FileCopy.csv",
        required=False,
        help='Specify output file')

    parser.add_argument('-b','--basetime',
        action='store',
        type=int,
        default="0",
        required=False,
        help='Set the base time(monotonic clock as nanoseconds)')

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

    # Set base time
    if args.basetime <= 0:
        basetime = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    else:
        basetime = int(args.basetime)

    # Read the Copy File List
    try:
        status = 'unknown'
        mes    = ''
        start_localtime = time.localtime()
        end1st = 0
        end2nd = 0
        # the 1st file
        start = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        shutil.copy(args.src1, args.dst)
        end1st = time.clock_gettime_ns(time.CLOCK_MONOTONIC)

        # the 2nd file
        shutil.copy(args.src2, args.dst)
        end2nd = time.clock_gettime_ns(time.CLOCK_MONOTONIC)

    except:
        mes = sys.exc_info()
        logging.error(mes)
        status = 'Failed'
    else:
        status = 'Success'

    finally:
        end = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        delta_start  = int( (start - basetime)/10**6 )
        if end1st == 0:
            delta_end1st = -1
        else:
            delta_end1st = int( (end1st - basetime)/10**6 )
        
        if end2nd == 0:
            delta_end2nd = -1
        else:
            delta_end2nd = int( (end2nd - basetime)/10**6 )
        ret = [args.src1, args.src2, args.dst, time.strftime("%a %b %d %H:%M:%S %Y",start_localtime), delta_start, delta_end1st, delta_end2nd, status, mes ]

    #Write result
    with open(args.output, "w") as fd:
        writer = csv.writer(fd, lineterminator='\n')
        writer.writerow( ret )
        fd.close()
    
    #debug
    if args.debug:
        print(ret)

    return

if __name__ == "__main__":
    sys.exit(main())
