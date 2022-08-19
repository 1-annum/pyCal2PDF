# -*- coding:utf-8 -*-
#!/usr/bin/env python
"""
Created on Jan 15, 2012

@version:0.0.2 - 2014/March/6 - first version to work on MacOSx
@version 0.0.3 - 2022-01-10 - first package version for pip and py3
@author: oberron
"""
## Standar modules
from argparse import ArgumentParser
from platform import system
import logging
import os
from os.path import abspath, join, pardir

## from pip

## local
from . import pyCalPDF


#pdf_output_parent_path = abspath(join(__file__,pardir,pardir))

def PDFFactory(ProductionMode,pdf_output_parent_path,**args):
    """ Wrapper to call the pyCalPDF code with parameters for easier integration
    Parameters:
    -----------
    ProductionMode: bool
        True: show pictures
        False: does not show picture in pdf
    pdf_output_parent_path: str
        path to where the pdf should be stored
    args: dict
        calendar: (obsolete) name of calendar (key for global var config_files)
        filename: str - prefix for the file to be created
            calendar temmplate and .pdf will be appended to filename to form final file name
        PageSize: dict
            - Width_cm : float
            - height_cm : float
        main_lang: list of str
            - valid values: "EN","FR","ES","DE","CHS"
        sec_langs: list of str (optional)
            - valid_values: "EN","FR","ES","DE","CHS"
        calendar_year:str,
            - FIXME: should be an int
        calscale:str
            - default : "gregorian"
        pictures: list of dict 
            - FIXME: should be optional
        icals: list of ical
            - ical: dict of str
                - header: str
                    - valid_values: icon or banner
                - ressource: str
                    - path to the image (svg, png or jpg) used to display the single day event 
                - ical: str
                    - path to the ical file
                - isHoliday: bool
                    - if True the day of month is showed in Red
                - showContent: bool
                    - if True shows the summary of the event as written in the ical
                - fonts: dict
                    - the font used to display the summary of the event
        pdf_file_information_title: the PDF file information title showed in Acrobat reader
        dtstart: str (deprecated)
            - first day of calendar
        dtend: str (deprecated)
            - last day of calendar
    Returns:
    --------
    pdf_output_parent_path: str
        full path where the ./out folder where the pdf is located
    Usage:
    ------
    see the test folder for examples
    """
    log_msg = f'using config file located at : {args["pdf_json_config_file"]}'
    logging.info(log_msg)

    pdf_json_config_file = args["pdf_json_config_file"]
    logging.info("config file used located at: %s"%(pdf_json_config_file))
    ical_log_file = abspath(join(__file__,pardir,pardir,"out","log.txt"))
    ical_log_enable = ProductionMode

    c = pyCalPDF.pdfCalendar(config_json=args,\
                            folderpath=pdf_output_parent_path, \
                             CreateTempFile=True,preserveAspectRatio=True) #,**cli)
    c.debugPath = ical_log_file
    
    c.debug(TrueFalse =ical_log_enable,debugPath= ical_log_file,ShowPix = ProductionMode)
    c.LoadICS()
    c.SetFirstDayofWeek(c.firstDOW_ISO8601)
    c.Generate()
    c.Save()
    return pdf_output_parent_path

if __name__=="__main__":
    from my_logging import default_setup

    parser = ArgumentParser(description='Generating pdf calendar from json config files')
    parser.add_argument("-c", "--calendar", default="default.json",dest="calendar",\
            help="select calendar to be used", metavar="CAL")
    parser.add_argument("-ds", "--dtstart",dest="dtstart",\
            help="date start for calendar rendering %%Y%%m%%d (e.g. 20060101 for jan 1st 2001)")
    parser.add_argument("-s", "--show", default="Y", dest="ShowPix",\
            help="verbosity level")
    parser.add_argument("-v", "--verbose", default=2, dest="verbose",\
            help="verbosity level")
    parser.add_argument("-de", "--dtend", dest="dtend",\
            help="date end for calendar rendering %%Y%%m%%d (e.g. 20061231 for dec 31st 2001)")
    parser.add_argument("-ye", "--year", dest="calendar_year",\
            help="generate calendar for given year, overrides dtstart and dtend")
    
    #transorm the parser format to a dict for passing as **args
    args = vars(parser.parse_args())

    console_logging = "warning"
    if args["ShowPix"].lower()=="y":
        ShowPix = True    
    else:
        ShowPix = False

    if args["verbose"]<2:
        console_logging = "error"
    elif args["verbose"]>=4:
        console_logging = "debug"
        logging.info("removing pictures from output for faster pdf generation/ cheaper printing")
        ShowPix = False
    default_setup(setup_console_log_level = console_logging)

    if calendar=="default.json":
        calendar = abspath(join(__file__,pardir,"rsc","default.json"))
    with open(calendar,'r') as fi:
        json_config = json.load(fi)
    for key in args:
        json_config[key] = args[key]
       
    out_full_path = PDFFactory(ProductionMode = ShowPix,**json_config)
    #signal we are done and location of file
    print("pyCal SVG generated",out_full_path)
