pro cpiimage, state, x, y, select

; finds the image that has been selected and creates a png image
   finfo = {day: 0B, hour: 0B, minute: 0B, second: 0B, msecond: 0U, $
      totx: 0, toty: 0, startx:0, starty:0, badcount: 0, indata: 0, filepos: 0L, startpos:0L, len: 0.0, $
      wid: 0.0, area: 0.0, per: 0.0}
   savelabel = ""
   finfo.badcount = 0
   foundimage = 0
   savex = 0
   savey = 0
   levelmaxy = 0
   numimages = 0
   fullscreen = 0
   finfo.indata = state.indata
   if state.screen(state.screennum) ne 0 then $
      point_lun, state.indata, state.screen(state.screennum)
   wset, state.displaywin
   while foundimage eq 0 and fullscreen eq 0 and $
         not eof(state.indata) and (finfo.badcount lt 500) do begin
      cpiread, finfo
      if numimages eq 0 then begin
         firstsecyear = secondsInYear(state.year, state.month, $
            finfo.day, finfo.hour, finfo.minute, finfo.second)
      endif
      numimages = numimages + 1
      secyear = secondsInYear(state.year, state.month, $
         finfo.day, finfo.hour, finfo.minute, finfo.second)
      if secyear gt (firstsecyear + 1) then begin
         fullscreen = 1
      endif else begin
         savelabel = string(format= '(I2.2, I2.2, I2.2, I3.3)', $
            finfo.hour, finfo.minute, finfo.second, finfo.msecond)
         savet = string(format= '(I2.2, ":", I2.2, ":", I2.2, ".", I3.3)', $
            finfo.hour, finfo.minute, finfo.second, finfo.msecond)
      endelse
      if finfo.totx gt state.winx then checkx = state.winx else checkx = finfo.totx
      if (savex + checkx) gt state.winx then begin
         savey = savey + levelmaxy + 1
         savex = 0
         levelmaxy = 0
      endif
      if (finfo.toty gt levelmaxy) then levelmaxy = finfo.toty
      roidata = bytarr(finfo.totx, finfo.toty)
      readu, state.indata, roidata
      if (x ge savex) and (x le savex + checkx + 1) and $
            (y ge savey) and (y le (savey + finfo.toty + 1)) then begin
         foundimage = 1
         if select eq 1 then begin
            image = string(format='(I3.3, ".png")', numimages)
            filename = state.pngdir + savelabel + image
            state.pngfile = savelabel + image
            write_png, filename, tvrd(savex,savey,finfo.totx,finfo.toty)
         endif else if select eq 4 then begin
            state.len = finfo.totx * 2.3
            state.wid = finfo.toty * 2.3
            state.timel = savet
         endif
      endif 
      savex = savex + checkx + 1 
   end
end
