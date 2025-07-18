pro cpiopen, state

   A = {PIFILEHEADER, version:0U, year:0U, month:0U, imagex:0U,  $
      imagey:0U, info:bytarr(70)}
   if state.indata ne 0 then begin
      close, state.indata
      for i = 0, 999 do begin
         state.screen(i) = 0
      endfor
   endif
   on_ioerror, ioerr
   state.screennum = 0
   state.endfile = 0
   state.begfile = 1
 
   openr, indata, state.cpiFile, /get_lun, /swap_if_big_endian
   state.indata = indata
   readu, state.indata, A
; save file position 
   point_lun, -state.indata, filepos
   state.screen(state.screennum) = filepos
   state.year = A.year
   state.month = A.month
   state.imagex = A.imagex
   state.imagey = A.imagey
   goto, noerr
   ioerr: state.imagecnt = -1
   noerr:
end

