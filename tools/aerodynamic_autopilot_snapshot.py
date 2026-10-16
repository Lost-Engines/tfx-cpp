"""Shared native fields for complete autopilot/automatic-landing captures."""
guide_fields=[0x14378,0x143c8,0x14390,0x143b0,0x143a8,0x14370,0x14388,0x143a0,0x14300,0x142f8,0x142f0,0x14340,0x14318,0x13d00,0x14398,0x14380]
recovery_fields=[(0x14962,'<H'),(0x1327a,'<H'),(0x1327c,'<H'),(0x1327e,'<H'),(0x13278,'<H'),(0x13270,'<Q'),(0x13269,'<B')]
def snapshot(image):
 return [image.read(f,'<Q')[0] for f in guide_fields]+[v&0xffffffff for f in (0x14920,0x1492c) for v in image.read(f,'<3i')]+[image.read(0x597c,'<H')[0],image.read(0x14938,'<H')[0]]+[image.read(f,fmt)[0] for f,fmt in recovery_fields]+[int(image.read(0x1347b,'<B')[0]==255)]
