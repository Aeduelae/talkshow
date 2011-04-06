import os
import math
from wrappers import *
from widget import *
import glob
import subprocess
import pyglet
from delayed_call import *
import animated_property
import time
from win32process import TerminateProcess
from datetime import datetime, timedelta
import _winreg

def normalizePath(path):
    path = path.replace("\\", "/")
    while "//" in path:
        path = path.replace("//", "/")
    return path

def WindowsPath(path):
    path = path.replace("/", "\\")
    # return absolute path
    return os.getcwd() + path[1:]

def clamp(v, low=0.0, high=1.0):
    if v>high: v = high
    if v<low: v = low
    return v

class Field(Widget):    
    def __init__(self, parent, x, y, w, h, text):
        Widget.__init__(self, parent, "Field", w = w, h = h, x = x, y = y)
        border = self.border = Rect(self, "border", 0, 0, w, h, color="#1f1f1f")        
        border.opacity=0
        bg = self.bg = Rect(self, "bg", 2, 2, w-4, h-4)        
        bg.color = "#7f7f7f"
        l = self.label = Label(self, "label", x=20, y=20, size=h/5, text=text)        
        self.PROGRESS = 0

    def startHighlight(self):
        #self.border.animate("opacity", 1, 0, 0, 250)
        self.bg.animate("opacity", 0, 1, 0, 250)

    def doLayout(self, new_w, new_h):
        self.border.extent = new_w, new_h
        self.bg.extent = new_w-4, new_h-4        
        self.label.size = new_h/5
        if hasattr(self, "icon"):
            self.icon.x = (self.w - self.icon.w) / 2.0
            self.icon.y = (self.h - self.icon.h) / 2.0

    def _getTEXT(self):
        return self.label.text
    def _setTEXT(self, t):
        self.label.text = t        
    text = property(_getTEXT, _setTEXT)
    
    def _getCOLOR(self):
        return self.bg.color            
    def _setCOLOR(self, c):        
        self.bg.color = c
    color = property(_getCOLOR, _setCOLOR)
    
    def _getPROGRESS(self):
        return self.PROGRESS        
    def _setPROGRESS(self, p):
        self.PROGRESS = p
        self.label.progress = clamp((p - 0.5) / 0.5)        
        box_progress = clamp(p / 0.5)
        
        self.bg.w = (self.w-4) * box_progress
        self.bg.h = (self.h-4) * box_progress
        self.bg.x = 2+ (self.w-4)/2 - ((self.w-4)/2 * box_progress)
        self.bg.y = 2+ (self.h-4)/2 - ((self.h-4)/2 * box_progress)
           
        self.bg.opacity = box_progress          
        if hasattr(self, "icon"): self.icon.opacity = box_progress
    progress = property(_getPROGRESS, _setPROGRESS)


    def _getOPACITY(self):
        return self.bg.opacity
    def _setOPACITY(self, o):        
        self.bg.opacity = o        
    opacity = property(_getOPACITY, _setOPACITY)

class Grid(Widget):
    instanceCount = 0
    
    def __init__(self, parent, fieldCount, delegate):
        Widget.__init__(self, parent, "Grid", w = parent.w, h = parent.h)
        self.delegate = delegate
        self.fields = []
        cols = round(math.sqrt(fieldCount) * 1) #parent.w / parent.h)
        rows = fieldCount / cols
        if rows != int(rows):
            rows += 1

        rows = int(rows)
        cols = int(cols)
        #print cols, rows

        w = int(parent.w / cols)
        h = int(parent.h / rows)

        i = 0
        for r in range(rows):
            for c in range(cols):
                if i < fieldCount:
                    field = Field(self, w=w-4, h=h-4, x=w*c, y=h*r, text=delegate.getFieldText(i))
                    icon = delegate.getFieldIcon(i)
                    if icon != None:
                        field.icon = icon
                        icon.parent = field  
                        field.doLayout(field.w, field.h)      
                    field.progress=0                
                    field.animate("progress", 0, 1, 0, 250)
                    field.color = "#%2X%2X00" % (int(255 * (c+1)/cols), int(255 * (r+1)/rows))
                    field.index = i
                    self.fields.append(field)
                    i += 1
                    
    def onMouseButtonDown(self, button, x, y):
        field = None
        for f in self:
            if f.contains(x,y):
                field = f
        
        if field != None:
            self.delegate.onFieldClicked(field)

    def enterFIeld(self, field):
        
        if field != None:
            for f in self:
                if f != field:
                    f.animate("progress", f.progress, 0, 0, 250)
            
            delay = 125
            duration = 250
            field.animate("x", field.x, 0.0, delay, duration)
            field.animate("y", field.y, 0, delay, duration)
            field.animate("w", field.w, self.w, delay, duration)
            field.animate("h", field.h, self.h, delay, duration)
            field.animate("opacity", field.opacity, 0, delay+duration, duration)
            self.delegate.bg.animate("color", self.delegate.bg.color, field.color, delay+duration, duration)
            if hasattr(field, "icon"):
                field.icon.animate("opacity", field.opacity, 0, delay*2, duration)
                
       
class Talkshow(Widget):
    def __init__(self, screen):
        Widget.__init__(self, screen, "Talkshow", w=screen.w, h=screen.h)
                
        Titleheight        = self.h/50
        
        screenmarginvert   = self.h/100 #10
        screenmarginhoriz  = screenmarginvert
        
        bgmarginvert       = self.h/100 #10
        bgmarginhoriz      = bgmarginvert
        
        Headwidth          = 0
        Footwidth          = 0
        Rightwidth         = self.w/10
        Leftwidth          = Rightwidth
        
        BackGroundWidth    = self.w - 2 * screenmarginhoriz - Rightwidth - Leftwidth
        BackGroundHeigth   = self.h - 2 * screenmarginvert  - Headwidth  - Footwidth
        BackGroundPosX     = screenmarginhoriz + Leftwidth
        BackGroundPosY     = screenmarginvert  + Headwidth
        
        GridContainerWidth  = BackGroundWidth  - 2 * bgmarginhoriz
        GridContainerHeigth = BackGroundHeigth - 2 * bgmarginvert
        GridContainerPosX   = BackGroundPosX + bgmarginhoriz
        GridContainerPosY   = BackGroundPosY + bgmarginvert
        
        quitButtonWidth    = Rightwidth
        quitButtonHeight   = Rightwidth
        quitButtonPosX     = self.w - screenmarginhoriz - quitButtonWidth
        quitButtonPosY     = screenmarginvert
        
        AttButtonWidth     = Leftwidth
        AttButtonHeight    = Leftwidth
        AttButtonPosX      = screenmarginhoriz
        AttButtonPosY      = screenmarginvert + Headwidth 
        
        homeButtonWidth    = Leftwidth
        homeButtonHeight   = Leftwidth
        homeButtonPosX     = screenmarginhoriz 
        homeButtonPosY     = self.h - screenmarginvert - Footwidth - homeButtonHeight
        
        backButtonWidth    = Leftwidth
        backButtonHeight   = Leftwidth
        backButtonPosX     = screenmarginhoriz
        backButtonPosY     = homeButtonPosY - backButtonHeight
        
        VolumeSliderWidth  = Rightwidth
        VolumeSliderHeight = 2 * Rightwidth
        VolumeSliderPosX   = self.w - screenmarginhoriz - VolumeSliderWidth
        VolumeSliderPosY   = self.h - screenmarginvert - Footwidth - VolumeSliderHeight
        
        self.bg = Rect(self, "bg",  w = BackGroundWidth , h=BackGroundHeigth, x=BackGroundPosX, y=BackGroundPosY, color="#202020")
        
        self.gridContainer       = Widget(self, "gridContainer",  w = GridContainerWidth, h = GridContainerHeigth, x = GridContainerPosX, y = GridContainerPosY)
        
        b = self.quitButton      = Button(self, "quitbutton"   ,  w = quitButtonWidth   , h = quitButtonHeight,    x = quitButtonPosX,    y = quitButtonPosY,   handler = self.quit, text='X')        

        b = self.AttentionButton = Button(self, "attentionbutton",w = AttButtonWidth    , h = AttButtonHeight,     x = AttButtonPosX,     y = AttButtonPosY,    handler = self.DrawAttention, text='!')
        
        b = self.backButton      = Button(self, "backbutton",     w = backButtonWidth   , h = backButtonHeight,    x = backButtonPosX,    y = backButtonPosY,   handler = self.back, text='<')
                         
        self.homeButton          = Button(self, "homebutton",     w = homeButtonWidth   , h = homeButtonHeight,    x = homeButtonPosX,    y = homeButtonPosY,   handler = self.home, text="<<")
        
        self.volumeSlider         = Slider(self, "volume"    ,    w = VolumeSliderWidth , h = VolumeSliderHeight,  x = VolumeSliderPosX,  y = VolumeSliderPosY, action = self.setVolume)
        self.volumeSlider.knobPosition = 0.0
        
        self.count = 9        
        
        self.pathPrefix = "./Content/"
        self.path= ""
        self.grid = None
        self.videoplayer = None
        self.gridFromPath()
        #self.newGrid()
        
        l = self.label = Label(self, "title", x=GridContainerPosX + 10, y=GridContainerPosY, size=Titleheight, text = "KommHelp Talkshow", color = "#0030ff")        
        #l.animate("progress", 0, 1, 0, 3000)
        
    def quit(self):
        sys.exit(0)
    
    def getFieldText(self, i):
         return self.items[i]
        
    def pathForField(self, i):
        path = self.path + "/" + self.items[i]
        if path[0] == "/": path = path[1:]
        return path
             
    def getFieldIcon(self, i):
        path = self.pathForField(i)
        return self.iconForPath(self.pathPrefix + path)
         
    def onFieldClicked(self, f):        
        if f != None:
            f.startHighlight()
            
            if f.index<len(self.items):
              subfields = self.subdirs(self.pathPrefix, self.pathForField(f.index))
              
              if len(subfields)>0:
                  #self.path = self.pathForField(f.index)     

                  self.grid.enterFIeld(f)
                  self.dc = DelayedCall(self.gridFromPath, 500, (f.color, self.pathForField(f.index)))
              self.playPath(self.pathPrefix + self.pathForField(f.index))
              #self.playPath_AudioRecorder(self.pathPrefix + self.pathForField(f.index))
    
    def iconForPath(self, path):
        #print path
        images = glob.glob(path+"/*.png")
        if images:
            path = normalizePath(images[0])
            #print path
            i = Image(None, path, path)
            return i
        return None
          
    def cancelVideo(self):
        if self.videoplayer:
            self.videoplayer.unref()
            self.videoplayer.parent = None
            self.videoplayer = None
    
    def playPath(self, path):
        
        WaveSounds = glob.glob(path+"/*.wav")
        #print "sounds", sounds
        if WaveSounds:
            wave = normalizePath(WaveSounds[0])
            print 'playing: ', wave
            s = self.sound  = Sound(0, wave)
            s.speed=1
        else:
            Media = glob.glob(path+"/*.avi") + glob.glob(path+"/*.wmv") + glob.glob(path+"/*.mpg") + glob.glob(path+"/*.mp3") + glob.glob(path+"/*.wma") + glob.glob(path+"/*.asf") + glob.glob(path+"/*.midi") + glob.glob(path+"/*.aiff") + glob.glob(path+"/*.au")
        
            if Media:
           
                if sys.platform == 'win32':
                    try:
                        RegKey         = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,'Software\\Microsoft\\MediaPlayer\\Setup\\CreatedLinks')
                    except:
                        print 'Sorry. Media Player not found.'
                        return
                        
                    self.MediaPlayerExe = _winreg.QueryValueEx(RegKey,'AppName')[0] + ' '
                    print self.MediaPlayerExe
                    MediaString = ''
                    for filename in Media:
                        WinName = WindowsPath(filename)
                        MediaString = MediaString + '"' + WinName + '"'
                    
                    self.play_MediaPlayer(MediaString)
                    return
                else:
                    print 'Sorry. Currently, media other than *.wav files can only be played back on Windows 32 systems.'

            
    #def play_AudioRecorder(self, mp3):
    #    AudioRecorderExe = 'c:\WINDOWS\system32\sndrec32.exe '
    #    #Arguments        = '/embedding /play /close '
    #    Arguments        = '/play /close '
    #    os.system(AudioRecorderExe + Arguments + '"' + mp3 + '"')
            
    def play_MediaPlayer(self, media):
        #MediaPlayerExe = os.getcwd() + '\\content\\Verknüpfung mit wmplayer.exe.lnk '
        #MediaPlayerExe = 'C:\\Programme\\Windows Media Player\\wmplayer.exe '
        
        Arguments      = ' '
        
        print 'PLAYING:', self.MediaPlayerExe + media
        screen.window.set_fullscreen(0)
        
        process = subprocess.Popen(self.MediaPlayerExe + media + Arguments)
        
        process.wait()
        screen.window.set_fullscreen(1)
    
    def Terminate_Process(self, process):
        TerminateProcess(process._handle, 1)
                
    def setVolume(self, v):
        #print "Volume", v
        #tubifex.volume = v
        Sound.setGlobalVolume(v)
        
    def back(self):
        l = self.path.split("/")

        if l:
            self.path= "/".join(l[:-1])
            self.gridFromPath(("#000000",self.path))
            self.cleanUp()
  
    def home(self):
        l = self.path = ""
        self.gridFromPath()
        self.cleanUp()
              
    def subdirs(self, prefix, path):
        items = os.listdir(unicode(prefix+path))        
        items = filter(lambda x: os.path.isdir(prefix + path + "/" + x), items)            
        #print items
        return items
                
    def gridFromPath(self, color_and_path = None):
        path = ""
        color="#000000"
        if color_and_path:
            color, path = color_and_path
        
        print self.pathPrefix+ path
        self.path = path
        #print items
        self.items =  self.subdirs(self.pathPrefix, self.path)
        #print self.items
        self.count = len(self.items)
        if self.count:
            self.newGrid(color)
        
    def newGrid(self, color="#000000"):
        self.bg.color=color
        self.grid = Grid(self.gridContainer, self.count, self)
        print "instanceCount", Grid.instanceCount
        self.cleanupDC = DelayedCall(self.cleanUp, 375)

    def cleanUp(self):
        self.cancelVideo()
        
        # remove all children from gridCOntainer except the last one
        c = len(self.gridContainer)
        i = 0
        for x in self.gridContainer:
            if i<c-1:
                x.parent = None
            i+=1
            

    def key_sink(self, k):
        if k=="+":
            self.count += 1
            self.newGrid()
        if k=="-":
            self.count -= 1
            self.newGrid()
            
    def DrawAttention(self):
        self.playPath(self.pathPrefix + '/Alarm')


#environment.set("character_spacing", -2)                    

screen = Screen("Talkshow", "", 1280, 768)
talkshow = Talkshow(screen)

#tubifex.keyboard_sink = talkshow.key_sink
screen.event_handler = talkshow

# boilerplate
def tick():
    animated_property.T = time.time()*1000
    animated_property.AnimatedProperty.tick()
    return True

pc = PeriodicCall(tick,0)
pyglet.app.run()