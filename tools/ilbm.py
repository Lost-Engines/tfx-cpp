"""Small independent IFF/ByteRun128 reader for screenshot verification."""
import struct

def decode_ilbm(source):
 assert source[:4]==b'FORM'and source[8:12]==b'ILBM','not an ILBM'
 assert struct.unpack_from('>I',source,4)[0]+8==len(source),'incorrect FORM length'
 chunks={};position=12
 while position<len(source):
  name=source[position:position+4];size,=struct.unpack_from('>I',source,position+4)
  chunks[name]=source[position+8:position+8+size];position+=8+size+(size&1)
 width,height,_,_,planes,masking,compression=struct.unpack_from('>HHhhBBB',chunks[b'BMHD'])
 assert planes==8 and masking==0 and compression==1,'unsupported ILBM layout'
 body=chunks[b'BODY'];position=0;stride=((width+15)//16)*2;pixels=bytearray(width*height)
 for y in range(height):
  for plane in range(planes):
   row=bytearray()
   while len(row)<stride:
    count=body[position];position+=1
    if count<=127:row+=body[position:position+count+1];position+=count+1
    elif count>=129:row+=bytes([body[position]])*(257-count);position+=1
   assert len(row)==stride,'packet crossed a plane row'
   for x in range(width):pixels[y*width+x]|=((row[x//8]>>(7-x%8))&1)<<plane
 assert position==len(body),'trailing BODY bytes'
 return (width,height),bytes(pixels),chunks[b'CMAP']
