# -*- coding:utf-8 -*-
"""
Created on Nov 17, 2011
@version:0.2 - 2014/March/6 - first version to work on MacOSx
@version 0.0.3 - 2022-01-10 - first package version for pip and py3
ab

About
-----

Usage
-----

To come
------
* add alternate page sizes and the picture handling (non stretching, cropping, ...)
* add binding (there is a binding added after printing) or stapled (all pages are stapled, 
meaning that on the print the month need to be alternated)
* consider writing it as a subclass of python TextCalendar HTMLCalendar


History
-------

Dependencies
------------
http://www.reportlab.com/software/installation/
https://pypi.python.org/pypi/svglib/

@author: oberron
"""
#standard modules
import calendar, time, datetime
import datetime
import functools
import locale
from math import floor
from os.path import abspath, join, pardir
import sys, encodings, encodings.aliases

#pip modules
from reportlab.lib import pagesizes
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.cidfonts import UnicodeCIDFont,findCMapFile
from reportlab.lib.codecharts import KutenRowCodeChart,hBoxText
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont

from lunardate import LunarDate
from svglib.svglib import svg2rlg

from pyICSParser import pyiCalendar
"""
from pyICSParser import pyiCalendar
ical_fp = "./cal.ics"
ds="20060101"
de="20061231"
mycal = pyiCalendar.iCalendar()
mycal.local_load(ical_fp)
dates = mycal.get_event_instances(ds,de)
"""
import json
import logging

AnnumMoto = "1-annum.com - tailor made calendars" #used by the pdf generator
DPI = 72/2.54 #DOT per inches: conversion for cm dimensions to dots dimensions for reportlab 
CalendarTemplates = ["bound-top","bound-middle","stapled-middle","bound-top-no-pix"]

class flowable():
    """ (x0,y0): origin, (x,y) current coordinates
    (xe,ye): limit coordinates
    all defining a flowable box
    """
    x0=0
    y0=0
    x=0
    y=0
    xe=0
    ye=0

class pdfCalendar():
    
    """
    parses a config file giving ical files and how to render it into a pdf
    """
    width = 20
    height = 20
    margins = {"left":0,"right":0,"top":0,"bottom":0}
    pcal = ""
    author = "YOU"
    langlist = []
    conf = []
    template = "split"
    ShowPix = True
    
    #FIXME:
    #http://theserverpages.com/php/manual/en/function.setlocale.php
    #http://msdn.microsoft.com/en-us/library/cdax410z(vs.71).aspx
    #    $this->languages = array("fra","gbr","deu","esp","chs");
    
    from platform import system
    if system() == "Windows":
        supportedlang = {"FR":"FRA",
                         "DE":"DEU",
                         "EN":"ENG",
                         "ES":"ESP",
                         "CHS":"CHS"
                         }
    else:
        supportedlang = {"FR":"FRA",
                         "DE":"DEU",
                         "EN":"en_GB.UTF-8",
                         "ES":"ESP",
                         "CHS":"CHS"
                         }
        
    pub={"FR":"http://www.1-annum.com - Calendrier sur mesure",
        "DE":"http://www.1-annum.com - Individuelle Posterkalender",
        "EN":"http://www.1-annum.com - tailor made calendars",
        "ES":"http://www.1-annum.com - Calendarios Personalizados",
        "CHS":"定制日历"}
    #http://en.wikipedia.org/wiki/Week-day_names#endnote_LORD.E2.98.891
    lDOW={"FRA":["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"],
          "ENG":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
          "DEU":["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"],
          "ESP":["lunes","martes","miércoles","jueves","viernes","sábado","domingo"],
          "CHS":["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
          }
    firstDOW_ISO8601 = 1
    firstDOW = 1
    #http://msdn.microsoft.com/en-us/library/39cwe7zf
    title = "21st century"
    debug_mode = False
    debugPath = "../out/log.txt"
    debug_level = 0
    PageSize = ""
    PDFOutFolder = ""
    def nonzero(self,row):
        return len([x for x in row if x!=0])
    def __init__(self,config_json,folderpath="./",CreateTempFile=False,preserveAspectRatio=False): #,**kwargs):
        """ the creator
        Parameters:
        -----------
        config_json: dict

        folderpath: str
            path to root of all ressources (under folderpath/www)
        CreateTempFile: bool
        preserveAspectRatio: bool
        Returns:
        --------
        None - but creates a pdf file (if successful) under folderpath/out
        """
        self.PDFOutFolder = abspath(join(folderpath,"out"))
#        self.SetConfiguration(config_file,CreateTempFile)
        self.preserveAspectRatio=preserveAspectRatio
        """path = config_file
        json_data=open(path)
        self.conf = json.load(json_data)
        json_data.close()"""
        self.conf = config_json
        self.SetLanguage(self.conf["main_lang"])
        self.CalDates = {}
        if "paths" in self.conf:
            self.defaultpath = abspath(join(folderpath,self.conf["paths"]))
        else:
            self.defaultpath = "."
        #FIXME: here check if file already exists and open, if so create a temp file to avoid error
        
        PageHeightcm = self.conf["PageSize"]["height_cm"]*DPI
        PageWidthcm = self.conf["PageSize"]["Width_cm"]*DPI
        PageSize = (PageWidthcm,PageHeightcm)
        self.width, self.height = PageWidthcm, PageHeightcm
        
        if "pdf_file_information_title" in self.conf:
            #the title appears in the pdf document properties 
            self.title = self.conf["pdf_file_information_title"]
        else:
            self.title = "1-annum.com bespoke calendars to help connecting lives"
        
        
        if "caltemplate" in self.conf:
            if self.conf["caltemplate"] not in CalendarTemplates:
                self.conf["caltemplate"]=CalendarTemplates[0]
                logging.info("Calendar configuration template set to bound-top")
        else:
            self.conf["caltemplate"]="bound-top"
            logging.info("Calendar configuration template set to bound-top")
        self.template = self.conf["caltemplate"]

        
        year = datetime.datetime.now().year        
        if "dtstart" not in self.conf:
            CurrentMonth = datetime.datetime.now().month
            if CurrentMonth<10:
                self.conf["dtstart"] = datetime.datetime.strftime(datetime.datetime(year,1,1),"%Y%m%d")
                self.conf["dtend"] = datetime.datetime.strftime(datetime.datetime(year,12,1),"%Y%m%d")
            else:
                year +=1
                self.conf["dtstart"] = datetime.datetime.strftime(datetime.datetime(year,1,1),"%Y%m%d")
                self.conf["dtend"] = datetime.datetime.strftime(datetime.datetime(year,12,1),"%Y%m%d")
        """for key in self.conf:
            if key in kwargs:
                self.conf[key]=kwargs[key]"""
        logging.info("mcv after: 186 - %s - %s"%(self.conf["dtstart"], self.conf["dtend"]))

        if "Calendar_Title" not in self.conf:
            self.conf["Calendar_Title"] = self.conf["dtstart"][0:4]
        
        if "Calendar_SubTitle" not in self.conf:
            self.conf["Calendar_SubTitle"] = ""
            
        if "filename" not in self.conf:
            self.conf["filename"] = "temp%s_%s_%s.pdf"%(str(datetime.datetime.now()),self.conf["caltemplate"],year)
        else:
            self.conf["filename"] += "_%s_%s.pdf"%(self.conf["caltemplate"],year)
            
        if "Author" not in self.conf:
            self.conf["Author"] = "1-annum"
        self.author = self.conf["Author"]
        pdf_file_output = abspath(join(self.PDFOutFolder,self.conf["filename"]))
        self.pcal = Canvas(pdf_file_output, PageSize)
    def debug(self,TrueFalse,debugPath="./log.txt",debug_level=0,ShowPix = False):
        """sets the debg mode: logging / not logging , debug_level"""
        #TODO: move this to python logging
        self.debug_mode = TrueFalse
        self._log("self debug is now",[TrueFalse])
        self.debug_level = debug_level
        self.debugPath = debugPath
        self.ShowPix = ShowPix
#        log = open(self.debugPath,'w')
#        log.close()
    def _log(self,title,list,level=0):
        if self.debug_mode == True:
            if level >= self.debug_level:
                #FIXME: hardcoded path
                log=open(self.debugPath,'a')
                line = "**"+title+"\n"
                for el in list:
                    if len(str(el))<1000:
                        line = line + "\t"+str(el)
                    else:
                        line = line + "\t"+str(el)[0:1000]
                log.write(line+"\n")
                log.close()
        if level <0:
            logging.info("pyCalPDF 227:%s - %s"%(title,list))
#            print title,list
    def SetFirstDayofWeek(self,isoWeekDOW):
        self.firstDOW = isoWeekDOW -1 
    def stringWidth(self,string,font,size,charspace=3):
        return stringWidth(string, font, size)
    def stringHeight(self,string,fontType,fontSize):
        f = pdfmetrics.getTypeFace(fontType)
        return (f.ascent - f.descent)*fontSize/1000
    def CenteredString(self,x0,xe,y,string,font,size,charspace=1):
        width = stringWidth(string, font, size)
        width += (len(string) - 1) * charspace  
        xs = x0+(xe-x0-width)/2
        #print x0,xe,width,xs
        self.pcal.drawString(xs, y, string)
    def SetLanguage(self,langlist):
        """sets the language for month and day of weeks"""
        for lang in langlist:
            if lang in self.supportedlang:
                self.langlist.append(lang)
            else:
                self._log("bad language :",lang,level=-1)
    def CalendarLine(self,datetodisplay=datetime.date(2012,1,1),DOW=1,Line="Month",sep=" "):
        """ returns a unicode string with the name of month in selected language(s) or 
        date of the week in selected language(s)"""
        moline = ""
        index = 0
        if Line == "Month":
            for lang in self.langlist:
                index +=1
                if index == len(self.langlist):
                    separ =""
                else:
                    separ=sep
                if lang not in ["CHS","pinyin"]:
                    moline += calendar.LocaleTextCalendar(locale=self.supportedlang[lang]).formatmonthname(datetodisplay.year,datetodisplay.month,1) + separ
                    #moline = u'\u6771\u4EAC'
                elif lang in ["CHS","pinyin"]:
                    #moline += lunardate.LunarDate.fromSolarToUTF(datetodisplay.year,datetodisplay.month,datetodisplay.day,lang)+separ
                    chinese_moon_month = LunarDate.fromSolarDate(datetodisplay.year,datetodisplay.month,datetodisplay.day).month
                    #name as per: https://en.wikipedia.org/wiki/Chinese_calendar#Names_of_months
                    chinese_modern_names = ["正月","二月","三月","四月","五月","六月","七月","八月","九月","十月","冬月","腊月"]
                    moline += chinese_modern_names[chinese_moon_month-1]+separ
        elif Line== "DOW":
            #FIXME below only returns english DOW
            for lang in self.langlist:
#                 moline = self.lDOW[self.supportedlang[lang]][(DOW+self.firstDOW-1) % 7]
#                 moline += calendar.LocaleTextCalendar(locale=self.supportedlang[lang]).day_name((DOW+self.firstDOW-1) % 7)
                moline = calendar.day_abbr[(DOW+self.firstDOW-1) % 7] #.decode(calendar.TimeEncoding(self.supportedlang[lang]).__enter__())

        #return unicode(moline)
        return moline
    def NextMonth(self,month):
        """ returns next month and caters for roll over year end"""
        mycal = pyiCalendar.iCalendar()
        mo = month.month
        y = month.year
        #here we make sure that if we wrap the year, we decrease year index and go for modulo on the months
        if mo ==12:
            mo =1 
            y +=1
        else:
            mo+=1
        #here we make sure that if the next month has less days thatn the previous one we still generate a valid date (if month has 31
        #days, next month has 30 (most of time) so the day of month will be 30 if we had 31
        try:
            nexMo = datetime.date(y,mo,month.day)
        except:
            nexMo = datetime.date(y,mo,mycal._last_dom(y,mo))
        return nexMo
    def PrevMonth(self,month):
        mycal = pyiCalendar.iCalendar()
        mo = month.month
        y = month.year
        if mo == 1:
            mo =12
            y -= 1
        else:
            mo -=1
        try:
            preMo = datetime.date(y,mo,month.day)
        except:
            preMo = datetime.date(y,mo,mycal._last_dom(y,mo))
        #here we make sure that if the next month has less days thatn the previous one we still generate a valid date (if month has 31
        #days, next month has 30 (most of time) so the day of month will be 30 if we had 31
        return preMo
    def addMonthTable(self,month,x0,y0,wm,hm,Fonts,TableBorders, Layout,
                      showWE=False,showDOW=False,HeaderRatio=1,nDOW=1,DOW_FontSize=12,
                      showMonthName=True):
        """ adds the table for the month with options to display the day of week names, 
        display or not the borders for each day, ...
        table is rendered between (x0,y0), (x0+wm,y0+hm) 
        """
        self.pcal.saveState()
        #FIXME: 72 is the dots per inch but hard coded,7 is the number of rows
        self.pcal.setFont(Fonts["FontType"] , hm*7/72) 
        
        #create local calendar
        mycal = calendar
        mycal.setfirstweekday((self.firstDOW)%7)
        cal = mycal.monthcalendar(month.year, month.month)
        
        #set up constants
        width, height = wm,hm
        rows, cols = len(cal), 7
        rowsheader = 0
        if showDOW:
            rowsheader+=HeaderRatio
        if showMonthName:
            rowsheader+=1
        lastweek = self.nonzero(cal[-1])
        firstweek = self.nonzero(cal[0])
        weeks = len(cal)
        rowheight = height / (rows+rowsheader)
        boxwidth = width/cols

        if TableBorders["ShowBorders"]:
            for row in range(rows+1):
                first, last = cols,cols
                if row >= rows and not TableBorders["ShowLastMonthBorder"]:
                    first = firstweek
                elif row == 0 and not TableBorders["ShowNextMonthBorder"]:
                    last = lastweek
                y = y0 + (row * rowheight)
                startx = x0+(cols-first)*boxwidth
                endx = x0+last*boxwidth
                self.pcal.line(startx, y, endx, y)
            #now draw the vert lines
            x = x0
            starty=y0
            for col in range(8):
                last, first = 0,0
                if col >= lastweek +1 and not TableBorders["ShowNextMonthBorder"]: 
                    last = 1
                if (col <= 6 - firstweek) and not TableBorders["ShowLastMonthBorder"]:
                    first = 1
                starty = y0 + last * rowheight
                endy = y0 + (rows -first)* rowheight
                if showDOW:
                    x = x
                    self.pcal.line(x, y0 + rows * rowheight, x, y0 + (rows+HeaderRatio) * rowheight)
                self.pcal.line(x, starty, x, endy)
                x +=  boxwidth

        if showDOW and TableBorders["ShowHeaderBorder"]:
            y=y0 + (rows * rowheight)
            self.pcal.line(x0, y, x0+ (boxwidth * cols), y)
            y+=HeaderRatio*rowheight
            self.pcal.line(x0, y , x0+ (boxwidth * cols), y)
        
        #now fill in the day numbers and any data
        x = x0 + boxwidth/2
        y = y0 + ((rows+rowsheader) * rowheight)
        if showMonthName:
                self.CenteredString(x0, x0+width, y-rowsheader*rowheight/2, self.CalendarLine(month), Fonts["FontType"], Fonts["Font_Size_DOW"],1)
                #self.CenteredString(x0, x0, y, "a", Fonts["FontType"], Fonts["Font_Size_DOW"])
                #self.CenteredString(x0+width, x0+width, y, "a", Fonts["FontType"], Fonts["Font_Size_DOW"])
                
                #self.pcal.drawString(x, y, self.CalendarLine(year, month))
                y = y - rowheight            
        if showDOW:
            jds = 1
            y -= rowheight*HeaderRatio
            x = x0
            for jds in range(1,8):
                self.pcal.setFont(Fonts["FontType"], Fonts["Font_Size_DOW"]) 
                #FIXME: here we leverage the fact that 2006/Jan/1 is Monday
                sDOW= self.CalendarLine(DOW=jds,Line = "DOW")
                if nDOW >0:
                    sDOW = sDOW[0:1]
                self.CenteredString(x, x+boxwidth, y+rowheight*HeaderRatio/3, sDOW,Fonts["FontType"],Fonts["Font_Size_DOW"])
                x = x + boxwidth
            y = y - rowheight
            x = x0 
        for week in cal:
            self.pcal.setFont(Fonts["FontType"], Fonts["Font_Size_DOM"]) 
            for day in week:
                if day:
                    self.dayCell(datetime.datetime(month.year,month.month,day),x,y,boxwidth,rowheight,Fonts,Layout)
                x = x + boxwidth
            y = y - rowheight
            x = x0
        
        self.pcal.restoreState()
    def isEvent(self,day):
        ret = [["","","","",""]]
        isHoliday = False
        day = day.date()
        if day in self.CalDates:
            for events in self.CalDates[day]:
                cal = self.conf["icals"][events[0]]
                isHoliday |= cal["isHoliday"]
                ret.append([events[1], cal["ressource"],cal["header"],cal["ical"],cal['fonts']])
        return ret , isHoliday
    def dayCell(self,day,x0,y0,boxwidth,rowheight,Fonts,Layout):
        """ fills the cell for a day
        used by addMonthTable
        """
        events, isHoliday = self.isEvent(day)
        banner = flowable()
        icon = flowable()
        banner.xe = x0+boxwidth
        banner.x0 = x0
        banner.y0 = y0
        banner.ye = y0-rowheight
        icon.xe = banner.xe
        icon.x0 = x0
        icon.x = icon.x0
        icon.y0 = y0
        icon.ye = banner.ye
                
        showContent = True
        x,y=x0,y0
        
        banner_ratio = 1.0/20
        icon_ratio = 2.0/10 #MCV default is 1.0/10
#        icon_size = 
        interline = icon_ratio/4.0

        if isHoliday:
            self.pcal.setFillColorRGB(1,0,0)
        
        self.pcal.setFont(Fonts["FontType"], Fonts["Font_Size_DOM"]) 
#        self.pcal.setFont(Fonts["FontType"], 30) 
        if Layout["quantieme"] =="c":
            #self.pcal.drawString(x, y, str(day))
            self.CenteredString(x, x+boxwidth, y, str(day.day),Fonts["FontType"],Fonts["Font_Size_DOM"])
            self.pcal.setFillColorRGB(0,0,0)
        elif Layout["quantieme"] =="tl": #tl = top left
            banner.y=y+rowheight-rowheight*banner_ratio
            #FIXME: below relies on the header not flowing over
            #BEFORE: icon.y=y+rowheight-self.stringHeight(str(day.day), Fonts["FontType"],Fonts["Font_Size_DOM"])
            #AFTER:
            icon.y=y+rowheight-self.stringHeight(str(day.day), Fonts["FontType"],Fonts["Font_Size_DOM"])
            self.pcal.drawString(x, icon.y, str(day.day))
            icon.y0=icon.y-rowheight*interline-rowheight*icon_ratio
            icon.y=icon.y0
            icon.x=icon.x0
            self.pcal.setFillColorRGB(0,0,0)
            #start banner after current "quantieme"
            banner.x0=x+self.stringWidth(str(day.day), Fonts["FontType"],Fonts["Font_Size_DOM"])
            for event in events:
                #FIXME: if header self.stringWidth(str(" "+content), Fonts["FontType"],6)>icon.xe, then overflows the next cell !!!
                showContent = True
                content, ressource, header,ical,font = event
                if len(content)>0:
                    #FIXME: below relies on the ical file for moon cycle to have moon in its name!!!!
                    #TODO: work on algo for layout
                    if ical.upper().find("MOON")>0 or ical.upper().find("LUNE")> 0:
                        path="/rsc/svg"
                        path = self.defaultpath
                        showContent = False
                        if content.lower().find("first quarter")>=0 or content.find("Premier quartier")>0:
                            ressource = abspath(join(__file__,pardir,pardir,pardir,pardir,"rsc","FirstQuarter.svg"))
                        elif content.lower().find("full moon")>=0 or content.find("Pleine lune")>0:
                            ressource =abspath(join(__file__,pardir,pardir,pardir,pardir,"rsc","FullMoon.svg"))

                        elif content.lower().find("last quarter")>=0 or content.find("Dernier quartier")>0:
                            ressource = abspath(join(__file__,pardir,pardir,pardir,pardir,"rsc","LastQuarter.svg"))

                        elif content.lower().find("new moon")>=0 or content.find("Nouvelle lune")>0:
                            ressource = abspath(join(__file__,pardir,pardir,pardir,pardir,"rsc","NewMoon.svg"))

                    svg_full_path = abspath(join(self.defaultpath,ressource))
                    try:
                        drawing = svg2rlg(svg_full_path)
                    except:
                        print(499,svg_full_path)
                        raise
                    if drawing is None:
                        logging.warning("ressource file not found:%s"%(ressource))
                        warn_fp = abspath(join(__file__,pardir,pardir,pardir,pardir,"rsc","Warning.svg"))
                        drawing = svg2rlg(warn_fp) 
                    if not showContent:
                        content = " "
                    if header=="banner":
                        drawing.scale((boxwidth-self.stringWidth(str(day.day), Fonts["FontType"],Fonts["Font_Size_DOM"]))/drawing.width,rowheight/drawing.height*banner_ratio)
                        x = banner.x0
                        y= banner.y
                        #FIXME: if we have too many banners this overflows into the icon flowable:add a user warning
                        banner.y -= rowheight*banner_ratio
                    elif header=="icon":
                        xscale = boxwidth*icon_ratio/drawing.width
                        yscale = rowheight*icon_ratio/drawing.height
                        drawing.scale(xscale,yscale)
                        if icon.x+boxwidth*icon_ratio+self.stringWidth(str(" "+content), font['face'],font['size'])>icon.xe:
                            icon.y-= rowheight*icon_ratio
                            x=icon.x0
                            icon.x=x+boxwidth*icon_ratio+self.stringWidth(str(" "+content), font['face'],font['size'])
                            y=icon.y
                        else:
                            x=icon.x
                            y=icon.y
                            icon.x+=boxwidth*icon_ratio+self.stringWidth(str(" "+content), font['face'],font['size'])
                    drawing.drawOn(self.pcal, x, y)
                    x+=boxwidth*icon_ratio
                    self.pcal.saveState()
                    self.pcal.setFont(font['face'],font['size']) 
                    self.pcal.drawString(x, y, content)
                    self.pcal.restoreState()
    def addMonth(self,MonthStart,NumberMonths,
                 CalType="Gregorian",Pictures=[]):
        """ template for one month: month picture + previous month + next month 
        + month name(s) + current month table
        """ 
        #FIXME: font-sizes are hardcoded:
        FontSizeMonthName = 58 #make this relative to page width, calculating with longest month name: October/november
        Font_Size_DOM_BT = 24
        Font_Size_DOW_BT = 8
        Font_Size_DOW_ST = 8
        Font_Size_DOM_ST = 8
        FontsBigTable = {"Font_Size_DOM":Font_Size_DOM_BT,"Font_Size_DOW":Font_Size_DOW_BT,"FontType":"Times-Roman"}
        FontsSmallTable = {"Font_Size_DOM":Font_Size_DOM_ST,"Font_Size_DOW":Font_Size_DOW_ST,"FontType":"Times-Roman"}
        MonthPicture = MonthStart
        MonthTable = MonthStart
        if self.ShowPix:
            MonthPictureIndex = self.conf["pictures"][(MonthPicture.month-1) % (len(self.conf["pictures"]))]
            image_full_path = abspath(join(self.defaultpath,MonthPictureIndex["path"]))
        
        height_mo = 100
        if NumberMonths %2 ==0:
            NumberPages = NumberMonths+1
        else:
            NumberPages = NumberMonths

        # *** PICTURE + 2 small months ****
        if self.template == "bound-middle":
            x0 = self.margins["left"]
            y0 = 0
            wid = self.width-self.margins["right"]-self.margins["left"]
            localheight = self.height
            pass
        elif self.template == "bound-top":
            x0 = self.margins["left"]
            y0 = self.height/2
            localheight = self.height/2
            pass
        elif self.template == "stapled-middle":
            x0 = self.margins["left"]
            y0 = self.height/2
            localheight = self.height/2
            if MonthStart.month > (NumberMonths+2.0)/2:
                return
            mo = (NumberPages+1-MonthStart.month) %12
            if mo==0:
                mo=12
            dy = int((NumberPages-MonthStart.month)/12.0)
            DualMonth = datetime.date(MonthStart.year+dy,mo,1)
            MonthPicture = MonthStart
            MonthTable = DualMonth
        elif self.template == "bound-top-no-pix":
            """ one sided calendar, staplers are the top, no picture above month table """
            x0 = self.margins["left"]
            #y0: the line on top of which the calendar month and prev/next cal tables will be displaye
            #0 = bottom corner, height = top of page
            y0 = self.height-self.margins["top"]-height_mo
            localheight = self.height/2
        else:
            raise Exception("line 440: wrong calendar template")

        """ Adding MONTH PIX + 2 previous MONTHS """
            
        image_height = localheight-height_mo-2*self.margins["top"]
        if self.template.find("no-pix")<0:
            #FIXME: seems like broken logic
            if self.ShowPix:
                #self.pcal.drawImage(Pictures["path"],x0,y0+height_mo+self.margins["bottom"],self.width-2*self.margins["right"],localheight-height_mo-2*self.margins["top"])
                self.pcal.drawImage(image_full_path,x0,y0+height_mo+self.margins["bottom"],self.width-2*self.margins["right"],localheight-height_mo-2*self.margins["top"],preserveAspectRatio=self.preserveAspectRatio)
                self.pcal.saveState()
                self.pcal.translate(self.width-self.margins["right"],y0+height_mo+self.margins["bottom"])
                self.pcal.rotate(90)
                self.pcal.drawString(0, 0, MonthPictureIndex["description"])
        #            self.pcal.drawCentredString(0, 0,  MonthPictureIndex["description"])
                self.pcal.restoreState()
                #self._log("pictures",Pictures,0)
            else:
                #def drawCentredString(self, x, y, text,mode=None):
                #Draws a string centred on the x coordinate. 
                self.pcal.drawCentredString(self.width / 2, y0+height_mo+(localheight-height_mo-2*self.margins["top"])/2,  "Picture displayed here")
    #        Fonts = {"Font_Size_DOM":8,"Font_Size_DOW":Font_Size_DOW_Small_Table,"FontType":"Times-Roman"}
        Layout = {"quantieme":"c"}
        TableBorders = {"ShowBorders":False,"ShowLastMonthBorder":False,"ShowNextMonthBorder":False,"ShowHeaderBorder":False}
        self.addMonthTable(self.PrevMonth(MonthPicture),self.margins["left"],y0+self.margins["bottom"],height_mo,height_mo,FontsSmallTable,TableBorders,Layout,showDOW=True)
        self.addMonthTable(self.NextMonth(MonthPicture),self.width-height_mo-self.margins["right"],y0+self.margins["bottom"],height_mo,height_mo,FontsSmallTable,TableBorders,Layout,showDOW=True)
        self.pcal.saveState()
        #add the name of the month
        self.pcal.setFont("Times-Roman", FontSizeMonthName)
        tit = self.CalendarLine(MonthPicture,sep="\n")
        self.pcal.drawCentredString(self.width / 2, y0+height_mo/2,  tit)
        self.pcal.saveState()

        #add the publicity line at the bottome of the page
        self.pcal.setFont("Times-Roman", 6)
        self.pcal.drawCentredString(self.width / 2, y0+height_mo/4, self.pub[self.langlist[0]])
        self.pcal.restoreState()
        self.pcal.restoreState()
        
        if self.template == "bound-middle":
            self.pcal.showPage() #START A NEW PAGE

        
        """
        MONTH TABLE
        """
        if self.template == "bound-middle":
            wmar = self.margins["left"]
            hmar = self.margins["top"]
            wm = self.width - 2*wmar
            hm = self.height - 2*hmar
        elif self.template == "bound-top":
            wmar = self.margins["left"]
            hmar = self.margins["top"]
            wm = self.width - 2*wmar
            hm = self.height/2 - 2*hmar
        elif self.template == "stapled-middle":
            wmar = self.margins["left"]
            hmar = self.margins["top"]
            wm = self.width - 2*wmar
            hm = self.height/2 - 2*hmar
        elif self.template == "bound-top-no-pix":
            wmar = self.margins["left"]
            hmar = self.margins["top"]
            wm = self.width - 2*wmar
            hm = self.height- height_mo - 2*hmar
        else:
            raise Exception("wrong calendar template")

        Layout = {"quantieme":"tl"}
        TableBorders = {"ShowBorders":True,"ShowLastMonthBorder":True,"ShowNextMonthBorder":True,"ShowHeaderBorder":True}
        self.addMonthTable(MonthTable,wmar,hmar,wm,hm,FontsBigTable,TableBorders,Layout,showMonthName=False,showDOW=True,HeaderRatio = 0.2,nDOW=0)
        self.pcal.showPage()  #START A NEW PAGE

        if self.template == "stapled-middle" and MonthStart.month < (NumberMonths+1.0)/2:
            self.pcal.saveState()
            self.pcal.rotate(180)
            self.pcal.translate(-1*self.width, hmar-1.5*self.height) #90 deg, dx = self.width,dy=-self.height
            self.addMonthTable(MonthPicture,x0,y0,wm,hm,FontsBigTable,TableBorders,Layout,showMonthName=False,showDOW=True,HeaderRatio = 0.2,nDOW=0)
            self.pcal.restoreState()
            
            self.pcal.saveState()
            self.pcal.translate(self.width / 2, 1.0/2*localheight)
            self.pcal.rotate(180)
            if self.ShowPix:
                #MonthPicturePath = self.defaultpath+self.conf["pictures"][(NumberPages+1-MonthStart.month) %len(self.conf["pictures"])]["path"]
                MonthPicturePath = abspath(join(self.defaultpath,self.conf["pictures"][(NumberPages+1-MonthStart.month) %len(self.conf["pictures"])]["path"]))
                self.pcal.drawImage(MonthPicturePath,-self.width/2+self.margins["right"],self.margins["top"]+height_mo-self.height/4,self.width-2*self.margins["right"],localheight-height_mo-2*self.margins["top"],preserveAspectRatio=self.preserveAspectRatio)
                #self._log("pictures",Pictures,0)
            else:
                self.pcal.drawCentredString(0, 0,  "Picture displayed here")
            self.pcal.restoreState()
            
            
            self.pcal.saveState()
            self.pcal.translate(self.width / 2, y0-height_mo/4)
            self.pcal.rotate(180)
            
#            Fonts = {"Font_Size_DOM":8,"Font_Size_DOW":Font_Size_DOW_Small_Table,"FontType":"Times-Roman"}
            Layout = {"quantieme":"c"}
            TableBorders = {"ShowBorders":False,"ShowLastMonthBorder":False,"ShowNextMonthBorder":False,"ShowHeaderBorder":False}
#            self.addMonthTable(self.PrevMonth(MonthStart),self.margins["left"],y0-self.margins["bottom"]-height_mo,height_mo,height_mo,Fonts,TableBorders,Layout,showDOW=True)
#            self.addMonthTable(self.NextMonth(MonthStart),self.width-height_mo-self.margins["right"],y0-self.margins["bottom"]-height_mo,height_mo,height_mo,Fonts,TableBorders,Layout,showDOW=True)
            self.addMonthTable(self.PrevMonth(MonthTable),-self.width/2+0*height_mo+self.margins["left"],0,height_mo,height_mo,FontsSmallTable,TableBorders,Layout,showDOW=True)
            self.addMonthTable(self.NextMonth(MonthTable),self.width/2-height_mo-self.margins["right"],0,height_mo,height_mo,FontsSmallTable,TableBorders,Layout,showDOW=True)
            self.pcal.saveState()
            #add the name of the month
            self.pcal.setFont("Times-Roman", FontSizeMonthName)
            #self.pcal.setFont("DejaVuSans", FontSizeMonthName)
            tit = self.CalendarLine(MonthTable,sep="\n")
            self.pcal.drawCentredString(0, 0,  tit)
            self.pcal.restoreState()
            self.pcal.restoreState()
            self.pcal.showPage()

      
    def Save(self):
        pyICSver = pyiCalendar.iCalendar.version
        self.pcal.setAuthor(self.author)
        self.pcal.setCreator(AnnumMoto +" - pyICSParser v"+pyICSver)
        
        #encrypt = reporlab.pdfencrypt.StandardEncryption(     "", canPrint=1, canModify=0, canCopy=0, canAnnotate=0 ) 
        #self.pcal.setEncrypt(encrypt)
        #self.pcal.
        self.pcal.setProducer("1-annum.com CAL2PDF engine")
        self.pcal.setTitle(self.title)
        self.pcal.setSubject("Personal Calendar")
        self.pcal.save()
        self.pcal= None
    def SetConfiguration(self,path,CreateTempFile):
        pass

    def LoadICS(self, ResesetCalDates = False):
        #we use one month before and after for generating dates from ical files 
        #to secure that the small calendars also display the right info
        if ResesetCalDates:
            self.CalDates = {}
        dtstart = datetime.datetime.strptime(self.conf["dtstart"],"%Y%m%d")
        new_dtstart =self.PrevMonth(dtstart).strftime("%Y%m%d")
        dtend = datetime.datetime.strptime(self.conf["dtend"],"%Y%m%d")
        new_dtend = self.NextMonth(self.NextMonth(dtend)).strftime("%Y%m%d")
        print("scanning ICS on dates:",new_dtstart ,new_dtend,dtstart,dtend)
#        mycal = ical.ics(new_dtstart ,new_dtend)
        mycal = pyiCalendar.iCalendar()
        print("*** \t generating pdf from ical with pyICSParser v%s \t ***"%(mycal.version))
        calindex=-1
        old_percentage=0
        print("loading ICS:")
        for cal in self.conf["icals"]:
            calindex +=1
            log_msg = "parsing calendar"+cal["ical"]
            self._log("parsing calendar", cal["ical"], level = -1)
            logging.info(log_msg)
#            print "loading cal: %s/%s"%(calindex,len(self.conf["icals"]))
            percentage = int((10.0*calindex)/len(self.conf["icals"]))

            if percentage == old_percentage:
                pass
            else:
                self.PrintConsoleProgress(percentage*10)
                old_percentage = percentage
            ics_full_path = abspath(join(self.defaultpath,cal["ical"]))
            try:
                #FIXME: here report the error code when failing to load: if BYMONTH=t
                mycal.local_load(ics_full_path)
                dates = mycal.get_event_instances(new_dtstart,new_dtend)
            except:
                logging.warning("failed to load:%s"%(ics_full_path))
                dates = []
#            mycal.parse_loaded()
            #before: 
#            mycal.flatten()
#            dates = sorted(mycal.flat_events)
            #after - from 0.6.1y4'
            for (date, summary, uid) in dates:
                if not (type(date) == type(datetime.datetime.now().date())):
                    date = date.date()
                if date not in self.CalDates:
                    self.CalDates[date]=[]
                    self.CalDates[date].append([calindex,summary])
                else:
                    self.CalDates[date].append([calindex,summary])
            if len(dates)<3:
                #if the calendar does not have any dates (or less than 3), warn about this
                logging.warning("calendar: %s\n\thas <3 dates in selected time interval"%(ics_full_path))
                print(dates)
            cal["dates"]=dates
        self.PrintConsoleProgress(100)
        print("DONE, ICS loaded and parsed")

    def PrintConsoleProgress(self,ratio):
        sys.stdout.write(str(ratio) + "% ")
        sys.stdout.flush()


    def Generate(self):
        Title= self.conf["Calendar_Title"]
        subTitle = self.conf["Calendar_SubTitle"]
        dtstart = self.conf["dtstart"]
        year = int(dtstart[0:4])
        MonthStart = int(dtstart[4:6])
        day = int(dtstart[6:8])
        
        self.margins["top"]=1.5*self.height/100
        self.margins["left"]=1.5*self.width/100
        self.margins["bottom"]=self.margins["top"]
        self.margins["right"]=self.margins["left"]

        calStart = datetime.date(year,MonthStart,day)
        dtend = self.conf["dtend"]
        year = int(dtend[0:4])
        MonthEnd = int(dtend[4:6])
        day = int(dtend[6:8])
        dtend = datetime.date(year,MonthEnd,day)
        index = 0
        
        rotate_title = 0
        if self.template=="bound-middle":
            xtitle = self.width/2
            ytitle = self.height/2
            xsubtitle = self.width/2
            ysubtitle= 50
        elif self.template=="bound-top":
            xtitle = self.width/2
            ytitle = self.height/2
            xsubtitle = self.width/2
            ysubtitle= 50
        elif self.template=="stapled-middle":
            xtitle = self.width/2
            ytitle = (3.0*self.height)/4
            xsubtitle = self.width/2
            ysubtitle= self.height-50
            rotate_title = 180
        elif self.template=="bound-top-no-pix":
            """ binding at the top and no pictures between top and 
            the month title """
            xtitle = self.width/2
            ytitle = self.height/2
            xsubtitle = self.width/2
            ysubtitle= 50

        self.pcal.saveState()
        self.pcal.setFont("Times-Roman", 100)
        self.pcal.translate(xtitle,ytitle)
        self.pcal.rotate(rotate_title)
        self.pcal.drawCentredString(0, 0,  Title)
        self.pcal.restoreState()

        self.pcal.saveState()
        self.pcal.setFont("Times-Roman", 6)
        self.pcal.translate(xsubtitle, ysubtitle)
        self.pcal.rotate(rotate_title)
        self.pcal.drawCentredString(0, 0,  subTitle)
        self.pcal.restoreState()

        self.pcal.showPage()
        while (calStart <= dtend):
            self.addMonth(calStart,NumberMonths = MonthEnd-MonthStart+1, CalType = self.conf["calscale"]) #,Pictures = self.conf["pictures"][index % (len(self.conf["pictures"]))])
            calStart = self.NextMonth(calStart)
            self._log("printing month", [calStart.month], level = -1)
            index +=1


    
