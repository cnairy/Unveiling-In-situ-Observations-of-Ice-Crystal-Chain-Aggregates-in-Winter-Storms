pro cpiread, finfo

   on_ioerror, ioerr
; read until an roi image is found, then return
   B = {BLOCKTYPE, hdrblk:0U}
   C = {IMAGEBLK, blksize:0UL, version:0U, numrois:0U, tot:0UL,  $
      day:0B, hour:0B, minute:0B, second:0B, msecond:0U,  $
      type:0U, startx:0U, starty:0U, endx:0U, endy:0U, $
      info:bytarr(74)} 
   H = {HOUSEKEEPING, blksize:0UL, version:0U, info:bytarr(98)} 
   H2 = {HOUSEKEEPING2, blksize:0UL, version:0U, info:bytarr(172)} 
   R = {ROIIMAGE, blksize:0UL, version:0U, startx:0U, starty:0U,  $
      endx:0U, endy:0U, pixbytes:0, flags:0U, length:0.0, $
      startlen:0UL, endlen:0UL, width:0.0, startwidth:0UL, $
      endwidth:0UL, roidepth:0U, area:0.0, perimeter:0.0}
   done = 0
   
   ;Save the start position for collage mode
   point_lun, -finfo.indata, startpos
   finfo.startpos=startpos
   
   while done eq 0 do begin
      readu, finfo.indata, B

      case B.hdrblk of 
; Image Block
         'A3D5'XU:  BEGIN 
            finfo.badcount = 0 
            point_lun, -finfo.indata, filepos
            finfo.filepos = filepos - 2
            readu, finfo.indata, C
         END
; Housekeeping
         'A1D7'XU: BEGIN
            finfo.badcount = 0
            readu, finfo.indata, H
         END
         'A1D9'XU: BEGIN
            finfo.badcount = 0
            readu, finfo.indata, H2
         END
; ROI Image
         'B2E6'XU: BEGIN
            done = 1
            finfo.badcount = 0
; only save if just read an image block
            if C.numrois ne 0 then begin 
               finfo.day = C.day
               finfo.hour = C.hour
               finfo.minute = C.minute
               finfo.second = C.second
               finfo.msecond = C.msecond
            endif
            readu, finfo.indata, R
            finfo.totx = R.endx - R.startx + 1
            finfo.toty = R.endy - R.starty + 1
            finfo.startx = R.startx
            finfo.starty = R.starty
         END
         else: finfo.badcount = finfo.badcount + 1
      endcase
   end
   goto, noerr
   ioerr: finfo.badcount = 500
   noerr:
end

