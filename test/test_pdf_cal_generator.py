from datetime import datetime
import json
import sys

sys.path.insert(1, "E:/gitw/pyCal2PDF/src/")
from Generate_PDF import PDFFactory
from pyCalPDF import CalendarTemplates

print(CalendarTemplates)

for t in CalendarTemplates:
    #for l in ["EN","FR","ES","DE","CHS"]:
    for l in ["EN"]:
        conf = {"filename":f"test_1234",
                "PageSize": {"Width_cm" : 21, "height_cm" : 29.7},
                "main_lang":[l],
                "calendar_year":"2022",
                "calscale":"gregorian",
                #"pdf_file_information_title":"pdf_file_information_title",
                "pictures":[
                    {"index":1, "path":"janvier.jpeg","credit":"","description":""},
                    {"index":2, "path":"fevrier.jpeg","credit":"","description":""},
                    {"index":3, "path":"mars.jpeg","credit":"","description":""},
                    {"index":4, "path":"avril.jpeg","credit":"","description":""},
                    {"index":5, "path":"mai.jpeg","credit":"","description":""},
                    {"index":6, "path":"juin.jpeg","credit":"","description":""},
                    {"index":7, "path":"juillet.jpeg","credit":"","description":""},
                    {"index":8, "path":"aout.jpeg","credit":"","description":""},
                    {"index":9, "path":"septembre.jpeg","credit":"","description":""},
                    {"index":10,"path":"octobre.jpeg","credit":"","description":""},
                    {"index":11,"path":"novembre.jpeg","credit":"","description":""},
                    {"index":12,"path":"decembre.jpeg","credit":"","description":""},
                    {"index":13,"path":"janvier.jpeg","credit":"","description":""}
                    ],
                "icals":[
                    {"header":"icon","ressource":"Flag_FRANCE.svg","ical":"FR_doi_2000_2040.ics","isHoliday":False,"showContent":True,"fonts":{"size":6,"face":"Times-Roman","color":"black"}},

                    {"header":"icon","ressource":"St_Patrick.svg","ical":"St_Patrick.ics","isHoliday":False,"showContent":True,"fonts":{"size":6,"face":"Times-Roman","color":"black"}}
                    ]
                }
        
        conf["caltemplate"]=t
        
        year = datetime.now().year
        conf["dtstart"] = datetime.strftime(datetime(year,1,1),"%Y%m%d")
        conf["dtend"] = datetime.strftime(datetime(year,12,31),"%Y%m%d")
        
        fp = "tmp.json"
        conf["pdf_json_config_file"]=fp
        with open(fp,'w') as fo:
            fo.write(json.dumps(conf,indent=4))
        args=conf
        res = PDFFactory(ProductionMode=False,pdf_output_parent_path="E:\\gitw\\annum.com\\",**args)
        print(f"saved at : {res}")
        exit()

    
    