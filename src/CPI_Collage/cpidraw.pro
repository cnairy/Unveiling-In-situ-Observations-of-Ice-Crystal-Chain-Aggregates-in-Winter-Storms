pro cpidraw, state, new

   on_ioerror, ioerr
; display 2 seconds of images at one time
   finfo = {day: 0B, hour: 0B, minute: 0B, second: 0B, msecond: 0U, $
      totx: 0, toty: 0, startx:0, starty:0, badcount: 0, indata: 0, filepos: 0L, startpos:0L, len: 0.0, $
      wid: 0.0, area: 0.0, per: 0.0}
   fullscreen = 0
   savex = 0
   savey = 0
   levelmaxy = 0
   firstimage = 0
   state.imagecnt = 0
   savelabel = ""
   finfo.badcount = 0
; if just selected a new file, then open that file
   if new eq 1 then cpiopen, state
   if state.imagecnt eq -1 then return
   finfo.indata = state.indata
;print, state.screennum, state.screen(state.screennum)
; if have information on file positioning from an earlier read,
; then set file position
   if state.screen(state.screennum) ne 0 then $
      point_lun, state.indata, state.screen(state.screennum)
   wset, state.displaywin
   erase
; set fullscreen to 1 when all two seconds of data have been read
; badcount keeps track of how many reads in a row didn't have a good
; record type.  if > 500 read in a row, then assume the rest of the
; file is bad

;Make a frame and display it
backgroundcolor=0
IF state.collage eq 1 THEN BEGIN
   background = (bytarr(state.imagex+2,state.imagey+2)+150)
   background[1:state.imagex, 1:state.imagey] = backgroundcolor
   tv, background
ENDIF

   while fullscreen eq 0 and not eof(state.indata) and $
         (finfo.badcount lt 500) do begin
      cpiread, finfo
      if finfo.badcount eq 500 and firstimage eq 0 then begin
         state.imagecnt = -1
         return
      endif

      ;First image housekeeping
      if firstimage eq 0 then begin
         firstimage = 1
         state.begtime = string(format= $
            '(I2.2, ":", I2.2, ":", I2.2, ".", I3.3)',  $
            finfo.hour, finfo.minute, finfo.second, finfo.msecond)
         firstsecyear = secondsInYear(state.year, state.month, $
            finfo.day, finfo.hour, finfo.minute, finfo.second)
         state.cpiDate = string(format= $
            '(I2.2, "/", I2.2, "/", I4.4)', $
            state.month, finfo.day, state.year)
         firstmillisec = finfo.second + finfo.msecond
      endif

      secyear = secondsInYear(state.year, state.month, $
         finfo.day, finfo.hour, finfo.minute, finfo.second)
      millisec = finfo.second + finfo.msecond

      ;Check if over time, 2 seconds for normal, any time change for collage mode
      overtime=0
      if (secyear gt (firstsecyear + 1)) and (state.collage eq 0) then overtime=1
      if (millisec ne firstmillisec) and (state.collage eq 1) then overtime=1
;print,millisec  ;testing to make sure all particles are accounted for
      if overtime eq 1 then begin
         fullscreen = 1
         state.endtime = savelabel
         state.screenheight = savey + levelmaxy
      ;Otherwise display the image
      endif else begin
         savelabel = string(format= $
            '(I2.2, ":", I2.2, ":", I2.2, ".", I3.3)',  $
            finfo.hour, finfo.minute, finfo.second, finfo.msecond)
         if finfo.totx gt state.winx then checkx = state.winx else checkx = finfo.totx
         if (savex + checkx) gt state.winx then begin
            savey = savey + levelmaxy + 1
            savex = 0
            levelmaxy = 0
         endif
         if (finfo.toty gt levelmaxy) then levelmaxy = finfo.toty
         if (finfo.totx le 0 or finfo.toty le 0) then goto, ioerr
         roidata = bytarr(finfo.totx, finfo.toty)
         readu, state.indata, roidata

         ;Compute abparams and mask out background for display
         IF 1 eq 2 THEN BEGIN  ;This works, but looks kind of weird
            res=2.3
            dp=2
            contourlevel=0.6
            gradient=0
            ;ab=abparams2(roidata, dp=dp*res, res=res, contourlevel=contourlevel, gradient=gradient)
            ;Find indexes of particle inside bounding polygon
            IF ab.error eq 0 THEN BEGIN
               q=polyfillv(ab.x, ab.y, finfo.totx, finfo.toty)
               ;Make a new roi, removing background pixels
               roi2 = (roidata + backgroundcolor)/2   ;Copy and blend with background
               roi2[q] = roidata[q]
               roidata=roi2
            ENDIF
         ENDIF

         wset, state.displaywin
         IF state.collage eq 0 THEN tvscl, roidata, savex, savey
         IF state.collage eq 1 THEN tv, roidata, finfo.startx+1, finfo.starty+1  ;+1 is to account for the frame
         savex = savex + checkx + 1
      endelse
   end
   goto, noerr
   ioerr: finfo.badcount = 500
   noerr: if eof(state.indata) or finfo.badcount ge 500 then begin
      state.endfile = 1
      state.endtime = savelabel
   endif else begin
      state.endfile = 0
      state.screen(state.screennum+1) = finfo.startpos ;finfo.filepos  ;AB had to change this
   endelse
   if state.screennum eq 0 then state.begfile = 1 $
      else state.begfile = 0
end
