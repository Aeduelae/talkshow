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
if sys.platform == 'win32':
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

def ExpandPath(path):
    path = os.path.expandvars(path[:-4].replace('%','$')).replace('$','')
    return path
    
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
                
        self.screen = screen
        self.SetLayout('Vertical')
        
        #self.DoLayout()
        
        self.count = 9        
        
        self.pathPrefix = "./Content/"
        self.path= ""
        self.grid = None
        self.videoplayer = None
        self.MenuFlag = 0
        self.gridFromPath()
        self.SetPlayer('VLC')
        
        #self.newGrid()
        
        
        #l.animate("progress", 0, 1, 0, 3000)
        
    def GetWidgetSize(self,name,Alignment):
        if Alignment == 'Vertical':            
            self.Headwidth          = 0
            self.Footwidth          = 0
            self.Rightwidth         = self.w/10
            self.Leftwidth          = self.Rightwidth
            
        else: 
            self.Headwidth          = self.h/10
            self.Footwidth          = self.Headwidth
            self.Rightwidth         = 0
            self.Leftwidth          = 0
        
        self.screenmarginvert   = self.h/100 #10
        self.screenmarginhoriz  = self.screenmarginvert
        
        self.bgmarginvert       = self.h/100 #10
        self.bgmarginhoriz      = self.bgmarginvert  
            
        
        if name == 'bg':
            w = self.BackGroundWidth    = self.w - 2 * self.screenmarginhoriz - self.Rightwidth - self.Leftwidth 
            h = self.BackGroundHeigth   = self.h - 2 * self.screenmarginvert  - self.Headwidth  - self.Footwidth
            x = self.BackGroundPosX     = self.screenmarginhoriz + self.Leftwidth
            y = self.BackGroundPosY     = self.screenmarginvert  + self.Headwidth
            handler = None
            text = ''
            isbutton = 0

        elif name == 'gridContainer':
            w = self.GridContainerWidth  = self.BackGroundWidth  - 2 * self.bgmarginhoriz
            h = self.GridContainerHeigth = self.BackGroundHeigth - 2 * self.bgmarginvert
            x = self.GridContainerPosX   = self.BackGroundPosX + self.bgmarginhoriz
            y = self.GridContainerPosY   = self.BackGroundPosY + self.bgmarginvert
            handler = None
            text = ''
            isbutton = 0
         
        elif name == 'quitbutton': 
            w = self.quitButtonWidth    = self.Rightwidth  + self.Headwidth
            h = self.quitButtonHeight   = self.Rightwidth  + self.Headwidth
            x = self.quitButtonPosX     = self.w - self.screenmarginhoriz - self.quitButtonWidth
            y = self.quitButtonPosY     = self.screenmarginvert
            handler = self.quit
            text = 'X'
            isbutton = 1
            
        elif name == 'menubutton':
            w = self.menuButtonWidth    = self.Rightwidth  + self.Headwidth
            h = self.menuButtonHeight   = self.Rightwidth  + self.Headwidth
            x = self.menuButtonPosX     = self.w - self.screenmarginhoriz - self.Rightwidth - 2 * self.Headwidth
            y = self.menuButtonPosY     = self.screenmarginvert + 2 * self.Rightwidth
            handler = self.menu
            text = 'M'
            isbutton = 1
        
        elif name == 'attentionbutton':
            w = self.AttButtonWidth     = self.Leftwidth + self.Footwidth
            h = self.AttButtonHeight    = self.Leftwidth + self.Footwidth
            x = self.AttButtonPosX      = self.screenmarginhoriz
            y = self.AttButtonPosY      = self.screenmarginvert
            handler = self.DrawAttention
            text = '!'
            isbutton = 1
        
        elif name == 'homebutton':
            w = self.homeButtonWidth    = self.Leftwidth  + self.Footwidth
            h = self.homeButtonHeight   = self.Leftwidth  + self.Footwidth
            x = self.homeButtonPosX     = self.screenmarginhoriz 
            y = self.homeButtonPosY     = self.h - self.screenmarginvert - self.homeButtonHeight
            handler = self.home
            text = '<<'
            isbutton = 1
        
        elif name == 'backbutton':
            w = self.backButtonWidth    = self.Leftwidth  + self.Footwidth
            h = self.backButtonHeight   = self.Leftwidth  + self.Footwidth
            x = self.backButtonPosX     = self.screenmarginhoriz + self.Footwidth
            y = self.backButtonPosY     = self.homeButtonPosY    - self.Leftwidth
            handler = self.back
            text = '<'
            isbutton = 1
        
        elif name == 'volume':
            w = self.VolumeSliderWidth  = self.Rightwidth  + self.Headwidth
            h = self.VolumeSliderHeight = 2 * self.Rightwidth
            x = self.VolumeSliderPosX   = self.w - self.screenmarginhoriz - self.VolumeSliderWidth
            y = self.VolumeSliderPosY   = self.h - self.screenmarginvert - self.Footwidth - self.VolumeSliderHeight
            handler = self.setVolume
            text = ''
            isbutton = 0
        else:
            x = 0
            y = 0
            w = 0
            h = 0
            handler = None
            text = ''
            isbutton = 0
            
#        VolumeSliderWidth  = 2 * Footwidth
#        VolumeSliderHeight = Footwidth
#        VolumeSliderPosX   = self.w - screenmarginhoriz - VolumeSliderWidth
#        VolumeSliderPosY   = self.h - screenmarginvert  - VolumeSliderHeight
        
        return [x, y, w, h, handler, text, isbutton]
    
    def SetLayout(self,Alignment):
        
        name = 'bg'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        self.bg              = Rect  (self, name,  w = self.BackGroundWidth , h=self.BackGroundHeigth, x=self.BackGroundPosX, y=self.BackGroundPosY, color="#202020")
        
        name = 'gridContainer'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        self.gridContainer   = Widget(self, name,  w = self.GridContainerWidth, h = self.GridContainerHeigth, x = self.GridContainerPosX, y = self.GridContainerPosY)
        
        name = 'quitbutton'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        self.quitButton      = Button(self, name   ,  w = self.quitButtonWidth   , h = self.quitButtonHeight,    x = self.quitButtonPosX,    y = self.quitButtonPosY,   handler = handler, text=text)        
        
        name = 'menubutton'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        self.menuButton      = Button(self, name   ,  w = self.menuButtonWidth   , h = self.menuButtonHeight,    x = self.menuButtonPosX,    y = self.menuButtonPosY,   handler = handler, text=text)
        
        name = 'attentionbutton'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        self.AttentionButton = Button(self, name,w = self.AttButtonWidth    , h = self.AttButtonHeight,     x = self.AttButtonPosX,     y = self.AttButtonPosY,    handler = handler, text=text)
        
        name = 'homebutton'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        self.homeButton      = Button(self, name,     w = self.homeButtonWidth   , h = self.homeButtonHeight,    x = self.homeButtonPosX,    y = self.homeButtonPosY,   handler = handler, text=text)
        
        name = 'backbutton'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        self.backButton      = Button(self, name,     w = self.backButtonWidth   , h = self.backButtonHeight,    x = self.backButtonPosX,    y = self.backButtonPosY,   handler = handler, text=text)
        
        name = 'volume'
        [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(name,Alignment)
        #self.volumeSlider   = Slider(self, "volume"    ,    w = self.VolumeSliderWidth , h = self.VolumeSliderHeight,  x = self.VolumeSliderPosX,  y = self.VolumeSliderPosY, action = self.setVolume)
        #self.volumeSlider.knobPosition = 0.0
        
        
        #x = self.GridContainerPosX + 10
        #y = self.GridContainerPosY
        
        size = self.h/30
        x    = self.w/2
        y    = self.screenmarginvert + 5 
        
        self.label           = Label (self, 'title', x, y, size, text = "KommHelp Talkshow", color = "#0030ff")
        
        self.label.x = self.w/2 - self.label.w/2
          
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
                MediaString = ''
                for filename in Media:
                    WinName = WindowsPath(filename)
                    MediaString = MediaString + ' "' + WinName + '"'
                #print MediaString
                self.play_MediaPlayer(MediaString)
                return
            
            
    #def play_AudioRecorder(self, mp3):
    #    AudioRecorderExe = 'c:\WINDOWS\system32\sndrec32.exe '
    #    #Arguments        = '/embedding /play /close '
    #    Arguments        = '/play /close '
    #    os.system(AudioRecorderExe + Arguments + '"' + mp3 + '"')
            
    def play_MediaPlayer(self, media):
        
        Arguments      = '--volume=1 '

        screen.window.set_fullscreen(0)
        print 'Play command: ', self.MediaPlayerExe + Arguments + media
        process = subprocess.Popen(self.MediaPlayerExe + Arguments + media)
        
        process.wait()
        screen.window.set_fullscreen(1)
    
    def SetPlayer(self,Player):
        if sys.platform == 'win32':
            if Player == 'VLC':
                KeyName = 'SOFTWARE\\VideoLAN\\VLC'
                AppName = ''
                
            elif Player == 'WMP':
                KeyName = 'Software\\Microsoft\\MediaPlayer\\Setup\\CreatedLinks'
                AppName = 'AppName'
                
            else: 
                print 'Media player not defined.'
            try:
                
                RegKey     = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,KeyName)
                Executable = ExpandPath(_winreg.QueryValueEx(RegKey,AppName)[0])
            except:
                print 'Sorry. VLC not found.'
                return
                
            
            self.MediaPlayerExe = Executable + ' '            
            print self.MediaPlayerExe
            
        else:
            print 'Sorry. Currently, media other than *.wav files can only be played back on Windows 32 systems.'

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
        if self.MenuFlag:
            self.MenuFlag = 0
            self.menuButton.h = self.menuButtonWidth
            self.backButton.h = self.backButtonWidth
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
        if self.MenuFlag:
            ok = self.MenuCommand(path[path.rfind('/')+1:])
            if ok:
                self.gridFromPath()
                self.home()
                return
                #pass
            
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
        
    def menu(self):

        self.menuButton.h = 0
        self.backButton.h = 0
        self.MenuFlag = 1
        self.gridFromPath(("#000000",'../Menu'))
        self.cleanUp()
    
    def MenuCommand(self,Command):
        print 'Menu Befehl: ',Command
        if Command == 'Horizontal' or Command == 'Vertical':
            
            for c in self.screen.__children__[0]:
                
                [x, y, w, h, handler, text, isbutton] = self.GetWidgetSize(c.name,Command)
                if not(x==0 and y==0 and w==0 and h==0):
                    if isbutton:
                        c.__init__(self, c.name, x=x, y=y, w=w, h=h, handler = handler,text=text)
                    else:
                        c.__init__(self, c.name, x=x, y=y, w=w, h=h)
            print 'ok'
            return 1

            
        elif Command == 'on':
            print 'Scan einschalten'
        elif Command == 'off':
            print 'Scan ausschalten'
        elif Command == 'Record sound':
            print 'Aufnahme'
        elif Command == 'Set volume':
            print 'Lautstaerke'
        elif Command == 'VLC':
            print 'VLC spielt'
            self.SetPlayer('VLC')
            return 1
        elif Command == 'Media Player':
            print 'Media'
            self.SetPlayer('WMP')
            return 1
            
        return 0
        

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