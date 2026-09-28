# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
"""Procedural, monochrome ornaments and patterns, drawn at printer resolution."""
import math
import random
from PIL import Image, ImageDraw

BORDERS = ['solid', 'double', 'dashed', 'dotted', 'stars', 'hearts', 'streamers']
PATTERNS = ['polka dots', 'stripes', 'checkerboard', 'grid', 'chevrons',
            'waves', 'stars', 'hearts', 'confetti', 'streamers']


def symbol(draw, kind, x, y, size):
    radius = size/2
    if kind == 'stars':
        points = []
        for i in range(10):
            angle = -math.pi/2+i*math.pi/5
            r = radius if i%2 == 0 else radius*.44
            points.append((x+math.cos(angle)*r,y+math.sin(angle)*r))
        draw.polygon(points,fill=0)
    elif kind == 'hearts':
        points = []
        for i in range(64):
            t = i*math.tau/64
            hx = 16*math.sin(t)**3
            hy = 13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)
            points.append((x+hx*size/32,y-(hy+2)*size/32))
        draw.polygon(points,fill=0)
    else:
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=0)


def pattern_image(size, kind, spacing=28, weight=2):
    if kind not in PATTERNS or not 12 <= spacing <= 64 or not 1 <= weight <= 5:
        raise ValueError('Invalid pattern, spacing or line weight')
    width,height = size
    image = Image.new('L',size,255)
    draw = ImageDraw.Draw(image)
    if kind in ('polka dots','stars','hearts','confetti'):
        rng = random.Random(20)  # Stable across preview, export and printing.
        for row,y in enumerate(range(spacing//2,height+spacing,spacing)):
            for x in range(spacing//2,width+spacing,spacing):
                x += spacing//2 if row%2 else 0
                if kind == 'confetti':
                    x += rng.randint(-spacing//4,spacing//4)
                    yj = y+rng.randint(-spacing//4,spacing//4)
                    angle = rng.random()*math.tau
                    r = spacing*.14
                    draw.line((x-r*math.cos(angle),yj-r*math.sin(angle),
                               x+r*math.cos(angle),yj+r*math.sin(angle)),fill=0,width=weight+1)
                else:
                    symbol(draw,kind,x,y,spacing*(.18 if kind=='polka dots' else .5))
    elif kind == 'checkerboard':
        for y in range(0,height,spacing):
            for x in range(0,width,spacing):
                if (x//spacing+y//spacing)%2==0:
                    draw.rectangle((x,y,x+spacing-1,y+spacing-1),fill=0)
    elif kind == 'grid':
        for x in range(0,width,spacing): draw.line((x,0,x,height),fill=0,width=weight)
        for y in range(0,height,spacing): draw.line((0,y,width,y),fill=0,width=weight)
    elif kind == 'stripes':
        for start in range(-height,width,spacing):
            draw.line((start,0,start+height,height),fill=0,width=weight)
    else:
        for base in range(-spacing,height+spacing,spacing):
            points = []
            for x in range(width):
                phase = x/spacing
                if kind == 'chevrons':
                    offset = (abs((phase%2)-1)-.5)*spacing*.65
                else:
                    offset = math.sin(phase*math.tau)*spacing*.2
                points.append((x,base+offset))
            draw.line(points,fill=0,width=weight)
            if kind == 'streamers':
                draw.line([(x,y+spacing*.16) for x,y in points],fill=0,width=weight)
    return image


def border_padding(kind, size):
    return 0 if kind=='solid' else (6 if kind in ('double','dashed','dotted') else size+6)


def draw_border(image, shape, margin, kind, size):
    if kind not in BORDERS or not 8 <= size <= 24:
        raise ValueError('Invalid border style or ornament size')
    width,height = image.size
    draw = ImageDraw.Draw(image)
    edge = max(0,(width-384)//2)
    left,top,right,bottom = edge+margin,margin,width-edge-margin-1,height-margin-1
    if kind in ('solid','double'):
        for inset in ([0,5] if kind=='double' else [0]):
            box=(left+inset,top+inset,right-inset,bottom-inset)
            if shape=='round':
                box=(margin+inset,margin+inset,width-margin-inset-1,height-margin-inset-1)
                draw.ellipse(box,outline=0,width=2)
            else: draw.rectangle(box,outline=0,width=2)
        return
    ornament = kind in ('stars','hearts','streamers')
    inset = size/2 if ornament else 1
    left,top,right,bottom=left+inset,top+inset,right-inset,bottom-inset
    if shape=='round':
        radius = (width-1)/2-margin-inset
        length = math.tau*radius
        def point(s):
            angle=s/radius
            return ((width-1)/2+radius*math.cos(angle),(height-1)/2+radius*math.sin(angle))
        def normal(s): return (math.cos(s/radius),math.sin(s/radius))
    else:
        w,h=right-left,bottom-top
        length=2*(w+h)
        def point(s):
            s %= length
            if s<w: return left+s,top
            if s<w+h: return right,top+s-w
            if s<2*w+h: return right-(s-w-h),bottom
            return left,bottom-(s-2*w-h)
        def normal(s):
            s %= length
            if s<w: return 0,-1
            if s<w+h: return 1,0
            if s<2*w+h: return 0,1
            return -1,0
    if kind=='streamers':
        periods=max(1,round(length/(size*2)))
        for phase in (0,math.pi):
            points=[]
            for s in range(math.ceil(length)+1):
                x,y=point(s)
                nx,ny=normal(s)
                offset=math.sin(s/length*math.tau*periods+phase)*size*.3
                points.append((x+nx*offset,y+ny*offset))
            draw.line(points,fill=0,width=2)
    elif kind=='dashed':
        for start in range(0,int(length),14):
            draw.line([point(s) for s in range(start,min(start+8,int(length))+1)],fill=0,width=2)
    else:
        spacing = size*1.6 if ornament else 8
        count=max(1,int(length/spacing))
        for i in range(count):
            x,y=point(i*length/count)
            symbol(draw,kind,x,y,size if ornament else 3)
