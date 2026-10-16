"""Caller setup for complete original aerodynamic initialization captures."""
import struct

def initialise_reference(im,row,baseline):
    craft,model,landed,cold,terrain,boost,terrain_boost,gear,slot,weapon,occupied,low,high,height,speed=row[:15];position=row[15:18];frame=row[18:27];temperature,celsius=row[27:]
    im.cpu.mem_write(im.data,baseline)
    for field,value,fmt in ((0x11b2a,craft-1,'<H'),(0x1347a,(1,6,0,2)[model],'<B'),(0x8d3a,landed,'<H'),(0x1347c,cold,'<B'),(0xabea,terrain,'<B'),(0xe774,128 if boost else 0,'<B'),(0xe762,terrain_boost,'<H'),(0xabf2,height,'<h'),(0x13444,speed,'<i')):im.write(field,fmt,value)
    im.write(0x8f30,'<B',temperature);im.write(0x14956,'<H',0);im.write(0x8c98,'<h',celsius)
    im.write(0x1345e,'<9h',*frame)
    for field,value in zip((0x1341c,0x13428,0x13434),position):im.write(field,'<I',value)
    for field,value in zip((0x13424,0x13430,0x1343c),position):im.write(field,'<i',int(struct.unpack('<f',struct.pack('<I',value))[0]))
    im.cpu.mem_write(0x300000,struct.pack('<9h',*frame))
    for function,field in ((0xcd574,0x86c8),(0xcd5a8,0x86ca),(0xcd5c4,0x86cc)):im.write(field,'<H',im.call(function,eax=0x300000)&65535)
    im.cpu.mem_write(0x300000,struct.pack('<9h',*frame));heading=im.call(0xcd5a8,eax=0x300000)&65535;im.write(0x86ca,'<H',heading)
    for i in range(12):im.write(0x7d70+i,'<B',gear if i==10 else 2)
    im.cpu.mem_write(im.data+0x13374,bytes(20));im.write(0x13374+slot*2,'<2B',weapon,occupied)
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high))
    im.call(0x95f3c,limit=2000000)
