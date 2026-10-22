"""Icone vetorial simples renderizado para o instalador do Chrome."""
from pathlib import Path
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parents[1]
for size in (192,512):
    image=Image.new('RGB',(size,size),'#10141b')
    d=ImageDraw.Draw(image)
    def box(values):return tuple(round(v*size/512) for v in values)
    d.rounded_rectangle(box((75,75,437,437)),radius=round(size*.14),fill='#263447')
    d.rounded_rectangle(box((136,145,376,307)),radius=round(size*.035),outline='#95e5be',width=max(3,round(size*.018)))
    d.line(box((256,307,256,348)),fill='#95e5be',width=max(3,round(size*.018)))
    d.rounded_rectangle(box((198,344,314,358)),radius=round(size*.01),fill='#95e5be')
    d.ellipse(box((317,320,363,366)),fill='#42d998')
    image.save(root/f'icon-{size}.png')
