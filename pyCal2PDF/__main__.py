#from standard modules
from datetime import datetime, timedelta
import json
import logging
from os import getcwd
from os.path import abspath, dirname, exists, join, pardir
from pathlib import Path
from argparse import ArgumentParser

#from pip
from pyCal2PDF.Generate_PDF import PDFFactory
from pyCal2PDF.pyCalPDF import pdfCalendar

def PDFFactory(ProductionMode,**args):
    """ Wrapper to call the pyCalPDF code with parameters for easier integration
    Parameters:
    -----------
    ProductionMode: bool
        True: show pictures
        False: does not show picture in pdf
    args: dict
        calendar: name of calendar (key for global var config_files)
        dtstart: str - first day of calendar
        dtend: str - last day of calendar
    Returns:
    --------
    pdf_output_parent_path: str
        full path where the ./out folder where the pdf is located
    Usage:
    ------
    TBA
    """
    if "calendar" in args:
        calendar = args["calendar"]
    else:
        calendar = "Abb"

    if "rsc" in args:
        print("using rsc path as:", args["rsc"])
        json_folder = abspath(join(args["rsc"],"json"))
        fpi_explicit = abspath(join(json_folder,calendar+".json"))
        print("rsc json exists?",fpi_explicit, exists(fpi_explicit))
        if exists(fpi_explicit):
            with open(fpi_explicit) as fi:
                json_config = json.load(fi)
        else:
            fpi_implicit = abspath(join(json_folder,config_files[calendar]))
            if exists(fpi_implicit):
                with open(fpi_implicit) as fi:
                    json_config = json.load(fi)
            else:
                raise Exception(f"File does not exist: {pdf_json_config_file}")

        json_config["paths"]=abspath(join(getcwd(), args["rsc"]))

        
        # verifier ici si le theme existe
        if "theme" in json_config:
            dp = abspath(json_config["paths"], "img", "Public_Themes", json_config["theme"])
            fp = abspath(join(dp, "theme.json"))
            if exists(fp):
                with open(fp) as fi:
                    json_theme = json.load(fi)
                print(90, json_theme)
                print(91, json_theme["pictures"])
                for p in json_theme["pictures"]:
                    p["path"] = abspath(join(dp, p["path"]))
                json_config["pictures"] = json_theme["pictures"]
            else:
                print("nok")

        
        dpo = args["out_folder"]
        if not exists(dpo):
            #creating a new directory called pythondirectory
            Path(dpo).mkdir(parents=True, exist_ok=True)
        fpo = abspath(join(dpo, "config.json"))

        for c in json_config["icals"]:
            if c["ical"].find("ics/years")>=0:
                ics = c["ical"].split("/")[-1]
                dp = join("ics","years",args["calendar_year"], ics)
                c["ical"] = dp

        
        with open(fpo, 'w', encoding="utf-8") as fo:
            fo.write(json.dumps(json_config, indent=4))
        pdf_json_config_file = fpo

        # else:
        #     raise Exception(f"File does not exist: {pdf_json_config_file}")
    else:
        pdf_json_config_file = abspath(join(json_folder,config_files[calendar]))

    if "verbose" in args:
        my_debug_level = 50 - args["verbose"]*10
    else:
        my_debug_level = 30
    
    logger = logging.getLogger()
    logger.setLevel(my_debug_level)
    
    logging.info("config file used located at: %s"%(pdf_json_config_file))
    ical_log_file = abspath(join(dpo, "log.txt"))
    ical_log_enable = ProductionMode
    if args:
        cli={}
    if "dtstart" in args:
        if args["dtstart"]:
            cli["dtstart"]=args["dtstart"]
            print(71,"dtstart",cli["dtstart"])
    if "dtend" in args:
        if args["dtend"]:
            cli["dtend"]=args["dtend"]
    print(103, args)
    if "calendar_year" in args:
        cli["dtstart"]="%s0101"%(args["calendar_year"])
        cli["dtend"]="%s1231"%(args["calendar_year"])
        cli["Calendar_Title"]=args["calendar_year"]
        cli["year"] = args["calendar_year"]
        cli["filename"]=args["calendar"] #+args["calendar_year"]+".pdf"
    
    c = pdfCalendar(config_file=pdf_json_config_file,folderpath=dpo,dpo=dpo,
                             CreateTempFile=True,preserveAspectRatio=True,**cli)
    c.debugPath = ical_log_file


    c.debug(TrueFalse =ical_log_enable,debug_level=my_debug_level, debugPath= ical_log_file,\
            ShowPix = ProductionMode)
    c.LoadICS()
    c.SetFirstDayofWeek(c.firstDOW_ISO8601)
    # c.defaultpath=root_folder #abspath(join(root_folder,"www"))
    c.Generate()
    c.Save()
    return abspath(join(dpo, c.conf["filename"]))

def cal_maker_wrapper(cal_name,year,rsc_cal, dpo):

    local_rsc_cal = abspath(join(__file__, pardir, pardir, "rsc"))
    my_json = None
    fn = f"{cal_name}.json"
    for dp in [local_rsc_cal, rsc_cal]:
        fp = abspath(join(dp, "json", fn))
        if exists(fp):
            with open(fp ,'r') as fi:
                my_json = json.load(fi)
                break
    if my_json is None:
        raise FileNotFoundError(f"cannot find {fn}")
    # fp = f"E:\\gitw\\annum.com\\rsc\\json\\{cal_name}.json"
    #    fp = "E:\\gitw\\annum.com\\rsc\\json\\James_no_pix.json"
    #    fp = "E:\\gitw\\annum.com\\rsc\\json\\James_catho_pix.json"

    my_json["pdf_json_config_file"]=fp
    if not "pictures" in my_json:
        my_json["pictures"]=[]
    if "theme" in my_json:
        dp = f"E:\\gitw\\annum.com\\rsc\\img\\Public_Themes\\{my_json['theme']}\\"
        with open(f"{dp}theme.json",'r') as fi:
            theme = json.load(fi)
        print(23,theme)
        my_json["pictures"]=theme
        for index,_ in enumerate(my_json["pictures"]):
            my_json["pictures"][index]["path"]=dp+my_json["pictures"][index]["path"]

    if "paths" in my_json:
        base_fold = my_json["paths"]
        if base_fold == ".":
            base_fold = dirname(fp)
        elif base_fold == "..":
            base_fold = abspath(join(dirname(fp),pardir))
        else:
            pass
        
    icals = []
    for ical in my_json["icals"]:
        fp = abspath(join(base_fold,ical["ressource"]))
        ical["ressource"]=fp
        fp = abspath(join(base_fold,ical["ical"]))
        from os import sep
        pattern = sep+"years"+sep
        lenp = len(pattern)
        if fp.find(pattern)>=0:
            fp =fp[:fp.find(pattern)]+f"{sep}years{sep}{year}"+fp[fp.find(pattern)+lenp+4:]
        ical["ical"]=fp
        icals.append(ical)
    my_json["icals"]=icals
    #year = datetime.now().year
    my_json["dtstart"] = datetime.strftime(datetime(year,1,1),"%Y%m%d")
    my_json["dtend"] = datetime.strftime(datetime(year,12,31),"%Y%m%d")
    my_json["calendar_year"]=str(year)
    my_json["Calendar_Title"]=my_json["calendar_year"]
    my_json["filename"]=f"{cal_name}_{year}.pdf"
        
    if len(my_json["pictures"])>0:
        production_mode = True
    else:
        production_mode = False
        
    res = PDFFactory(ProductionMode=production_mode,pdf_output_parent_path=dpo,**my_json)
    print("ok")

if __name__=="__main__":
    dpo_default = abspath(join(__file__, pardir, pardir, "out"))
    cal_year = str((datetime.now()+timedelta(days=364)).strftime("%Y"))
    logging.basicConfig(level=logging.INFO)
    
    parser = ArgumentParser(description='Generating pdf calendar from json config files')
    parser.add_argument("-c", "--calendar", default="Abb",dest="calendar",\
            help="select calendar to be used", metavar="CAL")
    parser.add_argument("-e", "--dtend", dest="dtend",\
            help="date end for calendar rendering %%Y%%m%%d (e.g. 20061231 for dec 31st 2001)")
    parser.add_argument("-o", "--out_folder", default=dpo_default,
                    help="increase output verbosity")
    parser.add_argument("-p", "--production", default="Y",dest="production",\
            help="if set to True, will display pictures")
    parser.add_argument("-r", "--rsc", dest="rsc",
            help="private ressource for calendar path")
    parser.add_argument("-s", "--dtstart",dest="dtstart",\
            help="date start for calendar rendering %%Y%%m%%d (e.g. 20060101 for jan 1st 2001)")
    parser.add_argument("-v","--verbose",dest="verbose", default=2,type=int,\
            help="1=>ALERT only to 4=>DEBUG and all higher, v>=3 hides pictures in output for faster pdf generation")
    parser.add_argument("-y", "--year", default = cal_year, dest="calendar_year",\
            help="generate calendar for given year, overrides dtstart and dtend")
    #transorm the parser format to a dict for passing as **args
    args = vars(parser.parse_args())
    #call the PDF Factory class
    ShowPix = True

    if "verbose" in args:
        if args["verbose"]>=3:
            logging.info("removing pictures from output for faster pdf generation/ cheaper printing")
            ShowPix = False
    if args["production"]=="Y":
        if not ShowPix:
            logging.info("Showing pictures")
        ShowPix=True
    print("FIXME: need to iterate over ressources to find if calendar is public or private and fix the relative links in teh json")

    out_full_path = PDFFactory(ProductionMode = ShowPix,**args)
    #signal we are done and location of file
    print(f"pyCal SVG generated and save here: {out_full_path}")

    exit()

    
    parser = argparse.ArgumentParser()
    parser.add_argument("cal_name", type=str,
                    help="selects the calendar to be generated")
    
    parser.add_argument("-r", "--rsc_cal",
                    help="private calendar ressources root folder")    
    parser.add_argument("-v", "--verbose",
                    help="increase output verbosity")
    parser.add_argument("year", type=str,
                    help="selects the calendar to be generated")
    args = parser.parse_args()
    print(81, args)
    cal_year = int(args.year)
    cal_maker_wrapper(args.cal_name,cal_year , args.rsc_cal, args.out_folder)