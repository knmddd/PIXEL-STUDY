from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import time

from PIL import Image, ImageDraw, ImageOps, ImageTk

from .core import QUADRANTS, ReminderQueue, Task, TaskStore
from .timer import Pomodoro


BG = '#fff3fa'
INK = '#402b4c'
RED = '#ff386a'
PINK = '#ff6d9d'
WHITE = '#fffaf3'
PURPLE = '#6b4bba'
ACCENTS = ('#eb4069', '#ca8d00', '#4475e7', '#15a385')
FONTS = ('Consolas', 'Courier New')


def asset(name: str) -> Path:
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    return root / 'assets' / name


def fit_pixel(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(im.convert('RGB'), size, method=Image.Resampling.NEAREST,
                        centering=(0.5, 0.5))


def font(size=14, bold=False):
    return ('Consolas', size, 'bold' if bold else 'normal')


class PixelStudyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('PixelStudy')
        self.geometry('1160x770')
        self.minsize(960, 645)
        self.configure(bg='#202033')
        try:
            self.iconphoto(True, tk.PhotoImage(file=str(asset('icon.png'))))
        except tk.TclError:
            pass

        self.store = TaskStore()
        self.queue = ReminderQueue()
        self.timer = Pomodoro()
        self._notified: set[str] = set()
        self.page = 'welcome'
        self._photos: list[ImageTk.PhotoImage] = []
        self.bg_item = None
        self.timer_id = None
        self.scrolls = [0, 0, 0, 0]
        self._resize_after = None
        self._gif_frames = []
        self._frame_index = 0
        self._frame_at = time.monotonic()
        self._backgrounds = {
            'meadow': Image.open(asset('meadow.png')).convert('RGB'),
            'night': Image.open(asset('night.jpg')).convert('RGB'),
        }
        try:
            gif = Image.open(asset('welcome.gif'))
            for i in range(getattr(gif, 'n_frames', 1)):
                gif.seek(i)
                self._gif_frames.append(gif.convert('RGB').copy())
        except (OSError, ValueError):
            self._gif_frames = [Image.open(asset('welcome_preview.jpg')).convert('RGB')]
        self._buttons = {
            'reminders': Image.open(asset('reminders_button.png')).convert('RGBA'),
            'pomodoro': Image.open(asset('pomodoro_button.png')).convert('RGBA'),
        }
        self._logo = Image.open(asset('pixelstudy_logo.png')).convert('RGBA')

        self.canvas = tk.Canvas(self, bg=BG, bd=0, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', self._resize)
        self.canvas.bind('<MouseWheel>', self._wheel)
        self.bind('<Escape>', self._escape)
        self.bind('<space>', self._space)
        self.after(150, self.render)
        self.after(180, self._tick)

    def _resize(self, _event=None):
        if self._resize_after:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(120, self.render)

    def _wh(self):
        return max(960, self.canvas.winfo_width()), max(645, self.canvas.winfo_height())

    def _escape(self, _event=None):
        if self.page in ('reminders', 'pomodoro'):
            self.set_page('menu')
        elif self.page == 'menu':
            self.set_page('welcome')

    def _space(self, event):
        if self.page == 'pomodoro' and event.widget == self:
            self.toggle_timer()

    def _wheel(self, event):
        if self.page != 'reminders':
            return
        w, h = self._wh()
        for i, (x, y, pw, ph) in enumerate(self._panel_geoms(w, h)):
            if x <= event.x <= x+pw and y <= event.y <= y+ph:
                self._scroll_quadrant(i, -1 if event.delta > 0 else 1)
                return

    def set_page(self, page):
        if self.page == 'pomodoro' and page != 'pomodoro':
            self.timer.pause()
        self.page = page
        self._frame_index = 0
        self._frame_at = time.monotonic()
        self.render()

    def _use_bg(self, background: Image.Image):
        self._photos = []
        photo = ImageTk.PhotoImage(background)
        self._photos.append(photo)
        self.bg_item = self.canvas.create_image(0, 0, image=photo, anchor='nw')

    def _text(self, x, y, content, size=15, color=INK, bold=False, anchor='center', tags=()):
        return self.canvas.create_text(x, y, text=content, fill=color, font=font(size, bold),
                                       anchor=anchor, tags=tags)

    def _small_task_button(self, x, y, text, color, action):
        """Create a small clickable button beside an assignment."""
        tag = f'action_{time.monotonic_ns()}'
        width = 51 if text == 'EDIT' else 62
        self.canvas.create_rectangle(x, y, x + width, y + 28, fill=color,
                                     outline='#ffffff', width=1, tags=(tag,))
        self._text(x + width / 2, y + 14, text, 10, '#ffffff', True, tags=(tag,))
        self.canvas.tag_bind(tag, '<Button-1>', lambda event: action())
        self.canvas.tag_bind(tag, '<Enter>', lambda event: self.canvas.config(cursor='hand2'))
        self.canvas.tag_bind(tag, '<Leave>', lambda event: self.canvas.config(cursor=''))

    def _pixel_button(self, x, y, w, h, title, action, color=RED, fontsize=14):
        tag = f'btn_{time.monotonic_ns()}'
        c = self.canvas
        # Strong pixel edges and little bottom shadow, based on the supplied buttons.
        pts = lambda X,Y,W,H: [X+10,Y, X+W-10,Y, X+W,Y+10,
                                X+W,Y+H-10, X+W-10,Y+H,
                                X+10,Y+H, X,Y+H-10, X,Y+10]
        c.create_polygon(pts(x+2,y+5,w,h), fill='#2b2644', outline='#2b2644',
                         width=2, tags=(tag,))
        shape = c.create_polygon(pts(x,y,w,h-4), fill=color, outline='#22223a',
                                 width=3, tags=(tag,))
        self._text(x+w/2,y+(h-4)/2,title,fontsize,'#fffaf6',True,tags=(tag,))
        def hover(_):
            c.itemconfigure(shape, fill=('#ff729a' if color==RED else '#8b71df'))
            c.configure(cursor='hand2')
        def leave(_):
            c.itemconfigure(shape, fill=color)
            c.configure(cursor='')
        c.tag_bind(tag,'<Enter>',hover)
        c.tag_bind(tag,'<Leave>',leave)
        c.tag_bind(tag,'<Button-1>',lambda _e: action())
        return tag

    def _logo_image(self, x, y, width):
        im = self._logo
        height = round(width * im.height / im.width)
        photo = ImageTk.PhotoImage(im.resize((int(width), int(height)), Image.Resampling.LANCZOS))
        self._photos.append(photo)
        self.canvas.create_image(x, y, image=photo, anchor='center')
        return height

    def _image_button(self, x, y, width, original, command):
        im = self._buttons[original]
        height = round(width * im.height / im.width)
        photo = ImageTk.PhotoImage(im.resize((int(width), int(height)), Image.Resampling.NEAREST))
        self._photos.append(photo)
        tag = f'img_{original}'
        self.canvas.create_image(x, y, image=photo, anchor='center', tags=(tag,))
        self.canvas.tag_bind(tag, '<Button-1>', lambda e: command())
        self.canvas.tag_bind(tag, '<Enter>', lambda e: self.canvas.config(cursor='hand2'))
        self.canvas.tag_bind(tag, '<Leave>', lambda e: self.canvas.config(cursor=''))
        return height

    def render(self):
        if not self.winfo_exists():
            return
        c = self.canvas
        c.delete('all')
        w, h = self._wh()
        self.timer_id = None
        if self.page == 'welcome':
            self._draw_welcome(w,h)
        elif self.page == 'menu':
            self._draw_menu(w,h)
        elif self.page == 'reminders':
            self._draw_reminders(w,h)
        elif self.page == 'pomodoro':
            self._draw_pomodoro(w,h)

    def _welcome_bg(self, w, h):
        bg = fit_pixel(self._gif_frames[self._frame_index], (w,h)).convert('RGBA')
        overlay = Image.new('RGBA', (w,h), (34,29,66,65))
        bg = Image.alpha_composite(bg,overlay)
        return bg.convert('RGB')

    def _draw_welcome(self,w,h):
        self._use_bg(self._welcome_bg(w,h))
        self._logo_image(w/2,h*.19,min(670,int(w*.66)))
        self._pixel_button(w/2-123,h*.47,246,59,'START',lambda:self.set_page('menu'),RED,20)
        self._pixel_button(w/2-123,h*.60,246,55,'EXIT',self.destroy,PURPLE,19)

    def _draw_menu(self,w,h):
        bg=fit_pixel(self._backgrounds['meadow'],(w,h)).convert('RGBA')
        overlay=Image.new('RGBA',(w,h),(0,15,38,26))
        bg=Image.alpha_composite(bg,overlay)
        self._use_bg(bg.convert('RGB'))
        self._logo_image(w/2,h*.14,min(525,int(w*.53)))
        bwidth=min(252,int(w*.28))
        self._image_button(w/2,h*.40,bwidth,'reminders',lambda:self.set_page('reminders'))
        self._image_button(w/2,h*.59,bwidth,'pomodoro',lambda:self.set_page('pomodoro'))
        self._pixel_button(28,h-70,155,45,'← BACK',lambda:self.set_page('welcome'),PURPLE,13)
        self._pixel_button(w-180,h-70,150,45,'EXIT',self.destroy,RED,13)

    def _panel_geoms(self,w,h):
        margin = 27
        gap = 17
        top = 140
        bottom = 20
        pw = (w-2*margin-gap)/2
        ph = (h-top-bottom-gap)/2
        return [(margin,top,pw,ph),(margin+pw+gap,top,pw,ph),
                (margin,top+ph+gap,pw,ph),(margin+pw+gap,top+ph+gap,pw,ph)]

    def _draw_reminders(self,w,h):
        bg=fit_pixel(self._backgrounds['meadow'],(w,h)).convert('RGBA')
        art=Image.new('RGBA',(w,h),(0,0,0,0))
        d=ImageDraw.Draw(art,'RGBA')
        d.rounded_rectangle((15,10,w-15,128),radius=20,fill=(253,248,254,211),outline=(255,255,255,240),width=3)
        colors=[(255,223,231,224),(255,242,212,225),(218,233,255,225),(215,252,233,224)]
        for i,(x,y,pw,ph) in enumerate(self._panel_geoms(w,h)):
            d.rounded_rectangle((int(x),int(y),int(x+pw),int(y+ph)),radius=21,
                                fill=colors[i],outline=(255,255,255,246),width=3)
        bg=Image.alpha_composite(bg,art)
        self._use_bg(bg.convert('RGB'))
        self._text(34,44,'✿ REMINDERS',27,'#c72b67',True,'w')
        self._text(35,82,'Sort your school tasks by urgency and importance.',13,'#4b4777',False,'w')
        self._pixel_button(w-460,27,136,46,'UNDO',self.undo,PURPLE,13)
        self._pixel_button(w-313,27,148,46,'+ ADD TASK',lambda:self.open_task_form(),RED,13)
        self._pixel_button(w-155,27,124,46,'← BACK',lambda:self.set_page('menu'),PURPLE,13)
        self._text(38,114,f'{len(self.store.tasks)} tasks  •  {sum(t.completed for t in self.store.tasks)} completed',
                   12,'#705971',False,'w')
        for i,(x,y,pw,ph) in enumerate(self._panel_geoms(w,h)):
            self._draw_quadrant(i,x,y,pw,ph)

    def _draw_quadrant(self,i,x,y,pw,ph):
        label = QUADRANTS[i]
        colors = ('#be2654','#926500','#2c56be','#007a5c')
        self._text(x+19,y+22,['I','II','III','IV'][i]+' · '+label,14,colors[i],True,'w')
        tasks = self.store.filtered_sorted(i)
        self._text(x+pw-93,y+22,f'({len(tasks)})',12,colors[i],True,'e')
        self._pixel_button(x+pw-75,y+8,59,32,'+',lambda i=i:self.open_task_form(default_quadrant=i),
                           PURPLE,18)
        start_y=y+49
        row_height=54
        visible=max(2,int((ph-85)//row_height))
        max_scroll=max(0,len(tasks)-visible)
        self.scrolls[i]=max(0,min(self.scrolls[i],max_scroll))
        page=tasks[self.scrolls[i]:self.scrolls[i]+visible]
        if not tasks:
            self._text(x+pw/2,y+ph*.55,'No tasks here yet ♡',15,colors[i],True)
        for j,task in enumerate(page):
            yy=start_y+j*row_height
            rx1,ry1,rx2,ry2=x+13,yy,x+pw-13,yy+48
            tag=f'task_{task.id}'
            self.canvas.create_rectangle(rx1,ry1,rx2,ry2,fill='#fffaf5',outline='#ffffff',
                                         width=2,tags=(tag,))
            completed=task.completed
            cbx=x+25; cby=yy+15
            tick=f'check_{task.id}'
            self.canvas.create_rectangle(cbx,cby,cbx+16,cby+16,
                                         fill='#c3b6c7' if completed else '#ffffff',
                                         outline=colors[i],width=2,tags=(tick,))
            if completed:
                self._text(cbx+8,cby+8,'✓',13,'#ffffff',True,tags=(tick,))

            max_title=max(12,int((pw-262)//10))
            title=task.title if len(task.title)<=max_title else task.title[:max_title-1]+'…'
            self._text(x+55,yy+16,title,13,'#a3a0a4' if completed else INK,True,'w',(tag,))
            due_text=task.due.strftime('%b %d, %I:%M %p')
            meta=f'{task.subject or "General"}  ·  {due_text}'
            now=datetime.now()
            if task.due < now and not completed:
                meta='OVERDUE  ·  '+meta
            elif task.due.date()==now.date() and not completed:
                meta='TODAY  ·  '+meta
            self._text(x+55,yy+37,meta[:max(12,int((pw-235)//7))],10,
                       '#bb5465' if ('OVERDUE' in meta or 'TODAY' in meta) else '#877992',
                       False,'w',(tag,))

            self._small_task_button(x+pw-137, yy+9, 'EDIT', PURPLE,
                                    lambda task_id=task.id: self.open_task_form(task_id=task_id))
            self._small_task_button(x+pw-79, yy+9, 'DELETE', RED,
                                    lambda task_id=task.id: self.delete_task(task_id))
            self.canvas.tag_bind(tick, '<Button-1>',
                                 lambda e, task_id=task.id: self.toggle_completed(task_id))
            self.canvas.tag_bind(tick, '<Enter>', lambda e: self.canvas.config(cursor='hand2'))
            self.canvas.tag_bind(tick, '<Leave>', lambda e: self.canvas.config(cursor=''))
        if max_scroll:
            self._text(x+pw/2,y+ph-18,
                       f'▲  {self.scrolls[i]+1}-{self.scrolls[i]+len(page)} of {len(tasks)}  ▼   (scroll here)',
                       11,colors[i],True)
            up=f'up_{i}'; down=f'down_{i}'
            self.canvas.create_rectangle(x+pw/2-160,y+ph-29,x+pw/2-100,y+ph-5,
                                         fill='',outline='',tags=(up,))
            self.canvas.create_rectangle(x+pw/2+80,y+ph-29,x+pw/2+162,y+ph-5,
                                         fill='',outline='',tags=(down,))
            self.canvas.tag_bind(up,'<Button-1>',lambda e,i=i:self._scroll_quadrant(i,-1))
            self.canvas.tag_bind(down,'<Button-1>',lambda e,i=i:self._scroll_quadrant(i,1))

    def _scroll_quadrant(self,i,change):
        w,h=self._wh()
        _,_,_,ph=self._panel_geoms(w,h)[i]
        count=len(self.store.filtered_sorted(i))
        visible=max(2,int((ph-85)//54))
        self.scrolls[i]=min(max(0,count-visible),max(0,self.scrolls[i]+change))
        self.render()

    def toggle_completed(self,task_id):
        task=self.store.get(task_id)
        if task:
            self.store.edit(task_id,completed=not task.completed)
            self.render()

    def delete_task(self,task_id):
        task=self.store.get(task_id)
        if task and messagebox.askyesno('Delete reminder?',
                f'Delete "{task.title}"?\n\nYou can restore it using UNDO.',parent=self):
            self.store.remove(task_id)
            self.render()

    def undo(self):
        if self.store.undo_last():
            self.render()
        else:
            messagebox.showinfo('Undo', 'No recent task changes to undo.',parent=self)

    def open_task_form(self,task_id=None,default_quadrant=None):
        existing=self.store.get(task_id) if task_id else None
        dlg=tk.Toplevel(self)
        dlg.title('Edit reminder' if existing else 'New reminder')
        dlg.configure(bg='#fff3f9')
        dlg.geometry('490x536+%d+%d' % (self.winfo_rootx() + max(0, (self.winfo_width()-490)//2),
                                          self.winfo_rooty() + max(0, (self.winfo_height()-536)//2)))
        dlg.resizable(False,False)
        dlg.transient(self)
        dlg.grab_set()
        pane=tk.Frame(dlg,bg='#fff3f9',padx=28,pady=20)
        pane.pack(fill='both',expand=True)
        tk.Label(pane,text='✿ EDIT REMINDER' if existing else '✿ NEW REMINDER',font=font(20,True),
                 fg='#d93171',bg='#fff3f9').pack(anchor='w',pady=(0,13))

        def entry_row(label,value=''):
            tk.Label(pane,text=label,font=font(12,True),fg=INK,bg='#fff3f9').pack(anchor='w',pady=(5,3))
            v=tk.StringVar(value=value)
            en=tk.Entry(pane,textvariable=v,bg='#fffefa',fg=INK,font=font(13),
                         relief='solid',bd=1,highlightcolor='#ec5f91',highlightthickness=1)
            en.pack(fill='x',ipady=7)
            return v,en

        title_var,title_entry=entry_row('TASK NAME *',existing.title if existing else '')
        subject_var,_=entry_row('SUBJECT (e.g. Differential Equations)',
                                existing.subject if existing else '')
        date_frame=tk.Frame(pane,bg='#fff3f9');date_frame.pack(fill='x',pady=(9,2))
        tk.Label(date_frame,text='DUE DATE',font=font(12,True),fg=INK,bg='#fff3f9').pack(side='left')
        date_var=tk.StringVar(value=existing.due.strftime('%Y-%m-%d') if existing else
                              datetime.now().strftime('%Y-%m-%d'))
        de=tk.Entry(pane,textvariable=date_var,bg='#fffefa',fg=INK,font=font(13),
                    relief='solid',bd=1)
        de.pack(fill='x',ipady=6)
        tk.Button(date_frame,text='PICK DATE  ▦',bg='#ffdeec',fg='#8f3664',
                  font=font(11,True),relief='flat',cursor='hand2',
                  command=lambda:self._calendar_picker(dlg,date_var)).pack(side='right')
        hour_label=tk.Frame(pane,bg='#fff3f9');hour_label.pack(fill='x',pady=(13,3))
        tk.Label(hour_label,text='DUE TIME (24-HOUR)',font=font(12,True),fg=INK,
                 bg='#fff3f9').pack(anchor='w')
        tim=existing.due if existing else (datetime.now()+timedelta(hours=1))
        clock=tk.Frame(pane,bg='#fff3f9');clock.pack(anchor='w')
        hour=tk.StringVar(value=f'{tim.hour:02d}')
        minute=tk.StringVar(value=f'{tim.minute:02d}')
        hh=ttk.Combobox(clock,textvariable=hour,values=[f'{i:02d}' for i in range(24)],
                        font=font(12),width=5,state='readonly')
        hh.pack(side='left')
        tk.Label(clock,text=' : ',font=font(15,True),bg='#fff3f9',fg=INK).pack(side='left')
        mm=ttk.Combobox(clock,textvariable=minute,values=[f'{i:02d}' for i in range(60)],
                        font=font(12),width=5,state='readonly')
        mm.pack(side='left')
        urgent_val=existing.urgent if existing else default_quadrant in (0,2)
        important_val=existing.important if existing else default_quadrant in (0,1)
        urgent=tk.BooleanVar(value=urgent_val)
        important=tk.BooleanVar(value=important_val)
        tk.Label(pane,text='PRIORITY',font=font(12,True),fg=INK,bg='#fff3f9').pack(anchor='w',pady=(14,5))
        tk.Checkbutton(pane,text='Urgent',variable=urgent,bg='#fff3f9',fg='#9b3154',
                       activebackground='#fff3f9',font=font(13,True),selectcolor='#fff2f7').pack(anchor='w')
        tk.Checkbutton(pane,text='Important',variable=important,bg='#fff3f9',fg='#9b3154',
                       activebackground='#fff3f9',font=font(13,True),selectcolor='#fff2f7').pack(anchor='w')
        buttons=tk.Frame(pane,bg='#fff3f9');buttons.pack(fill='x',pady=(15,0))
        def do_save():
            title=title_var.get().strip()
            if not title:
                messagebox.showwarning('Missing title','Please enter a task name.',parent=dlg)
                return
            try:
                due=datetime.strptime(f'{date_var.get()} {hour.get()}:{minute.get()}',
                                      '%Y-%m-%d %H:%M')
            except ValueError:
                messagebox.showerror('Invalid date/time',
                                     'Choose a valid date and time (YYYY-MM-DD).',parent=dlg)
                return
            attrs=dict(title=title,subject=subject_var.get().strip(),
                       due_at=due.strftime('%Y-%m-%d %H:%M'),
                       urgent=urgent.get(),important=important.get())
            if existing:
                self.store.edit(existing.id,**attrs)
            else:
                self.store.add(Task(**attrs))
            dlg.destroy()
            self.render()
        tk.Button(buttons,text='SAVE REMINDER',command=do_save,bg=RED,fg='white',
                  activebackground='#ff7fa5',font=font(13,True),relief='flat',cursor='hand2',
                  padx=20,pady=9).pack(side='left')
        tk.Button(buttons,text='CANCEL',command=dlg.destroy,bg='#d9c2db',fg=INK,
                  font=font(12,True),relief='flat',padx=14,pady=9).pack(side='right')
        title_entry.focus_set()
        dlg.bind('<Return>',lambda e:do_save() if e.widget not in (hh,mm) else None)

    def _calendar_picker(self,parent,value):
        try:
            selected=datetime.strptime(value.get(),'%Y-%m-%d')
        except ValueError:
            selected=datetime.now()
        pop=tk.Toplevel(parent)
        pop.title('Choose a date')
        pop.configure(bg='#fff5f9')
        pop.geometry('310x335')
        pop.transient(parent)
        pop.geometry('310x335+%d+%d' % (parent.winfo_rootx()+90, parent.winfo_rooty()+100))
        parent.grab_release()
        pop.grab_set()
        def close_picker():
            pop.grab_release()
            pop.destroy()
            if parent.winfo_exists():
                parent.grab_set()
        pop.protocol('WM_DELETE_WINDOW', close_picker)
        year,month=selected.year,selected.month
        outer=tk.Frame(pop,bg='#fff5f9',padx=12,pady=12)
        outer.pack(fill='both',expand=True)
        def redraw():
            for child in outer.winfo_children(): child.destroy()
            nav=tk.Frame(outer,bg='#fff5f9');nav.pack(fill='x')
            def shift(by):
                nonlocal year,month
                month+=by
                if month<1: month=12;year-=1
                if month>12: month=1;year+=1
                redraw()
            tk.Button(nav,text='◀',command=lambda:shift(-1),relief='flat',
                      bg='#f9d2e4').pack(side='left')
            tk.Label(nav,text=f'{calendar.month_name[month]} {year}',fg=INK,bg='#fff5f9',
                     font=font(13,True)).pack(side='left',expand=True)
            tk.Button(nav,text='▶',command=lambda:shift(1),relief='flat',
                      bg='#f9d2e4').pack(side='right')
            grid=tk.Frame(outer,bg='#fff5f9');grid.pack(pady=12)
            for col,wd in enumerate(('Mo','Tu','We','Th','Fr','Sa','Su')):
                tk.Label(grid,text=wd,width=4,bg='#fff5f9',fg=PURPLE,
                         font=font(10,True)).grid(row=0,column=col,pady=2)
            weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(year,month)
            for row,week in enumerate(weeks,1):
                for col,day in enumerate(week):
                    if day:
                        def choose(day=day):
                            value.set(f'{year:04d}-{month:02d}-{day:02d}')
                            close_picker()
                        tk.Button(grid,text=str(day),width=3,font=font(11),relief='flat',
                                  bg='#fce2ee' if day==selected.day and month==selected.month
                                     and year==selected.year else '#fffafd',
                                  command=choose).grid(row=row,column=col,padx=1,pady=2)
        redraw()


    def _draw_pomodoro(self,w,h):
        bg=fit_pixel(self._backgrounds['night'],(w,h)).convert('RGBA')
        art=Image.new('RGBA',(w,h),(0,0,0,0))
        d=ImageDraw.Draw(art,'RGBA')
        panel_w=min(665,w-200)
        x1=(w-panel_w)/2
        d.rounded_rectangle((int(x1),int(h*.19),int(w-x1),int(h*.84)),
                            radius=40,fill=(41,20,101,175),outline=(255,230,255,215),width=3)
        self._use_bg(Image.alpha_composite(bg,art).convert('RGB'))
        self._text(34,42,'✦ PIXELSTUDY',21,WHITE,True,'w')
        self._pixel_button(w-172,22,143,49,'← BACK',lambda:self.set_page('menu'),PURPLE,13)
        self._text(w/2,h*.29,f'ROUND {self.timer.round_number} / 4',
                   17,'#ffeaf7',True)
        self.timer_id=self._text(w/2,h*.46,self.timer.formatted,83,'#fff4fe',True)
        bx=w/2-190
        btn_y=h*.60
        self._pixel_button(bx,btn_y,192,65,
                           'PAUSE' if self.timer.running else 'START',
                           self.toggle_timer,RED,19)
        self._pixel_button(bx+211,btn_y,174,65,'RESET',self.reset_timer,PURPLE,19)
        current=(self.timer.total_focus%4)
        for i in range(4):
            cx=w/2-63+42*i
            self.canvas.create_oval(cx-11,h*.735-11,cx+11,h*.735+11,
                                    fill='#ff73b3' if i<current else '#dfcee7',
                                    outline='#fff1f7',width=2)

    def toggle_timer(self):
        if self.timer.running:
            self.timer.pause()
        else:
            self.timer.start()
        self.render()

    def reset_timer(self):
        if messagebox.askyesno('Reset Pomodoro?',
                               'Restart the Pomodoro rounds from 25:00?',parent=self):
            self.timer.reset()
            self.render()

    def _show_toast(self, text, duration=3600):

        if self.page not in ('pomodoro','reminders'):
            return
        w,_=self._wh()
        self.canvas.delete('toast')
        self.canvas.create_rectangle(w-455,88,w-20,135,fill='#fff2f9',
                                     outline='#ff87b6',width=3,tags=('toast',))
        self._text(w-237,110,text[:46],12,'#963f72',True,tags=('toast',))
        self.after(duration,lambda:self.canvas.delete('toast') if self.winfo_exists() else None)
        try:self.bell()
        except tk.TclError:pass


    def _tick(self):
        if not self.winfo_exists():
            return
        if self.page == 'welcome' and self._gif_frames:
            now=time.monotonic()
            if now-self._frame_at>=1/6:
                self._frame_at=now
                self._frame_index=(self._frame_index+1)%len(self._gif_frames)
                w,h=self._wh()
                pic=ImageTk.PhotoImage(self._welcome_bg(w,h))
                if self._photos:
                    self._photos[0] = pic
                else:
                    self._photos.append(pic)
                if self.bg_item:
                    self.canvas.itemconfigure(self.bg_item,image=pic)
        transition=self.timer.update()
        if transition:
            if self.page=='pomodoro':
                self.render()
                self._show_toast(('Break time! ♡' if transition!='focus'
                                  else 'Break over, focus time! ✦'))
        elif self.page=='pomodoro' and self.timer_id:
            self.canvas.itemconfigure(self.timer_id,text=self.timer.formatted)
        if int(time.time())%12==0 and not getattr(self,'_checked_this_second',False):
            self._checked_this_second=True
            self._check_reminders()
        elif int(time.time())%12!=0:
            self._checked_this_second=False
        self.after(180,self._tick)

    def _check_reminders(self):
        now=datetime.now()
        for task in self.store.tasks:
            if task.id in self._notified or task.completed:
                continue
            elapsed=(now-task.due).total_seconds()
            if 0<=elapsed<120:
                self.queue.enqueue(task)
                self._notified.add(task.id)
        if len(self.queue):
            next_task=self.queue.dequeue()
            self.bell()

            messagebox.showinfo('PixelStudy reminder 🌸',
                                f'{next_task.title}\n\nSubject: {next_task.subject or "General"}\nDue now!',
                                parent=self)
